#!/usr/bin/env python3
"""Housekeeping audit: touches conformance and drift detection.

One command answers "is this project still on the rails?" -- whether any task
branch edited files outside its declared ``touches`` scope, whether the
backlog and generated docs are current, whether the quality gate is actually
installed, and whether anything has silently stalled. This is a reporting
tool for a human or orchestrator to run periodically; it never fixes anything
it finds and never edits task files, ``BACKLOG.md``, or ``LESSONS.md``.

Run without a virtualenv; this tool is stdlib-only on purpose so it works in a
fresh git worktree that has never been ``uv sync``-ed.

Usage:
    python .agents/tasks/scripts/housekeep.py touches [<branch> ...]
    python .agents/tasks/scripts/housekeep.py drift [--review-days N]
    python .agents/tasks/scripts/housekeep.py setup
    python .agents/tasks/scripts/housekeep.py worktrees
    python .agents/tasks/scripts/housekeep.py all
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _frontmatter import FrontmatterError
from _schema import (
    BACKLOG_FILE,
    INTEGRATION_BRANCH,
    REPO_ROOT,
    TYPES,
    Task,
    ValidationError,
    find_task,
    load_tasks,
    paths_overlap,
)

logger = logging.getLogger("housekeep")

#: Matches a task branch name, e.g. ``chore/T-0014-housekeeping-audit``.
_BRANCH_RE = re.compile(
    r"^(" + "|".join(re.escape(t) for t in TYPES) + r")/(T-\d{4,})-.+$"
)

#: Default staleness threshold for a task sitting in ``review``.
DEFAULT_REVIEW_DAYS = 7

_SECONDS_PER_DAY = 86400.0


# --- git helpers ---------------------------------------------------------------


def _git(*args: str) -> subprocess.CompletedProcess:
    """Run a git command in the repo root, never raising on a non-zero exit.

    Args:
        *args: Arguments following ``git``.

    Returns:
        The completed process, with stdout/stderr captured as text.
    """
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )


def branch_exists(branch: str) -> bool:
    """Report whether a local branch exists.

    Args:
        branch: Branch name to check.

    Returns:
        ``True`` if git resolves the branch to a commit.
    """
    return (
        _git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").returncode == 0
    )


def list_task_branches() -> list[str]:
    """List local branches whose name matches the ``<type>/T-00XX-<slug>`` shape.

    Returns:
        Matching branch names, in the order git reports them.
    """
    result = _git("branch", "--format=%(refname:short)")
    if result.returncode != 0:
        return []
    return [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and _BRANCH_RE.match(line.strip())
    ]


def branch_diff_files(branch: str, base: str = INTEGRATION_BRANCH) -> list[str] | None:
    """List files a branch changed relative to where it diverged from ``base``.

    Args:
        branch: Branch to inspect.
        base: Branch it is expected to have diverged from.

    Returns:
        Changed repo-relative paths, or ``None`` if the diff could not be
        computed (e.g. no common history with ``base``).
    """
    result = _git("diff", "--name-only", f"{base}...{branch}")
    if result.returncode != 0:
        return None
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def commits_ahead(branch: str, base: str = INTEGRATION_BRANCH) -> int | None:
    """Count commits a branch has beyond its merge-base with ``base``.

    Args:
        branch: Branch to inspect.
        base: Branch to compare against.

    Returns:
        The commit count, or ``None`` if it could not be computed.
    """
    result = _git("rev-list", "--count", f"{base}..{branch}")
    if result.returncode != 0 or not result.stdout.strip().isdigit():
        return None
    return int(result.stdout.strip())


def file_age_days(path: Path) -> float | None:
    """Age in days since the last commit that touched ``path``.

    Args:
        path: Absolute path to a tracked file.

    Returns:
        Age in days, or ``None`` if the file has no git history (e.g.
        uncommitted).
    """
    try:
        rel = path.relative_to(REPO_ROOT)
    except ValueError:
        rel = path
    result = _git("log", "-1", "--format=%ct", "--", str(rel))
    stamp = result.stdout.strip()
    if result.returncode != 0 or not stamp.isdigit():
        return None
    return (time.time() - int(stamp)) / _SECONDS_PER_DAY


def file_exists_on_branch(branch: str, path: Path) -> bool:
    """Report whether ``path`` exists on ``branch``.

    Args:
        branch: Branch name to inspect.
        path: Absolute path to a tracked file.

    Returns:
        ``True`` if ``git show <branch>:<path>`` resolves the file.
    """
    try:
        rel = path.relative_to(REPO_ROOT)
    except ValueError:
        rel = path
    result = _git("show", f"{branch}:{rel}")
    return result.returncode == 0


# --- touches conformance ---------------------------------------------------------


def check_touches(branches: Sequence[str] | None = None) -> list[str]:
    """Audit task branches for files changed outside their declared ``touches``.

    Args:
        branches: Explicit branch names to check. When empty/``None``, every
            local branch matching the task-branch naming convention is used.

    Returns:
        One finding per problem: a changed file outside scope. Empty means
        every checked branch is clean.
    """
    findings: list[str] = []
    targets = list(branches) if branches else list_task_branches()

    for branch in targets:
        if not branch_exists(branch):
            findings.append(f"TOUCHES {branch}: branch does not exist")
            continue

        match = _BRANCH_RE.match(branch)
        task_id = match.group(2) if match else None
        if not task_id:
            findings.append(f"TOUCHES {branch}: branch name does not encode a task id")
            continue

        try:
            task = find_task(task_id)
        except ValidationError:
            findings.append(f"TOUCHES {branch}: no task file found for {task_id}")
            continue

        changed = branch_diff_files(branch)
        if changed is None:
            findings.append(
                f"TOUCHES {branch}: could not diff against {INTEGRATION_BRANCH} "
                "(no common history?)"
            )
            continue

        declared = task.touches
        if not declared:
            # An empty touches list is, by convention, treated as "touches
            # everything" (see _schema.tasks_conflict) -- nothing to flag.
            continue

        try:
            report_rel = task.report_path.relative_to(REPO_ROOT)
        except ValueError:
            report_rel = task.report_path
        in_scope = list(declared) + [str(report_rel)]

        for changed_path in changed:
            if any(paths_overlap(entry, changed_path) for entry in in_scope):
                continue
            findings.append(
                f"TOUCHES {branch}: {changed_path} is outside {task_id}'s declared "
                f"touches {declared}"
            )

    return findings


# --- drift detection ---------------------------------------------------------


def backlog_is_stale(tasks: Sequence[Task]) -> bool:
    """Report whether ``BACKLOG.md`` no longer matches the task files on disk.

    Args:
        tasks: Every currently loaded task.

    Returns:
        ``True`` when the generated backlog would render differently.
    """
    import backlog as backlog_mod

    if not BACKLOG_FILE.exists():
        return True
    expected = backlog_mod.render_backlog(tasks)
    actual = BACKLOG_FILE.read_text(encoding="utf-8")
    if "## Tasks" not in actual or "## Tasks" not in expected:
        return True
    # The generated header carries today's date, so compare the table body on.
    return expected.split("## Tasks", 1)[1] != actual.split("## Tasks", 1)[1]


def check_drift(review_days: int = DEFAULT_REVIEW_DAYS) -> list[str]:
    """Detect staleness across the backlog, reports, branches, and dependencies.

    Args:
        review_days: A task sitting in ``review`` longer than this is flagged.

    Returns:
        One finding per detected problem.
    """
    findings: list[str] = []
    tasks = load_tasks()
    by_id = {task.id.upper(): task for task in tasks}

    if backlog_is_stale(tasks):
        findings.append(
            "DRIFT BACKLOG.md: stale -- run: python .agents/tasks/scripts/backlog.py reindex"
        )

    for task in tasks:
        if task.status == "done" and not task.report_path.exists():
            try:
                report_rel = task.report_path.relative_to(REPO_ROOT)
            except ValueError:
                report_rel = task.report_path
            branch = task.branch
            report_on_branch = branch_exists(branch) and file_exists_on_branch(
                branch, task.report_path
            )
            if not report_on_branch:
                findings.append(
                    f"DRIFT {task.id}: status done but no report at {report_rel}"
                )

        if task.status == "in_progress":
            branch = task.branch
            if not branch_exists(branch):
                findings.append(
                    f"DRIFT {task.id}: in_progress but branch {branch!r} does not exist"
                )
            else:
                count = commits_ahead(branch)
                if not count:
                    findings.append(
                        f"DRIFT {task.id}: in_progress but branch {branch!r} has no commits "
                        f"ahead of {INTEGRATION_BRANCH}"
                    )

        if task.status == "review":
            age = file_age_days(task.path)
            if age is None:
                findings.append(
                    f"DRIFT {task.id}: status review but age could not be determined "
                    "(no git history for the task file)"
                )
            elif age > review_days:
                findings.append(
                    f"DRIFT {task.id}: in review for {age:.1f} day(s), exceeds the "
                    f"{review_days}-day threshold"
                )

        for dependency in task.depends_on:
            dep_task = by_id.get(dependency.upper())
            if dep_task is not None and dep_task.status == "in_progress":
                findings.append(
                    f"DRIFT {task.id}: depends_on {dep_task.id} which is in_progress "
                    "(not yet done)"
                )

    return findings


# --- worktree hygiene -----------------------------------------------------------


def list_worktrees() -> list[dict[str, str]]:
    """List all git worktrees for this repo via ``git worktree list --porcelain``.

    Returns:
        One dict per worktree with keys ``path`` and ``branch`` (``branch``
        is ``""`` for a detached HEAD). The first entry is always the
        primary checkout, per git's own ordering.
    """
    result = _git("worktree", "list", "--porcelain")
    if result.returncode != 0:
        return []
    worktrees: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if not line.strip():
            if current:
                worktrees.append(current)
                current = {}
            continue
        if line.startswith("worktree "):
            current = {"path": line[len("worktree ") :].strip(), "branch": ""}
        elif line.startswith("branch "):
            ref = line[len("branch ") :].strip()
            current["branch"] = ref.removeprefix("refs/heads/")
    if current:
        worktrees.append(current)
    return worktrees


def is_branch_merged(branch: str, base: str = INTEGRATION_BRANCH) -> bool:
    """Report whether ``branch`` is already an ancestor of ``base``.

    Args:
        branch: Branch to check.
        base: Branch to check ancestry against.

    Returns:
        ``True`` if ``branch`` has already been merged into ``base``.
    """
    return _git("merge-base", "--is-ancestor", branch, base).returncode == 0


def check_worktrees() -> list[str]:
    """Audit local worktrees for stale merged branches and misplaced integration branches.

    Flags two independent problems:

    - A secondary worktree whose branch is already merged into ``develop``
      but was never removed with ``git worktree remove`` (the cleanup step
      documented in ``.agents/README.md``'s execution loop and
      ``CONTRIBUTING.md``'s Worktrees section).
    - Any worktree holding `develop`/`main` checked out that is not the
      primary checkout -- these must only ever live in the primary checkout
      (see ``CONTRIBUTING.md`` § Worktrees).

    Returns:
        One finding per problem, in the same style as the other checks.
    """
    findings: list[str] = []
    worktrees = list_worktrees()
    if not worktrees:
        return findings

    primary_path = worktrees[0]["path"]

    for worktree in worktrees[1:]:
        path, branch = worktree["path"], worktree["branch"]
        if not branch:
            continue  # detached HEAD -- nothing to say about it here

        if branch in ("develop", "main"):
            findings.append(
                f"WORKTREE {path}: checked out on {branch!r}, which must only live in "
                f"the primary checkout ({primary_path}) -- see CONTRIBUTING.md's "
                "Worktrees section"
            )
            continue

        if is_branch_merged(branch):
            findings.append(
                f"WORKTREE {path}: branch {branch!r} is merged into {INTEGRATION_BRANCH} "
                f"but the worktree was never removed -- run: git worktree remove {path}"
            )

    return findings


# --- environment setup ---------------------------------------------------------


def check_setup() -> list[str]:
    """Verify the developer environment is actually wired to the quality gate.

    This repo uses Husky (see ``CONTRIBUTING.md`` § Agent verify/resolve
    workflow) to install ``pre-commit``/``pre-push`` hooks under ``.husky/``.

    Returns:
        One finding per problem: unconfigured ``core.hooksPath``, a missing
        ``.husky/`` directory, or missing/non-executable hook files in it.
    """
    findings: list[str] = []

    husky_dir = REPO_ROOT / ".husky"
    if not husky_dir.is_dir():
        findings.append(
            "SETUP .husky/: directory does not exist -- run the Husky install step "
            "(e.g. `npm run prepare`) per CONTRIBUTING.md"
        )
    else:
        hook_files = sorted(
            p for p in husky_dir.iterdir() if p.is_file() and not p.name.startswith("_")
        )
        if not hook_files:
            findings.append(
                "SETUP .husky/: directory exists but contains no hook scripts"
            )
        for hook in hook_files:
            if not os.access(hook, os.X_OK):
                findings.append(f"SETUP .husky/{hook.name}: not executable")

    result = _git("config", "--get", "core.hooksPath")
    hooks_path = result.stdout.strip()
    if result.returncode != 0 or not hooks_path:
        findings.append(
            "SETUP core.hooksPath: not configured -- the Husky install step should set this"
        )

    return findings


# --- CLI ---------------------------------------------------------------------


def _print_findings(findings: Sequence[str]) -> None:
    """Print one line per finding, or a clean confirmation.

    Args:
        findings: Findings to print.
    """
    if not findings:
        print("clean -- no findings.")
        return
    for finding in findings:
        print(finding)


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Argument list; defaults to ``sys.argv[1:]``.

    Returns:
        The parsed :class:`argparse.Namespace`.
    """
    parser = argparse.ArgumentParser(
        prog="housekeep.py", description="Audit the agent task workflow for drift."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    touches = sub.add_parser(
        "touches",
        help=f"Diff task branches against {INTEGRATION_BRANCH} and flag out-of-scope changes.",
    )
    touches.add_argument(
        "branches",
        nargs="*",
        help="Explicit branch names. Default: every task branch found.",
    )

    drift = sub.add_parser(
        "drift", help="Report backlog, report, branch, and dependency drift."
    )
    drift.add_argument(
        "--review-days",
        type=int,
        default=DEFAULT_REVIEW_DAYS,
        help=f"Flag review tasks older than this many days (default {DEFAULT_REVIEW_DAYS}).",
    )

    sub.add_parser("setup", help="Verify the quality gate is actually installed.")

    sub.add_parser(
        "worktrees",
        help="Flag merged-but-not-removed worktrees and develop/main in a secondary worktree.",
    )

    all_cmd = sub.add_parser(
        "all", help="Run touches, drift, setup, and worktrees; summarize."
    )
    all_cmd.add_argument(
        "--review-days",
        type=int,
        default=DEFAULT_REVIEW_DAYS,
        help=f"Flag review tasks older than this many days (default {DEFAULT_REVIEW_DAYS}).",
    )

    return parser.parse_args(argv)


def main(argv=None) -> int:
    """Entry point.

    Args:
        argv: Argument list; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code: ``0`` when clean, ``1`` when findings were reported.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)

    try:
        if args.command == "touches":
            findings = check_touches(args.branches)
            _print_findings(findings)
            return 1 if findings else 0

        if args.command == "drift":
            findings = check_drift(args.review_days)
            _print_findings(findings)
            return 1 if findings else 0

        if args.command == "setup":
            findings = check_setup()
            _print_findings(findings)
            return 1 if findings else 0

        if args.command == "worktrees":
            findings = check_worktrees()
            _print_findings(findings)
            return 1 if findings else 0

        if args.command == "all":
            sections = [
                ("touches", check_touches()),
                ("drift", check_drift(args.review_days)),
                ("setup", check_setup()),
                ("worktrees", check_worktrees()),
            ]
            total = 0
            for name, findings in sections:
                print(f"--- {name} ({len(findings)} finding(s)) ---")
                _print_findings(findings)
                total += len(findings)
                print()
            if total:
                print(
                    f"housekeep all: {total} finding(s) across {len(sections)} check(s)."
                )
                return 1
            print("housekeep all: clean -- no findings.")
            return 0

    except (ValidationError, FrontmatterError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
