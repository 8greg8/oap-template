"""Tests for `scripts/changelog.py`.

The `check`, `preview` and `assemble` cases run the real script as a subprocess inside a scratch
git repository, so the git plumbing (ranges, merges, per-commit additions, tree reads) is
exercised for real. Every case uses temporary repositories and fixtures; none reads this
repository's own CHANGELOG.md or changelog.d/, so the file also passes in a generated project.
"""

from __future__ import annotations

import datetime
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "changelog.py"
NEXT_VERSION = REPO_ROOT / "scripts" / "next_version.py"

HEADER = """\
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

"""
EMPTY_CHANGELOG = HEADER + "## [Unreleased]\n"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


changelog = _load("changelog", SCRIPT)
next_version = _load("next_version_under_test", NEXT_VERSION)


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


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=_env(),
    )
    return result.stdout.strip()


def write(repo: Path, relative: str, content: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_bytes(repo: Path, relative: str, content: bytes) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def commit(repo: Path, message: str, files: dict[str, str | None] | None = None) -> str:
    """Commit the given files (a None value deletes the file) and return the new hash."""
    for relative, content in (files or {}).items():
        if content is None:
            git(repo, "rm", "-q", relative)
        else:
            write(repo, relative, content)
            git(repo, "add", relative)
    git(repo, "commit", "-q", "--allow-empty", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository on `develop` with a root commit holding an empty CHANGELOG.md."""
    path = tmp_path / "proj"
    path.mkdir()
    git(path, "init", "-q", "-b", "develop")
    git(path, "config", "core.hooksPath", "/dev/null")
    commit(path, "chore: root", {"CHANGELOG.md": EMPTY_CHANGELOG})
    return path


def base_of(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD")


# --- classification parity -------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "feat: add thing",
        "feat(scope): add thing\n\nbody",
        "fix: repair",
        "fix(x)!: repair\n\nBREAKING CHANGE: changes output",
        "feat!: drop api\n\nBREAKING CHANGE: gone",
        "chore: tidy\n\nBREAKING CHANGE: surprise",
        "docs: words",
        "chore(release): v1.0.0",
        "not conventional",
        "",
    ],
)
def test_classify_matches_next_version(message: str) -> None:
    assert changelog.classify(message) == next_version.classify(message)


# --- check: which commits need a fragment ----------------------------------------------------


@pytest.mark.parametrize(
    "message",
    ["feat: add x", "fix: repair x", "chore!: drop x\n\nBREAKING CHANGE: x is gone"],
)
def test_check_fails_for_versioned_commit_without_fragment(
    repo: Path, message: str
) -> None:
    base = base_of(repo)
    commit(repo, message, {"src/a.py": "x = 1\n"})
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 1
    assert "adds no changelog fragment" in result.stderr
    assert message.split("\n")[0] in result.stderr


@pytest.mark.parametrize(
    "message", ["chore: tidy", "docs: words", "test: more", "refactor: x"]
)
def test_check_passes_for_unversioned_commit_without_fragment(
    repo: Path, message: str
) -> None:
    base = base_of(repo)
    commit(repo, message, {"src/a.py": "x = 1\n"})
    assert run(repo, "check", base, "HEAD").returncode == 0


def test_check_passes_when_range_is_empty(repo: Path) -> None:
    assert run(repo, "check", "HEAD", "HEAD").returncode == 0


def test_check_passes_with_fragment_in_same_commit(repo: Path) -> None:
    base = base_of(repo)
    commit(
        repo,
        "feat: add x",
        {"src/a.py": "x = 1\n", "changelog.d/T-0001.added.md": "- Added x.\n"},
    )
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 0, result.stderr


def test_check_passes_with_fragment_in_another_commit_of_the_range(repo: Path) -> None:
    base = base_of(repo)
    commit(repo, "feat: add x", {"src/a.py": "x = 1\n"})
    write(repo, "changelog.d/T-0001.added.md", "- Added x.\n")
    git(repo, "add", "changelog.d/T-0001.added.md")
    git(repo, "commit", "-q", "-m", "docs: changelog for x")
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 0, result.stderr


def test_check_ignores_merge_commits(repo: Path) -> None:
    base = base_of(repo)
    git(repo, "checkout", "-q", "-b", "task")
    commit(repo, "chore: work", {"src/a.py": "x = 1\n"})
    git(repo, "checkout", "-q", "develop")
    git(
        repo,
        "merge",
        "--no-ff",
        "-q",
        "task",
        "-m",
        "feat!: merge task\n\nBREAKING CHANGE: merge text must not count",
    )
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 0, result.stderr


def test_check_counts_fragment_added_then_deleted_in_range(repo: Path) -> None:
    base = base_of(repo)
    write(repo, "changelog.d/T-0001.added.md", "- Added x.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "docs: add fragment")
    commit(repo, "feat: add x", {"src/a.py": "x = 1\n"})
    git(repo, "rm", "-q", "changelog.d/T-0001.added.md")
    git(repo, "commit", "-q", "-m", "chore(release): v0.1.0")
    assert not (repo / "changelog.d" / "T-0001.added.md").exists()
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 0, result.stderr


def test_check_does_not_count_fragment_added_before_base(repo: Path) -> None:
    write(repo, "changelog.d/T-0001.added.md", "- Added x.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "docs: add fragment")
    base = base_of(repo)
    commit(repo, "fix: repair x", {"src/a.py": "x = 1\n"})
    assert run(repo, "check", base, "HEAD").returncode == 1


def test_check_does_not_count_a_modified_fragment(repo: Path) -> None:
    write(repo, "changelog.d/T-0001.added.md", "- Added x.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "docs: add fragment")
    base = base_of(repo)
    commit(repo, "fix: repair x", {"src/a.py": "x = 1\n"})
    write(repo, "changelog.d/T-0001.added.md", "- Added x, reworded.\n")
    git(repo, "commit", "-q", "-am", "docs: reword")
    assert run(repo, "check", base, "HEAD").returncode == 1


def test_check_reads_fragments_at_tip_not_in_working_tree(repo: Path) -> None:
    base = base_of(repo)
    write(repo, "changelog.d/T-0001.added.md", "- Added x.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "feat: add x")
    write(repo, "changelog.d/T-0001.added.md", "- TODO\n")  # uncommitted breakage
    assert run(repo, "check", base, "HEAD").returncode == 0


def test_check_unknown_base_exits_2(repo: Path) -> None:
    result = run(repo, "check", "no-such-ref", "HEAD")
    assert result.returncode == 2
    assert "git log" in result.stderr


def test_check_unknown_tip_exits_2(repo: Path) -> None:
    result = run(repo, "check", "HEAD", "no-such-ref")
    assert result.returncode == 2
    assert "git log" in result.stderr


def test_check_outside_a_repository_exits_2(tmp_path: Path) -> None:
    outside = tmp_path / "plain"
    outside.mkdir()
    result = run(outside, "check", "a", "b")
    assert result.returncode == 2


@pytest.mark.parametrize("args", [[], ["check"], ["check", "only-base"], ["bogus"]])
def test_usage_errors_exit_2(repo: Path, args: list[str]) -> None:
    assert run(repo, *args).returncode == 2


# --- check: fragment validation at the tip ---------------------------------------------------


@pytest.mark.parametrize(
    ("name", "content", "expected"),
    [
        ("notes.md", "- Added x.\n", "bad name"),
        ("notes.txt", "- Added x.\n", "bad name"),
        ("T-0001.md", "- Added x.\n", "bad name"),
        ("T-0001.added.txt", "- Added x.\n", "bad name"),
        ("T 0001.added.md", "- Added x.\n", "bad name"),
        ("a.b.added.md", "- Added x.\n", "bad name"),
        ("-lead.added.md", "- Added x.\n", "bad name"),
        (".gitkeep", "", "bad name"),
        (".hidden.added.md", "- Added x.\n", "bad name"),
        ("README.txt", "- Added x.\n", "bad name"),
        ("readme.md", "- Added x.\n", "bad name"),
        ("T-0001.feature.md", "- Added x.\n", "unknown category 'feature'"),
        ("T-0001.Added.md", "- Added x.\n", "unknown category 'Added'"),
        ("T-0001.added.md", "", "no bullet line"),
        ("T-0001.added.md", "\n\n", "no bullet line"),
        ("T-0001.added.md", "Added x.\n", "no bullet line"),
        ("T-0001.added.md", "-Added x.\n", "no bullet line"),
        ("T-0001.added.md", "- \n", "empty bullet"),
        ("T-0001.added.md", "- Added x.\n- \n", "empty bullet"),
        ("T-0001.added.md", "* \n", "empty bullet"),
        ("T-0001.added.md", "-  \n   \n", "empty bullet"),
        ("T-0001.added.md", "- TODO\n", "placeholder text 'TODO'"),
        ("T-0001.added.md", "- todo\n", "placeholder text 'todo'"),
        ("T-0001.added.md", "- To-Do: write this\n", "placeholder text 'To-Do'"),
        ("T-0001.added.md", "- Added x (todo)\n", "placeholder text 'todo'"),
        ("T-0001.added.md", "- Added x. TBD\n", "placeholder text 'TBD'"),
        ("T-0001.added.md", "- tbd\n", "placeholder text 'tbd'"),
        ("T-0001.fixed.md", "- FIXME later\n", "placeholder text 'FIXME'"),
        ("T-0001.fixed.md", "* fixme\n", "placeholder text 'fixme'"),
        ("T-0001.fixed.md", "- Fixed <...> here\n", "placeholder text '<...>'"),
        (
            "T-0001.fixed.md",
            "- Fixed x.\n  TODO continued\n",
            "placeholder text 'TODO'",
        ),
        ("T-0001.fixed.md", "- Fixed x.\n\tTBD\n", "placeholder text 'TBD'"),
        # Only bullets, indented continuations and blank lines may be folded into CHANGELOG.md.
        (
            "T-0001.added.md",
            "Intro line.\n\n- Added x.\n",
            "line 1: not a bullet or an indented continuation: 'Intro line.'",
        ),
        (
            "T-0001.added.md",
            "- Added x.\n\nTrailing prose.\n",
            "line 3: not a bullet or an indented continuation",
        ),
        (
            "T-0001.added.md",
            "# Heading\n- Added x.\n",
            "line 1: not a bullet or an indented continuation",
        ),
        (
            "T-0001.added.md",
            "- Added x.\nunindented follow-up\n",
            "line 2: not a bullet or an indented continuation",
        ),
        (
            "T-0001.added.md",
            "- Added x.\n---\n",
            "line 2: not a bullet or an indented continuation",
        ),
        (
            "T-0001.added.md",
            "- Added x.\n\n  indented after a blank line\n",
            "line 3: indented line without a bullet directly before it",
        ),
        (
            "T-0001.added.md",
            "  indented before any bullet\n- Added x.\n",
            "line 1: indented line without a bullet directly before it",
        ),
        (
            "T-0001.added.md",
            "- Added x.\n\n\ttab-indented after a blank line\n",
            "line 3: indented line without a bullet directly before it",
        ),
        # Only one leading BOM is ignored.
        ("T-0001.added.md", "\ufeff\ufeff- Added x.\n", "line 1: not a bullet"),
        ("T-0001.added.md", "- Added x.\n\ufeff- Added y.\n", "line 2: not a bullet"),
    ],
)
def test_check_rejects_invalid_fragment(
    repo: Path, name: str, content: str, expected: str
) -> None:
    base = base_of(repo)
    write(repo, f"changelog.d/{name}", content)
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "docs: add fragment")
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 1
    assert f"changelog.d/{name}" in result.stderr
    assert expected in result.stderr


def test_check_rejects_nested_fragment_path(repo: Path) -> None:
    base = base_of(repo)
    write(repo, "changelog.d/sub/T-0001.added.md", "- Added x.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "docs: add fragment")
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 1
    assert "changelog.d/sub" in result.stderr
    assert "not a file" in result.stderr


def test_check_validates_existing_fragment_even_when_range_has_no_versioned_commit(
    repo: Path,
) -> None:
    write(repo, "changelog.d/T-0001.added.md", "- TODO\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "docs: add fragment")
    base = base_of(repo)
    commit(repo, "chore: tidy", {"src/a.py": "x = 1\n"})
    assert run(repo, "check", base, "HEAD").returncode == 1


def test_check_reports_missing_fragment_and_invalid_fragment_together(
    repo: Path,
) -> None:
    write(repo, "changelog.d/bad.added.txt", "x\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "docs: add bad fragment")
    base = base_of(repo)
    commit(repo, "feat: add x", {"src/a.py": "x = 1\n"})
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 1
    assert "adds no changelog fragment" in result.stderr
    assert "changelog.d/bad.added.txt" in result.stderr


def test_check_ignores_readme(repo: Path) -> None:
    base = base_of(repo)
    write(
        repo, "changelog.d/README.md", "# How to write a fragment\n\nNo bullets here.\n"
    )
    write(repo, "changelog.d/T-0001.added.md", "- Added x.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "feat: add x")
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "content",
    [
        "- Added x.\n",
        "* Added x.\n",
        "- Added x.\n  and a continuation line.\n",
        "- Added x.\n\n- Added y.\n",
        "- Added x.\n  one continuation.\n  and another.\n- Added y.\n\tmore.\n",
        "- Added x.   \n\n\n- Added y.\n\n",
        "\ufeff- Added x.\n",
        "- Handled todos and to-dos in the parser.\n",
        "- Documented the `changelog.d/<id>.<category>.md` pattern.\n",
    ],
)
def test_check_accepts_valid_fragment_content(repo: Path, content: str) -> None:
    base = base_of(repo)
    write(repo, "changelog.d/T-0001.added.md", content)
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "feat: add x")
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 0, result.stderr


def test_check_validates_committed_fragment_even_if_deleted_in_working_tree(
    repo: Path,
) -> None:
    base = base_of(repo)
    write(repo, "changelog.d/T-0001.added.md", "- TODO\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "docs: add fragment")
    (repo / "changelog.d" / "T-0001.added.md").unlink()
    assert run(repo, "check", base, "HEAD").returncode == 1


def test_check_checks_the_tip_revision_not_the_checked_out_one(repo: Path) -> None:
    base = base_of(repo)
    git(repo, "checkout", "-q", "-b", "task")
    commit(repo, "feat: add x", {"src/a.py": "x = 1\n"})
    git(repo, "checkout", "-q", "develop")
    assert run(repo, "check", base, "task").returncode == 1
    assert run(repo, "check", base, "develop").returncode == 0


def test_readme_alone_is_not_a_fragment_for_a_feat_commit(repo: Path) -> None:
    base = base_of(repo)
    write(repo, "changelog.d/README.md", "- A bullet in the readme.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "feat: add x")
    assert run(repo, "check", base, "HEAD").returncode == 1


# --- check: encoding and BOM -----------------------------------------------------------------

BAD_UTF8 = b"- Added caf\xe9.\n"  # Latin-1 e-acute, not valid UTF-8
BOM_BYTES = b"\xef\xbb\xbf"


def test_check_rejects_non_utf8_fragment_without_a_traceback(repo: Path) -> None:
    base = base_of(repo)
    write_bytes(repo, "changelog.d/T-0001.added.md", BAD_UTF8)
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "feat: add x")
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 1
    assert "changelog.d/T-0001.added.md: not valid UTF-8" in result.stderr
    assert "Traceback" not in result.stderr
    assert "\ufffd" not in result.stderr


def test_check_reads_the_fragment_blob_strictly_not_with_replacement(
    repo: Path,
) -> None:
    """A lossy decode would turn the bad byte into U+FFFD and accept the bullet."""
    base = base_of(repo)
    write_bytes(repo, "changelog.d/T-0001.added.md", b"- Added \xff\xfe thing.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "docs: add fragment")
    assert run(repo, "check", base, "HEAD").returncode == 1


def test_check_does_not_read_the_content_of_a_badly_named_file(repo: Path) -> None:
    base = base_of(repo)
    write_bytes(repo, "changelog.d/notes.txt", BAD_UTF8)
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "docs: add file")
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 1
    assert "bad name" in result.stderr
    assert "UTF-8" not in result.stderr


def test_check_accepts_a_fragment_with_a_leading_bom(repo: Path) -> None:
    base = base_of(repo)
    write_bytes(repo, "changelog.d/T-0001.added.md", BOM_BYTES + b"- Added x.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "feat: add x")
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 0, result.stderr


def test_check_accepts_a_bom_fragment_with_crlf_line_endings(repo: Path) -> None:
    base = base_of(repo)
    write_bytes(
        repo,
        "changelog.d/T-0001.added.md",
        BOM_BYTES + b"- Added x.\r\n  continued.\r\n- Added y.\r\n",
    )
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "feat: add x")
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 0, result.stderr


# --- check: what counts as an added fragment -------------------------------------------------


def test_check_does_not_count_a_rename_of_an_existing_fragment(repo: Path) -> None:
    write(repo, "changelog.d/T-0001.added.md", "- Added x, described at length.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "docs: add fragment")
    base = base_of(repo)
    commit(repo, "fix: repair x", {"src/a.py": "x = 1\n"})
    git(repo, "mv", "changelog.d/T-0001.added.md", "changelog.d/T-0001.fixed.md")
    git(repo, "commit", "-q", "-m", "docs: recategorize the fragment")
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 1
    assert "adds no changelog fragment" in result.stderr


def test_check_does_not_count_deleting_and_adding_the_same_fragment_path(
    repo: Path,
) -> None:
    write(repo, "changelog.d/T-0001.added.md", "- Added x.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "docs: add fragment")
    base = base_of(repo)
    commit(repo, "fix: repair x", {"src/a.py": "x = 1\n"})
    git(repo, "rm", "-q", "changelog.d/T-0001.added.md")
    git(repo, "commit", "-q", "-m", "docs: drop the fragment")
    commit(repo, "docs: add it back", {"changelog.d/T-0001.added.md": "- Added x.\n"})
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 1
    assert "adds no changelog fragment" in result.stderr


def test_check_counts_a_new_fragment_added_next_to_an_existing_one(repo: Path) -> None:
    write(repo, "changelog.d/T-0001.added.md", "- Added x.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "docs: add fragment")
    base = base_of(repo)
    commit(
        repo,
        "fix: repair y",
        {"src/a.py": "x = 1\n", "changelog.d/T-0002.fixed.md": "- Fixed y properly.\n"},
    )
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 0, result.stderr


def test_check_counts_a_fragment_added_in_range_and_renamed_later(repo: Path) -> None:
    base = base_of(repo)
    commit(
        repo,
        "fix: repair x",
        {"src/a.py": "x = 1\n", "changelog.d/T-0001.fixed.md": "- Fixed x properly.\n"},
    )
    git(repo, "mv", "changelog.d/T-0001.fixed.md", "changelog.d/T-0002.fixed.md")
    git(repo, "commit", "-q", "-m", "docs: rename the fragment")
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 0, result.stderr


# --- exit status 3: internal errors ----------------------------------------------------------


def _lonely_copy(tmp_path: Path, next_version_source: str | None) -> Path:
    """Copy changelog.py to a directory whose sibling next_version.py is missing or replaced."""
    lonely = tmp_path / "lonely"
    lonely.mkdir()
    shutil.copy(SCRIPT, lonely / "changelog.py")
    if next_version_source is not None:
        (lonely / "next_version.py").write_text(next_version_source, encoding="utf-8")
    return lonely / "changelog.py"


@pytest.mark.parametrize(
    "next_version_source",
    [None, "raise RuntimeError('boom')\n", "def classify(:\n"],
    ids=["missing", "raises-on-load", "syntax-error"],
)
def test_check_exits_3_when_next_version_cannot_be_loaded(
    repo: Path, tmp_path: Path, next_version_source: str | None
) -> None:
    script = _lonely_copy(tmp_path, next_version_source)
    base = base_of(repo)
    commit(repo, "feat: add x", {"src/a.py": "x = 1\n"})
    result = subprocess.run(
        [sys.executable, str(script), "check", base, "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )
    assert result.returncode == 3
    lines = result.stderr.strip().splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("changelog.py: internal error: ")
    assert "adds no changelog fragment" not in result.stderr


def test_assemble_exits_3_on_an_unexpected_exception(repo: Path) -> None:
    """A CHANGELOG.md that is not UTF-8 is not a fragment problem; it is an unexpected error."""
    write_bytes(repo, "CHANGELOG.md", b"# Changelog\n\n## [Unreleased]\n\xff\n")
    add_fragments(repo, T__0001_added="- Added x.\n")
    result = run(repo, "assemble", "0.1.0")
    assert result.returncode == 3
    assert len(result.stderr.strip().splitlines()) == 1
    assert "internal error" in result.stderr
    assert (repo / "changelog.d" / "T-0001.added.md").exists()


def test_exit_codes_1_and_2_are_unchanged(repo: Path) -> None:
    base = base_of(repo)
    commit(repo, "feat: add x", {"src/a.py": "x = 1\n"})
    assert run(repo, "check", base, "HEAD").returncode == 1
    assert run(repo, "check", "no-such-ref", "HEAD").returncode == 2


# --- assemble --------------------------------------------------------------------------------


def add_fragments(repo: Path, **fragments: str) -> None:
    """Write fragments to the working tree; keys use `_` for `.` and `__` for `-`."""
    for key, content in fragments.items():
        name = key.replace("__", "-").replace("_", ".") + ".md"
        write(repo, f"changelog.d/{name}", content)


def test_assemble_writes_ordered_dated_section_and_deletes_fragments(
    repo: Path,
) -> None:
    add_fragments(
        repo,
        T__0003_security="- Closed a hole.\n",
        T__0002_fixed="- Fixed y.\n",
        T__0001_added="- Added x.\n- Added x2.\n",
        T__0004_removed="- Removed z.\n",
        T__0005_deprecated="- Deprecated w.\n",
        T__0006_changed="- Changed v.\n",
        topic_added="- Added from topic.\n",
    )
    write(repo, "changelog.d/README.md", "# Readme\n")
    result = run(repo, "assemble", "1.2.3", "--date", "2026-10-04")
    assert result.returncode == 0, result.stderr
    expected = (
        HEADER
        + "## [Unreleased]\n\n"
        + "## [1.2.3] - 2026-10-04\n\n"
        + "### Added\n\n- Added x.\n- Added x2.\n- Added from topic.\n\n"
        + "### Changed\n\n- Changed v.\n\n"
        + "### Deprecated\n\n- Deprecated w.\n\n"
        + "### Removed\n\n- Removed z.\n\n"
        + "### Fixed\n\n- Fixed y.\n\n"
        + "### Security\n\n- Closed a hole.\n"
    )
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == expected
    assert sorted(p.name for p in (repo / "changelog.d").iterdir()) == ["README.md"]
    assert (repo / "changelog.d" / "README.md").read_text(
        encoding="utf-8"
    ) == "# Readme\n"


def test_assemble_accepts_v_prefix(repo: Path) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n")
    assert run(repo, "assemble", "v0.1.0", "--date", "2026-10-04").returncode == 0
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [0.1.0] - 2026-10-04\n" in text


def test_assemble_places_new_section_above_older_sections_and_keeps_footer(
    repo: Path,
) -> None:
    older = (
        HEADER
        + "## [Unreleased]\n\n"
        + "## [0.1.0] - 2026-01-01\n\n### Added\n\n- Old.\n\n"
        + "[Unreleased]: https://example.com/compare/v0.1.0...HEAD\n"
        + "[0.1.0]: https://example.com/releases/v0.1.0\n"
    )
    write(repo, "CHANGELOG.md", older)
    add_fragments(repo, T__0001_fixed="- Fixed x.\n")
    assert run(repo, "assemble", "0.1.1", "--date", "2026-02-02").returncode == 0
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert text == (
        HEADER
        + "## [Unreleased]\n\n"
        + "## [0.1.1] - 2026-02-02\n\n### Fixed\n\n- Fixed x.\n\n"
        + "## [0.1.0] - 2026-01-01\n\n### Added\n\n- Old.\n\n"
        + "[Unreleased]: https://example.com/compare/v0.1.0...HEAD\n"
        + "[0.1.0]: https://example.com/releases/v0.1.0\n"
    )


def test_assemble_refuses_non_empty_unreleased(repo: Path) -> None:
    dirty = EMPTY_CHANGELOG + "\n### Added\n\n- Stranded entry.\n"
    write(repo, "CHANGELOG.md", dirty)
    add_fragments(repo, T__0001_added="- Added x.\n")
    result = run(repo, "assemble", "0.1.0")
    assert result.returncode == 1
    assert "not empty" in result.stderr
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == dirty
    assert (repo / "changelog.d" / "T-0001.added.md").exists()


def test_assemble_refuses_invalid_fragment_and_changes_nothing(repo: Path) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n", T__0002_fixed="- TODO\n")
    result = run(repo, "assemble", "0.1.0")
    assert result.returncode == 1
    assert "placeholder" in result.stderr
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == EMPTY_CHANGELOG
    assert (repo / "changelog.d" / "T-0001.added.md").exists()


def test_assemble_refuses_when_there_are_no_fragments(repo: Path) -> None:
    write(repo, "changelog.d/README.md", "# Readme\n")
    result = run(repo, "assemble", "0.1.0")
    assert result.returncode == 1
    assert "no fragments" in result.stderr
    assert (repo / "changelog.d" / "README.md").exists()


def test_assemble_refuses_an_existing_version(repo: Path) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n")
    assert run(repo, "assemble", "0.1.0").returncode == 0
    add_fragments(repo, T__0002_added="- Added y.\n")
    result = run(repo, "assemble", "0.1.0")
    assert result.returncode == 1
    assert "already has a section" in result.stderr


def test_assemble_refuses_changelog_without_unreleased_heading(repo: Path) -> None:
    write(repo, "CHANGELOG.md", "# Changelog\n")
    add_fragments(repo, T__0001_added="- Added x.\n")
    result = run(repo, "assemble", "0.1.0")
    assert result.returncode == 1
    assert "[Unreleased]" in result.stderr


def test_assemble_refuses_missing_changelog(repo: Path) -> None:
    git(repo, "rm", "-q", "CHANGELOG.md")
    add_fragments(repo, T__0001_added="- Added x.\n")
    result = run(repo, "assemble", "0.1.0")
    assert result.returncode == 1
    assert "not found" in result.stderr


@pytest.mark.parametrize("version", ["1.2", "one", "1.2.3.4", "v1.2", ""])
def test_assemble_rejects_bad_version(repo: Path, version: str) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n")
    result = run(repo, "assemble", version)
    assert result.returncode == 2
    assert "X.Y.Z" in result.stderr
    assert (repo / "changelog.d" / "T-0001.added.md").exists()


@pytest.mark.parametrize(
    "date",
    [
        "04-10-2026",
        "2026-1-5",
        "20261005",
        "2026-W41-1",
        "2026-10-05T00:00:00",
        " 2026-10-05",
        "2026-10-05\n",
        "\uff12\uff10\uff12\uff16-10-05",
        "2026-13-01",
        "2026-02-30",
        "",
    ],
)
def test_assemble_rejects_any_date_but_yyyy_mm_dd(repo: Path, date: str) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n")
    result = run(repo, "assemble", "0.1.0", "--date", date)
    assert result.returncode == 2
    assert "YYYY-MM-DD" in result.stderr
    assert (repo / "changelog.d" / "T-0001.added.md").exists()
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == EMPTY_CHANGELOG


def test_assemble_output_then_passes_check_after_commit(repo: Path) -> None:
    base = base_of(repo)
    write(repo, "changelog.d/T-0001.added.md", "- Added x.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "feat: add x")
    assert run(repo, "assemble", "0.1.0", "--date", "2026-10-04").returncode == 0
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore(release): v0.1.0")
    assert run(repo, "check", base, "HEAD").returncode == 0


def test_assemble_orders_fragments_by_file_name_within_a_category(repo: Path) -> None:
    add_fragments(
        repo,
        T__0010_added="- Ten.\n",
        T__0002_added="- Two a.\n- Two b.\n",
        topic_added="- Topic.\n",
        Alpha_added="- Alpha.\n",
    )
    assert run(repo, "assemble", "0.1.0", "--date", "2026-10-04").returncode == 0
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "### Added\n\n- Alpha.\n- Two a.\n- Two b.\n- Ten.\n- Topic.\n" in text


def test_assemble_writes_no_compare_link_footer(repo: Path) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n")
    assert run(repo, "assemble", "0.1.0", "--date", "2026-10-04").returncode == 0
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert not re.search(r"^\[[^\]]+\]:", text, re.MULTILINE)
    assert "http" not in text.split("## [Unreleased]")[1]


def test_assemble_edits_the_working_tree_without_staging(repo: Path) -> None:
    write(repo, "changelog.d/T-0001.added.md", "- Added x.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "docs: add fragment")
    assert git(repo, "diff", "--cached", "--name-only") == ""
    assert run(repo, "assemble", "0.1.0", "--date", "2026-10-04").returncode == 0
    assert git(repo, "diff", "--cached", "--name-only") == ""
    unstaged = git(repo, "diff", "--name-only").splitlines()
    assert sorted(unstaged) == ["CHANGELOG.md", "changelog.d/T-0001.added.md"]


@pytest.mark.parametrize(
    ("name", "content"),
    [
        (".gitkeep", ""),
        ("notes.txt", "- Added x.\n"),
        ("T-0002.feature.md", "- Added x.\n"),
        ("T-0002.added.md", "- \n"),
        ("T-0002.added.md", "Intro line.\n\n- Added y.\n"),
        ("T-0002.added.md", "- Added y.\n\n  stray indented line\n"),
    ],
)
def test_assemble_refuses_when_any_file_fails_the_rules(
    repo: Path, name: str, content: str
) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n")
    write(repo, f"changelog.d/{name}", content)
    result = run(repo, "assemble", "0.1.0")
    assert result.returncode == 1
    assert f"changelog.d/{name}" in result.stderr
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == EMPTY_CHANGELOG
    assert (repo / "changelog.d" / "T-0001.added.md").exists()
    assert (repo / "changelog.d" / name).exists()


def test_assemble_refuses_a_non_utf8_fragment_without_a_traceback(repo: Path) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n")
    write_bytes(repo, "changelog.d/T-0002.fixed.md", BAD_UTF8)
    result = run(repo, "assemble", "0.1.0")
    assert result.returncode == 1
    assert "changelog.d/T-0002.fixed.md: not valid UTF-8" in result.stderr
    assert "Traceback" not in result.stderr
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == EMPTY_CHANGELOG
    assert (repo / "changelog.d" / "T-0001.added.md").exists()
    assert (repo / "changelog.d" / "T-0002.fixed.md").exists()


def test_assemble_parses_a_bom_fragment_and_writes_no_bom(repo: Path) -> None:
    write_bytes(repo, "changelog.d/T-0001.added.md", BOM_BYTES + b"- Added x.\n")
    result = run(repo, "assemble", "0.1.0", "--date", "2026-10-04")
    assert result.returncode == 0, result.stderr
    raw = (repo / "CHANGELOG.md").read_bytes()
    assert BOM_BYTES not in raw
    assert b"### Added\n\n- Added x.\n" in raw


def test_assemble_with_no_fragments_changes_nothing(repo: Path) -> None:
    result = run(repo, "assemble", "0.1.0")
    assert result.returncode == 1
    assert "no fragments" in result.stderr
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == EMPTY_CHANGELOG
    assert git(repo, "status", "--porcelain") == ""


# --- preview ---------------------------------------------------------------------------------


def local_today() -> str:
    return datetime.datetime.now().astimezone().date().isoformat()


def test_preview_with_version_prints_section_and_changes_nothing(repo: Path) -> None:
    add_fragments(
        repo,
        T__0001_added="- Added x.\n",
        T__0002_fixed="- Fixed y.\n",
    )
    git(repo, "add", "-A")
    before = git(repo, "status", "--porcelain")
    changelog_before = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    first = local_today()
    result = run(repo, "preview", "0.2.0")
    second = local_today()
    assert result.returncode == 0, result.stderr
    body = "\n\n### Added\n\n- Added x.\n\n### Fixed\n\n- Fixed y.\n"
    assert result.stdout in (
        f"## [0.2.0] - {first}{body}",
        f"## [0.2.0] - {second}{body}",
    )
    assert git(repo, "status", "--porcelain") == before
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == changelog_before
    assert (repo / "changelog.d" / "T-0001.added.md").exists()
    assert (repo / "changelog.d" / "T-0002.fixed.md").exists()


def test_preview_accepts_v_prefix(repo: Path) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n")
    result = run(repo, "preview", "v0.2.0")
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("## [0.2.0] - ")


def test_preview_without_version_is_headed_unreleased(repo: Path) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n", T__0002_fixed="- Fixed y.\n")
    result = run(repo, "preview")
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "## [Unreleased]\n\n### Added\n\n- Added x.\n\n### Fixed\n\n- Fixed y.\n"
    )


def test_preview_never_calls_next_version(repo: Path, tmp_path: Path) -> None:
    # A copy of the tool with no sibling next_version.py: preview must still work.
    lonely = tmp_path / "lonely"
    lonely.mkdir()
    shutil.copy(SCRIPT, lonely / "changelog.py")
    add_fragments(repo, T__0001_added="- Added x.\n")
    for extra in ([], ["0.3.0"]):
        result = subprocess.run(
            [sys.executable, str(lonely / "changelog.py"), "preview", *extra],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
            env=_env(),
        )
        assert result.returncode == 0, result.stderr
        assert "- Added x." in result.stdout


def test_preview_matches_what_assemble_writes(repo: Path) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n", T__0002_changed="- Changed y.\n")
    previewed = run(repo, "preview", "0.2.0").stdout
    assert run(repo, "assemble", "0.2.0").returncode == 0
    assert previewed in (repo / "CHANGELOG.md").read_text(encoding="utf-8")


def test_preview_with_no_fragments_prints_nothing(repo: Path) -> None:
    result = run(repo, "preview", "0.1.0")
    assert result.returncode == 0
    assert result.stdout == ""
    assert "no fragments" in result.stderr


def test_preview_ignores_readme(repo: Path) -> None:
    write(repo, "changelog.d/README.md", "- A bullet in the readme.\n")
    result = run(repo, "preview", "0.1.0")
    assert result.returncode == 0
    assert result.stdout == ""


def test_preview_fails_on_invalid_fragment(repo: Path) -> None:
    add_fragments(repo, T__0001_added="- TODO\n")
    result = run(repo, "preview", "0.1.0")
    assert result.returncode == 1
    assert "placeholder" in result.stderr


def test_preview_fails_on_non_utf8_fragment_without_a_traceback(repo: Path) -> None:
    write_bytes(repo, "changelog.d/T-0001.added.md", BAD_UTF8)
    result = run(repo, "preview", "0.1.0")
    assert result.returncode == 1
    assert "not valid UTF-8" in result.stderr
    assert "Traceback" not in result.stderr


def test_preview_fails_on_a_fragment_with_a_non_bullet_line(repo: Path) -> None:
    add_fragments(repo, T__0001_added="Intro line.\n\n- Added x.\n")
    result = run(repo, "preview", "0.1.0")
    assert result.returncode == 1
    assert "line 1: not a bullet" in result.stderr


def test_preview_parses_a_bom_fragment(repo: Path) -> None:
    write_bytes(repo, "changelog.d/T-0001.added.md", BOM_BYTES + b"- Added x.\n")
    result = run(repo, "preview")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "## [Unreleased]\n\n### Added\n\n- Added x.\n"


def test_preview_rejects_bad_version(repo: Path) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n")
    assert run(repo, "preview", "1.2").returncode == 2


def test_assemble_default_date_is_local_today(repo: Path) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n")
    first = local_today()
    assert run(repo, "assemble", "0.1.0").returncode == 0
    second = local_today()
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [0.1.0] - {first}\n" in text or f"## [0.1.0] - {second}\n" in text
