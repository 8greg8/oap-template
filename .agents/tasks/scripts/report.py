#!/usr/bin/env python3
"""Create executor reports and harvest their lessons into shared memory.

A report is written by the subagent that executed a task, on that task's branch.
``harvest`` collects the "Lessons learned" section from every report into
``.agents/LESSONS.md``, grouped by tag, so a future task hitting a similar
problem can find what was already learned.

Usage:
    python .agents/tasks/scripts/report.py new T-0004
    python .agents/tasks/scripts/report.py harvest
    python .agents/tasks/scripts/report.py lessons --tag geospatial
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _frontmatter import FrontmatterError
from _schema import (
    INTEGRATION_BRANCH,
    LESSONS_FILE,
    OUTCOMES,
    PLACEHOLDER,
    REPO_ROOT,
    REPORT_TEMPLATE,
    REQUIRED_REPORT_SECTIONS,
    TASKS_DIR,
    Report,
    Task,
    ValidationError,
    find_task,
    load_reports,
    load_tasks,
    paths_overlap,
)

logger = logging.getLogger("report")

UNTAGGED = "untagged"

#: Repository-discovery variables a git hook exports; they would override ``cwd``
#: and point the merge lookup at the wrong repository.
_GIT_ENV_TO_STRIP = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES",
)

#: The one form the independent-verify line takes in "## Tests run".
VERIFY_LINE_RE = re.compile(
    r"^Independent verify agent \(fresh context\) :: (?P<status>.+?)\s*$",
    re.MULTILINE,
)

#: A verify line names its commit as ``commit <hash>`` (7 to 40 hex digits).
VERIFY_COMMIT_RE = re.compile(r"\bcommit [0-9a-f]{7,40}\b")

#: A summary that calls the verify pending or not run contradicts the verify line.
STALE_SUMMARY_RE = re.compile(
    r"verif\w*[^.\n]*\b(pending|has not run)\b", re.IGNORECASE
)

#: The other stale-summary wording: acceptance met "except the independent verify".
STALE_SUMMARY_PHRASE = "except the independent verify"

TOUCHES_TICKED_RE = re.compile(
    r"^- \[[xX]\] No files changed outside the task's declared `touches` scope\.",
    re.MULTILINE,
)

GENERATED_HEADER = (
    "<!-- GENERATED FILE — do not edit by hand.\n"
    "     Regenerate with: python .agents/tasks/scripts/report.py harvest\n"
    "     The reports in .agents/tasks/reports/ are the source of truth. -->"
)


def current_branch() -> str:
    """Return the current git branch name.

    Returns:
        The branch name, or an empty string if git is unavailable or detached.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=TASKS_DIR,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def create_report(task_id: str, force: bool = False) -> Path:
    """Write a report skeleton for a task, prefilled from the task file.

    Args:
        task_id: Identifier such as ``T-0004``.
        force: Overwrite an existing report instead of refusing.

    Returns:
        Path of the created report.

    Raises:
        ValidationError: If the task does not exist, or a report already exists
            and ``force`` is not set.
    """
    task = find_task(task_id)
    path = task.report_path
    if path.exists() and not force:
        raise ValidationError(f"{path.name} already exists; pass --force to overwrite")

    branch = current_branch() or task.branch
    text = REPORT_TEMPLATE.read_text(encoding="utf-8")
    for key, value in {
        "id": task.id,
        "title": task.title,
        "outcome": PLACEHOLDER,
        "branch": branch,
        "commit": PLACEHOLDER,
        "tags": "",
    }.items():
        text = text.replace("{" + key + "}", value)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _git_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in _GIT_ENV_TO_STRIP}


