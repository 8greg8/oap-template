"""Tests for `scripts/release.py`.

Each case builds a scratch repository with a local bare `origin`, copies the real `release.py`,
`next_version.py`, `changelog.py` and `config/gate.sh` into it, and runs the script as a
subprocess. Nothing touches the network or reads this repository's own CHANGELOG.md,
changelog.d/ or history, so the file also passes in a generated project.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"

HEADER = """\
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

"""
EMPTY_CHANGELOG = HEADER + "## [Unreleased]\n"


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


def release(
    repo: Path, *args: str, expect: int | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, "scripts/release.py", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )
    if expect is not None:
        assert result.returncode == expect, result.stdout + result.stderr
    return result


def output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo `proj` on `develop`, equal to `main`, with a bare `origin` holding both."""
    bare = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", "main", str(bare)],
        check=True,
        env=_env(),
    )
    work = tmp_path / "proj"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    git(work, "config", "core.hooksPath", "/dev/null")
    (work / "scripts" / "config").mkdir(parents=True)
    for name in ("release.py", "next_version.py", "changelog.py"):
        shutil.copy(SCRIPTS / name, work / "scripts" / name)
    shutil.copy(SCRIPTS / "config" / "gate.sh", work / "scripts" / "config" / "gate.sh")
    (work / "CHANGELOG.md").write_text(EMPTY_CHANGELOG, encoding="utf-8")
    (work / "changelog.d").mkdir()
    (work / "changelog.d" / "README.md").write_text("# Fragments\n", encoding="utf-8")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "chore: init")
    git(work, "remote", "add", "origin", str(bare))
    git(work, "push", "-q", "origin", "main")
    git(work, "checkout", "-q", "-b", "develop")
    git(work, "push", "-q", "origin", "develop")
    return work


def origin_of(repo: Path) -> Path:
    return repo.parent / "origin.git"


def commit(
    repo: Path,
    filename: str,
    message: str,
    fragment: str | None = None,
    content: str = "x\n",
) -> None:
    """Commit one file, plus a valid fragment with that name when given."""
    (repo / filename).write_text(content, encoding="utf-8")
    git(repo, "add", filename)
    if fragment:
        path = repo / "changelog.d" / fragment
        path.write_text(f"- Change from {filename}.\n", encoding="utf-8")
        git(repo, "add", str(path))
    git(repo, "commit", "-q", "-m", message)


def feat(repo: Path, name: str = "a") -> None:
    commit(repo, f"{name}.txt", f"feat: add {name}", f"{name}.added.md")


def snapshot(repo: Path) -> dict[str, str]:
    """Everything a refused or dry run must leave alone.

    Remote-tracking refs are left out: `git fetch origin` is allowed to update them.
    """
    return {
        "refs": git(
            repo,
            "for-each-ref",
            "--format=%(refname) %(objectname)",
            "refs/heads",
            "refs/tags",
        ),
        "origin": git(
            origin_of(repo), "for-each-ref", "--format=%(refname) %(objectname)"
        ),
        "branch": git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
        "status": git(repo, "status", "--porcelain"),
        "changelog": (repo / "CHANGELOG.md").read_text(encoding="utf-8"),
        "fragments": git(repo, "ls-files", "changelog.d"),
    }


def assert_refused(repo: Path, args: tuple[str, ...], message: str) -> None:
    before = snapshot(repo)
    result = release(repo, *args)
    assert result.returncode == 1, output(result)
    assert message in output(result)
    assert snapshot(repo) == before


def parents(repo: Path, ref: str) -> list[str]:
    return git(repo, "log", "-1", "--format=%P", ref).split()


def subject(repo: Path, ref: str) -> str:
    return git(repo, "log", "-1", "--format=%s", ref)


# ---------------------------------------------------------------------------- dry run


