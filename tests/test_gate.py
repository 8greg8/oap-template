"""Tests for the gate records of `scripts/gate.sh` and its `--if-needed` mode.

Each case builds a scratch repository holding a copy of the real `scripts/`, whose config logs
every gate command with its working directory instead of running lint, typecheck and tests. The
log lives outside the repository so it never dirties the tree. `uv` and `node` are stubs on
`PATH` that print versions read from files, so a case can change a tool version. A record is
observed through behavior: whether a later `--if-needed` runs the gate again.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
RECORD_PATHS_OF_PLAN = (
    ".agents/tasks/T-*.md .agents/tasks/reports/ .agents/tasks/BACKLOG.md "
    ".agents/tasks/.counter .agents/LESSONS.md .agents/plans/"
)


class Scratch:
    """A scratch repository, its call log and its tool-version stubs."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.repo = root / "proj"
        self.log = root / "calls.log"
        self.tools = root / "tools"
        self.bin = root / "bin"

    def env(self) -> dict[str, str]:
        env: dict[str, str] = {
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "TOOLS": str(self.tools),
            "TMPDIR": str(self.root / "tmp"),
        }
        for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
            env.pop(name, None)
        return env

    def git(self, *args: str, cwd: Path | None = None) -> str:
        result = subprocess.run(
            ["git", "-C", str(cwd or self.repo), *args],
            capture_output=True,
            text=True,
            check=True,
            env=self.env(),
        )
        return result.stdout.strip()

    def write(self, files: dict[str, str]) -> None:
        for rel, content in files.items():
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def commit(self, files: dict[str, str], message: str = "c") -> str:
        self.write(files)
        self.git("add", "-A")
        self.git("commit", "-q", "--no-verify", "-m", message)
        return self.git("rev-parse", "HEAD")

    def gate(
        self, *args: str, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", "scripts/gate.sh", *args],
            cwd=cwd or self.repo,
            capture_output=True,
            text=True,
            check=False,
            env=self.env(),
        )

    def calls(self) -> list[str]:
        return self.log.read_text().splitlines() if self.log.exists() else []

    def clear_calls(self) -> None:
        self.log.unlink(missing_ok=True)

    def records(self) -> list[Path]:
        directory = Path(self.git("rev-parse", "--git-common-dir"))
        if not directory.is_absolute():
            directory = self.repo / directory
        found = directory / "gate-pass"
        return sorted(found.iterdir()) if found.is_dir() else []

    def set_tool(self, name: str, version: str) -> None:
        (self.tools / name).write_text(version + "\n", encoding="utf-8")