def merge_commit_for(task_id: str, repo_root: Path) -> str | None:
    """Find the merge commit whose subject names a task.

    Args:
        task_id: Identifier such as ``T-0004``.
        repo_root: Repository to search (history reachable from ``HEAD``).

    Returns:
        The newest matching commit hash, or ``None`` when there is none.
    """
    number = task_id.strip().upper().removeprefix("T-")
    subject = f"chore(merge): merge task {number} into {INTEGRATION_BRANCH}"
    try:
        result = subprocess.run(
            ["git", "log", "--format=%H %s", "--fixed-strings", f"--grep={subject}"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_root,
            env=_git_env(),
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    for line in result.stdout.splitlines():
        commit, _, found = line.partition(" ")
        if found == subject:
            return commit
    return None


def _outside_touches(files: list[str], task: Task) -> list[str]:
    allowed = [*task.touches, f".agents/tasks/reports/{task.id}.md"]
    task_file_prefix = f".agents/tasks/{task.id}-"
    return [
        name
        for name in files
        if not (
            any(paths_overlap(name, entry) for entry in allowed)
            or (
                name.startswith(task_file_prefix)
                and name.endswith(".md")
                and "/" not in name.removeprefix(".agents/tasks/")
            )
        )
    ]


def validate_done_rules(
    report: Report, task: Task, repo_root: Path = REPO_ROOT
) -> list[str]:
    """Apply the verify and touches rules to a ``done`` task's report.

    Args:
        report: The parsed report.
        task: The task the report belongs to.
        repo_root: Repository searched for the task's merge commit.

    Returns:
        Problems found; empty when the task is not done or is compliant.
    """
    if task.status != "done":
        return []
    problems: list[str] = []

    match = VERIFY_LINE_RE.search(report.section_text("Tests run"))
    if not match:
        problems.append(
            "done task has no 'Independent verify agent (fresh context) :: <status>' "
            "line in '## Tests run'"
        )
    else:
        status = match.group("status").lower()
        if not status.startswith("passed"):
            problems.append(
                f"independent verify is recorded as {match.group('status')!r}; "
                "a done task needs a verify status that starts with 'passed'"
            )
        elif not (VERIFY_COMMIT_RE.search(match.group("status"))):
            problems.append(
                "independent verify line names no commit; record it as "
                "'passed (commit <hash>; ...)' with the commit the verify checked"
            )

    summary = report.section_text("Summary")
    if STALE_SUMMARY_RE.search(summary) or STALE_SUMMARY_PHRASE in summary.lower():
        problems.append(
            "'## Summary' calls the independent verify pending, not run or "
            "excepted; state the outcome only in the verify line"
        )

    if TOUCHES_TICKED_RE.search(report.section_text("Safety confirmations")):
        commit = merge_commit_for(task.id, repo_root)
        if commit is None:
            logger.info("%s: no merge commit yet; touches check skipped", task.id)
        else:
            try:
                diff = subprocess.run(
                    ["git", "diff", "--name-only", f"{commit}^1", commit],
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=repo_root,
                    env=_git_env(),
                )
            except (OSError, subprocess.CalledProcessError) as exc:
                problems.append(f"could not diff merge commit {commit[:12]}: {exc}")
            else:
                outside = _outside_touches(diff.stdout.split(), task)
                if outside:
                    problems.append(
                        "touches box is ticked but merge "
                        f"{commit[:12]} changed files outside touches: "
                        + ", ".join(outside)
                    )
    return problems


def validate_report(
    report: Report, task: Task | None = None, repo_root: Path = REPO_ROOT
) -> list[str]:
    """Check a report for missing sections, placeholders and false claims.

    Args:
        report: The parsed report.
        task: The report's task; when given, the done-task rules also run.
        repo_root: Repository used by the touches check.

    Returns:
        A list of human-readable problems; empty means the report is complete.
    """
    problems: list[str] = []
    if report.outcome not in OUTCOMES:
        problems.append(f"outcome {report.outcome!r} not in {list(OUTCOMES)}")
    if not report.task_id:
        problems.append("missing 'task' frontmatter key")
    for heading in REQUIRED_REPORT_SECTIONS:
        text = report.section_text(heading)
        if not text:
            problems.append(f"missing section '## {heading}'")
        elif PLACEHOLDER in text:
            problems.append(f"section '## {heading}' still contains a placeholder")
    if task is not None:
        problems += validate_done_rules(report, task, repo_root)
    return problems


def collect_lessons() -> dict[str, list[tuple]]:
    """Gather the lessons section from every report, each lesson once.

    A lesson is filed under the first tag its report declares. The remaining
    tags are kept on the entry so the tag index can still link to it.

    Returns:
        A mapping of first tag to a list of
        ``(task_id, outcome, text, stem, tags)`` tuples, where ``stem`` is the
        report's filename without ``.md`` and ``tags`` is every tag of the
        report. Reports with no lessons, or with an unfilled placeholder, are
        skipped.
    """
    grouped: dict[str, list[tuple]] = defaultdict(list)
    for report in load_reports():
        text = report.section_text("Lessons learned")
        if not text or PLACEHOLDER in text:
            continue
        tags = report.tags or [UNTAGGED]
        grouped[tags[0]].append(
            (report.task_id, report.outcome, text, report.path.stem, tags)
        )
    return grouped


def _lesson_anchor(stem: str, outcome: str) -> str:
    """Return the Markdown anchor of a lesson heading ``### <stem> (<outcome>)``."""
    return (
        f"{stem} ({outcome})".lower()
        .replace("(", "")
        .replace(")", "")
        .replace(" ", "-")
    )


def render_lessons(grouped: dict[str, list[tuple]]) -> str:
    """Render ``.agents/LESSONS.md`` from grouped lessons.

    Each lesson is written once, under its first tag. A tag index at the top
    links every tag to all the lessons that carry it.

    Args:
        grouped: Output of :func:`collect_lessons`.

    Returns:
        The complete Markdown text.
    """
    total = sum(len(entries) for entries in grouped.values())
    lines = [
        GENERATED_HEADER,
        "",
        "# Lessons Learned",
        "",
        "Harvested from task reports. Read the tags relevant to your task before",
        "starting — these are repo-specific traps that already cost someone time.",
        "",
        (
            f"{total} lesson(s) across {len(grouped)} section(s). "
            f"Generated {dt.datetime.now().astimezone().date().isoformat()}."
        ),
        "",
    ]

    if not grouped:
        lines += ["*No lessons recorded yet.*", ""]
        return "\n".join(lines)

    by_tag: dict[str, list[tuple]] = defaultdict(list)
    for entries in grouped.values():
        for entry in entries:
            for tag in entry[4]:
                by_tag[tag].append(entry)

    lines += [
        "## Tag index",
        "",
        "Each lesson appears once, under its first tag; the index links every tag",
        "to all lessons that carry it.",
        "",
    ]
    for tag in sorted(by_tag):
        links = ", ".join(
            f"[{stem}](#{_lesson_anchor(stem, outcome)})"
            for _task_id, outcome, _text, stem, _tags in sorted(by_tag[tag])
        )
        lines.append(f"- `{tag}` — {links}")
    lines.append("")

    for tag in sorted(grouped):
        lines += [f"## {tag}", ""]
        for _task_id, outcome, text, stem, tags in sorted(grouped[tag]):
            lines += [
                f"### {stem} ({outcome})",
                "",
                text,
                "",
                f"Tags: {', '.join(f'`{t}`' for t in tags)}",
                "",
                f"Source: [`reports/{stem}.md`](tasks/reports/{stem}.md)",
                "",
            ]

    return "\n".join(lines)


def harvest() -> Path:
    """Regenerate ``.agents/LESSONS.md`` from all reports.

    Returns:
        Path of the written lessons file.
    """
    grouped = collect_lessons()
    LESSONS_FILE.write_text(render_lessons(grouped), encoding="utf-8")
    total = sum(len(entries) for entries in grouped.values())
    logger.info("harvested %d lesson(s) into %s", total, LESSONS_FILE.name)
    return LESSONS_FILE


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Argument list; defaults to ``sys.argv[1:]``.

    Returns:
        The parsed :class:`argparse.Namespace`.
    """
    parser = argparse.ArgumentParser(
        prog="report.py", description="Create and harvest agent task reports."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="Create a report skeleton for a task.")
    new.add_argument("id", help="Task ID, e.g. T-0004.")
    new.add_argument(
        "--force", action="store_true", help="Overwrite an existing report."
    )

    sub.add_parser("harvest", help="Regenerate .agents/LESSONS.md from all reports.")

    lessons = sub.add_parser(
        "lessons", help="Print lessons, optionally filtered by tag."
    )
    lessons.add_argument("-t", "--tag", help="Only show lessons carrying this tag.")

    validate = sub.add_parser("validate", help="Check reports for missing sections.")
    validate.add_argument("id", nargs="?", help="Optional single task ID to check.")

    return parser.parse_args(argv)


def main(argv=None):
    """Entry point.

    Args:
        argv: Argument list; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)
    repo_root = TASKS_DIR.parent.parent

    try:
        if args.command == "new":
            print(create_report(args.id, force=args.force).relative_to(repo_root))
            return 0

        if args.command == "harvest":
            print(harvest().relative_to(repo_root))
            return 0

        if args.command == "lessons":
            entries = sorted(
                entry for group in collect_lessons().values() for entry in group
            )
            found = False
            for task_id, outcome, text, _stem, tags in entries:
                if args.tag and args.tag not in tags:
                    continue
                found = True
                label = args.tag or ", ".join(tags)
                print(f"--- {label} / {task_id} ({outcome}) ---\n{text}\n")
            if not found:
                print("(no matching lessons)")
            return 0

        if args.command == "validate":
            reports = load_reports()
            if args.id:
                wanted = args.id.strip().upper()
                reports = [r for r in reports if r.task_id.upper() == wanted]
                if not reports:
                    raise ValidationError(f"no report for {args.id}")
            tasks = {t.id.upper(): t for t in load_tasks()}
            problems = [
                f"{report.path.name}: {problem}"
                for report in reports
                for problem in validate_report(
                    report, tasks.get(report.task_id.upper())
                )
            ]
            if problems:
                for problem in problems:
                    print(f"INCOMPLETE {problem}", file=sys.stderr)
                return 1
            print(f"{len(reports)} report(s) complete.")
            return 0

    except (ValidationError, FrontmatterError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
