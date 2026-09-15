#!/usr/bin/env python3
"""Create, inspect, and update agent task work orders.

Run without a virtualenv; this tool is stdlib-only on purpose so it works in a
fresh git worktree that has never been ``uv sync``-ed.

Usage:
    python .agents/tasks/scripts/task.py new --title "..." --type fix
    python .agents/tasks/scripts/task.py show T-0004
    python .agents/tasks/scripts/task.py set-status T-0004 in_progress
    python .agents/tasks/scripts/task.py validate
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _frontmatter import FrontmatterError, serialize  # noqa: E402
from _ids import allocate_id  # noqa: E402
from _schema import (  # noqa: E402
    PRIORITIES,
    STATUSES,
    TASK_TEMPLATE,
    TASKS_DIR,
    TYPES,
    ValidationError,
    detect_cycles,
    find_task,
    load_task,
    load_tasks,
    slugify,
    validate_citations,
    validate_task,
)

logger = logging.getLogger("task")


def render_template(template: Path, values: dict[str, str]) -> str:
    """Substitute ``{key}`` placeholders in a template file.

    Uses plain replacement rather than :meth:`str.format` so that literal braces
    in a title or description cannot raise a formatting error.

    Args:
        template: Template file to read.
        values: Mapping of placeholder name to replacement text.

    Returns:
        The rendered document.
    """
    text = template.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text


def create_task(
    title: str,
    task_type: str,
    priority: str = "medium",
    depends_on: Sequence[str] = (),
    touches: Sequence[str] = (),
) -> Path:
    """Allocate an ID and write a new task file from the template.

    Args:
        title: One-line task title.
        task_type: Conventional Commits type; drives the branch prefix.
        priority: One of ``high``, ``medium``, ``low``.
        depends_on: Task IDs that must be ``done`` before this one may start.
        touches: Repo-relative paths this task is expected to modify.

    Returns:
        Path of the newly created task file.

    Raises:
        ValidationError: If the type or priority is outside the vocabulary.
    """
    if task_type not in TYPES:
        raise ValidationError(f"type {task_type!r} not in {list(TYPES)}")
    if priority not in PRIORITIES:
        raise ValidationError(f"priority {priority!r} not in {list(PRIORITIES)}")
    if not title.strip():
        raise ValidationError("title must not be empty")

    task_id = allocate_id()
    slug = slugify(title)
    path = TASKS_DIR / f"{task_id}-{slug}.md"

    text = render_template(
        TASK_TEMPLATE,
        {
            "id": task_id,
            "title": title.strip(),
            "status": "open",
            "type": task_type,
            "priority": priority,
            "depends_on": ", ".join(item.strip().upper() for item in depends_on),
            "touches": ", ".join(item.strip() for item in touches),
            "created": dt.date.today().isoformat(),
            "slug": slug,
        },
    )
    path.write_text(text, encoding="utf-8")
    return path


def set_status(task_id: str, status: str) -> Path:
    """Change a task's status in place, leaving the body untouched.

    Args:
        task_id: Identifier such as ``T-0004``.
        status: New status, which must be in the known vocabulary.

    Returns:
        Path of the updated task file.

    Raises:
        ValidationError: If the status is unknown or the task does not exist.
    """
    if status not in STATUSES:
        raise ValidationError(f"status {status!r} not in {list(STATUSES)}")
    task = find_task(task_id)
    task.meta["status"] = status
    task.path.write_text(serialize(task.meta, task.body), encoding="utf-8")
    return task.path


def _collect_problems() -> list[str]:
    """Validate every task in the backlog.

    Returns:
        A flat list of ``"<file>: <problem>"`` strings; empty means all valid.
    """
    problems: list[str] = []
    tasks = []
    for path in sorted(TASKS_DIR.glob("T-*.md")):
        try:
            tasks.append(load_task(path))
        except FrontmatterError as exc:
            problems.append(str(exc))

    known_ids = [task.id for task in tasks]
    for task in tasks:
        for problem in validate_task(task, known_ids):
            problems.append(f"{task.path.name}: {problem}")
        for problem in validate_citations(task):
            problems.append(f"{task.path.name}: {problem}")

    for cycle in detect_cycles(tasks):
        problems.append(f"dependency cycle: {' -> '.join(cycle)}")

    return problems


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Argument list; defaults to ``sys.argv[1:]``.

    Returns:
        The parsed :class:`argparse.Namespace`.
    """
    parser = argparse.ArgumentParser(
        prog="task.py", description="Manage agent task work orders."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="Create a task from the template.")
    new.add_argument("-t", "--title", required=True, help="One-line task title.")
    new.add_argument(
        "-T", "--type", required=True, choices=list(TYPES), help="Conventional Commits type."
    )
    new.add_argument(
        "-p", "--priority", default="medium", choices=list(PRIORITIES), help="Priority bucket."
    )
    new.add_argument(
        "-d",
        "--depends-on",
        nargs="*",
        default=[],
        metavar="ID",
        help="Task IDs that must be done first.",
    )
    new.add_argument(
        "-f",
        "--touches",
        nargs="*",
        default=[],
        metavar="PATH",
        help="Repo-relative paths this task will modify.",
    )

    show = sub.add_parser("show", help="Print a task file.")
    show.add_argument("id", help="Task ID, e.g. T-0004.")

    status = sub.add_parser("set-status", help="Change a task's status.")
    status.add_argument("id", help="Task ID, e.g. T-0004.")
    status.add_argument("status", choices=list(STATUSES), help="New status.")

    validate = sub.add_parser("validate", help="Check tasks against the schema.")
    validate.add_argument("id", nargs="?", help="Optional single task ID to check.")

    sub.add_parser("list-ids", help="Print every known task ID, one per line.")

    return parser.parse_args(argv)


def main(argv=None):
    """Entry point.

    Args:
        argv: Argument list; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code: ``0`` on success, ``1`` on validation failure.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)

    try:
        if args.command == "new":
            path = create_task(
                title=args.title,
                task_type=args.type,
                priority=args.priority,
                depends_on=args.depends_on,
                touches=args.touches,
            )
            print(path.relative_to(TASKS_DIR.parent.parent))
            return 0

        if args.command == "show":
            print(find_task(args.id).path.read_text(encoding="utf-8"), end="")
            return 0

        if args.command == "set-status":
            path = set_status(args.id, args.status)
            print(f"{args.id.upper()} -> {args.status}  ({path.name})")
            return 0

        if args.command == "list-ids":
            for task in load_tasks():
                print(task.id)
            return 0

        if args.command == "validate":
            if args.id:
                task = find_task(args.id)
                problems = [
                    f"{task.path.name}: {problem}"
                    for problem in validate_task(task, [t.id for t in load_tasks()])
                ] + [f"{task.path.name}: {problem}" for problem in validate_citations(task)]
            else:
                problems = _collect_problems()
            if problems:
                for problem in problems:
                    print(f"INVALID {problem}", file=sys.stderr)
                print(f"\n{len(problems)} problem(s) found.", file=sys.stderr)
                return 1
            print("All tasks valid.")
            return 0

    except (ValidationError, FrontmatterError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