def _stub(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


@pytest.fixture
def scratch(tmp_path: Path) -> Scratch:
    s = Scratch(tmp_path)
    s.repo.mkdir()
    (tmp_path / "tmp").mkdir()
    _stub(
        s.bin / "uv",
        'if [ "$1" = "--version" ]; then cat "$TOOLS/uv"; else cat "$TOOLS/python"; fi',
    )
    _stub(s.bin / "node", 'cat "$TOOLS/node"')
    s.tools.mkdir()
    s.set_tool("uv", "uv 1.0.0")
    s.set_tool("python", "Python 3.12.0")
    s.set_tool("node", "v20.0.0")
    s.git("init", "-q", "-b", "develop")
    s.git("config", "core.hooksPath", "/dev/null")
    shutil.copytree(
        SCRIPTS,
        s.repo / "scripts",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    config = s.repo / "scripts" / "config" / "gate.sh"
    config.write_text(
        config.read_text(encoding="utf-8")
        + "\n".join(
            [
                "",
                f'log() {{ echo "$1 $PWD" >> "{s.log}"; }}',
                'LINT_CMD="log lint"',
                'FORMAT_CHECK_CMD="log format"',
                'TYPECHECK_CMD="log typecheck"',
                'TEST_CMD="log test"',
                "export -f log",
                "",
            ]
        ),
        encoding="utf-8",
    )
    s.commit({"src/app.py": "x = 1\n"}, "init")
    return s


def _ran(scratch: Scratch) -> list[str]:
    """The gate commands that ran, without their working directories."""
    return [line.split()[0] for line in scratch.calls()]


FULL = ["lint", "format", "typecheck", "test"]


# --- the record ----------------------------------------------------------------


def test_record_paths_are_the_plans_list() -> None:
    text = (SCRIPTS / "config" / "gate.sh").read_text(encoding="utf-8")
    assert f'RECORD_PATHS="{RECORD_PATHS_OF_PLAN}"' in text


def test_full_clean_run_writes_a_record_in_the_git_common_dir(scratch: Scratch) -> None:
    result = scratch.gate()
    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == FULL
    (record,) = scratch.records()
    body = record.read_text(encoding="utf-8")
    assert f"commit={scratch.git('rev-parse', 'HEAD')}" in body
    assert "slow_tests=yes" in body
    assert record.parent == scratch.repo / ".git" / "gate-pass"


def test_record_is_not_part_of_the_working_tree(scratch: Scratch) -> None:
    scratch.gate()
    assert scratch.git("status", "--porcelain", "--untracked-files=all") == ""


def test_fast_run_writes_no_record(scratch: Scratch) -> None:
    assert scratch.gate("--fast").returncode == 0
    assert scratch.records() == []


def test_staged_run_writes_no_record(scratch: Scratch) -> None:
    scratch.write({"b.py": "y = 1\n"})
    scratch.git("add", "b.py")
    assert scratch.gate("--staged").returncode == 0
    assert scratch.records() == []


def test_run_on_a_dirty_tree_writes_no_record(scratch: Scratch) -> None:
    scratch.write({"untracked.txt": "u\n"})
    result = scratch.gate()
    assert result.returncode == 0
    assert "not clean" in result.stderr
    assert scratch.records() == []


def test_run_on_a_modified_tracked_file_writes_no_record(scratch: Scratch) -> None:
    scratch.write({"src/app.py": "x = 2\n"})
    assert scratch.gate().returncode == 0
    assert scratch.records() == []


def test_run_that_dirties_the_tree_writes_no_record(scratch: Scratch) -> None:
    config = scratch.repo / "scripts" / "config" / "gate.sh"
    scratch.commit(
        {
            "scripts/config/gate.sh": config.read_text(encoding="utf-8")
            + 'TEST_CMD="touch generated.txt"\n'
        }
    )
    result = scratch.gate()
    assert result.returncode == 0
    assert "changed the working tree" in result.stderr
    assert scratch.records() == []


def test_failing_gate_writes_no_record(scratch: Scratch) -> None:
    config = scratch.repo / "scripts" / "config" / "gate.sh"
    scratch.commit(
        {
            "scripts/config/gate.sh": config.read_text(encoding="utf-8")
            + 'TYPECHECK_CMD="false"\n'
        }
    )
    assert scratch.gate().returncode == 1
    assert scratch.records() == []


def test_unknown_arguments_are_refused(scratch: Scratch) -> None:
    assert scratch.gate("--nope").returncode == 1
    assert scratch.gate("HEAD").returncode == 1
    assert scratch.gate("--fast", "--if-needed").returncode == 1
    assert scratch.gate("--staged", "--if-needed").returncode == 1
    assert scratch.calls() == []


# --- the key -------------------------------------------------------------------

RECORD_FILES = {
    ".agents/tasks/T-0002-a-task.md": "task\n",
    ".agents/tasks/reports/T-0002.md": "report\n",
    ".agents/tasks/BACKLOG.md": "backlog\n",
    ".agents/tasks/.counter": "2\n",
    ".agents/LESSONS.md": "lessons\n",
    ".agents/plans/2026-10-05-p.md": "plan\n",
}

CODE_FILES = {
    "src/app.py": "x = 2\n",
    ".agents/README.md": "readme\n",
    ".agents/tasks/scripts/task.py": "x = 1\n",
    ".agents/tasks/templates/task.md": "template\n",
    ".agents/other/T-0003.md": "elsewhere\n",
    "README.md": "r\n",
}


def test_changing_record_paths_keeps_the_key(scratch: Scratch) -> None:
    assert scratch.gate().returncode == 0
    scratch.clear_calls()
    scratch.commit(RECORD_FILES, "chore: records")
    scratch.commit({k: v + "more\n" for k, v in RECORD_FILES.items()}, "chore: edit")
    result = scratch.gate("--if-needed")
    assert result.returncode == 0, result.stderr + result.stdout
    assert scratch.calls() == []
    assert len(scratch.records()) == 1


@pytest.mark.parametrize("name", sorted(CODE_FILES))
def test_changing_any_other_tracked_file_changes_the_key(
    scratch: Scratch, name: str
) -> None:
    assert scratch.gate().returncode == 0
    scratch.clear_calls()
    scratch.commit({name: CODE_FILES[name]}, "change")
    result = scratch.gate("--if-needed")
    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == FULL
    assert len(scratch.records()) == 2


def test_deleting_a_code_file_changes_the_key(scratch: Scratch) -> None:
    assert scratch.gate().returncode == 0
    scratch.clear_calls()
    scratch.git("rm", "-q", "src/app.py")
    scratch.git("commit", "-q", "--no-verify", "-m", "rm")
    assert scratch.gate("--if-needed").returncode == 0
    assert _ran(scratch) == FULL


def test_reverting_to_passed_code_reuses_its_record(scratch: Scratch) -> None:
    assert scratch.gate().returncode == 0
    scratch.commit({"src/app.py": "x = 2\n"})
    scratch.commit({"src/app.py": "x = 1\n"})
    scratch.clear_calls()
    assert scratch.gate("--if-needed").returncode == 0
    assert scratch.calls() == []


@pytest.mark.parametrize(
    ("tool", "version"),
    [
        ("uv", "uv 1.0.1"),
        ("python", "Python 3.12.1"),
        ("node", "v20.1.0"),
    ],
)
def test_changing_a_tool_version_changes_the_key(
    scratch: Scratch, tool: str, version: str
) -> None:
    assert scratch.gate().returncode == 0
    scratch.clear_calls()
    assert scratch.gate("--if-needed").returncode == 0
    assert scratch.calls() == []
    scratch.set_tool(tool, version)
    assert scratch.gate("--if-needed").returncode == 0
    assert _ran(scratch) == FULL
    assert len(scratch.records()) == 2


def test_a_missing_tool_changes_the_key_and_does_not_fail(scratch: Scratch) -> None:
    """Without the stub, node is either absent or a real version other than the stub's."""
    assert scratch.gate().returncode == 0
    scratch.clear_calls()
    (scratch.bin / "node").unlink()
    result = scratch.gate("--if-needed")
    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == FULL


def test_config_without_record_paths_still_works(scratch: Scratch) -> None:
    config = scratch.repo / "scripts" / "config" / "gate.sh"
    lines = [
        ln
        for ln in config.read_text(encoding="utf-8").splitlines()
        if not ln.startswith("RECORD_PATHS=")
    ]
    scratch.commit({"scripts/config/gate.sh": "\n".join(lines) + "\n"})
    assert scratch.gate().returncode == 0
    scratch.clear_calls()
    scratch.commit({".agents/tasks/T-0002-a.md": "t\n"})
    assert scratch.gate("--if-needed").returncode == 0
    assert _ran(scratch) == FULL


# --- --if-needed ---------------------------------------------------------------


def test_if_needed_defaults_to_head_and_runs_then_skips(scratch: Scratch) -> None:
    first = scratch.gate("--if-needed")
    assert first.returncode == 0, first.stderr + first.stdout
    assert _ran(scratch) == FULL
    scratch.clear_calls()
    second = scratch.gate("--if-needed")
    assert second.returncode == 0
    assert scratch.calls() == []
    assert "skipped" in second.stdout


def test_if_needed_on_the_checked_out_clean_commit_runs_in_the_checkout(
    scratch: Scratch,
) -> None:
    assert scratch.gate("--if-needed").returncode == 0
    assert {line.split(maxsplit=1)[1] for line in scratch.calls()} == {
        str(scratch.repo.resolve())
    }
    assert scratch.git("worktree", "list", "--porcelain").count("worktree ") == 1


def test_if_needed_with_several_commits_skips_only_those_with_records(
    scratch: Scratch,
) -> None:
    a = scratch.commit({"src/app.py": "x = 2\n"})
    assert scratch.gate("--if-needed", a).returncode == 0
    b = scratch.commit({"src/app.py": "x = 3\n"})
    c = scratch.commit({"src/app.py": "x = 4\n"})
    scratch.clear_calls()
    result = scratch.gate("--if-needed", a, b, c)
    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == FULL + FULL
    scratch.clear_calls()
    assert scratch.gate("--if-needed", a, b, c).returncode == 0
    assert scratch.calls() == []
    assert len(scratch.records()) == 3


def test_if_needed_with_the_same_commit_twice_runs_once(scratch: Scratch) -> None:
    head = scratch.git("rev-parse", "HEAD")
    assert scratch.gate("--if-needed", head, "HEAD", "develop").returncode == 0
    assert _ran(scratch) == FULL


def test_if_needed_fails_when_any_commit_fails_the_gate(scratch: Scratch) -> None:
    good = scratch.commit({"src/app.py": "x = 2\n"})
    config = scratch.repo / "scripts" / "config" / "gate.sh"
    bad = scratch.commit(
        {
            "scripts/config/gate.sh": config.read_text(encoding="utf-8")
            + 'LINT_CMD="false"\n'
        }
    )
    result = scratch.gate("--if-needed", good, bad)
    assert result.returncode == 1
    assert "gate failed" in result.stderr
    assert len(scratch.records()) == 1


def test_if_needed_with_an_unknown_commit_fails(scratch: Scratch) -> None:
    result = scratch.gate("--if-needed", "no-such-commit")
    assert result.returncode == 1
    assert "not a commit" in result.stderr
    assert scratch.calls() == []


def test_if_needed_gates_a_commit_that_is_not_checked_out_in_a_temporary_worktree(
    scratch: Scratch,
) -> None:
    scratch.git("checkout", "-q", "-b", "side")
    side = scratch.commit({"src/app.py": "x = 5\n"}, "side work")
    scratch.git("checkout", "-q", "develop")
    assert scratch.git("rev-parse", "HEAD") != side
    result = scratch.gate("--if-needed", side)
    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == FULL
    where = {line.split(maxsplit=1)[1] for line in scratch.calls()}
    assert len(where) == 1
    (cwd,) = where
    assert cwd != str(scratch.repo.resolve())
    assert not Path(cwd).exists()
    assert scratch.git("worktree", "list", "--porcelain").count("worktree ") == 1
    assert list((scratch.root / "tmp").iterdir()) == []
    assert len(scratch.records()) == 1
    scratch.clear_calls()
    assert scratch.gate("--if-needed", side).returncode == 0
    assert scratch.calls() == []


def test_if_needed_uses_a_temporary_worktree_when_the_checkout_is_dirty(
    scratch: Scratch,
) -> None:
    scratch.write({"untracked.txt": "u\n"})
    result = scratch.gate("--if-needed")
    assert result.returncode == 0, result.stderr + result.stdout
    (cwd,) = {line.split(maxsplit=1)[1] for line in scratch.calls()}
    assert cwd != str(scratch.repo.resolve())
    assert (scratch.repo / "untracked.txt").exists()
    assert len(scratch.records()) == 1


def test_if_needed_works_from_a_linked_worktree_and_shares_records(
    scratch: Scratch,
) -> None:
    other = scratch.root / "other"
    scratch.git("worktree", "add", "-q", "--detach", str(other), "HEAD")
    assert scratch.gate("--if-needed", cwd=other).returncode == 0
    assert _ran(scratch) == FULL
    scratch.clear_calls()
    assert scratch.gate("--if-needed").returncode == 0
    assert scratch.calls() == []


def test_a_failing_gate_in_a_temporary_worktree_still_removes_it(
    scratch: Scratch,
) -> None:
    scratch.git("checkout", "-q", "-b", "side")
    config = scratch.repo / "scripts" / "config" / "gate.sh"
    side = scratch.commit(
        {
            "scripts/config/gate.sh": config.read_text(encoding="utf-8")
            + 'TEST_CMD="false"\n'
        }
    )
    scratch.git("checkout", "-q", "develop")
    result = scratch.gate("--if-needed", side)
    assert result.returncode == 1
    assert scratch.git("worktree", "list", "--porcelain").count("worktree ") == 1
    assert list((scratch.root / "tmp").iterdir()) == []
    assert scratch.records() == []


def test_if_needed_never_refuses_for_want_of_a_checkout(scratch: Scratch) -> None:
    """A commit on no branch at all, with a different commit checked out, is still gated."""
    orphan = scratch.git("commit-tree", "HEAD^{tree}", "-m", "unreachable")
    result = scratch.gate("--if-needed", orphan)
    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == FULL
