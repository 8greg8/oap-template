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
import fnmatch
import logging
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _frontmatter import FrontmatterError, parse, read
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

#: The gate record a verify line may name: ``gate <record-key>`` is one
#: ``;``-separated part of the status. A gate record key is 40 or 64 lowercase hex
#: characters; the verify line may cite 12 to 64 of them.
VERIFY_GATE_RE = re.compile(r"gate [0-9a-f]{12,64}")

#: A part of the verify status that is ``gate`` alone, or starts with ``gate`` and a
#: space, claims to name a gate record, so it must match :data:`VERIFY_GATE_RE` exactly.
_VERIFY_GATE_CLAIM_RE = re.compile(r"gate(\s|$)")

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


def _verify_gate_problems(status: str) -> list[str]:
    """Check the optional ``gate <record-key>`` part of a passed verify status.

    The form is ``passed (commit <hash>; gate <record-key>; <counts>)``. The part is
    optional so reports written before it existed keep validating; when a part starts
    with ``gate`` and a space, its key must be 12 to 64 lowercase hex characters.

    Args:
        status: The text after ``::`` on the verify line.

    Returns:
        Problems found; empty when no ``gate`` part is present or it is well formed.
    """
    inner = status[status.find("(") + 1 :].rstrip(")") if "(" in status else ""
    return [
        f"verify line names a gate record {part!r} that is not 'gate <record-key>' "
        "with a record key of 12 to 64 lowercase hex characters"
        for part in (p.strip() for p in inner.split(";"))
        if _VERIFY_GATE_CLAIM_RE.match(part) and not VERIFY_GATE_RE.fullmatch(part)
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
        else:
            problems.extend(_verify_gate_problems(match.group("status")))

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


def _git_lines(args: list[str], repo_root: Path) -> list[str]:
    """Run a read-only git command; return its output lines, or none on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_root,
            env=_git_env(),
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    return result.stdout.splitlines()


def branch_report_text(
    task: Task, report_rel: str, repo_root: Path = REPO_ROOT
) -> tuple[str, str] | None:
    """Read a task's report from the task's own branch, via git.

    Looks at local branches (``refs/heads``) and ``origin/`` branches whose name
    matches ``*/<ID>-*``. Local branches are tried first, then ``origin/``, each
    in name order; the first that holds the report file wins.

    Args:
        task: The task whose report is wanted.
        report_rel: Repo-relative POSIX path of the report file.
        repo_root: Repository to search.

    Returns:
        ``(branch, text)`` for the first matching branch holding the report, or
        ``None`` when no matching branch has it (or git is unavailable).
    """
    pattern = f"*/{task.id.upper()}-*"
    refs = _git_lines(
        ["for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes/origin"],
        repo_root,
    )
    candidates = [
        (ref, ref.removeprefix("refs/heads/"), ref.removeprefix("refs/heads/"))
        for ref in sorted(r for r in refs if r.startswith("refs/heads/"))
    ] + [
        (
            ref,
            ref.removeprefix("refs/remotes/origin/"),
            ref.removeprefix("refs/remotes/"),
        )
        for ref in sorted(r for r in refs if r.startswith("refs/remotes/origin/"))
    ]
    for ref, name, display in candidates:
        if not fnmatch.fnmatchcase(name, pattern):
            continue
        try:
            shown = subprocess.run(
                ["git", "show", f"{ref}:{report_rel}"],
                capture_output=True,
                text=True,
                check=True,
                cwd=repo_root,
                env=_git_env(),
            )
        except (OSError, subprocess.CalledProcessError):
            continue
        return display, shown.stdout
    return None


def report_problems(
    task: Task, repo_root: Path = REPO_ROOT, target_status: str | None = None
) -> list[str]:
    """Check that a task has a complete report, as ``report.py validate`` would.

    Used by ``task.py set-status`` to gate transitions that require a report.
    The report is read from the working tree at ``task.report_path``; if that
    file is absent, from the task's branch via :func:`branch_report_text`. The
    content is checked with :func:`validate_report`, whichever source it came
    from. If neither source has it, the one problem ``validate`` cannot raise
    for a file it never loads is returned: the report does not exist.

    ``validate_report`` applies the verify and touches rules only to a task
    whose status is ``done``. With ``target_status`` set, they are evaluated
    for a copy of the task carrying that status, so a transition to ``done`` is
    judged as ``validate`` will judge the task once it is done. The rules
    themselves are unchanged. The touches rule needs the task's merge commit in
    ``repo_root``; it is skipped, as ``validate`` skips it, while there is none.

    Args:
        task: The task whose report is checked.
        repo_root: Repository used by the branch lookup and the touches check.
        target_status: Status the task is about to take; defaults to its own.

    Returns:
        A list of human-readable problems; empty means the report exists and
        validates.

    Raises:
        FrontmatterError: If the report's frontmatter cannot be parsed. The
            message names the file, or the branch and path, it came from.
    """
    path = task.report_path
    shown = path.relative_to(repo_root) if path.is_relative_to(repo_root) else path
    if path.is_file():
        meta, body = read(path)
        source = path
    else:
        found = branch_report_text(task, Path(shown).as_posix(), repo_root)
        if found is None:
            return [
                (
                    f"no report at {shown} or on a branch matching "
                    f"'*/{task.id}-*'; create it with `report.py new {task.id}`"
                )
            ]
        branch, text = found
        source = Path(f"{branch}:{Path(shown).as_posix()}")
        try:
            meta, body = parse(text)
        except FrontmatterError as exc:
            raise FrontmatterError(f"{source}: {exc}") from None
    report = Report(path=source, meta=meta, body=body)
    judged = task
    if target_status is not None and target_status != task.status:
        judged = Task(task.path, {**task.meta, "status": target_status}, task.body)
    label = source if source is not path else shown
    problems = [
        f"{label}: {problem}" for problem in validate_report(report, judged, repo_root)
    ]
    if report.task_id and report.task_id.upper() != task.id.upper():
        problems.append(
            f"{label}: 'task' frontmatter is {report.task_id!r}, not {task.id!r}"
        )
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
