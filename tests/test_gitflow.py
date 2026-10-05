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
    assert "add changelog.d/<id>.<category>.md" in result.stderr
    assert "(exit" not in result.stderr
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


def test_finish_falls_back_to_local_base_without_origin_ref(
    scratch: Path, tmp_path: Path
):
    _unpushed_feat_without_fragment(scratch)
    _start_commit(scratch, "docs", "T-0007-notes", "docs: notes", None)
    # `start` created origin/develop; now the remote goes away, so the fetch in `finish` fails
    # and the stale tracking ref must not be used.
    _git(scratch, "remote", "set-url", "origin", str(tmp_path / "no-such-remote.git"))
    assert _git(scratch, "rev-parse", "--verify", "refs/remotes/origin/develop")

    result = _gitflow(scratch, "docs", "finish", "T-0007-notes")

    # Against local develop the range holds only the docs commit.
    assert "could not fetch origin develop" in result.stderr
    assert "local develop" in result.stderr
    assert (scratch / "change.py").is_file()


def test_finish_falls_back_to_local_base_without_origin_remote(scratch: Path):
    _unpushed_feat_without_fragment(scratch)
    _start_commit(
        scratch, "docs", "T-0007-notes", "docs: notes", None, drop_origin_ref=True
    )
    _git(scratch, "remote", "remove", "origin")

    result = _gitflow(scratch, "docs", "finish", "T-0007-notes")

    assert "could not fetch origin develop" in result.stderr
    assert (scratch / "change.py").is_file()


def test_finish_fetches_the_base_so_origin_ref_is_current(
    scratch: Path, tmp_path: Path
):
    # A second clone pushes to origin after `start` fetched; the local origin/develop is stale.
    _start_commit(scratch, "docs", "T-0007-notes", "docs: notes", None)
    stale = _git(scratch, "rev-parse", "refs/remotes/origin/develop")
    other = tmp_path / "other"
    subprocess.run(
        ["git", "clone", "-q", str(tmp_path / "origin.git"), str(other)],
        check=True,
        env=_env(),
    )
    (other / "teammate.txt").write_text("hi\n", encoding="utf-8")
    _git(other, "add", "teammate.txt")
    _git(other, "commit", "-q", "--no-verify", "-m", "docs: teammate")
    _git(other, "push", "-q", "origin", "develop")
    fresh = _git(other, "rev-parse", "HEAD")
    assert fresh != stale

    result = _gitflow(scratch, "docs", "finish", "T-0007-notes")

    assert "could not fetch" not in result.stderr
    assert _git(scratch, "rev-parse", "refs/remotes/origin/develop") == fresh


def test_finish_reports_an_internal_changelog_error_not_a_missing_fragment(
    scratch: Path,
):
    worktree = _start_commit(
        scratch, "feature", "boom", "feat: has a fragment", "boom.added.md"
    )
    # A broken sibling makes changelog.py exit 3 (internal error) once it classifies a commit.
    (scratch / "scripts" / "next_version.py").write_text(
        "raise RuntimeError('boom')\n", encoding="utf-8"
    )

    result = _gitflow(scratch, "feature", "finish", "boom", check=False)

    assert result.returncode != 0
    assert "changelog check failed (exit 3) on feat/boom" in result.stderr
    assert "add changelog.d/" not in result.stderr
    assert worktree.is_dir()
    assert _git(scratch, "branch", "--list", "feat/boom") != ""


def test_hotfix_finish_tells_you_to_push_both_branches_then_release(scratch: Path):
    # A hotfix starts from main, so the scratch repo needs one, on origin as well.
    _git(scratch, "branch", "main", "develop")
    _git(scratch, "push", "-q", "origin", "main")
    worktree = _start_commit(
        scratch, "hotfix", "urgent", "fix: urgent repair", "urgent.fixed.md"
    )
    assert _git(worktree, "rev-parse", "--abbrev-ref", "HEAD") == "hotfix/urgent"

    result = _gitflow(scratch, "hotfix", "finish", "urgent")

    message = result.stdout + result.stderr
    assert "git push origin main develop" in message
    assert "git checkout main && scripts/release.py --yes" in message
    assert "nothing is pushed or tagged yet" in message
    # The merge into main and the back-merge into develop still happen, unpushed.
    assert _git(scratch, "log", "-1", "--format=%s", "main") == (
        "chore(merge): merge hotfix/urgent into main"
    )
    assert _git(scratch, "log", "-1", "--format=%s", "develop") == (
        "chore(merge): merge main into develop"
    )
    assert _git(scratch, "rev-parse", "origin/main") != _git(
        scratch, "rev-parse", "main"
    )


