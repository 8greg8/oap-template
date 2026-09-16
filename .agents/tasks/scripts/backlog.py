#!/usr/bin/env python3
"""Generate and query the task backlog index.

``BACKLOG.md`` is a derived artifact: it is regenerated from the task files and
must never be hand-edited. The task files are the source of truth.

Usage:
    python .agents/tasks/scripts/backlog.py reindex
    python .agents/tasks/scripts/backlog.py list --status open
    python .agents/tasks/scripts/backlog.py ready --parallel 3
    python .agents/tasks/scripts/backlog.py stats
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _frontmatter import FrontmatterError
from _schema import (
    BACKLOG_FILE,
    DONE_STATUSES,
    INACTIVE_STATUSES,
    PRIORITIES,
    REPORTS_DIR,
    STATUSES,
    TASKS_DIR,
    Task,
    load_tasks,
    tasks_conflict,
)

logger = logging.getLogger("backlog")

#: Sort weight for priority, highest first.
_PRIORITY_RANK = {name: index for index, name in enumerate(PRIORITIES)}

GENERATED_HEADER = (
    "<!-- GENERATED FILE — do not edit by hand.\n"
    "     Regenerate with: python .agents/tasks/scripts/backlog.py reindex\n"
    "     The task files in .agents/tasks/ are the source of truth. -->"
)


def sort_key(task: Task):
    """Ordering used throughout the backlog: priority first, then ID.

    Args:
        task: The task to rank.

    Returns:
        A tuple suitable for :func:`sorted`.
    """
    return (_PRIORITY_RANK.get(task.priority, len(PRIORITIES)), task.id)


def ready_tasks(tasks: Sequence[Task]) -> list[Task]:
    """Return tasks whose dependencies are all satisfied and that are not active.

    Args:
        tasks: All known tasks.

    Returns:
        Dispatchable tasks, ordered by priority then ID.
    """
    done = {task.id.upper() for task in tasks if task.status in DONE_STATUSES}
    candidates = [
        task
        for task in tasks
        if task.status not in INACTIVE_STATUSES
        and all(dependency.upper() in done for dependency in task.depends_on)
    ]
    return sorted(candidates, key=sort_key)


def parallel_batch(tasks: Sequence[Task], limit: int) -> list[Task]:
    """Select a set of ready tasks whose file scopes do not overlap.

    Greedy by priority: the highest-priority ready task is always taken, then
    each subsequent candidate is accepted only if its ``touches`` list is
    disjoint from every task already in the batch. This is what makes it safe to
    run the batch as parallel worktrees without creating merge conflicts.

    Args:
        tasks: Candidate tasks, typically the output of :func:`ready_tasks`.
        limit: Maximum batch size.

    Returns:
        A conflict-free batch of at most ``limit`` tasks.
    """
    batch: list[Task] = []
    for task in tasks:
        if len(batch) >= limit:
            break
        if any(tasks_conflict(task, chosen) for chosen in batch):
            continue
        batch.append(task)
    return batch


def render_backlog(tasks: Sequence[Task]) -> str:
    """Render the full ``BACKLOG.md`` document.

    Args:
        tasks: All known tasks.

    Returns:
        The complete Markdown text.
    """
    ordered = sorted(tasks, key=sort_key)
    counts = {status: 0 for status in STATUSES}
    for task in ordered:
        counts[task.status] = counts.get(task.status, 0) + 1

    lines = [
        GENERATED_HEADER,
        "",
        "# Task Backlog",
        "",
        f"{len(ordered)} task(s). Generated {dt.datetime.now(tz=dt.timezone.utc).date().isoformat()}.",
        "",
        "| "
        + " | ".join(f"{status}: {counts.get(status, 0)}" for status in STATUSES)
        + " |",
        "|" + "---|" * len(STATUSES),
        "",
        "## Tasks",
        "",
        "| ID | Title | Status | Prio | Type | Depends on | Report |",
        "|---|---|---|---|---|---|---|",
    ]

    for task in ordered:
        deps = ", ".join(task.depends_on) or "—"
        if task.report_path.exists():
            report = f"[report](reports/{task.id}.md)"
        else:
            report = "—"
        title = f"[{task.title}]({task.path.name})"
        lines.append(
            f"| {task.id} | {title} | {task.status} | {task.priority} | "
            f"{task.type} | {deps} | {report} |"
        )

    dispatchable = ready_tasks(ordered)
    lines += ["", "## Ready to dispatch", ""]
    if dispatchable:
        lines.append("Dependencies satisfied, not yet started:")
        lines.append("")
        for task in dispatchable:
            scope = ", ".join(f"`{item}`" for item in task.touches) or "*(unscoped)*"
            lines.append(f"- **{task.id}** {task.title} — {scope}")
        batch = parallel_batch(dispatchable, 3)
        lines += [
            "",
            "Suggested conflict-free parallel batch: "
            + ", ".join(task.id for task in batch),
        ]
    else:
        lines.append(
            "*Nothing ready — every open task is blocked or already in flight.*"
        )

    dispatchable_ids = {task.id for task in dispatchable}
    blocked = [
        task
        for task in ordered
        if task.status not in INACTIVE_STATUSES and task.id not in dispatchable_ids
    ]
    if blocked:
        lines += ["", "## Waiting on dependencies", ""]
        for task in blocked:
            lines.append(
                f"- **{task.id}** {task.title} — needs {', '.join(task.depends_on)}"
            )

    lines.append("")
    return "\n".join(lines)


def reindex() -> Path:
    """Regenerate ``BACKLOG.md`` from the task files.

    Returns:
        Path of the written backlog file.
    """
    tasks = load_tasks()
    BACKLOG_FILE.write_text(render_backlog(tasks), encoding="utf-8")
    logger.info("indexed %d task(s) into %s", len(tasks), BACKLOG_FILE.name)
    return BACKLOG_FILE


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Argument list; defaults to ``sys.argv[1:]``.

    Returns:
        The parsed :class:`argparse.Namespace`.
    """
    parser = argparse.ArgumentParser(
        prog="backlog.py", description="Generate and query the task backlog."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("reindex", help="Regenerate BACKLOG.md from the task files.")

    listing = sub.add_parser("list", help="List tasks as a plain table.")
    listing.add_argument(
        "-s", "--status", choices=list(STATUSES), help="Filter by status."
    )
    listing.add_argument(
        "-p", "--priority", choices=list(PRIORITIES), help="Filter by priority."
    )

    ready = sub.add_parser("ready", help="Print dispatchable task IDs.")
    ready.add_argument(
        "-n",
        "--parallel",
        type=int,
        metavar="N",
        help="Reduce to a conflict-free batch of at most N tasks.",
    )
    ready.add_argument(
        "-v", "--verbose", action="store_true", help="Include titles and file scopes."
    )

    sub.add_parser("stats", help="Print a status summary.")

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

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        tasks = load_tasks()
    except FrontmatterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("run 'task.py validate' for details", file=sys.stderr)
        return 1

    if args.command == "reindex":
        print(reindex().relative_to(TASKS_DIR.parent.parent))
        return 0

    if args.command == "list":
        selected = [
            task
            for task in sorted(tasks, key=sort_key)
            if (not args.status or task.status == args.status)
            and (not args.priority or task.priority == args.priority)
        ]
        for task in selected:
            print(f"{task.id}  {task.status:<12} {task.priority:<7} {task.title}")
        if not selected:
            print("(no matching tasks)")
        return 0

    if args.command == "ready":
        dispatchable = ready_tasks(tasks)
        if args.parallel:
            dispatchable = parallel_batch(dispatchable, args.parallel)
        for task in dispatchable:
            if args.verbose:
                scope = ", ".join(task.touches) or "(unscoped)"
                print(f"{task.id}  {task.priority:<7} {task.title}  [{scope}]")
            else:
                print(task.id)
        return 0

    if args.command == "stats":
        for status in STATUSES:
            count = sum(1 for task in tasks if task.status == status)
            print(f"{status:<12} {count}")
        print(f"{'total':<12} {len(tasks)}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
