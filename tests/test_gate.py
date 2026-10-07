"""Tests for the gate records of `scripts/gate.sh` and its `--if-needed` mode.

Each case builds a scratch repository holding a copy of the real `scripts/`, whose config logs
every gate command with its working directory instead of running lint, typecheck and tests,
through a `log` stub on `PATH` (the config stays POSIX-sourceable, as `.husky/pre-push` needs). The
log lives outside the repository so it never dirties the tree. `uv` and `node` are stubs on
`PATH` that print versions read from files, so a case can change a tool version. A record is
observed through behavior: whether a later `--if-needed` runs the gate again. The test command
logs as `test` and, when the gate appended the skip arguments for the slow tests, as `test-no-slow`.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
RECORD_PATHS_OF_PLAN = (
    ".agents/tasks/T-*.md .agents/tasks/reports/** .agents/tasks/BACKLOG.md "
    ".agents/tasks/.counter .agents/LESSONS.md .agents/plans/**"
)
PRE_PUSH = REPO_ROOT / ".husky" / "pre-push"
KEY = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


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
    _stub(
        s.bin / "log",
        'name="$1"\n[ "$3" = "not slow" ] && name="$1-no-slow"\n'
        f'echo "$name $PWD" >> "{s.log}"',
    )
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
        + '\nLINT_CMD="log lint"\nFORMAT_CHECK_CMD="log format"\n'
        + 'TYPECHECK_CMD="log typecheck"\nTEST_CMD="log test"\n',
        encoding="utf-8",
    )
    s.commit({"src/app.py": "x = 1\n"}, "init")
    return s


def _ran(scratch: Scratch) -> list[str]:
    """The gate commands that ran, without their working directories."""
    return [line.split()[0] for line in scratch.calls()]


FULL = ["lint", "format", "typecheck", "test"]
NO_SLOW = ["lint", "format", "typecheck", "test-no-slow"]


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
    assert "slow=yes" in body.splitlines()
    assert record.parent == scratch.repo / ".git" / "gate-pass"


def test_record_file_layout_and_output(scratch: Scratch) -> None:
    result = scratch.gate()
    assert result.returncode == 0, result.stderr + result.stdout
    (record,) = scratch.records()
    key = record.name
    assert KEY.fullmatch(key)
    lines = record.read_text(encoding="utf-8").splitlines()
    assert [line.split("=", 1)[0] for line in lines] == [
        "key",
        "commit",
        "slow",
        "date",
    ]
    assert lines[0] == f"key={key}"
    assert lines[1] == f"commit={scratch.git('rev-parse', 'HEAD')}"
    assert lines[2] == "slow=yes"
    out = result.stdout
    assert out.index(f"gate record {key} (slow tests: yes)") < out.index("gate clean")


def test_dirty_run_says_why_it_wrote_no_record(scratch: Scratch) -> None:
    scratch.write({"untracked.txt": "u\n"})
    result = scratch.gate()
    assert "dirty tree" in result.stderr
    assert "gate record" not in result.stdout


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
    assert "dirty tree" in result.stderr
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
    assert "dirty tree after the run" in result.stderr
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
    ".agents/tasks/reports/deep/er/T-0002.md": "report\n",
    ".agents/tasks/BACKLOG.md": "backlog\n",
    ".agents/tasks/.counter": "2\n",
    ".agents/LESSONS.md": "lessons\n",
    ".agents/plans/2026-10-05-p.md": "plan\n",
    ".agents/plans/sub/dir/p.md": "plan\n",
}

CODE_FILES = {
    "src/app.py": "x = 2\n",
    ".agents/README.md": "readme\n",
    ".agents/tasks/scripts/task.py": "x = 1\n",
    ".agents/tasks/templates/task.md": "template\n",
    ".agents/other/T-0003.md": "elsewhere\n",
    ".agents/tasks/sub/T-0004.md": "nested task\n",
    ".agents/tasks/T-0005/inner.md": "inside a task directory\n",
    ".agents/LESSONS.md.bak": "backup\n",
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


# --- pre-push from a linked worktree --------------------------------------------


def test_develop_push_from_a_linked_worktree_gates_a_commit_that_is_not_checked_out(
    scratch: Scratch,
) -> None:
    """The real hook, run from a linked worktree whose HEAD is not the pushed commit."""
    old = scratch.git("rev-parse", "HEAD")
    scratch.git("checkout", "-q", "-b", "candidate")
    pushed = scratch.commit({"src/app.py": "x = 7\n"}, "candidate work")
    scratch.git("checkout", "-q", "develop")
    linked = scratch.root / "linked"
    scratch.git("worktree", "add", "-q", "--detach", str(linked), old)
    assert scratch.git("rev-parse", "HEAD", cwd=linked) == old
    line = f"refs/heads/develop {pushed} refs/heads/develop {old}\n"

    result = subprocess.run(
        ["sh", "-e", str(PRE_PUSH), "origin", "https://example.invalid/repo.git"],
        input=line,
        cwd=linked,
        capture_output=True,
        text=True,
        env=scratch.env(),
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == FULL
    (cwd,) = {line.split(maxsplit=1)[1] for line in scratch.calls()}
    assert cwd not in {str(scratch.repo.resolve()), str(linked.resolve())}
    assert not Path(cwd).exists()
    assert scratch.git("worktree", "list", "--porcelain").count("worktree ") == 2
    assert list((scratch.root / "tmp").iterdir()) == []
    (record,) = scratch.records()
    assert f"commit={pushed}" in record.read_text(encoding="utf-8")
    # The same push again finds the record and runs nothing.
    scratch.clear_calls()
    again = subprocess.run(
        ["sh", "-e", str(PRE_PUSH), "origin", "https://example.invalid/repo.git"],
        input=line,
        cwd=linked,
        capture_output=True,
        text=True,
        env=scratch.env(),
        check=False,
    )
    assert again.returncode == 0, again.stderr + again.stdout
    assert scratch.calls() == []


def test_if_needed_survives_git_environment_variables_from_a_hook(
    scratch: Scratch,
) -> None:
    scratch.git("checkout", "-q", "-b", "side")
    side = scratch.commit({"src/app.py": "x = 5\n"}, "side work")
    scratch.git("checkout", "-q", "develop")
    env = scratch.env()
    env["GIT_INDEX_FILE"] = str(scratch.repo / ".git" / "no-such-index")
    env["GIT_PREFIX"] = ""
    result = subprocess.run(
        ["bash", "scripts/gate.sh", "--if-needed", side],
        cwd=scratch.repo,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == FULL


# --- the slow tests -------------------------------------------------------------

SAFE_LISTED = {
    ".agents/tasks/T-0002-a-task.md": "task\n",
    ".agents/tasks/reports/T-0002.md": "report\n",
    ".agents/tasks/BACKLOG.md": "backlog\n",
    ".agents/tasks/.counter": "2\n",
    ".agents/LESSONS.md": "lessons\n",
    ".agents/plans/2026-10-05-p.md": "plan\n",
    "changelog.d/T-0002.added.md": "- Added it.\n",
    "CONTRIBUTING.md": "c\n",
    "DEV_TOOLING_SPEC.md": "d\n",
    "PYTHON_CONVENTIONS.md": "p\n",
    "NOTICE.md": "n\n",
}

NOT_SAFE_LISTED = {
    "src/app.py": "x = 2\n",
    "README.md": "r\n",
    "changelog.d/README.md": "readme\n",
    "changelog.d/sub/T-0002.added.md": "- Added it.\n",
    "docs/CONTRIBUTING.md": "nested\n",
    ".agents/README.md": "readme\n",
    ".agents/tasks/scripts/task.py": "x = 1\n",
    ".agents/tasks/templates/report.md": "template\n",
    "scripts/extra.sh": "echo\n",
    "tests/test_x.py": "def test_x(): pass\n",
    "CONTRIBUTING.md.bak": "backup\n",
}


def _branch(scratch: Scratch, name: str = "feat/x") -> None:
    scratch.git("checkout", "-q", "-b", name)


def _slow_flag(scratch: Scratch) -> list[str]:
    return [
        line
        for record in scratch.records()
        for line in record.read_text(encoding="utf-8").splitlines()
        if line.startswith("slow=")
    ]


def test_slow_safe_paths_are_the_plans_list() -> None:
    script = (
        f". {SCRIPTS / 'config' / 'gate.sh'}\n"
        'printf "%s" "$SLOW_SAFE_PATHS"\nprintf "\\n%s" "$TEST_SKIP_SLOW_ARGS"\n'
    )
    result = subprocess.run(
        ["sh", "-e", "-u", "-c", script], capture_output=True, text=True, check=True
    )
    paths, skip_args = result.stdout.split("\n", 1)
    assert paths.split() == [
        *RECORD_PATHS_OF_PLAN.split(),
        "changelog.d/*.*.md",
        "CONTRIBUTING.md",
        "DEV_TOOLING_SPEC.md",
        "PYTHON_CONVENTIONS.md",
        "NOTICE.md",
    ]
    assert skip_args == '-m "not slow"'


@pytest.mark.parametrize("name", sorted(SAFE_LISTED))
def test_a_change_only_to_a_safe_listed_path_skips_the_slow_tests(
    scratch: Scratch, name: str
) -> None:
    _branch(scratch)
    scratch.commit({name: SAFE_LISTED[name]})
    result = scratch.gate()
    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == NO_SLOW
    assert _slow_flag(scratch) == ["slow=no"]
    assert "(slow tests: no)" in result.stdout
    assert "slow tests: skipped" in result.stderr


@pytest.mark.parametrize("name", sorted(NOT_SAFE_LISTED))
def test_a_change_to_any_other_path_runs_the_slow_tests(
    scratch: Scratch, name: str
) -> None:
    _branch(scratch)
    scratch.commit({name: NOT_SAFE_LISTED[name]})
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == FULL
    assert _slow_flag(scratch) == ["slow=yes"]


def test_one_unsafe_path_among_safe_ones_runs_the_slow_tests(scratch: Scratch) -> None:
    _branch(scratch)
    scratch.commit({"CONTRIBUTING.md": "c\n", ".agents/tasks/T-0002-a.md": "t\n"})
    scratch.commit({"src/app.py": "x = 2\n"})
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == FULL


def test_a_change_that_a_later_commit_reverts_is_not_a_change(scratch: Scratch) -> None:
    """The change set is the diff against the base, so an unsafe edit that was undone is gone."""
    _branch(scratch)
    scratch.commit({"src/app.py": "x = 2\n"})
    scratch.commit({"src/app.py": "x = 1\n", "NOTICE.md": "n\n"})
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == NO_SLOW


def test_an_empty_change_set_runs_the_slow_tests(scratch: Scratch) -> None:
    _branch(scratch)
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == FULL


def test_deleting_a_safe_listed_file_is_a_safe_change(scratch: Scratch) -> None:
    scratch.commit({"NOTICE.md": "n\n"})
    _branch(scratch)
    scratch.git("rm", "-q", "NOTICE.md")
    scratch.git("commit", "-q", "--no-verify", "-m", "rm")
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == NO_SLOW


def test_renaming_into_a_safe_listed_path_counts_the_old_path(scratch: Scratch) -> None:
    """With --no-renames the source of a rename is a change too: here it is code."""
    _branch(scratch)
    scratch.git("mv", "src/app.py", "NOTICE.md")
    scratch.git("commit", "-q", "--no-verify", "-m", "mv")
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == FULL


def test_the_working_tree_counts_modified_and_untracked_files(scratch: Scratch) -> None:
    _branch(scratch)
    scratch.write({"NOTICE.md": "n\n"})
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == NO_SLOW
    assert scratch.records() == []  # a dirty tree writes no record
    scratch.clear_calls()
    scratch.write({"src/app.py": "x = 2\n"})
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == FULL
    scratch.git("checkout", "-q", "--", "src/app.py")
    scratch.write({"untracked.py": "u = 1\n"})
    scratch.clear_calls()
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == FULL


def test_staged_changes_count_as_working_tree_changes(scratch: Scratch) -> None:
    _branch(scratch)
    scratch.write({"src/app.py": "x = 2\n", "NOTICE.md": "n\n"})
    scratch.git("add", "-A")
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == FULL


def test_all_runs_the_slow_tests_for_a_safe_change(scratch: Scratch) -> None:
    _branch(scratch)
    scratch.commit({"NOTICE.md": "n\n"})
    result = scratch.gate("--all")
    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == FULL
    assert _slow_flag(scratch) == ["slow=yes"]
    assert "slow tests: skipped" not in result.stderr


def test_all_cannot_be_combined_with_fast_or_staged(scratch: Scratch) -> None:
    assert scratch.gate("--all", "--fast").returncode == 1
    assert scratch.gate("--all", "--staged").returncode == 1
    assert scratch.calls() == []


def test_fast_and_staged_runs_are_unchanged_by_the_slow_selection(
    scratch: Scratch,
) -> None:
    _branch(scratch)
    scratch.commit({"NOTICE.md": "n\n"})
    assert scratch.gate("--fast").returncode == 0
    assert _ran(scratch) == ["lint", "format", "typecheck"]


@pytest.mark.parametrize(
    "setting", ['TEST_SKIP_SLOW_ARGS=""', 'SLOW_SAFE_PATHS=""', "unset SLOW_SAFE_PATHS"]
)
def test_without_skip_arguments_or_a_safe_list_the_slow_tests_always_run(
    scratch: Scratch, setting: str
) -> None:
    config = scratch.repo / "scripts" / "config" / "gate.sh"
    scratch.commit(
        {"scripts/config/gate.sh": config.read_text(encoding="utf-8") + setting + "\n"}
    )
    _branch(scratch)
    scratch.commit({"NOTICE.md": "n\n"})
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == FULL


def test_the_base_is_the_remote_develop_when_it_exists(scratch: Scratch) -> None:
    """Local develop moved on with code; origin/develop did not. The code is in the change."""
    init = scratch.git("rev-parse", "HEAD")
    scratch.commit({"src/app.py": "x = 2\n"})
    _branch(scratch)
    scratch.commit({"NOTICE.md": "n\n"})
    # Without a remote ref the local branch is the base, and only the doc is a change.
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == NO_SLOW
    scratch.clear_calls()
    scratch.git("update-ref", "refs/remotes/origin/develop", init)
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == FULL


def test_a_hotfix_branch_takes_main_as_its_base(scratch: Scratch) -> None:
    scratch.git("branch", "main")
    scratch.git("checkout", "-q", "main")
    scratch.commit({"src/app.py": "x = 2\n"}, "main moved")
    scratch.git("checkout", "-q", "-b", "hotfix/x")
    scratch.commit({"NOTICE.md": "n\n"})
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == NO_SLOW
    scratch.clear_calls()
    # The same commit on another branch takes develop as its base, and so sees the code.
    scratch.git("checkout", "-q", "-B", "feat/x")
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == FULL
    scratch.clear_calls()
    # A detached HEAD takes the develop base too.
    scratch.git("checkout", "-q", "--detach")
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == FULL


def test_a_hotfix_branch_prefers_origin_main_and_falls_back_to_local_main(
    scratch: Scratch,
) -> None:
    init = scratch.git("rev-parse", "HEAD")
    scratch.git("branch", "main")
    scratch.git("checkout", "-q", "main")
    scratch.commit({"src/app.py": "x = 2\n"}, "main moved")
    scratch.git("checkout", "-q", "-b", "hotfix/x")
    scratch.commit({"NOTICE.md": "n\n"})
    scratch.git("update-ref", "refs/remotes/origin/main", init)
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == FULL


def test_without_any_base_branch_the_slow_tests_run(scratch: Scratch) -> None:
    scratch.git("checkout", "-q", "-b", "elsewhere")
    scratch.git("branch", "-D", "develop")
    scratch.commit({"NOTICE.md": "n\n"})
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == FULL


def test_a_remote_ref_without_a_merge_base_runs_the_slow_tests(
    scratch: Scratch,
) -> None:
    scratch.git("checkout", "-q", "--orphan", "other")
    scratch.git("commit", "-q", "--no-verify", "--allow-empty", "-m", "unrelated")
    unrelated = scratch.git("rev-parse", "HEAD")
    scratch.git("checkout", "-q", "-b", "feat/x", "develop")
    scratch.commit({"NOTICE.md": "n\n"})
    scratch.git("update-ref", "refs/remotes/origin/develop", unrelated)
    assert scratch.gate().returncode == 0
    assert _ran(scratch) == FULL


# --- the slow tests and the record ------------------------------------------------


def test_a_run_without_slow_tests_is_recorded_and_reused_for_the_same_change(
    scratch: Scratch,
) -> None:
    _branch(scratch)
    scratch.commit({"NOTICE.md": "n\n"})
    assert scratch.gate("--if-needed").returncode == 0
    assert _ran(scratch) == NO_SLOW
    assert _slow_flag(scratch) == ["slow=no"]
    scratch.clear_calls()
    again = scratch.gate("--if-needed")
    assert again.returncode == 0
    assert scratch.calls() == []
    assert "skipped" in again.stdout


def test_if_needed_all_does_not_accept_a_record_without_slow_tests(
    scratch: Scratch,
) -> None:
    _branch(scratch)
    scratch.commit({"NOTICE.md": "n\n"})
    assert scratch.gate("--if-needed").returncode == 0
    scratch.clear_calls()
    result = scratch.gate("--if-needed", "--all")
    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == FULL
    assert _slow_flag(scratch) == ["slow=yes"]
    scratch.clear_calls()
    # A record with slow tests satisfies every check, --all included.
    assert scratch.gate("--if-needed", "--all").returncode == 0
    assert scratch.gate("--all", "--if-needed").returncode == 0
    assert scratch.gate("--if-needed").returncode == 0
    assert scratch.calls() == []


def test_a_record_without_slow_tests_does_not_satisfy_a_change_that_needs_them(
    scratch: Scratch,
) -> None:
    """The same tree under a hotfix base (code since main: none) and a develop base (code)."""
    scratch.git("branch", "main")
    scratch.git("checkout", "-q", "main")
    scratch.commit({"src/app.py": "x = 2\n"}, "main moved")
    scratch.git("checkout", "-q", "-b", "hotfix/x")
    scratch.commit({"NOTICE.md": "n\n"})
    assert scratch.gate().returncode == 0
    assert _slow_flag(scratch) == ["slow=no"]
    scratch.clear_calls()
    scratch.git("checkout", "-q", "-B", "feat/x")
    result = scratch.gate("--if-needed")
    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == FULL
    assert _slow_flag(scratch) == ["slow=yes"]
    assert "without the slow tests" in result.stdout


def test_a_record_with_slow_tests_is_never_overwritten_by_one_without(
    scratch: Scratch,
) -> None:
    scratch.git("branch", "main")
    scratch.git("checkout", "-q", "main")
    scratch.commit({"src/app.py": "x = 2\n"}, "main moved")
    scratch.git("checkout", "-q", "-b", "hotfix/x")
    scratch.commit({"NOTICE.md": "n\n"})
    scratch.git("checkout", "-q", "-B", "feat/x")
    assert scratch.gate().returncode == 0  # develop base: slow tests run
    assert _slow_flag(scratch) == ["slow=yes"]
    (record,) = scratch.records()
    before = record.read_text(encoding="utf-8")
    scratch.clear_calls()
    scratch.git("checkout", "-q", "-B", "hotfix/x")
    result = scratch.gate()  # hotfix base: slow tests skipped
    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == NO_SLOW
    assert record.read_text(encoding="utf-8") == before
    assert "(slow tests: yes)" in result.stdout


def test_a_record_with_slow_tests_satisfies_a_safe_change(scratch: Scratch) -> None:
    _branch(scratch)
    scratch.commit({"NOTICE.md": "n\n"})
    assert scratch.gate("--all").returncode == 0
    scratch.clear_calls()
    assert scratch.gate("--if-needed").returncode == 0
    assert scratch.calls() == []


def test_a_record_without_a_slow_line_counts_as_without_slow_tests(
    scratch: Scratch,
) -> None:
    assert scratch.gate().returncode == 0
    (record,) = scratch.records()
    lines = record.read_text(encoding="utf-8").splitlines()
    record.write_text(
        "\n".join(line for line in lines if not line.startswith("slow=")) + "\n",
        encoding="utf-8",
    )
    scratch.clear_calls()
    assert scratch.gate("--if-needed", "--all").returncode == 0
    assert _ran(scratch) == FULL


def test_if_needed_decides_per_commit(scratch: Scratch) -> None:
    """Both commits are on a side branch; develop, the checkout, is at the base."""
    scratch.git("checkout", "-q", "-b", "side")
    safe = scratch.commit({"NOTICE.md": "n\n"})
    code = scratch.commit({"src/app.py": "x = 2\n"})
    scratch.git("checkout", "-q", "develop")
    result = scratch.gate("--if-needed", safe, code)
    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == NO_SLOW + FULL
    assert sorted(_slow_flag(scratch)) == ["slow=no", "slow=yes"]


def test_a_named_safe_commit_is_gated_without_slow_tests_in_a_worktree(
    scratch: Scratch,
) -> None:
    scratch.git("checkout", "-q", "-b", "side")
    side = scratch.commit({"NOTICE.md": "n\n"}, "side work")
    scratch.git("checkout", "-q", "develop")
    result = scratch.gate("--if-needed", side)
    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == NO_SLOW
    (cwd,) = {line.split(maxsplit=1)[1] for line in scratch.calls()}
    assert cwd != str(scratch.repo.resolve())
    assert _slow_flag(scratch) == ["slow=no"]
    scratch.clear_calls()
    assert scratch.gate("--if-needed", side).returncode == 0
    assert scratch.calls() == []
    # --all in a temporary worktree: the inner gate gets --all and runs everything.
    assert scratch.gate("--if-needed", "--all", side).returncode == 0
    assert _ran(scratch) == FULL
    assert _slow_flag(scratch) == ["slow=yes"]


def test_if_needed_all_passes_all_on_to_the_gate_of_the_checkout(
    scratch: Scratch,
) -> None:
    _branch(scratch)
    scratch.commit({"NOTICE.md": "n\n"})
    result = scratch.gate("--if-needed", "--all")
    assert result.returncode == 0, result.stderr + result.stdout
    assert _ran(scratch) == FULL
    assert _slow_flag(scratch) == ["slow=yes"]


def test_the_pre_push_hook_runs_the_slow_tests_for_main_and_skips_them_for_develop(
    scratch: Scratch,
) -> None:
    """The real hook with the real gate: develop's safe-only change skips, main's runs all."""
    scratch.git("update-ref", "refs/remotes/origin/develop", "HEAD")
    scratch.git("checkout", "-q", "-b", "feat/x")
    head = scratch.commit({"NOTICE.md": "n\n"})
    scratch.git("checkout", "-q", "develop")
    scratch.git("merge", "-q", "--ff-only", "feat/x")
    zero = "0" * 40

    def push(ref: str) -> subprocess.CompletedProcess[str]:
        line = f"refs/heads/{ref} {head} refs/heads/{ref} {zero}\n"
        return subprocess.run(
            ["sh", "-e", str(PRE_PUSH), "origin", "https://example.invalid/repo.git"],
            input=line,
            cwd=scratch.repo,
            capture_output=True,
            text=True,
            env=scratch.env(),
            check=False,
        )

    first = push("develop")
    assert first.returncode == 0, first.stderr + first.stdout
    assert _ran(scratch) == NO_SLOW
    assert _slow_flag(scratch) == ["slow=no"]
    scratch.clear_calls()
    second = push("main")
    assert second.returncode == 0, second.stderr + second.stdout
    assert _ran(scratch) == FULL
    assert _slow_flag(scratch) == ["slow=yes"]
    scratch.clear_calls()
    assert push("main").returncode == 0
    assert push("develop").returncode == 0
    assert scratch.calls() == []
