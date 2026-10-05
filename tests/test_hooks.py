"""Tests for `.husky/pre-push`, `.husky/pre-commit` and `scripts/gate.sh --staged`.

Each case builds a throwaway git repository. The real hook runs under `sh -e` the way Husky 9
does; the repository gets stub `scripts/gate.sh` and `scripts/autofix.sh` files that write marker
files, so the assertions are "was the gate asked to run" rather than "did pytest run". The
pre-push cases also copy the real `scripts/changelog.py`, `scripts/next_version.py` and
`scripts/config/gate.sh`, so the changelog fragment check runs for real. The
`gate.sh` / `autofix.sh` cases copy the real `scripts/` into the throwaway repository and replace
`scripts/config/gate.sh` with commands that log their arguments.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PRE_PUSH = REPO_ROOT / ".husky" / "pre-push"
PRE_COMMIT = REPO_ROOT / ".husky" / "pre-commit"
SCRIPTS = REPO_ROOT / "scripts"
ZERO = "0" * 40


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


def _write(repo: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _commit(repo: Path, files: dict[str, str], message: str = "c") -> str:
    _write(repo, files)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _stub(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "develop")
    _git(repo, "config", "core.hooksPath", "/dev/null")
    _commit(repo, {"src/app.py": "x = 1\n", ".agents/tasks/T-0001.md": "task\n"})
    return repo


def _install_gate_stubs(repo: Path, exit_code: int = 0) -> tuple[Path, Path]:
    """Add stub scripts/gate.sh and scripts/autofix.sh and the real config (all untracked).

    The gate stub appends one line of arguments per call to its marker file. Returns the
    gate and autofix marker files.
    """
    gate_marker = repo.parent / "gate-called"
    fix_marker = repo.parent / "autofix-called"
    _stub(
        repo / "scripts" / "gate.sh",
        f'echo "$@" >> "{gate_marker}"\nexit {exit_code}',
    )
    (repo / "scripts" / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy(SCRIPTS / "config" / "gate.sh", repo / "scripts" / "config" / "gate.sh")
    _stub(
        repo / "scripts" / "autofix.sh",
        f'echo "$@" > "{fix_marker}"',
    )
    return gate_marker, fix_marker


# --- pre-push -----------------------------------------------------------------


def _install_changelog_tooling(repo: Path) -> None:
    """Copy the real changelog check and its config into the repository (untracked)."""
    for rel in ("changelog.py", "next_version.py", "config/gate.sh"):
        target = repo / "scripts" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(SCRIPTS / rel, target)


def _run_pre_push(
    repo: Path,
    stdin: str,
    gate_exit: int = 0,
    remote: str = "origin",
    tooling: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], bool]:
    """Run the hook the way git does, with the remote's name and URL as its two arguments.

    Args:
        repo: The repository to run in.
        stdin: The ref lines git would send.
        gate_exit: Exit status of the stub `scripts/gate.sh`.
        remote: The first hook argument: a remote name, or a URL for a push to a bare URL.
        tooling: Replacement contents for files under `scripts/`, written after the real
            changelog tooling is copied in (to make it fail on purpose).

    Returns:
        The result and whether the stub gate.sh was invoked.
    """
    gate_marker, _ = _install_gate_stubs(repo, gate_exit)
    _install_changelog_tooling(repo)
    for rel, content in (tooling or {}).items():
        (repo / "scripts" / rel).write_text(content, encoding="utf-8")
    result = subprocess.run(
        ["sh", "-e", str(PRE_PUSH), remote, "https://example.invalid/repo.git"],
        input=stdin,
        cwd=repo,
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )
    return result, gate_marker.exists()


def _line(local_sha: str, remote_sha: str) -> str:
    return f"refs/heads/develop {local_sha} refs/heads/develop {remote_sha}\n"


def _gate_calls(repo: Path) -> list[str]:
    """The argument lines the stub gate.sh received, one per call, in order."""
    marker = repo.parent / "gate-called"
    return marker.read_text().splitlines() if marker.exists() else []


def test_agents_only_range_skips_gate(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(
        repo,
        {".agents/tasks/T-0002.md": "new task\n", ".agents/tasks/BACKLOG.md": "b\n"},
    )
    result, ran = _run_pre_push(repo, _line(head, base))
    assert result.returncode == 0, result.stderr
    assert not ran
    assert "skipping gate" in result.stdout


def test_range_touching_src_runs_gate(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, {"src/app.py": "x = 2\n"})
    result, ran = _run_pre_push(repo, _line(head, base))
    assert result.returncode == 0, result.stderr
    assert ran


def test_range_touching_agents_tooling_scripts_runs_gate(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, {".agents/tasks/scripts/task.py": "x = 1\n"})
    result, ran = _run_pre_push(repo, _line(head, base))
    assert result.returncode == 0, result.stderr
    assert ran


def test_tooling_scripts_mixed_with_records_runs_gate(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _commit(repo, {".agents/tasks/T-0002.md": "new task\n"})
    head = _commit(repo, {".agents/tasks/scripts/backlog.py": "x = 1\n"})
    result, ran = _run_pre_push(repo, _line(head, base))
    assert result.returncode == 0, result.stderr
    assert ran


def test_rename_into_agents_runs_gate(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "mv", "src/app.py", ".agents/app.py")
    _git(repo, "commit", "-q", "--no-verify", "-m", "mv")
    head = _git(repo, "rev-parse", "HEAD")
    result, ran = _run_pre_push(repo, _line(head, base))
    assert result.returncode == 0, result.stderr
    assert ran


def test_mixed_range_runs_gate(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _commit(repo, {".agents/tasks/T-0002.md": "new task\n"})
    head = _commit(repo, {"src/app.py": "x = 3\n"})
    result, ran = _run_pre_push(repo, _line(head, base))
    assert result.returncode == 0, result.stderr
    assert ran


def test_new_remote_branch_runs_gate(repo: Path) -> None:
    head = _commit(repo, {".agents/tasks/T-0002.md": "new task\n"})
    result, ran = _run_pre_push(repo, _line(head, ZERO))
    assert result.returncode == 0, result.stderr
    assert ran


def test_unknown_remote_sha_runs_gate(repo: Path) -> None:
    head = _commit(repo, {".agents/tasks/T-0002.md": "new task\n"})
    result, ran = _run_pre_push(repo, _line(head, "1" * 40))
    assert result.returncode == 0, result.stderr
    assert ran


def test_branch_deletion_alone_skips_gate(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    result, ran = _run_pre_push(repo, f"(delete) {ZERO} refs/heads/old {base}\n")
    assert result.returncode == 0, result.stderr
    assert not ran


def test_failing_gate_blocks_push(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, {"src/app.py": "x = 4\n"})
    result, ran = _run_pre_push(repo, _line(head, base), gate_exit=1)
    assert ran
    assert result.returncode != 0


def test_several_refs_one_touching_src_runs_gate(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    agents_head = _commit(repo, {".agents/tasks/T-0002.md": "new task\n"})
    _git(repo, "branch", "agents-only", agents_head)
    src_head = _commit(repo, {"src/app.py": "x = 5\n"})
    stdin = (
        f"refs/heads/agents-only {agents_head} refs/heads/agents-only {base}\n"
        f"refs/heads/develop {src_head} refs/heads/develop {base}\n"
    )
    result, ran = _run_pre_push(repo, stdin)
    assert result.returncode == 0, result.stderr
    assert ran


def test_src_change_reverted_inside_range_runs_gate(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _commit(repo, {"src/app.py": "x = 6\n"})
    head = _commit(repo, {"src/app.py": "x = 1\n"})
    assert _git(repo, "diff", "--name-only", base, head) == ""
    result, ran = _run_pre_push(repo, _line(head, base))
    assert result.returncode == 0, result.stderr
    assert ran


def test_src_change_made_only_inside_merge_commit_runs_gate(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "side")
    _commit(repo, {".agents/tasks/T-0003.md": "side task\n"})
    _git(repo, "checkout", "-q", "develop")
    _commit(repo, {".agents/tasks/T-0002.md": "new task\n"})
    _git(repo, "merge", "--no-ff", "--no-commit", "side")
    (repo / "src" / "app.py").write_text("x = 7\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "merge side")
    head = _git(repo, "rev-parse", "HEAD")
    result, ran = _run_pre_push(repo, _line(head, base))
    assert result.returncode == 0, result.stderr
    assert ran


def test_empty_stdin_skips_gate(repo: Path) -> None:
    result, ran = _run_pre_push(repo, "")
    assert result.returncode == 0, result.stderr
    assert not ran
    assert "skipping gate" in result.stdout


# --- pre-push: which gate runs ------------------------------------------------


def _push_one_file(repo: Path, name: str) -> str:
    """Commit one file on develop, run the hook for that push, and return its stdout."""
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, {name: "r\n"})
    result, _ = _run_pre_push(repo, _line(head, base))
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.mark.parametrize(
    "name",
    [
        ".agents/tasks/T-0002-new-task.md",
        ".agents/tasks/reports/T-0002.md",
        ".agents/tasks/BACKLOG.md",
        ".agents/tasks/.counter",
        ".agents/LESSONS.md",
        ".agents/plans/2026-10-05-a-plan.md",
    ],
)
def test_each_record_path_alone_skips_gate(repo: Path, name: str) -> None:
    out = _push_one_file(repo, name)
    assert "skipping gate" in out
    assert _gate_calls(repo) == []


@pytest.mark.parametrize(
    "name",
    [
        ".agents/README.md",
        ".agents/tasks/templates/task.md",
        ".agents/tasks/scripts/task.py",
        ".agents/tasks/notes.md",
        ".agents/other/T-0002.md",
    ],
)
def test_agents_paths_that_are_not_records_run_gate(repo: Path, name: str) -> None:
    _push_one_file(repo, name)
    assert len(_gate_calls(repo)) == 1


def test_rename_into_a_record_path_runs_gate(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    (repo / ".agents" / "plans").mkdir(parents=True)
    _git(repo, "mv", "src/app.py", ".agents/plans/app.py")
    _git(repo, "commit", "-q", "--no-verify", "-m", "mv")
    head = _git(repo, "rev-parse", "HEAD")
    result, ran = _run_pre_push(repo, _line(head, base))
    assert result.returncode == 0, result.stderr
    assert ran


def _config_with_record_paths(record_paths: str) -> dict[str, str]:
    """`tooling` for `_run_pre_push`: the real config with its RECORD_PATHS replaced."""
    real = (SCRIPTS / "config" / "gate.sh").read_text(encoding="utf-8")
    kept = [ln for ln in real.splitlines() if not ln.startswith("RECORD_PATHS=")]
    kept.append(f'RECORD_PATHS="{record_paths}"')
    return {"config/gate.sh": "\n".join(kept) + "\n"}


def test_pre_push_skips_a_path_the_config_adds_to_record_paths(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, {"notes/n.md": "n\n", "notes/deep/m.md": "m\n"})
    tooling = _config_with_record_paths("notes/")
    result, ran = _run_pre_push(repo, _line(head, base), tooling=tooling)
    assert result.returncode == 0, result.stderr
    assert not ran
    assert "skipping gate" in result.stdout


def test_pre_push_gates_a_path_the_config_removes_from_record_paths(
    repo: Path,
) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, {"notes/n.md": "n\n", ".agents/plans/p.md": "p\n"})
    tooling = _config_with_record_paths("notes/")
    result, ran = _run_pre_push(repo, _line(head, base), tooling=tooling)
    assert result.returncode == 0, result.stderr
    assert ran


def test_develop_push_asks_for_a_record_of_the_pushed_sha(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, {"src/app.py": "x = 2\n"})
    result, _ = _run_pre_push(repo, _line(head, base))
    assert result.returncode == 0, result.stderr
    assert _gate_calls(repo) == [f"--if-needed {head}"]


def test_main_push_asks_for_a_record_of_the_pushed_sha(repo: Path) -> None:
    first = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, {"src/app.py": "x = 2\n"})
    line = _ref_line(head, first, "refs/heads/main", "refs/heads/main")
    result, _ = _run_pre_push(repo, line)
    assert result.returncode == 0, result.stderr
    assert _gate_calls(repo) == [f"--if-needed {head}"]


def test_first_push_of_develop_asks_for_a_record(repo: Path) -> None:
    head = _commit(repo, {"src/app.py": "x = 2\n"})
    result, _ = _run_pre_push(repo, _line(head, ZERO))
    assert result.returncode == 0, result.stderr
    assert _gate_calls(repo) == [f"--if-needed {head}"]


def test_main_and_develop_pushed_together_pass_every_sha_and_skip_deleted_refs(
    repo: Path,
) -> None:
    first = _git(repo, "rev-parse", "HEAD")
    main_head = _commit(repo, {"src/app.py": "x = 2\n"})
    develop_head = _commit(repo, {"src/app.py": "x = 3\n"})
    stdin = (
        _ref_line(main_head, first, "refs/heads/main", "refs/heads/main")
        + _line(develop_head, first)
        + f"(delete) {ZERO} refs/heads/develop-old {first}\n"
    )
    result, _ = _run_pre_push(repo, stdin)
    assert result.returncode == 0, result.stderr
    assert _gate_calls(repo) == [f"--if-needed {main_head} {develop_head}"]


@pytest.mark.parametrize("remote_sha_is_new", [True, False])
def test_task_branch_push_runs_only_the_fast_gate(
    repo: Path, remote_sha_is_new: bool
) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _set_origin(repo, "develop", base)
    _checkout_new(repo, "docs/T-0001-x")
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "docs: change it")
    remote_sha = ZERO if remote_sha_is_new else base
    line = _ref_line(
        head, remote_sha, "refs/heads/docs/T-0001-x", "refs/heads/docs/T-0001-x"
    )
    result, _ = _run_pre_push(repo, line)
    assert result.returncode == 0, result.stderr
    assert _gate_calls(repo) == ["--fast"]


def test_task_branch_and_develop_pushed_together_run_both_modes(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _set_origin(repo, "develop", base)
    _checkout_new(repo, "docs/T-0001-x")
    branch_head = _commit(repo, {"src/app.py": "x = 2\n"}, "docs: change it")
    develop_head = _commit(repo, {"src/app.py": "x = 3\n"}, "docs: change it again")
    stdin = _ref_line(
        branch_head, base, "refs/heads/docs/T-0001-x", "refs/heads/docs/T-0001-x"
    ) + _line(develop_head, base)
    result, _ = _run_pre_push(repo, stdin)
    assert result.returncode == 0, result.stderr
    assert _gate_calls(repo) == ["--fast", f"--if-needed {develop_head}"]


def test_tag_only_push_runs_the_fast_gate(repo: Path) -> None:
    head = _git(repo, "rev-parse", "HEAD")
    _git(repo, "tag", "v0.0.1")
    line = _ref_line(head, ZERO, "refs/tags/v0.0.1", "refs/tags/v0.0.1")
    result, _ = _run_pre_push(repo, line)
    assert result.returncode == 0, result.stderr
    assert _gate_calls(repo) == ["--fast"]


def test_failing_fast_gate_blocks_a_task_branch_push(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _set_origin(repo, "develop", base)
    _checkout_new(repo, "docs/T-0001-x")
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "docs: change it")
    line = _ref_line(head, ZERO, "refs/heads/docs/T-0001-x", "refs/heads/docs/T-0001-x")
    result, ran = _run_pre_push(repo, line, gate_exit=1)
    assert ran
    assert result.returncode != 0


def test_failing_if_needed_gate_blocks_a_develop_push(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, {"src/app.py": "x = 2\n"})
    result, ran = _run_pre_push(repo, _line(head, base), gate_exit=1)
    assert ran
    assert result.returncode != 0


# --- pre-push: changelog fragment check ---------------------------------------

FRAGMENT = "changelog.d/T-0001.added.md"
FRAGMENT_BODY = "- Added the thing, described for a reader of the changelog.\n"


def _set_origin(repo: Path, branch: str, sha: str) -> None:
    """Create the remote-tracking ref `origin/<branch>` without a remote."""
    _git(repo, "update-ref", f"refs/remotes/origin/{branch}", sha)


def _checkout_new(repo: Path, branch: str) -> None:
    _git(repo, "checkout", "-q", "-b", branch)


def _ref_line(
    local_sha: str,
    remote_sha: str,
    remote_ref: str = "refs/heads/feat/x",
    local_ref: str = "HEAD",
) -> str:
    return f"{local_ref} {local_sha} {remote_ref} {remote_sha}\n"


def _assert_rejected_by_changelog(
    result: subprocess.CompletedProcess[str], ran: bool
) -> None:
    assert result.returncode != 0
    assert not ran
    assert "changelog fragment" in result.stderr


def test_feat_branch_without_fragment_is_rejected(repo: Path) -> None:
    _set_origin(repo, "develop", _git(repo, "rev-parse", "HEAD"))
    _checkout_new(repo, "feat/x")
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "feat(app): change it")
    result, ran = _run_pre_push(repo, _ref_line(head, ZERO))
    _assert_rejected_by_changelog(result, ran)


def test_feat_branch_with_fragment_passes_and_runs_gate(repo: Path) -> None:
    _set_origin(repo, "develop", _git(repo, "rev-parse", "HEAD"))
    _checkout_new(repo, "feat/x")
    head = _commit(
        repo, {"src/app.py": "x = 2\n", FRAGMENT: FRAGMENT_BODY}, "feat(app): change it"
    )
    result, ran = _run_pre_push(repo, _ref_line(head, ZERO))
    assert result.returncode == 0, result.stderr
    assert ran


def test_breaking_commit_without_fragment_is_rejected(repo: Path) -> None:
    _set_origin(repo, "develop", _git(repo, "rev-parse", "HEAD"))
    _checkout_new(repo, "chore/x")
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "chore(app)!: drop it")
    result, ran = _run_pre_push(repo, _ref_line(head, ZERO, "refs/heads/chore/x"))
    _assert_rejected_by_changelog(result, ran)


def test_fix_round_on_branch_that_already_has_fragment_passes(repo: Path) -> None:
    _set_origin(repo, "develop", _git(repo, "rev-parse", "HEAD"))
    _checkout_new(repo, "feat/x")
    pushed = _commit(
        repo, {"src/app.py": "x = 2\n", FRAGMENT: FRAGMENT_BODY}, "feat(app): change it"
    )
    head = _commit(repo, {"src/app.py": "x = 3\n"}, "fix(app): address review")
    result, ran = _run_pre_push(repo, _ref_line(head, pushed))
    assert result.returncode == 0, result.stderr
    assert ran


def test_docs_only_branch_passes_without_fragment(repo: Path) -> None:
    _set_origin(repo, "develop", _git(repo, "rev-parse", "HEAD"))
    _checkout_new(repo, "docs/x")
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "docs(app): explain it")
    result, ran = _run_pre_push(repo, _ref_line(head, ZERO, "refs/heads/docs/x"))
    assert result.returncode == 0, result.stderr
    assert ran


def test_branch_is_classified_by_remote_ref_not_local_ref(repo: Path) -> None:
    """Local ref `develop` pushed to `refs/heads/feat/x` is a feature branch, not develop.

    Classified by local_ref it would be a first push of develop and skip the check.
    """
    _set_origin(repo, "develop", _git(repo, "rev-parse", "HEAD"))
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "feat(app): change it")
    line = _ref_line(head, ZERO, "refs/heads/feat/x", "refs/heads/develop")
    result, ran = _run_pre_push(repo, line)
    _assert_rejected_by_changelog(result, ran)


def test_hotfix_branch_is_ranged_from_origin_main(repo: Path) -> None:
    """Both tracking refs exist: a hotfix is ranged from main, not from develop.

    origin/develop already holds the hotfix commit, so a range taken from it is empty and would
    pass; only the range from origin/main sees the `fix` commit without a fragment.
    """
    base = _git(repo, "rev-parse", "HEAD")
    _set_origin(repo, "main", base)
    _checkout_new(repo, "hotfix/x")
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "fix(app): patch it")
    _set_origin(repo, "develop", head)
    line = _ref_line(head, ZERO, "refs/heads/hotfix/x")
    result, ran = _run_pre_push(repo, line)
    _assert_rejected_by_changelog(result, ran)


def test_hotfix_branch_without_origin_main_skips_even_if_origin_develop_exists(
    repo: Path,
) -> None:
    _set_origin(repo, "develop", _git(repo, "rev-parse", "HEAD"))
    _checkout_new(repo, "hotfix/x")
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "fix(app): patch it")
    result, ran = _run_pre_push(repo, _ref_line(head, ZERO, "refs/heads/hotfix/x"))
    assert result.returncode == 0, result.stderr
    assert ran
    assert "no merge base with origin/main" in result.stderr


def test_hotfix_branch_with_fragment_passes(repo: Path) -> None:
    _set_origin(repo, "main", _git(repo, "rev-parse", "HEAD"))
    _checkout_new(repo, "hotfix/x")
    head = _commit(
        repo,
        {"src/app.py": "x = 2\n", "changelog.d/hot.fixed.md": FRAGMENT_BODY},
        "fix(app): patch it",
    )
    line = _ref_line(head, ZERO, "refs/heads/hotfix/x")
    result, ran = _run_pre_push(repo, line)
    assert result.returncode == 0, result.stderr
    assert ran


def test_feature_branch_without_origin_develop_skips_check_and_runs_gate(
    repo: Path,
) -> None:
    _set_origin(repo, "main", _git(repo, "rev-parse", "HEAD"))
    _checkout_new(repo, "feat/x")
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "feat(app): change it")
    result, ran = _run_pre_push(repo, _ref_line(head, ZERO))
    assert result.returncode == 0, result.stderr
    assert ran
    assert "skipping the changelog check" in result.stderr


@pytest.mark.parametrize("remote_ref", ["refs/tags/v0.1.0", "refs/notes/commits"])
def test_tag_ref_is_not_checked(repo: Path, remote_ref: str) -> None:
    """origin/develop exists, so a ref treated as a branch would be rejected for its feat commit."""
    _set_origin(repo, "develop", _git(repo, "rev-parse", "HEAD"))
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "feat(app): change it")
    _git(repo, "tag", "v0.1.0", head)
    result, ran = _run_pre_push(repo, _ref_line(head, ZERO, remote_ref, remote_ref))
    assert result.returncode == 0, result.stderr
    assert ran
    assert "changelog" not in result.stderr


@pytest.mark.parametrize("branch", ["develop", "main"])
def test_first_push_of_main_or_develop_is_not_checked(repo: Path, branch: str) -> None:
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "feat(app): change it")
    line = _ref_line(head, ZERO, f"refs/heads/{branch}")
    result, ran = _run_pre_push(repo, line)
    assert result.returncode == 0, result.stderr
    assert ran


@pytest.mark.parametrize("branch", ["develop", "main"])
def test_later_push_of_main_or_develop_without_fragment_is_rejected(
    repo: Path, branch: str
) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "fix(app): patch it")
    line = _ref_line(head, base, f"refs/heads/{branch}")
    result, ran = _run_pre_push(repo, line)
    _assert_rejected_by_changelog(result, ran)


def test_agents_only_push_skips_fragment_check_and_gate(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _set_origin(repo, "develop", base)
    _checkout_new(repo, "feat/x")
    head = _commit(
        repo, {".agents/tasks/T-0002.md": "new task\n"}, "feat(tasks): file a task"
    )
    result, ran = _run_pre_push(repo, _ref_line(head, base))
    assert result.returncode == 0, result.stderr
    assert not ran
    assert "skipping gate" in result.stdout


def test_unlistable_range_skips_fragment_check_and_runs_gate(repo: Path) -> None:
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "feat(app): change it")
    result, ran = _run_pre_push(repo, _line(head, "1" * 40))
    assert result.returncode == 0, result.stderr
    assert ran
    assert "skipping the changelog check" in result.stderr


def test_several_refs_are_all_checked(repo: Path) -> None:
    """A passing ref listed first does not hide a failing one after it."""
    base = _git(repo, "rev-parse", "HEAD")
    _set_origin(repo, "develop", base)
    _checkout_new(repo, "feat/ok")
    ok = _commit(
        repo, {"src/app.py": "x = 2\n", FRAGMENT: FRAGMENT_BODY}, "feat(app): change it"
    )
    _git(repo, "checkout", "-q", "-b", "feat/bad", base)
    bad = _commit(repo, {"src/other.py": "y = 1\n"}, "feat(app): other change")
    stdin = _ref_line(ok, ZERO, "refs/heads/feat/ok") + _ref_line(
        bad, ZERO, "refs/heads/feat/bad"
    )
    result, ran = _run_pre_push(repo, stdin)
    _assert_rejected_by_changelog(result, ran)


# --- pre-push: which remote the push goes to ----------------------------------


def test_push_to_a_second_remote_uses_that_remotes_tracking_ref(repo: Path) -> None:
    """origin/develop is already at the tip, so only upstream/develop sees the feat commit."""
    base = _git(repo, "rev-parse", "HEAD")
    _checkout_new(repo, "feat/x")
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "feat(app): change it")
    _set_origin(repo, "develop", head)
    _git(repo, "update-ref", "refs/remotes/upstream/develop", base)
    result, ran = _run_pre_push(repo, _ref_line(head, ZERO), remote="upstream")
    _assert_rejected_by_changelog(result, ran)


def test_push_to_a_second_remote_ignores_a_stale_origin_ref_that_would_reject(
    repo: Path,
) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _checkout_new(repo, "feat/x")
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "feat(app): change it")
    _set_origin(repo, "develop", base)
    _git(repo, "update-ref", "refs/remotes/upstream/develop", head)
    result, ran = _run_pre_push(repo, _ref_line(head, ZERO), remote="upstream")
    assert result.returncode == 0, result.stderr
    assert ran


def test_push_to_a_second_remote_without_its_ref_skips_the_check(repo: Path) -> None:
    _set_origin(repo, "develop", _git(repo, "rev-parse", "HEAD"))
    _checkout_new(repo, "feat/x")
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "feat(app): change it")
    result, ran = _run_pre_push(repo, _ref_line(head, ZERO), remote="upstream")
    assert result.returncode == 0, result.stderr
    assert ran
    assert "no merge base with upstream/develop" in result.stderr
    assert "skipping the changelog check" in result.stderr


@pytest.mark.parametrize(
    "url",
    ["https://example.invalid/team/repo.git", "/srv/git/repo.git", "../origin.git"],
)
def test_push_to_a_url_skips_the_check_even_when_origin_refs_exist(
    repo: Path, url: str
) -> None:
    _set_origin(repo, "develop", _git(repo, "rev-parse", "HEAD"))
    _checkout_new(repo, "feat/x")
    head = _commit(repo, {"src/app.py": "x = 2\n"}, "feat(app): change it")
    result, ran = _run_pre_push(repo, _ref_line(head, ZERO), remote=url)
    assert result.returncode == 0, result.stderr
    assert ran
    assert "skipping the changelog check" in result.stderr


# --- pre-push: changelog.py exit statuses -------------------------------------

EXIT_STUBS = {
    "exit 3": "import sys\nsys.exit(3)\n",
    "exit 127": "import sys\nsys.exit(127)\n",
    "signal": "import os, signal\nos.kill(os.getpid(), signal.SIGTERM)\n",
}


def _feat_without_fragment(repo: Path) -> str:
    _set_origin(repo, "develop", _git(repo, "rev-parse", "HEAD"))
    _checkout_new(repo, "feat/x")
    return _commit(repo, {"src/app.py": "x = 2\n"}, "feat(app): change it")


@pytest.mark.parametrize("stub", sorted(EXIT_STUBS))
def test_changelog_tool_failure_is_reported_as_a_failed_check_not_a_missing_fragment(
    repo: Path, stub: str
) -> None:
    head = _feat_without_fragment(repo)
    result, ran = _run_pre_push(
        repo, _ref_line(head, ZERO), tooling={"changelog.py": EXIT_STUBS[stub]}
    )
    assert result.returncode != 0
    assert not ran
    match = re.search(
        r"pre-push: changelog check failed \(exit (\d+)\) for refs/heads/feat/x",
        result.stderr,
    )
    assert match, result.stderr
    assert match.group(1) in {"3", "127", "143"}
    assert "changelog fragment" not in result.stderr


def test_internal_error_in_the_real_tool_is_reported_as_a_failed_check(
    repo: Path,
) -> None:
    head = _feat_without_fragment(repo)
    result, ran = _run_pre_push(
        repo,
        _ref_line(head, ZERO),
        tooling={"next_version.py": "raise RuntimeError('boom')\n"},
    )
    assert result.returncode != 0
    assert not ran
    assert "changelog check failed (exit 3) for refs/heads/feat/x" in result.stderr
    assert "changelog fragment" not in result.stderr


def test_missing_fragment_keeps_the_existing_message_and_is_not_a_failed_check(
    repo: Path,
) -> None:
    head = _feat_without_fragment(repo)
    result, ran = _run_pre_push(repo, _ref_line(head, ZERO))
    _assert_rejected_by_changelog(result, ran)
    assert "changelog check failed" not in result.stderr


def test_invalid_fragment_content_is_rejected_as_a_fragment_problem(repo: Path) -> None:
    _set_origin(repo, "develop", _git(repo, "rev-parse", "HEAD"))
    _checkout_new(repo, "feat/x")
    head = _commit(
        repo,
        {"src/app.py": "x = 2\n", FRAGMENT: "Intro line.\n\n" + FRAGMENT_BODY},
        "feat(app): change it",
    )
    result, ran = _run_pre_push(repo, _ref_line(head, ZERO))
    _assert_rejected_by_changelog(result, ran)
    assert "not a bullet" in result.stderr
    assert "changelog check failed" not in result.stderr


def test_a_failed_check_on_one_ref_is_not_hidden_by_a_passing_ref(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _set_origin(repo, "develop", base)
    _checkout_new(repo, "feat/ok")
    ok = _commit(repo, {"src/app.py": "x = 2\n", FRAGMENT: FRAGMENT_BODY}, "feat: ok")
    _git(repo, "checkout", "-q", "-b", "feat/bad", base)
    bad = _commit(repo, {"src/other.py": "y = 1\n"}, "docs: other")
    stdin = _ref_line(ok, ZERO, "refs/heads/feat/ok") + _ref_line(
        bad, ZERO, "refs/heads/feat/bad"
    )
    result, ran = _run_pre_push(
        repo,
        stdin,
        tooling={
            "changelog.py": "import sys\nsys.exit(3 if sys.argv[3] == "
            + repr(bad)
            + " else 0)\n"
        },
    )
    assert result.returncode != 0
    assert not ran
    assert "changelog check failed (exit 3) for refs/heads/feat/bad" in result.stderr


def test_push_of_develop_after_merging_feat_task_with_fragment_passes(
    repo: Path,
) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _checkout_new(repo, "feat/t")
    _commit(
        repo, {"src/app.py": "x = 2\n", FRAGMENT: FRAGMENT_BODY}, "feat(app): change it"
    )
    _git(repo, "checkout", "-q", "develop")
    _git(
        repo, "merge", "--no-ff", "-q", "-m", "chore(merge): merge task 0001", "feat/t"
    )
    head = _git(repo, "rev-parse", "HEAD")
    result, ran = _run_pre_push(repo, _line(head, base))
    assert result.returncode == 0, result.stderr
    assert ran


def test_push_of_develop_after_merging_feat_task_without_fragment_is_rejected(
    repo: Path,
) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _checkout_new(repo, "feat/t")
    _commit(repo, {"src/app.py": "x = 2\n"}, "feat(app): change it")
    _git(repo, "checkout", "-q", "develop")
    _git(
        repo, "merge", "--no-ff", "-q", "-m", "chore(merge): merge task 0001", "feat/t"
    )
    head = _git(repo, "rev-parse", "HEAD")
    result, ran = _run_pre_push(repo, _line(head, base))
    _assert_rejected_by_changelog(result, ran)


def test_release_push_of_main_develop_and_tag_passes(repo: Path) -> None:
    """The range on main holds the feat and its fragment; develop's holds only the release."""
    first = _git(repo, "rev-parse", "HEAD")
    _git(repo, "branch", "main", first)
    develop_before = _commit(
        repo, {"src/app.py": "x = 2\n", FRAGMENT: FRAGMENT_BODY}, "feat(app): change it"
    )
    _git(repo, "checkout", "-q", "main")
    _git(repo, "merge", "--no-ff", "-q", "-m", "chore(merge): merge develop", "develop")
    _git(repo, "rm", "-q", FRAGMENT)
    _write(repo, {"CHANGELOG.md": "# Changelog\n"})
    _git(repo, "add", "CHANGELOG.md")
    _git(repo, "commit", "-q", "--no-verify", "-m", "chore(release): v0.1.0")
    release = _git(repo, "rev-parse", "HEAD")
    _git(repo, "tag", "-a", "-m", "v0.1.0", "v0.1.0")
    tag = _git(repo, "rev-parse", "v0.1.0")
    _git(repo, "checkout", "-q", "develop")
    _git(repo, "merge", "--ff-only", "-q", "main")
    stdin = (
        _line(release, first).replace("develop", "main")
        + _line(release, develop_before)
        + _ref_line(tag, ZERO, "refs/tags/v0.1.0", "refs/tags/v0.1.0")
    )
    result, ran = _run_pre_push(repo, stdin)
    assert result.returncode == 0, result.stderr
    assert ran


