"""Tests for `scripts/gitflow.sh` start and finish.

Each case builds a scratch repository with a bare remote, copies the real `gitflow.sh`,
`scripts/lib/common.sh` and `scripts/config/gate.sh` into it, and replaces `scripts/gate.sh` with a
stub that exits 0, so the assertions cover the branch, worktree and merge handling only.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"


def _env() -> dict[str, str]:
    env: dict[str, str] = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(name, None)
    return env


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=_env(),
    )
    return result.stdout.strip()


def _gitflow(
    repo: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["bash", str(repo / "scripts" / "gitflow.sh"), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )
    if check:
        assert result.returncode == 0, result.stdout + result.stderr
    return result


@pytest.fixture
def scratch(tmp_path: Path) -> Path:
    """A repo named `proj` on `develop` with a bare `origin`; worktrees land beside it."""
    bare = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", "develop", str(bare)],
        check=True,
        env=_env(),
    )
    repo = tmp_path / "proj"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "develop")
    _git(repo, "config", "core.hooksPath", "/dev/null")
    (repo / "scripts" / "lib").mkdir(parents=True)
    (repo / "scripts" / "config").mkdir()
    shutil.copy(SCRIPTS / "gitflow.sh", repo / "scripts" / "gitflow.sh")
    shutil.copy(SCRIPTS / "lib" / "common.sh", repo / "scripts" / "lib" / "common.sh")
    shutil.copy(SCRIPTS / "config" / "gate.sh", repo / "scripts" / "config" / "gate.sh")
    gate = repo / "scripts" / "gate.sh"
    gate.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    gate.chmod(0o755)
    (repo / "package.json").write_text("{}\n", encoding="utf-8")
    (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    (repo / "node_modules").mkdir()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "init")
    _git(repo, "remote", "add", "origin", str(bare))
    _git(repo, "push", "-q", "origin", "develop")
    return repo


def _worktree(repo: Path, label: str, topic: str) -> Path:
    return repo.parent / f"proj-{label}-{topic}"


@pytest.mark.parametrize("kind", ["docs", "chore", "fix"])
def test_task_branch_kinds_start_and_finish_end_to_end(scratch: Path, kind: str):
    topic = "T-0005-write-it-up"
    branch = f"{kind}/{topic}"
    worktree = _worktree(scratch, kind, topic)

    _gitflow(scratch, kind, "start", topic)

    assert worktree.is_dir()
    assert _git(worktree, "rev-parse", "--abbrev-ref", "HEAD") == branch
    assert _git(scratch, "rev-parse", branch) == _git(scratch, "rev-parse", "develop")
    assert (worktree / "node_modules").is_symlink()
    assert (worktree / "node_modules").resolve() == (scratch / "node_modules").resolve()

    (worktree / "note.md").write_text("note\n", encoding="utf-8")
    _git(worktree, "add", "note.md")
    _git(worktree, "commit", "-q", "--no-verify", "-m", f"{kind}: add note")

    _gitflow(scratch, kind, "finish", topic)

    assert _git(scratch, "log", "-1", "--format=%s", "develop") == (
        "chore(merge): merge task 0005 into develop"
    )
    assert len(_git(scratch, "log", "-1", "--format=%P", "develop").split()) == 2
    assert (scratch / "note.md").is_file()
    assert not worktree.exists()
    assert _git(scratch, "branch", "--list", branch) == ""


def test_feature_kind_is_unchanged(scratch: Path):
    topic = "login"
    worktree = _worktree(scratch, "feat", topic)

    _gitflow(scratch, "feature", "start", topic)

    assert _git(worktree, "rev-parse", "--abbrev-ref", "HEAD") == "feat/login"
    assert (worktree / "node_modules").is_symlink()

    (worktree / "login.py").write_text("x = 1\n", encoding="utf-8")
    _git(worktree, "add", "login.py")
    _git(worktree, "commit", "-q", "--no-verify", "-m", "feat: login")

    _gitflow(scratch, "feature", "finish", topic)

    assert _git(scratch, "log", "-1", "--format=%s", "develop") == (
        "chore(merge): merge feat/login into develop"
    )
    assert not worktree.exists()
    assert _git(scratch, "branch", "--list", "feat/login") == ""


def test_unknown_kind_is_rejected(scratch: Path):
    result = _gitflow(scratch, "wibble", "start", "T-0005-x", check=False)
    assert result.returncode != 0
    assert "usage" in result.stderr
