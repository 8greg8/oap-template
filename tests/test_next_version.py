"""Tests for `scripts/next_version.py`, mainly the SemVer 0.x bump rule.

`bump` is tested directly. The end-to-end cases run the real script as a subprocess inside a
scratch git repository. Nothing here reads this repository's own history or tags.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "next_version.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("next_version_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


next_version = _load()


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


@pytest.mark.parametrize(
    ("tag", "level", "expected"),
    [
        # 0.x: breaking bumps minor, feat bumps minor, fix bumps patch.
        ("v0.0.0", "breaking", "v0.1.0"),
        ("v0.3.7", "breaking", "v0.4.0"),
        ("v0.3.7", "feat", "v0.4.0"),
        ("v0.3.7", "fix", "v0.3.8"),
        ("v0.0.0", "feat", "v0.1.0"),
        ("v0.0.0", "fix", "v0.0.1"),
        # 1.0 and later: unchanged rules.
        ("v1.0.0", "breaking", "v2.0.0"),
        ("v1.4.2", "breaking", "v2.0.0"),
        ("v1.4.2", "feat", "v1.5.0"),
        ("v1.4.2", "fix", "v1.4.3"),
        ("v12.0.1", "breaking", "v13.0.0"),
    ],
)
def test_bump(tag: str, level: str, expected: str):
    assert next_version.bump(tag, level) == expected


def test_bump_rejects_a_malformed_tag():
    with pytest.raises(ValueError):
        next_version.bump("1.2.3", "fix")


def test_docstring_states_the_zero_x_rule():
    doc = next_version.__doc__ or ""
    assert "0.x" in doc
    assert "bumps minor" in doc


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("feat: add x", "feat"),
        ("fix(core): repair y", "fix"),
        ("feat!: drop z", "breaking"),
        ("chore: tidy\n\nBREAKING CHANGE: contract moved", "breaking"),
        ("docs: words", None),
        ("not a conventional header", None),
    ],
)
def test_classify(message: str, expected: str | None):
    assert next_version.classify(message) == expected


def _repo(tmp_path: Path, tag: str | None) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "core.hooksPath", "/dev/null")
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "chore: init")
    if tag:
        _git(repo, "tag", "-a", tag, "-m", tag)
    return repo


def _commit(repo: Path, message: str) -> None:
    path = repo / "a.txt"
    path.write_text(path.read_text(encoding="utf-8") + "x\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def _run(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--quiet"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )


@pytest.mark.parametrize(
    ("tag", "message", "expected"),
    [
        (None, "feat!: first break", "v0.1.0"),
        (None, "fix: first fix", "v0.0.1"),
        ("v0.2.3", "feat!: break", "v0.3.0"),
        ("v0.2.3", "fix: patch\n\nBREAKING CHANGE: contract moved", "v0.3.0"),
        ("v0.2.3", "feat: add", "v0.3.0"),
        ("v1.2.3", "feat!: break", "v2.0.0"),
        ("v1.2.3", "fix: patch", "v1.2.4"),
    ],
)
def test_script_prints_the_next_version(
    tmp_path: Path, tag: str | None, message: str, expected: str
):
    repo = _repo(tmp_path, tag)
    _commit(repo, message)

    result = _run(repo)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


def test_script_exits_1_with_nothing_to_release(tmp_path: Path):
    repo = _repo(tmp_path, "v0.2.3")
    _commit(repo, "docs: only words")

    result = _run(repo)

    assert result.returncode == 1
    assert "nothing to release" in result.stderr