def test_push_of_main_alone_passes_when_a_release_folded_the_fragment(
    repo: Path,
) -> None:
    """The fragment is added and deleted inside main's range; it still satisfies the check."""
    first = _git(repo, "rev-parse", "HEAD")
    _git(repo, "branch", "main", first)
    _commit(
        repo, {"src/app.py": "x = 2\n", FRAGMENT: FRAGMENT_BODY}, "feat(app): change it"
    )
    _git(repo, "checkout", "-q", "main")
    _git(repo, "merge", "--no-ff", "-q", "-m", "chore(merge): merge develop", "develop")
    _git(repo, "rm", "-q", FRAGMENT)
    _git(repo, "commit", "-q", "--no-verify", "-m", "chore(release): v0.1.0")
    release = _git(repo, "rev-parse", "HEAD")
    assert not (repo / FRAGMENT).exists()
    line = _ref_line(release, first, "refs/heads/main", "refs/heads/main")
    result, ran = _run_pre_push(repo, line)
    assert result.returncode == 0, result.stderr
    assert ran


def test_push_of_main_alone_is_rejected_when_the_feat_never_had_a_fragment(
    repo: Path,
) -> None:
    first = _git(repo, "rev-parse", "HEAD")
    _git(repo, "branch", "main", first)
    _commit(repo, {"src/app.py": "x = 2\n"}, "feat(app): change it")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "merge", "--no-ff", "-q", "-m", "chore(merge): merge develop", "develop")
    release = _git(repo, "rev-parse", "HEAD")
    line = _ref_line(release, first, "refs/heads/main", "refs/heads/main")
    result, ran = _run_pre_push(repo, line)
    _assert_rejected_by_changelog(result, ran)


