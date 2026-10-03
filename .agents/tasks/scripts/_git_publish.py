#!/usr/bin/env python3
"""Git-atomic publish for new task files.

Task *filing* must land on the integration branch immediately so
every worktree sees it -- unlike task *execution*, which stays isolated on its
own branch (see ``.agents/README.md``, ``CLAUDE.md`` Working unit: the task").
This module syncs the primary checkout to ``origin/<integration branch>``,
commits a freshly-allocated task file, and pushes -- retrying with a fresh ID
allocation if a concurrent publish wins the race, instead of leaving a
colliding ID to surface later as a merge conflict.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

from _schema import INTEGRATION_BRANCH, REPO_ROOT

#: How many times to retry a rejected push before giving up.
MAX_PUBLISH_RETRIES = 5

#: Longest commit header ``scripts/commit_lint.py`` accepts.
MAX_HEADER_LENGTH = 100

_FILENAME_RE = re.compile(r"^(T-\d{4,})-(.+)$")

#: `_ids.allocate_id` updates this alongside the task file (relative to
#: whatever `repo_root` is passed in, not the real project's own path --
#: `publish_task` may run against a throwaway repo in tests).
_COUNTER_RELATIVE = Path(".agents/tasks/.counter")

#: Git environment variables that, if inherited from the invoking process
#: (e.g. a git hook, which sets these for the processes it spawns), take
#: precedence over an explicit `-C <path>` for repository discovery and can
#: redirect this module's git subprocesses onto an unrelated repository.
#: Stripped (popped, not just blanked) from every git subprocess's
#: environment so `-C`/`repo_root` is always what decides which repository
#: is touched. The same stripping is applied in `tests/test_task_scripts.py`'s
#: `_git()`.
_GIT_ENV_VARS_TO_STRIP = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES",
)


class PublishError(RuntimeError):
    """Raised when a task file cannot be published to the integration branch."""


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command against ``repo_root`` and capture its output."""
    env = dict(os.environ)
    for name in _GIT_ENV_VARS_TO_STRIP:
        env.pop(name, None)
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _require(result: subprocess.CompletedProcess[str], message: str) -> None:
    """Raise :class:`PublishError` with git's own stderr if ``result`` failed."""
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise PublishError(f"{message}: {detail}")


def is_primary_checkout(repo_root: Path = REPO_ROOT) -> bool:
    """Whether ``repo_root`` is a real checkout rather than a ``git worktree``.

    A secondary worktree has a ``.git`` *file* pointing at the shared gitdir;
    only the primary checkout has a real ``.git`` *directory*.
    """
    return (repo_root / ".git").is_dir()


def current_branch(repo_root: Path = REPO_ROOT) -> str:
    """Return the branch currently checked out at ``repo_root``."""
    result = _git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    _require(result, "could not determine current branch")
    return result.stdout.strip()


def _sync_integration_branch(repo_root: Path) -> None:
    """Fast-forward the local integration branch to its ``origin`` counterpart.

    Raises:
        PublishError: If the fetch fails, or the local branch has commits
            ``origin`` doesn't -- that divergence needs a human to
            resolve, not an automatic merge.
    """
    branch = INTEGRATION_BRANCH
    _require(
        _git(repo_root, "fetch", "origin", branch),
        f"git fetch origin {branch} failed",
    )
    _require(
        _git(repo_root, "merge", "--ff-only", f"origin/{branch}"),
        f"local {branch} has diverged from origin/{branch} and cannot be "
        "fast-forwarded automatically -- resolve by hand before filing a task",
    )


def _commit_message(task_id: str, slug: str) -> str:
    """Build ``chore(tasks): file <ID> <slug>``, truncating the slug to fit the header limit."""
    prefix = f"chore(tasks): file {task_id} "
    room = max(MAX_HEADER_LENGTH - len(prefix), 0)
    return prefix + slug[:room].rstrip("-")


def publish_task(
    create: Callable[[], Path],
    repo_root: Path = REPO_ROOT,
    max_retries: int = MAX_PUBLISH_RETRIES,
) -> Path:
    """Allocate, write, commit, and push a new task file to the integration branch.

    Must run from the primary checkout on the integration branch. Syncs to
    ``origin`` first, then loops: call ``create`` (which allocates the next
    task ID against current disk state and writes the file), commit it, and
    push. If the push is rejected because another publish won the race, the
    local commit is discarded, the branch is resynced, and ``create`` is
    called again -- so a colliding ID is corrected automatically instead of
    surfacing as a merge conflict later.

    Args:
        create: Zero-argument callable that allocates an ID and writes the
            task file, returning its path. Called once per attempt so a
            retry allocates a fresh ID against the resynced state.
        repo_root: Repository root to run git commands against.
        max_retries: Attempts before giving up.

    Returns:
        Path of the published task file.

    Raises:
        PublishError: Off the integration branch, in a secondary worktree, on
            an unresolvable divergence, or when retries are exhausted.
    """
    if not is_primary_checkout(repo_root):
        raise PublishError(
            "task.py new must run from the primary checkout, not a git "
            f"worktree -- task filing lands directly on {INTEGRATION_BRANCH}; "
            "only task execution uses a worktree/branch"
        )
    branch = current_branch(repo_root)
    if branch != INTEGRATION_BRANCH:
        raise PublishError(
            f"task.py new must run on {INTEGRATION_BRANCH} (currently on "
            f"{branch!r}) -- switch to the primary checkout's "
            f"{INTEGRATION_BRANCH} branch to file a task"
        )

    _sync_integration_branch(repo_root)

    last_error = ""
    for _ in range(max_retries):
        path = create()
        match = _FILENAME_RE.match(path.stem)
        if not match:
            raise PublishError(f"unexpected task filename {path.name!r}")
        task_id, slug = match.group(1), match.group(2)

        add_paths = [str(path)]
        counter_file = repo_root / _COUNTER_RELATIVE
        if counter_file.exists():
            add_paths.append(str(counter_file))
        _require(_git(repo_root, "add", *add_paths), "git add failed")
        _require(
            _git(repo_root, "commit", "-m", _commit_message(task_id, slug)),
            "git commit failed",
        )

        push = _git(repo_root, "push", "origin", INTEGRATION_BRANCH)
        if push.returncode == 0:
            return path

        last_error = push.stderr.strip() or push.stdout.strip()
        _require(
            _git(repo_root, "reset", "--hard", "HEAD~1"),
            "git reset failed after rejected push",
        )
        _sync_integration_branch(repo_root)

    raise PublishError(
        f"could not publish task after {max_retries} attempt(s); last push "
        f"error: {last_error}"
    )