def test_dry_run_prints_version_commits_and_changelog_and_changes_nothing(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    before = snapshot(repo)

    result = release(repo, expect=0)

    text = output(result)
    assert "v0.1.0" in text
    assert "feat: add a" in text
    assert "## [0.1.0] - " in text
    assert "### Added" in text
    assert "- Change from a.txt." in text
    assert "DRY RUN" in text
    assert snapshot(repo) == before
    assert (repo / "changelog.d" / "a.added.md").is_file()


# ----------------------------------------------------------------------- normal release


def test_normal_release_from_develop(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    origin_before = git(
        origin_of(repo), "for-each-ref", "--format=%(refname) %(objectname)"
    )

    release(repo, "--yes", expect=0)

    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "develop"
    release_commit = git(repo, "rev-parse", "main")
    assert git(repo, "rev-parse", "develop") == release_commit
    assert subject(repo, "main") == "chore(release): v0.1.0"
    assert subject(repo, "main~1") == "chore(merge): merge develop into main"
    assert len(parents(repo, "main~1")) == 2
    assert git(repo, "cat-file", "-t", "v0.1.0") == "tag"
    assert git(repo, "rev-list", "-n", "1", "v0.1.0") == release_commit
    changelog = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(r"^## \[0\.1\.0\] - \d{4}-\d{2}-\d{2}$", changelog, re.MULTILINE)
    assert "- Change from a.txt." in changelog
    assert not (repo / "changelog.d" / "a.added.md").exists()
    assert (repo / "changelog.d" / "README.md").is_file()
    assert git(repo, "status", "--porcelain") == ""
    # Nothing is pushed without --push.
    after = git(origin_of(repo), "for-each-ref", "--format=%(refname) %(objectname)")
    assert after == origin_before


def test_next_release_does_not_fold_anything_twice(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    release(repo, "--yes", "--push", expect=0)
    commit(repo, "b.txt", "fix: repair b", "b.fixed.md")
    git(repo, "push", "-q", "origin", "develop")

    release(repo, "--yes", "--push", expect=0)

    assert subject(repo, "main") == "chore(release): v0.1.1"
    changelog = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert changelog.count("- Change from a.txt.") == 1
    assert changelog.count("- Change from b.txt.") == 1
    assert changelog.index("## [0.1.1]") < changelog.index("## [0.1.0]")
    assert git(repo, "ls-files", "changelog.d") == "changelog.d/README.md"


def test_first_release_from_no_tags_with_breaking_commit_is_v0_1_0(repo: Path):
    commit(
        repo,
        "a.txt",
        "feat!: replace the interface\n\nBREAKING CHANGE: the old interface is gone",
        "a.changed.md",
    )
    git(repo, "push", "-q", "origin", "develop")
    assert git(repo, "tag", "--list") == ""

    release(repo, "--yes", expect=0)

    assert git(repo, "tag", "--list") == "v0.1.0"


# --------------------------------------------------------------------- hotfix release


def _hotfix_on_main(repo: Path) -> None:
    """Hotfix branch merged into main and back into develop, both pushed, main checked out."""
    git(repo, "checkout", "-q", "main")
    git(repo, "checkout", "-q", "-b", "hotfix/x")
    commit(repo, "x.txt", "fix: repair x", "x.fixed.md")
    git(repo, "checkout", "-q", "main")
    git(
        repo, "merge", "-q", "--no-ff", "hotfix/x", "-m", "chore(merge): merge hotfix/x"
    )
    git(repo, "checkout", "-q", "develop")
    git(repo, "merge", "-q", "--no-ff", "main", "-m", "chore(merge): merge main")
    git(repo, "push", "-q", "origin", "main", "develop")
    git(repo, "checkout", "-q", "main")


def test_hotfix_release_from_main_back_merges_develop(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    release(repo, "--yes", "--push", expect=0)
    feat(repo, "b")  # develop-only work, not released yet
    git(repo, "push", "-q", "origin", "develop")
    _hotfix_on_main(repo)

    release(repo, "--yes", "--push", expect=0)

    # Step 1 is skipped: the release commit sits directly on the hotfix merge.
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert subject(repo, "main") == "chore(release): v0.1.1"
    assert subject(repo, "main~1") == "chore(merge): merge hotfix/x"
    assert git(repo, "cat-file", "-t", "v0.1.1") == "tag"
    assert git(repo, "rev-list", "-n", "1", "v0.1.1") == git(repo, "rev-parse", "main")
    # develop diverged, so it takes a --no-ff back-merge of main.
    assert subject(repo, "develop") == "chore(merge): merge main into develop"
    assert len(parents(repo, "develop")) == 2
    assert git(repo, "merge-base", "--is-ancestor", "v0.1.1", "develop") == ""
    # The hotfix fragment was folded and is gone; develop's pending fragment stays.
    develop_files = git(repo, "ls-tree", "-r", "--name-only", "develop", "changelog.d")
    assert "changelog.d/b.added.md" in develop_files
    assert "x.fixed.md" not in develop_files
    main_changelog = git(repo, "show", "main:CHANGELOG.md")
    assert "- Change from x.txt." in main_changelog
    assert "- Change from b.txt." not in main_changelog
    # Everything landed on origin.
    for ref in ("main", "develop"):
        assert git(origin_of(repo), "rev-parse", ref) == git(repo, "rev-parse", ref)
    assert git(origin_of(repo), "rev-parse", "v0.1.1^{commit}") == git(
        repo, "rev-parse", "main"
    )

    # The next release from develop folds only what was left, once.
    git(repo, "checkout", "-q", "develop")
    release(repo, "--yes", "--push", expect=0)
    assert subject(repo, "main") == "chore(release): v0.2.0"
    changelog = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert changelog.count("- Change from x.txt.") == 1
    assert changelog.count("- Change from b.txt.") == 1
    assert git(repo, "rev-parse", "main") == git(repo, "rev-parse", "develop")


# ----------------------------------------------------------------------------- --version


def test_version_override_higher_than_latest_tag(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")

    release(repo, "--yes", "--version", "v1.0.0", expect=0)

    assert git(repo, "tag", "--list") == "v1.0.0"
    assert "## [1.0.0] - " in (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert subject(repo, "main") == "chore(release): v1.0.0"


def test_version_override_uses_semver_order_not_text_order(repo: Path):
    git(repo, "tag", "-a", "v0.10.0", "-m", "v0.10.0", "main")
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")

    assert_refused(repo, ("--yes", "--version", "v0.9.5"), "v0.10.0")
    assert_refused(repo, ("--yes", "--version", "v0.10.0"), "must be higher")

    release(repo, "--yes", "--version", "v0.10.1", expect=0)
    assert git(repo, "rev-list", "-n", "1", "v0.10.1") == git(repo, "rev-parse", "main")


def test_version_override_lower_than_any_tag_is_refused_without_tags_too(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")

    assert_refused(repo, ("--yes", "--version", "v0.0.0"), "must be higher")


@pytest.mark.parametrize("value", ["1.0.0", "v1.0", "v1.0.0-rc1", "latest", "v1.0.0.0"])
def test_version_accepts_only_vx_y_z(repo: Path, value: str):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    before = snapshot(repo)

    result = release(repo, "--yes", "--version", value)

    assert result.returncode == 2
    assert "vX.Y.Z" in result.stderr
    assert snapshot(repo) == before


# ---------------------------------------------------------------------------- refusals


def test_refuses_a_branch_other_than_main_or_develop(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    git(repo, "checkout", "-q", "-b", "feat/other")

    assert_refused(repo, ("--yes",), "cannot release from branch 'feat/other'")
    assert_refused(repo, (), "cannot release from branch 'feat/other'")


@pytest.mark.parametrize("args", [("--yes",), ()])
@pytest.mark.parametrize("kind", ["untracked", "modified"])
def test_refuses_a_dirty_tree(repo: Path, kind: str, args: tuple[str, ...]):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    if kind == "untracked":
        (repo / "scratch.txt").write_text("x\n", encoding="utf-8")
    else:
        (repo / "a.txt").write_text("changed\n", encoding="utf-8")

    assert_refused(repo, args, "working tree is not clean")


def _desync(repo: Path, branch: str, kind: str) -> None:
    """Make local `branch` ahead of, behind or diverged from origin; end on develop."""
    git(repo, "checkout", "-q", branch)
    if kind == "ahead":
        commit(repo, f"{branch}-local.txt", "chore: local only")
    elif kind == "behind":
        commit(repo, f"{branch}-remote.txt", "chore: remote only")
        git(repo, "push", "-q", "origin", branch)
        git(repo, "reset", "-q", "--hard", "HEAD~1")
    else:
        commit(repo, f"{branch}-remote.txt", "chore: remote only")
        git(repo, "push", "-q", "origin", branch)
        git(repo, "reset", "-q", "--hard", "HEAD~1")
        commit(repo, f"{branch}-local.txt", "chore: local only")
    git(repo, "checkout", "-q", "develop")


@pytest.mark.parametrize(
    ("kind", "wording"),
    [("ahead", "ahead of"), ("behind", "behind"), ("diverged", "diverged from")],
)
@pytest.mark.parametrize("branch", ["main", "develop"])
def test_refuses_a_branch_that_differs_from_origin(
    repo: Path, branch: str, kind: str, wording: str
):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    _desync(repo, branch, kind)

    assert_refused(repo, ("--yes",), f"local {branch!r} is {wording}")


def test_refuses_when_origin_has_no_main(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    git(origin_of(repo), "branch", "-m", "main", "trunk")
    git(repo, "update-ref", "-d", "refs/remotes/origin/main")

    assert_refused(repo, ("--yes",), "origin/main does not exist")


def test_refuses_when_fetch_fails(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    git(repo, "remote", "set-url", "origin", str(repo.parent / "missing.git"))

    assert_refused(repo, ("--yes",), "git fetch origin failed")


def test_refuses_when_main_is_checked_out_in_another_worktree(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    other = repo.parent / "wt-main"
    git(repo, "worktree", "add", "-q", str(other), "main")

    assert_refused(repo, ("--yes",), "checked out in another worktree")


def test_refuses_when_develop_is_checked_out_in_another_worktree(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    git(repo, "checkout", "-q", "main")
    other = repo.parent / "wt-develop"
    git(repo, "worktree", "add", "-q", str(other), "develop")

    assert_refused(repo, ("--yes",), "'develop' in")


def test_refuses_when_there_is_nothing_to_release(repo: Path):
    commit(repo, "notes.txt", "docs: only words")
    git(repo, "push", "-q", "origin", "develop")

    assert_refused(repo, ("--yes",), "nothing to release")
    assert_refused(repo, (), "nothing to release")


def test_refuses_when_nothing_is_new_since_the_last_release(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    release(repo, "--yes", "--push", expect=0)

    assert_refused(repo, ("--yes",), "nothing to release")


def test_refuses_a_release_without_changelog_fragments(repo: Path):
    commit(repo, "a.txt", "feat: add a without a fragment")
    git(repo, "push", "-q", "origin", "develop")

    assert_refused(repo, ("--yes",), "no changelog fragments")


def test_refuses_an_invalid_fragment(repo: Path):
    feat(repo, "a")
    (repo / "changelog.d" / "bad.added.md").write_text(
        "no bullet here\n", encoding="utf-8"
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore: add a bad fragment")
    git(repo, "push", "-q", "origin", "develop")

    assert_refused(repo, ("--yes",), "bad.added.md")


def test_refuses_a_tag_that_already_exists(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    # A tag on a commit no branch reaches: next_version.py does not see it, so it computes
    # v0.1.0 again.
    orphan = git(repo, "commit-tree", "develop^{tree}", "-m", "unreachable")
    git(repo, "tag", "v0.1.0", orphan)

    assert_refused(repo, ("--yes",), "tag v0.1.0 already exists")


# ------------------------------------------------------------------------------ --push


def test_push_lands_main_develop_and_tag_on_origin(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")

    result = release(repo, "--yes", "--push", expect=0)

    assert "pushed" in result.stdout
    bare = origin_of(repo)
    tip = git(repo, "rev-parse", "main")
    assert git(bare, "rev-parse", "main") == tip
    assert git(bare, "rev-parse", "develop") == tip
    assert git(bare, "rev-parse", "v0.1.0^{commit}") == tip
    assert git(bare, "cat-file", "-t", "v0.1.0") == "tag"


def test_push_is_atomic_when_one_ref_is_rejected(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    bare = origin_of(repo)
    hook = bare / "hooks" / "update"
    hook.write_text(
        '#!/bin/sh\ncase "$1" in refs/tags/*) echo "tags are rejected here" >&2; exit 1;; '
        "esac\nexit 0\n",
        encoding="utf-8",
    )
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    origin_before = git(bare, "for-each-ref", "--format=%(refname) %(objectname)")

    result = release(repo, "--yes", "--push")

    assert result.returncode == 1, output(result)
    assert "git push --atomic origin main develop v0.1.0" in result.stderr
    # The remote is unchanged: main and develop did not land without the tag.
    assert (
        git(bare, "for-each-ref", "--format=%(refname) %(objectname)") == origin_before
    )
    # The release itself is complete locally.
    assert git(repo, "tag", "--list") == "v0.1.0"
    assert subject(repo, "main") == "chore(release): v0.1.0"
    assert git(repo, "rev-parse", "develop") == git(repo, "rev-parse", "main")
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "develop"


# ------------------------------------------------------------ failure after a change


def test_merge_conflict_stops_and_prints_state_and_commands(repo: Path):
    git(repo, "checkout", "-q", "main")
    commit(repo, "clash.txt", "chore: main side", content="main\n")
    git(repo, "push", "-q", "origin", "main")
    git(repo, "checkout", "-q", "develop")
    commit(repo, "clash.txt", "feat: develop side", "a.added.md", content="develop\n")
    git(repo, "push", "-q", "origin", "develop")
    main_before = git(repo, "rev-parse", "main")
    develop_before = git(repo, "rev-parse", "develop")

    result = release(repo, "--yes")

    text = result.stderr
    assert result.returncode == 1
    assert "FAILED at step 'merge-main'" in text
    assert "Current state:" in text
    assert "merge in progress: yes" in text
    assert "To finish by hand" in text
    assert "git commit --no-edit" in text
    assert 'git tag -a v0.1.0 -m "Release v0.1.0"' in text
    assert "To undo" in text
    assert "git merge --abort" in text
    assert "git checkout develop" in text
    # Nothing was reset, forced or committed on top.
    assert (repo / ".git" / "MERGE_HEAD").exists()
    assert git(repo, "rev-parse", "main") == main_before
    assert git(repo, "rev-parse", "develop") == develop_before
    assert git(repo, "tag", "--list") == ""


def test_hook_rejecting_the_release_commit_stops_and_prints_commands(repo: Path):
    hooks = repo.parent / "hooks"
    hooks.mkdir()
    hook = hooks / "commit-msg"
    hook.write_text(
        '#!/bin/sh\nif grep -q "^chore(release)" "$1"; then\n'
        '  echo "release commit rejected by hook" >&2\n  exit 1\nfi\nexit 0\n',
        encoding="utf-8",
    )
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    git(repo, "config", "core.hooksPath", str(hooks))
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    develop_before = git(repo, "rev-parse", "develop")

    result = release(repo, "--yes")

    text = result.stderr
    assert result.returncode == 1
    assert "FAILED at step 'release-commit'" in text
    assert "release commit rejected by hook" in text
    assert 'git commit -m "chore(release): v0.1.0"' in text
    assert (
        "git restore --source=HEAD --staged --worktree -- CHANGELOG.md changelog.d"
        in text
    )
    assert "git branch -f main" in text
    # The merge step completed, the commit and the tag did not, and develop was not touched.
    assert subject(repo, "main") == "chore(merge): merge develop into main"
    assert git(repo, "tag", "--list") == ""
    assert git(repo, "rev-parse", "develop") == develop_before
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main"