# --- pre-commit ---------------------------------------------------------------


def _run_pre_commit(
    repo: Path,
    gate_exit: int = 0,
    fix_body: str | None = None,
    record_paths: str | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    """Run the hook against the current index; return the result and both marker files.

    `record_paths` replaces RECORD_PATHS in the copied config.
    """
    gate_marker, fix_marker = _install_gate_stubs(repo, gate_exit)
    if record_paths is not None:
        config = repo / "scripts" / "config" / "gate.sh"
        config.write_text(
            config.read_text(encoding="utf-8") + f'\nRECORD_PATHS="{record_paths}"\n',
            encoding="utf-8",
        )
    if fix_body is not None:
        _stub(
            repo / "scripts" / "autofix.sh", f'echo "$@" > "{fix_marker}"\n{fix_body}'
        )
    result = subprocess.run(
        ["sh", "-e", str(PRE_COMMIT)],
        cwd=repo,
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )
    return result, gate_marker, fix_marker


def test_pre_commit_nothing_staged_exits_clean(repo: Path) -> None:
    result, gate, fix = _run_pre_commit(repo)
    assert result.returncode == 0, result.stderr
    assert not gate.exists()
    assert not fix.exists()


def test_pre_commit_agents_records_only_skips_everything(repo: Path) -> None:
    _write(repo, {".agents/tasks/T-0002.md": "t\n", ".agents/tasks/BACKLOG.md": "b\n"})
    _git(repo, "add", "-A")
    result, gate, fix = _run_pre_commit(repo)
    assert result.returncode == 0, result.stderr
    assert not gate.exists()
    assert not fix.exists()
    assert "skipping gate" in result.stdout


def test_pre_commit_file_outside_agents_runs_staged_gate(repo: Path) -> None:
    _write(repo, {"src/app.py": "x = 2\n"})
    _git(repo, "add", "-A")
    result, gate, fix = _run_pre_commit(repo)
    assert result.returncode == 0, result.stderr
    assert gate.read_text().strip() == "--staged"
    assert fix.read_text().strip() == "--staged"


def test_pre_commit_tooling_scripts_run_staged_gate(repo: Path) -> None:
    _write(repo, {".agents/tasks/scripts/task.py": "x = 1\n"})
    _git(repo, "add", "-A")
    result, gate, _ = _run_pre_commit(repo)
    assert result.returncode == 0, result.stderr
    assert gate.exists()


def test_pre_commit_failing_gate_blocks_commit(repo: Path) -> None:
    _write(repo, {"src/app.py": "x = 2\n"})
    _git(repo, "add", "-A")
    result, gate, _ = _run_pre_commit(repo, gate_exit=1)
    assert gate.exists()
    assert result.returncode != 0


def test_pre_commit_restages_only_staged_files_after_autofix(repo: Path) -> None:
    _write(repo, {"src/app.py": "x = 2\n"})
    _git(repo, "add", "src/app.py")
    _write(repo, {".agents/tasks/T-0001.md": "dirty, never staged\n"})
    result, _, _ = _run_pre_commit(
        repo,
        fix_body="printf 'x = 3\\n' >> src/app.py; printf 'more\\n' >> .agents/tasks/T-0001.md",
    )
    assert result.returncode == 0, result.stderr
    staged_diff = _git(repo, "diff", "--cached", "--", "src/app.py")
    assert "+x = 3" in staged_diff
    assert _git(repo, "diff", "--cached", "--name-only") == "src/app.py"


@pytest.mark.parametrize(
    "name",
    ["sp ace.py", 'quo"te.py', "it's.py", "čšž.py", "new\nline.py"],
    ids=["space", "double-quote", "single-quote", "non-ascii", "newline"],
)
def test_pre_commit_restages_unusual_filenames_after_autofix(
    repo: Path, name: str
) -> None:
    _write(repo, {name: "x = 2\n"})
    _git(repo, "add", "--", name)
    result, gate, _ = _run_pre_commit(
        repo, fix_body=f"printf 'x = 3\\n' >> {shlex.quote(name)}"
    )
    assert result.returncode == 0, result.stderr
    assert gate.exists()
    assert _git(repo, "show", f":{name}") == "x = 2\nx = 3"


def test_pre_commit_restage_treats_glob_characters_literally(repo: Path) -> None:
    """A staged `a[1].py` must not sweep in the unstaged, modified `a1.py` via pathspec globbing."""
    _commit(repo, {"a1.py": "x = 1\n"})
    _write(repo, {"a[1].py": "x = 2\n", "a1.py": "x = 9\n"})
    _git(repo, "add", "--", ":(literal)a[1].py")
    assert _git(repo, "diff", "--cached", "--name-only") == "a[1].py"
    result, _, _ = _run_pre_commit(repo, fix_body="printf 'x = 3\\n' >> 'a[1].py'")
    assert result.returncode == 0, result.stderr
    assert _git(repo, "show", ":a[1].py") == "x = 2\nx = 3"
    assert _git(repo, "diff", "--cached", "--name-only") == "a[1].py"


def test_pre_commit_rename_into_agents_runs_gate(repo: Path) -> None:
    _git(repo, "mv", "src/app.py", ".agents/app.py")
    result, gate, _ = _run_pre_commit(repo)
    assert result.returncode == 0, result.stderr
    assert gate.exists()
    assert "skipping gate" not in result.stdout


def test_pre_commit_rename_within_agents_skips_gate(repo: Path) -> None:
    _git(repo, "mv", ".agents/tasks/T-0001.md", ".agents/tasks/T-0009.md")
    result, gate, fix = _run_pre_commit(repo)
    assert result.returncode == 0, result.stderr
    assert not gate.exists()
    assert not fix.exists()
    assert "skipping gate" in result.stdout


def test_pre_commit_deleting_file_outside_agents_runs_gate(repo: Path) -> None:
    """Parity with pre-push, which lists deletions too: removing src/ code is not a records-only commit."""
    _git(repo, "rm", "-q", "src/app.py")
    result, gate, _ = _run_pre_commit(repo)
    assert result.returncode == 0, result.stderr
    assert gate.exists()


@pytest.mark.parametrize(
    "name",
    [
        ".agents/tasks/T-0002-new-task.md",
        ".agents/tasks/reports/T-0002.md",
        ".agents/tasks/BACKLOG.md",
        ".agents/tasks/.counter",
        ".agents/LESSONS.md",
        ".agents/plans/2026-10-05-a-plan.md",
    ],
)
def test_pre_commit_each_record_path_alone_skips_gate(repo: Path, name: str) -> None:
    _write(repo, {name: "r\n"})
    _git(repo, "add", "-A")
    result, gate, fix = _run_pre_commit(repo)
    assert result.returncode == 0, result.stderr
    assert not gate.exists()
    assert not fix.exists()
    assert "skipping gate" in result.stdout


@pytest.mark.parametrize(
    "name",
    [
        ".agents/README.md",
        ".agents/tasks/templates/task.md",
        ".agents/tasks/notes.md",
        ".agents/other/T-0002.md",
    ],
)
def test_pre_commit_agents_paths_that_are_not_records_run_gate(
    repo: Path, name: str
) -> None:
    _write(repo, {name: "r\n"})
    _git(repo, "add", "-A")
    result, gate, _ = _run_pre_commit(repo)
    assert result.returncode == 0, result.stderr
    assert gate.exists()
    assert "skipping gate" not in result.stdout


def test_pre_commit_rename_into_a_record_path_runs_gate(repo: Path) -> None:
    (repo / ".agents" / "plans").mkdir(parents=True)
    _git(repo, "mv", "src/app.py", ".agents/plans/app.py")
    result, gate, _ = _run_pre_commit(repo)
    assert result.returncode == 0, result.stderr
    assert gate.exists()


def test_pre_commit_skip_rule_follows_record_paths_of_the_config(repo: Path) -> None:
    _write(repo, {"notes/n.md": "n\n", ".agents/plans/p.md": "p\n"})
    _git(repo, "add", "notes/n.md")
    result, gate, _ = _run_pre_commit(repo, record_paths="notes/")
    assert result.returncode == 0, result.stderr
    assert not gate.exists()
    _git(repo, "add", ".agents/plans/p.md")
    result, gate, _ = _run_pre_commit(repo, record_paths="notes/")
    assert result.returncode == 0, result.stderr
    assert gate.exists()


# --- gate.sh / autofix.sh --staged --------------------------------------------


@pytest.fixture
def tool_repo(tmp_path: Path) -> Path:
    """A repo holding a copy of scripts/ whose config logs every command's arguments."""
    repo = tmp_path / "tool"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "develop")
    shutil.copytree(
        SCRIPTS, repo / "scripts", ignore=shutil.ignore_patterns("__pycache__")
    )
    log = repo / "calls.log"
    config = "\n".join(
        [
            f'log() {{ echo "$1: $2" >> "{log}"; }}',
            'LINT_CMD="log lint"',
            'LINT_FIX_CMD="log lintfix"',
            'FORMAT_CHECK_CMD="log fmtcheck"',
            'FORMAT_FIX_CMD="log fmt"',
            'TYPECHECK_CMD="log ty"',
            'TEST_CMD="log test"',
            'MAIN_BRANCH="main"',
            'DEVELOP_BRANCH="develop"',
            'STAGED_GLOB="*.py"',
            "export -f log",
            "",
        ]
    )
    (repo / "scripts" / "config" / "gate.sh").write_text(config, encoding="utf-8")
    _commit(repo, {"README.md": "r\n"})
    return repo


