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
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _frontmatter import FrontmatterError
from _schema import (
    LESSONS_FILE,
    OUTCOMES,
    PLACEHOLDER,
    REPORT_TEMPLATE,
    REQUIRED_REPORT_SECTIONS,
    TASKS_DIR,
    Report,
    ValidationError,
    find_task,
    load_reports,
)

logger = logging.getLogger("report")

UNTAGGED = "untagged"

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


def validate_report(report: Report) -> list[str]:
    """Check a report for missing sections and unfilled placeholders.

    Args:
        report: The parsed report.

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
    return problems


def collect_lessons() -> dict[str, list[tuple]]:
    """Gather the lessons section from every report, grouped by tag.

    Returns:
        A mapping of tag to a list of ``(task_id, outcome, text)`` tuples.
        Reports with no lessons, or with an unfilled placeholder, are skipped.
    """
    grouped: dict[str, list[tuple]] = defaultdict(list)
    for report in load_reports():
        text = report.section_text("Lessons learned")
        if not text or PLACEHOLDER in text:
            continue
        for tag in report.tags or [UNTAGGED]:
            grouped[tag].append((report.task_id, report.outcome, text))
    return grouped


def render_lessons(grouped: dict[str, list[tuple]]) -> str:
    """Render ``.agents/LESSONS.md`` from grouped lessons.

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
            f"{total} entr(ies) across {len(grouped)} tag(s). "
            f"Generated {dt.datetime.now(tz=dt.timezone.utc).date().isoformat()}."
        ),
        "",
    ]

    if not grouped:
        lines += ["*No lessons recorded yet.*", ""]
        return "\n".join(lines)

    lines += ["## Tags", ""]
    for tag in sorted(grouped):
        anchor = tag.lower().replace(" ", "-")
        lines.append(f"- [`{tag}`](#{anchor}) — {len(grouped[tag])} entr(ies)")
    lines.append("")

    for tag in sorted(grouped):
        lines += [f"## {tag}", ""]
        for task_id, outcome, text in sorted(grouped[tag]):
            lines += [
                f"### {task_id} ({outcome})",
                "",
                text,
                "",
                f"Source: [`reports/{task_id}.md`](tasks/reports/{task_id}.md)",
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
            grouped = collect_lessons()
            tags = [args.tag] if args.tag else sorted(grouped)
            found = False
            for tag in tags:
                for task_id, outcome, text in grouped.get(tag, []):
                    found = True
                    print(f"--- {tag} / {task_id} ({outcome}) ---\n{text}\n")
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
            problems = [
                f"{report.path.name}: {problem}"
                for report in reports
                for problem in validate_report(report)
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
