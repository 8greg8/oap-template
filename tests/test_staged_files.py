"""Tests that `gate.sh --staged` and `autofix.sh --staged` handle unusual staged file names.

Each case copies the real `scripts/` into a throwaway git repository and replaces
`scripts/config/gate.sh` with stub commands. The stubs record every argument NUL-terminated (so a
newline inside a name stays visible) or edit the files they are given. The expectation is that each
staged name reaches every command as exactly one intact argument.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"

NAMES = ["sp ace.py", 'qu"ote.py', "it's.py", "čšž.py", "new\nline.py"]
IDS = ["space", "double-quote", "single-quote", "non-ascii", "newline"]


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


@pytest.fixture
def tool_repo(tmp_path: Path) -> Path:
    """A repo holding a copy of scripts/ whose config records or edits the files it is given."""
    repo = tmp_path / "tool"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "develop")
    shutil.copytree(
        SCRIPTS, repo / "scripts", ignore=shutil.ignore_patterns("__pycache__")
    )
    log = repo / "calls.log"
    config = "\n".join(
        [
            # Record the command label, then each file argument, each followed by a NUL.
            f'record() {{ printf "%s\\0" "$@" >> "{log}"; }}',
            # Append a line to every file argument, so a mangled name fails to open.
            'touchall() { for f in "$@"; do printf "fixed\\n" >> "$f" || exit 1; done; }',
            'LINT_CMD="record lint"',
            'LINT_FIX_CMD="touchall"',
            'FORMAT_CHECK_CMD="record fmtcheck"',
            'FORMAT_FIX_CMD="record fmt"',
            'TYPECHECK_CMD="record ty"',
            'TEST_CMD="record test"',
            'MAIN_BRANCH="main"',
            'DEVELOP_BRANCH="develop"',
            'STAGED_GLOB="*.py"',
            "export -f record touchall",
            "",
        ]
    )
    (repo / "scripts" / "config" / "gate.sh").write_text(config, encoding="utf-8")
    (repo / "README.md").write_text("r\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "c")
    return repo


def _stage(repo: Path, names: list[str]) -> None:
    for name in names:
        (repo / name).write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "--", *[f":(literal){name}" for name in names])


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


def _recorded(repo: Path) -> list[str]:
    """The recorded arguments, split on NUL; empty when nothing was recorded."""
    log = repo / "calls.log"
    if not log.exists():
        return []
    return log.read_bytes().decode("utf-8").split("\0")[:-1]


@pytest.mark.parametrize("name", NAMES, ids=IDS)
def test_gate_staged_passes_unusual_name_as_one_argument(
    tool_repo: Path, name: str
) -> None:
    _stage(tool_repo, [name])
    result = _run_script(tool_repo, "gate.sh", "--staged")
    assert result.returncode == 0, result.stderr + result.stdout
    assert _recorded(tool_repo) == ["lint", name, "fmtcheck", name, "ty", name]


def test_gate_staged_passes_all_unusual_names_together(tool_repo: Path) -> None:
    _stage(tool_repo, NAMES)
    result = _run_script(tool_repo, "gate.sh", "--staged")
    assert result.returncode == 0, result.stderr + result.stdout
    recorded = _recorded(tool_repo)
    n = len(NAMES)
    assert recorded[0] == "lint"
    assert sorted(recorded[1 : 1 + n]) == sorted(NAMES)
    assert recorded[1 + n] == "fmtcheck"
    assert sorted(recorded[2 + n : 2 + 2 * n]) == sorted(NAMES)
    assert recorded[2 + 2 * n] == "ty"
    assert sorted(recorded[3 + 2 * n :]) == sorted(NAMES)


@pytest.mark.parametrize("name", NAMES, ids=IDS)
def test_autofix_staged_fixes_unusual_name(tool_repo: Path, name: str) -> None:
    _stage(tool_repo, [name])
    result = _run_script(tool_repo, "autofix.sh", "--staged")
    assert result.returncode == 0, result.stderr + result.stdout
    assert (tool_repo / name).read_text(encoding="utf-8") == "x = 1\nfixed\n"
    assert _recorded(tool_repo) == ["fmt", name]


def test_autofix_staged_fixes_all_unusual_names_together(tool_repo: Path) -> None:
    _stage(tool_repo, NAMES)
    result = _run_script(tool_repo, "autofix.sh", "--staged")
    assert result.returncode == 0, result.stderr + result.stdout
    for name in NAMES:
        assert (tool_repo / name).read_text(encoding="utf-8") == "x = 1\nfixed\n"
    recorded = _recorded(tool_repo)
    assert recorded[0] == "fmt"
    assert sorted(recorded[1:]) == sorted(NAMES)


@pytest.mark.parametrize("script", ["gate.sh", "autofix.sh"])
def test_staged_with_no_matching_files_does_nothing(
    tool_repo: Path, script: str
) -> None:
    (tool_repo / "notes.txt").write_text("n\n", encoding="utf-8")
    _git(tool_repo, "add", "notes.txt")
    result = _run_script(tool_repo, script, "--staged")
    assert result.returncode == 0, result.stderr + result.stdout
    assert _recorded(tool_repo) == []