def _run_script(
    repo: Path, script: str, *args: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(repo / "scripts" / script), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )


def _calls(repo: Path) -> list[str]:
    log = repo / "calls.log"
    return log.read_text().splitlines() if log.exists() else []


def test_gate_staged_checks_only_matching_staged_files_and_no_tests(
    tool_repo: Path,
) -> None:
    _write(tool_repo, {"a.py": "x\n", "b.txt": "y\n", "c.py": "z\n"})
    _git(tool_repo, "add", "a.py", "b.txt")
    result = _run_script(tool_repo, "gate.sh", "--staged")
    assert result.returncode == 0, result.stderr + result.stdout
    assert _calls(tool_repo) == ["lint: a.py", "fmtcheck: a.py", "ty: a.py"]


def test_gate_staged_with_nothing_matching_exits_zero_without_running(
    tool_repo: Path,
) -> None:
    _write(tool_repo, {"b.txt": "y\n"})
    _git(tool_repo, "add", "b.txt")
    result = _run_script(tool_repo, "gate.sh", "--staged")
    assert result.returncode == 0, result.stderr + result.stdout
    assert _calls(tool_repo) == []


def test_gate_without_flags_runs_whole_repo_and_tests(tool_repo: Path) -> None:
    result = _run_script(tool_repo, "gate.sh")
    assert result.returncode == 0, result.stderr + result.stdout
    assert _calls(tool_repo) == ["lint: ", "fmtcheck: ", "ty: ", "test: "]


