"""Tests for `scripts/changelog.py`.

The `check`, `preview` and `assemble` cases run the real script as a subprocess inside a scratch
git repository, so the git plumbing (ranges, merges, per-commit additions, tree reads) is
exercised for real.
"""

from __future__ import annotations

import datetime
import importlib.util
import os
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
    write(repo, "changelog.d/T-0001.added.md", "TODO\n")  # uncommitted breakage
    assert run(repo, "check", base, "HEAD").returncode == 0


def test_check_bad_revision_exits_2(repo: Path) -> None:
    result = run(repo, "check", "no-such-ref", "HEAD")
    assert result.returncode == 2
    assert "git log" in result.stderr


# --- check: fragment validation at the tip ---------------------------------------------------


@pytest.mark.parametrize(
    ("name", "content", "expected"),
    [
        ("notes.md", "- Added x.\n", "name must be"),
        ("T-0001.md", "- Added x.\n", "name must be"),
        ("T-0001.added.txt", "- Added x.\n", "name must be"),
        ("T 0001.added.md", "- Added x.\n", "name must be"),
        ("T-0001.feature.md", "- Added x.\n", "unknown category 'feature'"),
        ("T-0001.Added.md", "- Added x.\n", "unknown category 'Added'"),
        ("T-0001.added.md", "", "no bullet line"),
        ("T-0001.added.md", "\n\n", "no bullet line"),
        ("T-0001.added.md", "Added x.\n", "no bullet line"),
        ("T-0001.added.md", "- \n", "no bullet line"),
        ("T-0001.added.md", "- TODO\n", "placeholder text 'TODO'"),
        ("T-0001.added.md", "- Added x. TBD\n", "placeholder text 'TBD'"),
        ("T-0001.fixed.md", "- FIXME later\n", "placeholder text 'FIXME'"),
        ("T-0001.fixed.md", "- XXX\n", "placeholder text 'XXX'"),
        ("T-0001.fixed.md", "- Describe the change here\n", "placeholder text"),
        ("T-0001.fixed.md", "- Lorem ipsum dolor\n", "placeholder text"),
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
    assert "nested path" in result.stderr


def test_check_validates_existing_fragment_even_when_range_has_no_versioned_commit(
    repo: Path,
) -> None:
    write(repo, "changelog.d/T-0001.added.md", "TODO\n")
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


def test_check_ignores_readme_and_hidden_files(repo: Path) -> None:
    base = base_of(repo)
    write(
        repo, "changelog.d/README.md", "# How to write a fragment\n\nNo bullets here.\n"
    )
    write(repo, "changelog.d/.gitkeep", "")
    write(repo, "changelog.d/T-0001.added.md", "- Added x.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "feat: add x")
    result = run(repo, "check", base, "HEAD")
    assert result.returncode == 0, result.stderr


def test_readme_alone_is_not_a_fragment_for_a_feat_commit(repo: Path) -> None:
    base = base_of(repo)
    write(repo, "changelog.d/README.md", "- A bullet in the readme.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "feat: add x")
    assert run(repo, "check", base, "HEAD").returncode == 1


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


def test_assemble_accepts_v_prefix_and_defaults_date_to_today(repo: Path) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n")

    def today() -> str:
        return datetime.datetime.now().astimezone().date().isoformat()

    before = today()
    assert run(repo, "assemble", "v0.1.0").returncode == 0
    after = today()
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [0.1.0] - {before}" in text or f"## [0.1.0] - {after}" in text


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
    add_fragments(repo, T__0001_added="- Added x.\n", T__0002_fixed="TODO\n")
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
    assert result.returncode == 1
    assert "X.Y.Z" in result.stderr
    assert (repo / "changelog.d" / "T-0001.added.md").exists()


def test_assemble_rejects_bad_date(repo: Path) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n")
    result = run(repo, "assemble", "0.1.0", "--date", "04-10-2026")
    assert result.returncode == 1
    assert "YYYY-MM-DD" in result.stderr
    assert (repo / "changelog.d" / "T-0001.added.md").exists()


def test_assemble_output_then_passes_check_after_commit(repo: Path) -> None:
    base = base_of(repo)
    write(repo, "changelog.d/T-0001.added.md", "- Added x.\n")
    git(repo, "add", "changelog.d")
    git(repo, "commit", "-q", "-m", "feat: add x")
    assert run(repo, "assemble", "0.1.0", "--date", "2026-10-04").returncode == 0
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore(release): v0.1.0")
    assert run(repo, "check", base, "HEAD").returncode == 0


# --- preview ---------------------------------------------------------------------------------


def test_preview_prints_section_and_changes_nothing(repo: Path) -> None:
    add_fragments(
        repo,
        T__0001_added="- Added x.\n",
        T__0002_fixed="- Fixed y.\n",
    )
    git(repo, "add", "-A")
    before = git(repo, "status", "--porcelain")
    changelog_before = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    result = run(repo, "preview", "0.2.0", "--date", "2026-10-04")
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "## [0.2.0] - 2026-10-04\n\n### Added\n\n- Added x.\n\n### Fixed\n\n- Fixed y.\n"
    )
    assert git(repo, "status", "--porcelain") == before
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == changelog_before
    assert (repo / "changelog.d" / "T-0001.added.md").exists()
    assert (repo / "changelog.d" / "T-0002.fixed.md").exists()


def test_preview_matches_what_assemble_writes(repo: Path) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n", T__0002_changed="- Changed y.\n")
    previewed = run(repo, "preview", "0.2.0", "--date", "2026-10-04").stdout
    assert run(repo, "assemble", "0.2.0", "--date", "2026-10-04").returncode == 0
    assert previewed in (repo / "CHANGELOG.md").read_text(encoding="utf-8")


def test_preview_takes_version_from_next_version(repo: Path) -> None:
    git(repo, "tag", "v0.1.0")
    commit(repo, "feat: add x", {"src/a.py": "x = 1\n"})
    add_fragments(repo, T__0001_added="- Added x.\n")
    result = run(repo, "preview", "--date", "2026-10-04")
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("## [0.2.0] - 2026-10-04\n")


def test_preview_falls_back_to_unreleased_when_nothing_to_release(repo: Path) -> None:
    add_fragments(repo, T__0001_added="- Added x.\n")
    result = run(repo, "preview", "--date", "2026-10-04")
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("## [Unreleased] - 2026-10-04\n")


def test_preview_with_no_fragments_prints_nothing(repo: Path) -> None:
    result = run(repo, "preview", "0.1.0")
    assert result.returncode == 0
    assert result.stdout == ""
    assert "no fragments" in result.stderr


def test_preview_fails_on_invalid_fragment(repo: Path) -> None:
    add_fragments(repo, T__0001_added="TODO\n")
    result = run(repo, "preview", "0.1.0")
    assert result.returncode == 1
    assert "placeholder" in result.stderr


# --- repository files ------------------------------------------------------------------------


def test_repository_changelog_has_header_and_empty_unreleased() -> None:
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert text.startswith("# Changelog\n")
    assert "keepachangelog.com/en/1.1.0" in text
    assert "semver.org" in text
    head, unreleased, tail = changelog.split_changelog(text)
    assert head[-1] == "## [Unreleased]"
    assert not any(line.strip() for line in unreleased)
    assert tail == []


def test_repository_fragments_are_valid() -> None:
    directory = REPO_ROOT / "changelog.d"
    names = {p.name for p in directory.iterdir()}
    assert {"README.md", "template.added.md", "T-0022.added.md"} <= names
    for path in directory.iterdir():
        if path.name == "README.md":
            continue
        _, problems = changelog.validate_fragment(path.name, path.read_text("utf-8"))
        assert problems == [], path.name


def test_repository_readme_names_no_template_string() -> None:
    text = (REPO_ROOT / "changelog.d" / "README.md").read_text(encoding="utf-8").lower()
    # Built from pieces so this file never names a template string itself (init scan).
    forbidden_strings = (
        "proj" + "_template",
        "proj" + "-template",
        "oap" + "-template",
        "8gre" + "g8",
    )
    for forbidden in forbidden_strings:
        assert forbidden not in text