def _commit_on_develop(scratch: Path, files: dict[str, str], message: str) -> None:
    """Commit files on develop and push it, so the primary checkout stays clean."""
    for rel, content in files.items():
        path = scratch / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git(scratch, "add", "-A")
    _git(scratch, "commit", "-q", "--no-verify", "-m", message)
    _git(scratch, "push", "-q", "origin", "develop")


def test_finish_runs_the_gate_with_if_needed_on_the_branch_tip(scratch: Path):
    log = scratch.parent / "gate-args"
    _commit_on_develop(
        scratch,
        {"scripts/gate.sh": f'#!/bin/sh\necho "$@ $PWD" >> "{log}"\n'},
        "chore: logging gate stub",
    )
    worktree = _start_commit(scratch, "docs", "T-0007-notes", "docs: notes", None)

    _gitflow(scratch, "docs", "finish", "T-0007-notes")

    (line,) = log.read_text(encoding="utf-8").splitlines()
    flag, ref, cwd = line.split(" ", 2)
    assert (flag, ref) == ("--if-needed", "refs/heads/docs/T-0007-notes")
    assert Path(cwd).resolve() == worktree.resolve()
    assert not worktree.exists()


def _install_real_gate(scratch: Path, log: Path) -> None:
    """Replace the stub gate with the real gate.sh, over a config that logs each gate command."""
    config = (scratch / "scripts" / "config" / "gate.sh").read_text(encoding="utf-8")
    logging = "\n".join(
        [
            "",
            f'log() {{ echo "$1" >> "{log}"; }}',
            'LINT_CMD="log lint"',
            'FORMAT_CHECK_CMD="log format"',
            'TYPECHECK_CMD="log typecheck"',
            'TEST_CMD="log test"',
            "export -f log",
            "",
        ]
    )
    _commit_on_develop(
        scratch,
        {
            ".gitignore": "node_modules\n",
            "scripts/gate.sh": (SCRIPTS / "gate.sh").read_text(encoding="utf-8"),
            "scripts/config/gate.sh": config + logging,
        },
        "chore: real gate with a logging config",
    )


FULL_GATE = ["lint", "format", "typecheck", "test"]


def test_finish_does_not_rerun_a_gate_that_already_passed_on_the_branch_tip(
    scratch: Path, tmp_path: Path
):
    """With the real gate.sh: a full run on the branch writes a record, so finish skips it."""
    log = tmp_path / "calls.log"
    _install_real_gate(scratch, log)
    worktree = _start_commit(scratch, "docs", "T-0007-notes", "docs: notes", None)
    first = subprocess.run(
        ["bash", "scripts/gate.sh"],
        cwd=worktree,
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )
    assert first.returncode == 0, first.stdout + first.stderr
    assert log.read_text(encoding="utf-8").split() == FULL_GATE
    log.unlink()

    result = _gitflow(scratch, "docs", "finish", "T-0007-notes")

    assert "skipped" in result.stdout
    assert not log.exists()
    assert (scratch / "change.py").is_file()


def test_finish_runs_the_gate_when_the_branch_tip_has_no_record(
    scratch: Path, tmp_path: Path
):
    log = tmp_path / "calls.log"
    _install_real_gate(scratch, log)
    _start_commit(scratch, "docs", "T-0007-notes", "docs: notes", None)

    _gitflow(scratch, "docs", "finish", "T-0007-notes")

    assert log.read_text(encoding="utf-8").split() == FULL_GATE