def test_gate_fast_skips_tests(tool_repo: Path) -> None:
    result = _run_script(tool_repo, "gate.sh", "--fast")
    assert result.returncode == 0, result.stderr + result.stdout
    assert _calls(tool_repo) == ["lint: ", "fmtcheck: ", "ty: "]


def test_gate_staged_failure_exits_nonzero(tool_repo: Path) -> None:
    config = tool_repo / "scripts" / "config" / "gate.sh"
    config.write_text(
        config.read_text().replace('LINT_CMD="log lint"', 'LINT_CMD="false"'),
        encoding="utf-8",
    )
    _write(tool_repo, {"a.py": "x\n"})
    _git(tool_repo, "add", "a.py")
    result = _run_script(tool_repo, "gate.sh", "--staged")
    assert result.returncode == 1


def test_autofix_staged_fixes_only_matching_staged_files(tool_repo: Path) -> None:
    _write(tool_repo, {"a.py": "x\n", "b.txt": "y\n", "c.py": "z\n"})
    _git(tool_repo, "add", "a.py", "b.txt")
    result = _run_script(tool_repo, "autofix.sh", "--staged")
    assert result.returncode == 0, result.stderr + result.stdout
    assert _calls(tool_repo) == ["lintfix: a.py", "fmt: a.py"]


