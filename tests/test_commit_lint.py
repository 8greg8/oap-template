"""Tests for `scripts/commit_lint.py` and `merge_message` (scripts/lib/common.sh)."""

from __future__ import annotations

import importlib.util
import re
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMON_SH = REPO_ROOT / "scripts" / "lib" / "common.sh"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "commit_lint", REPO_ROOT / "scripts" / "commit_lint.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


commit_lint = _load()


def merge_message(branch: str, base: str) -> str:
    result = subprocess.run(
        [
            "bash",
            "-c",
            f'. "{COMMON_SH}"; merge_message "$1" "$2"',
            "bash",
            branch,
            base,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def test_valid_message_passes() -> None:
    assert commit_lint.lint("feat(x): add y\n\nbody line\n") == []


def test_header_over_100_chars_fails() -> None:
    errors = commit_lint.lint("feat(x): " + "a" * 100)
    assert any("header is" in e for e in errors)


def test_body_line_at_100_chars_passes() -> None:
    assert commit_lint.lint("fix(x): y\n\n" + "b" * 100 + "\n") == []


def test_body_line_over_100_chars_fails() -> None:
    errors = commit_lint.lint("fix(x): y\n\n" + "b" * 101 + "\n")
    assert len(errors) == 1
    assert "line 3 is 101 chars" in errors[0]


def test_footer_line_over_100_chars_fails() -> None:
    errors = commit_lint.lint("fix(x): y\n\nbody\n\nRefs: " + "c" * 100 + "\n")
    assert any("must be <= 100" in e for e in errors)


def test_scissors_section_is_ignored() -> None:
    message = (
        "fix(x): y\n\nshort body\n"
        "# ------------------------ >8 ------------------------\n"
        "# Do not modify or remove the line above.\n"
        "diff --git a/f b/f\n"
        "+" + "z" * 300 + "\n"
    )
    assert commit_lint.lint(message) == []


def test_comment_lines_are_ignored() -> None:
    assert commit_lint.lint("fix(x): y\n# " + "c" * 300 + "\n") == []


def test_chore_merge_header_is_a_valid_conventional_header() -> None:
    assert commit_lint.lint("chore(merge): merge task 0002 into develop") == []
    assert commit_lint.lint("chore(merge): merge feat/x into develop") == []


def test_git_default_merge_message_stays_exempt() -> None:
    assert commit_lint.lint("Merge branch 'feat/x' into develop\n") == []


def test_default_merge_exemption_does_not_cover_long_body_of_normal_commit() -> None:
    assert commit_lint.lint("fix(x): y\n\n" + "b" * 150) != []


def test_merge_message_for_task_branch() -> None:
    assert (
        merge_message("fix/T-0002-x", "develop")
        == "chore(merge): merge task 0002 into develop"
    )


def test_merge_message_for_plain_branch() -> None:
    assert (
        merge_message("feat/x", "develop") == "chore(merge): merge feat/x into develop"
    )


def test_merge_message_for_hotfix_back_merge() -> None:
    assert merge_message("main", "develop") == "chore(merge): merge main into develop"


@pytest.mark.parametrize(
    ("branch", "base"),
    [("fix/T-0002-x", "develop"), ("feat/x", "develop"), ("main", "develop")],
)
def test_merge_messages_pass_commit_lint(branch: str, base: str) -> None:
    assert commit_lint.lint(merge_message(branch, base)) == []


def test_task_merge_message_matches_the_merge_lookup_subject() -> None:
    """report.py finds a task's merge by `chore(merge): merge task NNNN into <branch>`."""
    subject = merge_message("fix/T-0002-x", "develop")
    assert re.fullmatch(r"chore\(merge\): merge task 0002 into develop", subject)
