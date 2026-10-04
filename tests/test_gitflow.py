"""Tests for `scripts/gitflow.sh` start and finish.

Each case builds a scratch repository with a bare remote, copies the real `gitflow.sh`,
`scripts/lib/common.sh`, `scripts/config/gate.sh`, `scripts/changelog.py` and
`scripts/next_version.py` into it, and replaces `scripts/gate.sh` with a stub that exits 0, so the
assertions cover the branch, worktree, changelog check and merge handling only.
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
    shutil.copy(SCRIPTS / "changelog.py", repo / "scripts" / "changelog.py")
    shutil.copy(SCRIPTS / "next_version.py", repo / "scripts" / "next_version.py")
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


def _add_fragment(repo: Path, name: str) -> None:
    """Write and stage a valid changelog fragment."""
    path = repo / "changelog.d" / name
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        "- Described the change for a reader of the changelog.\n", encoding="utf-8"
    )
    _git(repo, "add", str(path))


def _start_commit(
    repo: Path,
    kind: str,
    topic: str,
    message: str,
    fragment: str | None,
    drop_origin_ref: bool = False,
) -> Path:
    """Start a branch, commit one file on it (with a fragment if named); return its worktree.

    `start` fetches, which recreates `origin/develop`, so dropping that ref happens after it.
    """
    label = "feat" if kind == "feature" else kind
    _gitflow(repo, kind, "start", topic)
    if drop_origin_ref:
        _git(repo, "update-ref", "-d", "refs/remotes/origin/develop")
    worktree = _worktree(repo, label, topic)
    (worktree / "change.py").write_text("x = 1\n", encoding="utf-8")
    _git(worktree, "add", "change.py")
    if fragment:
        _add_fragment(worktree, fragment)
    _git(worktree, "commit", "-q", "--no-verify", "-m", message)
    return worktree


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
    if kind == "fix":
        # A `fix` commit needs a changelog fragment; `docs` and `chore` do not.
        _add_fragment(worktree, "T-0005.fixed.md")
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
    _add_fragment(worktree, "login.added.md")
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


def test_finish_refuses_feat_branch_without_fragment(scratch: Path):
    worktree = _start_commit(scratch, "feature", "nofrag", "feat: no fragment", None)

    result = _gitflow(scratch, "feature", "finish", "nofrag", check=False)

    assert result.returncode != 0
    assert "changelog" in result.stderr
    assert worktree.is_dir()
    assert _git(scratch, "branch", "--list", "feat/nofrag") != ""
    assert _git(scratch, "log", "-1", "--format=%s", "develop") == "init"


def test_finish_merges_feat_branch_with_fragment(scratch: Path):
    worktree = _start_commit(
        scratch, "feature", "withfrag", "feat: fragment", "withfrag.added.md"
    )

    _gitflow(scratch, "feature", "finish", "withfrag")

    assert (scratch / "changelog.d" / "withfrag.added.md").is_file()
    assert not worktree.exists()


def _unpushed_feat_without_fragment(scratch: Path) -> None:
    """Commit a `feat` with no fragment on local develop only, so origin/develop is behind."""
    (scratch / "local.py").write_text("x = 1\n", encoding="utf-8")
    _git(scratch, "add", "local.py")
    _git(scratch, "commit", "-q", "--no-verify", "-m", "feat: unpushed")


def test_finish_checks_against_origin_base_when_it_exists(scratch: Path):
    _unpushed_feat_without_fragment(scratch)
    _start_commit(scratch, "docs", "T-0007-notes", "docs: notes", None)

    # Against origin/develop the range holds the unpushed feat commit, which has no fragment.
    result = _gitflow(scratch, "docs", "finish", "T-0007-notes", check=False)

    assert result.returncode != 0
    assert "changelog" in result.stderr


def test_finish_falls_back_to_local_base_without_origin_ref(scratch: Path):
    _unpushed_feat_without_fragment(scratch)
    _start_commit(
        scratch, "docs", "T-0007-notes", "docs: notes", None, drop_origin_ref=True
    )

    # Against local develop the range holds only the docs commit.
    _gitflow(scratch, "docs", "finish", "T-0007-notes")

    assert (scratch / "change.py").is_file()