def test_autofix_staged_with_nothing_matching_does_nothing(tool_repo: Path) -> None:
    result = _run_script(tool_repo, "autofix.sh", "--staged")
    assert result.returncode == 0, result.stderr + result.stdout
    assert _calls(tool_repo) == []


@pytest.mark.parametrize("script", ["gate.sh", "autofix.sh"])
def test_scripts_avoid_bash_4_only_constructs(script: str) -> None:
    """bash 3.2 (macOS default): no mapfile/readarray, empty arrays guarded under set -u."""
    lines = (SCRIPTS / script).read_text(encoding="utf-8").splitlines()
    code = "\n".join(line for line in lines if not line.lstrip().startswith("#"))
    assert not re.search(r"\b(mapfile|readarray)\b", code)
    # Every expansion of the array is guarded, never a bare "${files[@]}".
    guarded = '${files[@]+"${files[@]}"}'
    assert '"${files[@]}"' not in code.replace(guarded, "")


# --- scripts/config/gate.sh must be sourceable by POSIX sh ----------------------


def test_gate_config_is_sourceable_by_posix_sh() -> None:
    """.husky/pre-push sources it under `sh`; bash-only syntax there would break every push."""
    names = [
        "LINT_CMD",
        "LINT_FIX_CMD",
        "FORMAT_CHECK_CMD",
        "FORMAT_FIX_CMD",
        "TYPECHECK_CMD",
        "TEST_CMD",
        "MAIN_BRANCH",
        "DEVELOP_BRANCH",
        "STAGED_GLOB",
        "RECORD_PATHS",
    ]
    script = ". " + shlex.quote(str(SCRIPTS / "config" / "gate.sh")) + "\n"
    script += "".join(f'printf "%s=%s\\n" {name} "${name}"\n' for name in names)
    result = subprocess.run(
        ["sh", "-e", "-u", "-c", script],
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )
    assert result.returncode == 0, result.stderr
    values = dict(line.split("=", 1) for line in result.stdout.splitlines())
    assert sorted(values) == sorted(names)
    assert all(values[name] for name in names)


def test_gate_config_states_it_must_stay_posix_sourceable() -> None:
    text = (SCRIPTS / "config" / "gate.sh").read_text(encoding="utf-8")
    assert "POSIX-sourceable" in text
