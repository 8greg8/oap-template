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


def test_hotfix_release_from_main_merges_main_into_develop(repo: Path):
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


@pytest.mark.parametrize(
    "value",
    [
        "1.0.0",
        "v1.0",
        "v1.0.0-rc1",
        "latest",
        "v1.0.0.0",
        "v01.0.0",
        "v1.00.0",
        "v1.0.00",
        "v1.0.0\n",
    ],
)
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


def install_pre_push_hook(repo: Path) -> Path:
    """Wire the real pre-push hook and the real gate.sh into the scratch repo.

    The gate commands are replaced by `true` and committed on develop, so the tree stays clean
    and the gate runs for real except for lint, typecheck and tests. The hook is reached through
    a shim in a hooks directory, which the caller wires in with `core.hooksPath` when it wants
    the hook to run; the other hooks stay off. Returns that directory.
    """
    (repo / "scripts" / "lib").mkdir(parents=True, exist_ok=True)
    shutil.copy(SCRIPTS / "gate.sh", repo / "scripts" / "gate.sh")
    shutil.copy(SCRIPTS / "lib" / "common.sh", repo / "scripts" / "lib" / "common.sh")
    config = repo / "scripts" / "config" / "gate.sh"
    config.write_text(
        config.read_text(encoding="utf-8")
        + "LINT_CMD=true\nFORMAT_CHECK_CMD=true\nTYPECHECK_CMD=true\nTEST_CMD=true\n",
        encoding="utf-8",
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore: gate with cheap commands")
    git(repo, "push", "-q", "origin", "develop")
    hooks = repo.parent / "pre-push-hooks"
    hooks.mkdir()
    shim = hooks / "pre-push"
    shim.write_text(
        f'#!/bin/sh\nexec sh -e "{REPO_ROOT / ".husky" / "pre-push"}" "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return hooks


def test_hotfix_release_push_passes_the_pre_push_hook(repo: Path):
    """`release.py --yes --push` after a hotfix: main is checked out, develop is not.

    The hook gates main's release commit on the checkout, develop's back-merge in a temporary
    worktree (which it removes). The tag push runs no gate: the hook skips tags and other
    non-branch refs.
    """
    hooks = install_pre_push_hook(repo)  # not wired in yet
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    release(repo, "--yes", "--push", expect=0)
    feat(repo, "b")  # develop-only work, not released yet
    git(repo, "push", "-q", "origin", "develop")
    _hotfix_on_main(repo)
    git(repo, "config", "core.hooksPath", str(hooks))

    result = release(repo, "--yes", "--push", expect=0)

    assert "pushed" in result.stdout
    bare = origin_of(repo)
    assert git(bare, "rev-parse", "main") == git(repo, "rev-parse", "main")
    assert git(bare, "rev-parse", "develop") == git(repo, "rev-parse", "develop")
    assert git(bare, "rev-parse", "v0.1.1^{commit}") == git(repo, "rev-parse", "main")
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    # The hook ran the gate for both pushed commits and left no temporary worktree behind.
    gated = {
        line.removeprefix("commit=")
        for record in (repo / ".git" / "gate-pass").iterdir()
        for line in record.read_text(encoding="utf-8").splitlines()
        if line.startswith("commit=")
    }
    assert gated == {git(repo, "rev-parse", "main"), git(repo, "rev-parse", "develop")}
    assert git(repo, "worktree", "list", "--porcelain").count("worktree ") == 1


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


# ------------------------------------------- finishing by hand with the printed commands


def finish_lines(result: subprocess.CompletedProcess[str]) -> list[str]:
    """The commands under "To finish by hand", in order, without the prose hints."""
    lines = result.stderr.splitlines()
    start = next(i for i, line in enumerate(lines) if "To finish by hand" in line) + 1
    commands: list[str] = []
    for line in lines[start:]:
        if not line.strip():
            break
        if not line.strip().startswith("("):
            commands.append(line.strip())
    return commands


def run_finish(repo: Path, result: subprocess.CompletedProcess[str]) -> list[str]:
    """Run the printed finish commands verbatim in a shell, each of which must succeed."""
    commands = finish_lines(result)
    assert commands
    for command in commands:
        done = subprocess.run(
            command,
            shell=True,
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
            env=_env(),
        )
        assert done.returncode == 0, f"{command}\n{done.stdout}{done.stderr}"
    return commands


def reject_release_commits(repo: Path) -> Path:
    """Install a commit-msg hook that rejects `chore(release)` commits; return the hook."""
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
    return hook


def reject_tags(repo: Path) -> Path:
    """Install a reference-transaction hook that aborts creating any tag; return the hook."""
    hooks = repo.parent / "tag-hooks"
    hooks.mkdir()
    hook = hooks / "reference-transaction"
    hook.write_text(
        '#!/bin/sh\n[ "$1" = prepared ] || exit 0\nwhile read old new ref; do\n'
        '  case "$ref" in refs/tags/*) echo "tag rejected by hook" >&2; exit 1;; esac\n'
        "done\nexit 0\n",
        encoding="utf-8",
    )
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    git(repo, "config", "core.hooksPath", str(hooks))
    return hook


def assert_released(
    repo: Path, version: str, start: str, *, same_commit: bool, entry: str = "a.txt"
) -> None:
    """The plan's end state: tagged release on main, develop caught up, start checked out."""
    tip = git(repo, "rev-parse", "main")
    assert subject(repo, "main") == f"chore(release): {version}"
    assert git(repo, "cat-file", "-t", version) == "tag"
    assert git(repo, "rev-list", "-n", "1", version) == tip
    assert git(repo, "merge-base", "--is-ancestor", version, "develop") == ""
    if same_commit:
        assert git(repo, "rev-parse", "develop") == tip
    else:
        assert subject(repo, "develop") == "chore(merge): merge main into develop"
        assert len(parents(repo, "develop")) == 2
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == start
    assert git(repo, "status", "--porcelain") == ""
    assert not [f for f in git(repo, "ls-files", "changelog.d").split() if "added" in f]
    assert f"- Change from {entry}." in git(repo, "show", "main:CHANGELOG.md")


def test_finishing_after_a_merge_conflict_ends_with_develop_fast_forwarded(repo: Path):
    git(repo, "checkout", "-q", "main")
    commit(repo, "clash.txt", "chore: main side", content="main\n")
    git(repo, "push", "-q", "origin", "main")
    git(repo, "checkout", "-q", "develop")
    commit(repo, "clash.txt", "feat: develop side", "a.added.md", content="develop\n")
    git(repo, "push", "-q", "origin", "develop")
    result = release(repo, "--yes", "--push")
    assert result.returncode == 1
    assert "merge --no-ff main" not in result.stderr.split("To undo")[0]

    # A human resolves the conflict, then runs the printed commands as they are.
    (repo / "clash.txt").write_text("resolved\n", encoding="utf-8")
    git(repo, "add", "clash.txt")
    commands = run_finish(repo, result)

    assert "git merge --ff-only main" in commands
    assert commands[-1] == "git push --atomic origin main develop v0.1.0"
    assert_released(repo, "v0.1.0", "develop", same_commit=True, entry="clash.txt")
    assert subject(repo, "main~1") == "chore(merge): merge develop into main"
    for ref in ("main", "develop"):
        assert git(origin_of(repo), "rev-parse", ref) == git(repo, "rev-parse", ref)


def test_finishing_after_a_rejected_release_commit_starts_at_the_commit(repo: Path):
    hook = reject_release_commits(repo)
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")

    result = release(repo, "--yes")

    assert result.returncode == 1
    # The failed attempt left the assembled changelog staged, so assemble is not repeated.
    assert git(repo, "status", "--porcelain") != ""
    commands = finish_lines(result)
    assert commands[0] == "git add -A -- CHANGELOG.md changelog.d"
    assert not any("changelog.py assemble" in c for c in commands)
    assert "git merge --ff-only main" in commands
    assert not any("merge --no-ff main" in c for c in commands)

    hook.unlink()  # the problem is fixed; now run the printed commands
    run_finish(repo, result)

    assert_released(repo, "v0.1.0", "develop", same_commit=True)


def test_finishing_after_a_failed_tag_ends_with_develop_fast_forwarded(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    hook = reject_tags(repo)

    result = release(repo, "--yes")

    assert result.returncode == 1
    assert "FAILED at step 'tag'" in result.stderr
    assert subject(repo, "main") == "chore(release): v0.1.0"
    commands = finish_lines(result)
    assert commands[0].startswith("git tag -a v0.1.0")
    assert "git merge --ff-only main" in commands
    assert not any("merge --no-ff main" in c for c in commands)

    hook.unlink()  # the problem is fixed
    run_finish(repo, result)

    assert_released(repo, "v0.1.0", "develop", same_commit=True)


def test_finishing_after_a_failed_develop_checkout_fast_forwards_develop(repo: Path):
    hooks = repo.parent / "hooks"
    hooks.mkdir()
    hook = hooks / "post-checkout"
    # Its exit status becomes `git checkout`'s: fail once the tag exists and develop is entered.
    hook.write_text(
        '#!/bin/sh\n[ "$(git symbolic-ref --short HEAD)" = develop ] || exit 0\n'
        "git rev-parse -q --verify refs/tags/v0.1.0 >/dev/null || exit 0\n"
        'echo "checkout hook failed" >&2\nexit 1\n',
        encoding="utf-8",
    )
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    git(repo, "config", "core.hooksPath", str(hooks))
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")

    result = release(repo, "--yes", "--push")

    assert result.returncode == 1
    assert "FAILED at step 'develop'" in result.stderr
    assert git(repo, "tag", "--list") == "v0.1.0"
    assert git(repo, "rev-parse", "develop") != git(repo, "rev-parse", "main")
    commands = finish_lines(result)
    assert "git merge --ff-only main" in commands
    assert commands[-1] == "git push --atomic origin main develop v0.1.0"

    hook.unlink()  # the problem is fixed
    run_finish(repo, result)

    assert_released(repo, "v0.1.0", "develop", same_commit=True)
    for ref in ("main", "develop"):
        assert git(origin_of(repo), "rev-parse", ref) == git(repo, "rev-parse", ref)


def test_hotfix_finishing_after_a_failed_back_merge_ends_with_the_no_ff_merge(
    repo: Path,
):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    release(repo, "--yes", "--push", expect=0)
    # develop and the hotfix both change the same file, so merging main into develop conflicts.
    commit(repo, "clash.txt", "feat: develop side", "b.added.md", content="develop\n")
    git(repo, "push", "-q", "origin", "develop")
    git(repo, "checkout", "-q", "main")
    git(repo, "checkout", "-q", "-b", "hotfix/x")
    commit(repo, "clash.txt", "fix: hotfix side", "x.fixed.md", content="hotfix\n")
    git(repo, "checkout", "-q", "main")
    git(
        repo, "merge", "-q", "--no-ff", "hotfix/x", "-m", "chore(merge): merge hotfix/x"
    )
    git(repo, "push", "-q", "origin", "main")

    result = release(repo, "--yes", "--push")

    assert result.returncode == 1
    assert "FAILED at step 'develop'" in result.stderr
    assert "merge in progress: yes" in result.stderr
    assert git(repo, "tag", "--list").split() == ["v0.1.0", "v0.1.1"]
    assert not any("merge --ff-only" in c for c in finish_lines(result))

    (repo / "clash.txt").write_text("resolved\n", encoding="utf-8")
    git(repo, "add", "clash.txt")
    commands = run_finish(repo, result)

    assert commands[-1] == "git push --atomic origin main develop v0.1.1"
    assert subject(repo, "main") == "chore(release): v0.1.1"
    assert git(repo, "rev-list", "-n", "1", "v0.1.1") == git(repo, "rev-parse", "main")
    assert len(parents(repo, "develop")) == 2
    assert git(repo, "merge-base", "--is-ancestor", "v0.1.1", "develop") == ""
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert git(repo, "status", "--porcelain") == ""
    for ref in ("main", "develop"):
        assert git(origin_of(repo), "rev-parse", ref) == git(repo, "rev-parse", ref)


def test_hotfix_finishing_after_a_failed_tag_ends_with_the_no_ff_merge(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    release(repo, "--yes", "--push", expect=0)
    feat(repo, "b")
    git(repo, "push", "-q", "origin", "develop")
    _hotfix_on_main(repo)
    hook = reject_tags(repo)

    result = release(repo, "--yes")

    assert result.returncode == 1
    assert "FAILED at step 'tag'" in result.stderr
    commands = finish_lines(result)
    assert (
        'git merge --no-ff main -m "chore(merge): merge main into develop"' in commands
    )
    assert not any("--ff-only" in c for c in commands)

    hook.unlink()
    run_finish(repo, result)

    assert subject(repo, "main") == "chore(release): v0.1.1"
    assert subject(repo, "develop") == "chore(merge): merge main into develop"
    assert git(repo, "merge-base", "--is-ancestor", "v0.1.1", "develop") == ""
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert git(repo, "status", "--porcelain") == ""


# ------------------------------------------------------------ --push does not imply --yes


@pytest.mark.parametrize("extra", [(), ("--version", "v1.0.0")])
def test_push_without_yes_is_a_usage_error_and_changes_nothing(
    repo: Path, extra: tuple[str, ...]
):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    before = snapshot(repo)

    result = release(repo, "--push", *extra)

    assert result.returncode == 2, output(result)
    assert "usage:" in result.stderr
    assert "--push requires --yes" in result.stderr
    assert snapshot(repo) == before
    assert git(repo, "tag", "--list") == ""


def test_help_says_push_requires_yes(repo: Path):
    result = release(repo, "--help", expect=0)

    text = " ".join(result.stdout.split())
    assert "requires --yes" in text
    assert "implies --yes" not in text


# ------------------------------------------------------------- output of a failed step


def test_failed_step_prints_stdout_and_stderr_both_labelled(repo: Path):
    # Both branches change one file in different places: git merges it (and prints
    # "Auto-merging" on stdout), then pre-merge-commit rejects the merge (stderr).
    numbered = "".join(f"{n}\n" for n in range(1, 21))
    git(repo, "checkout", "-q", "main")
    commit(repo, "clash.txt", "chore: base", content=numbered)
    git(repo, "push", "-q", "origin", "main")
    git(repo, "checkout", "-q", "develop")
    git(repo, "merge", "-q", "main")
    commit(
        repo,
        "clash.txt",
        "feat: develop side",
        "a.added.md",
        content=numbered.replace("2\n", "two\n", 1),
    )
    git(repo, "push", "-q", "origin", "develop")
    git(repo, "checkout", "-q", "main")
    commit(
        repo,
        "clash.txt",
        "chore: main side",
        content=numbered.replace("19\n", "nineteen\n", 1),
    )
    git(repo, "push", "-q", "origin", "main")
    git(repo, "checkout", "-q", "develop")
    hooks = repo.parent / "hooks"
    hooks.mkdir()
    hook = hooks / "pre-merge-commit"
    hook.write_text(
        '#!/bin/sh\necho "merge rejected by hook" >&2\nexit 1\n', encoding="utf-8"
    )
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    git(repo, "config", "core.hooksPath", str(hooks))

    result = release(repo, "--yes")

    text = result.stderr
    assert result.returncode == 1
    assert "FAILED at step 'merge-main'" in text
    report = text.split("Current state:")[0]
    assert "stdout:\n  Auto-merging clash.txt" in report
    assert "stderr:\n  merge rejected by hook" in report
    assert report.index("stdout:") < report.index("stderr:")


def test_failed_step_with_no_output_on_a_stream_labels_it_empty(repo: Path):
    reject_tags(repo)
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")

    result = release(repo, "--yes")

    report = result.stderr.split("Current state:")[0]
    assert "FAILED at step 'tag'" in report
    assert "stdout:\n  (empty)" in report
    assert "stderr:\n  " in report
    assert "tag rejected by hook" in report


# -------------------------------------------- fragment conflict while updating develop


def _modify_delete_conflict_setup(repo: Path) -> None:
    """A hotfix fragment that develop reworded after the hotfix; main is checked out.

    Releasing from main folds the fragment and deletes it there, so merging main into develop
    is a modify/delete conflict on `changelog.d/x.fixed.md`.
    """
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    release(repo, "--yes", "--push", expect=0)
    feat(repo, "b")  # develop-only work: develop will not be an ancestor of main
    git(repo, "push", "-q", "origin", "develop")
    _hotfix_on_main(repo)  # develop now holds x.fixed.md too
    git(repo, "checkout", "-q", "develop")
    (repo / "changelog.d" / "x.fixed.md").write_text(
        "- Change from x.txt, reworded on develop.\n", encoding="utf-8"
    )
    git(repo, "add", "changelog.d/x.fixed.md")
    git(repo, "commit", "-q", "-m", "docs: reword the hotfix fragment")
    git(repo, "push", "-q", "origin", "develop")
    git(repo, "checkout", "-q", "main")


def test_fragment_conflict_on_the_develop_update_advises_git_rm(repo: Path):
    _modify_delete_conflict_setup(repo)

    result = release(repo, "--yes")

    text = result.stderr
    assert result.returncode == 1
    assert "FAILED at step 'develop'" in text
    assert "merge in progress: yes" in text
    finish = text.split("To finish by hand")[1].split("To undo")[0]
    assert "git rm changelog.d/x.fixed.md" in finish
    assert "resolve it as deleted" in finish
    assert finish.index("git rm changelog.d/x.fixed.md") < finish.index(
        "git commit --no-edit"
    )
    # The advice is for fragments only: README.md and other paths get no `git rm` line.
    assert finish.count("git rm") == 1


def test_following_the_git_rm_advice_folds_the_fragment_once(repo: Path):
    _modify_delete_conflict_setup(repo)
    result = release(repo, "--yes")
    assert result.returncode == 1

    commands = run_finish(repo, result)

    assert "git rm changelog.d/x.fixed.md" in commands
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert "changelog.d/x.fixed.md" not in git(repo, "ls-tree", "-r", "develop")
    git(repo, "push", "-q", "origin", "main", "develop", "v0.1.1")
    git(repo, "checkout", "-q", "develop")
    release(repo, "--yes", "--push", expect=0)
    changelog = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert changelog.count("Change from x.txt") == 1
    assert changelog.count("- Change from b.txt.") == 1


def test_a_conflict_on_another_file_gets_no_git_rm_advice(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    release(repo, "--yes", "--push", expect=0)
    commit(repo, "clash.txt", "feat: develop side", "b.added.md", content="develop\n")
    git(repo, "push", "-q", "origin", "develop")
    git(repo, "checkout", "-q", "main")
    git(repo, "checkout", "-q", "-b", "hotfix/x")
    commit(repo, "clash.txt", "fix: hotfix side", "x.fixed.md", content="hotfix\n")
    git(repo, "checkout", "-q", "main")
    git(
        repo, "merge", "-q", "--no-ff", "hotfix/x", "-m", "chore(merge): merge hotfix/x"
    )
    git(repo, "push", "-q", "origin", "main")

    result = release(repo, "--yes")

    assert "FAILED at step 'develop'" in result.stderr
    assert "git rm" not in result.stderr


# ------------------------------------------------------------------- a rejected push


def test_rejected_push_names_the_race_and_a_local_pre_push_hook(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    hooks = repo.parent / "hooks"
    hooks.mkdir()
    hook = hooks / "pre-push"
    hook.write_text(
        '#!/bin/sh\necho "pre-push hook says no" >&2\nexit 1\n', encoding="utf-8"
    )
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    git(repo, "config", "core.hooksPath", str(hooks))

    result = release(repo, "--yes", "--push")

    text = result.stderr
    assert result.returncode == 1, output(result)
    assert "pre-push hook says no" in text
    assert "push rejected" in text
    assert "another push won the race" in text
    assert "git fetch origin" in text
    assert "local pre-push hook failed" in text
    assert text.rstrip().endswith("git push --atomic origin main develop v0.1.0")
    assert git(origin_of(repo), "tag", "--list") == ""
    assert git(repo, "tag", "--list") == "v0.1.0"


# ------------------------------------------------------------------- no commits at all


def test_refuses_a_repository_with_no_commits(tmp_path: Path):
    work = tmp_path / "empty"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    (work / "scripts" / "config").mkdir(parents=True)
    for name in ("release.py", "next_version.py", "changelog.py"):
        shutil.copy(SCRIPTS / name, work / "scripts" / name)
    shutil.copy(SCRIPTS / "config" / "gate.sh", work / "scripts" / "config" / "gate.sh")

    for args in ((), ("--yes",)):
        result = release(work, *args)

        assert result.returncode == 1, output(result)
        assert "refusing to release" in result.stderr
        assert "no commits" in result.stderr
        assert "Traceback" not in output(result)
    assert git(work, "status", "--porcelain").startswith("??")
    assert git(work, "branch", "--list") == ""


# ----------------------------------------------------- the finish list repeats nothing


def test_finish_list_does_not_print_the_checkout_of_develop_twice(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    reject_tags(repo)

    result = release(repo, "--yes", "--push")

    commands = finish_lines(result)
    assert result.returncode == 1
    assert commands.count("git checkout develop") == 1
    assert len(commands) == len(set(commands))
    assert commands[-2:] == [
        "git merge --ff-only main",
        "git push --atomic origin main develop v0.1.0",
    ]


def test_finish_list_still_returns_to_main_after_a_hotfix_release(repo: Path):
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    release(repo, "--yes", "--push", expect=0)
    feat(repo, "b")
    git(repo, "push", "-q", "origin", "develop")
    _hotfix_on_main(repo)
    reject_tags(repo)

    result = release(repo, "--yes")

    commands = finish_lines(result)
    assert result.returncode == 1
    assert commands.count("git checkout develop") == 1
    assert commands[-1] == "git checkout main"
    assert len(commands) == len(set(commands))


# --------------------------------------------------- the real hooks on release.py's commits

HOOK_FILES = (
    ".husky/commit-msg",
    ".husky/pre-commit",
    ".husky/pre-push",
    "scripts/commit_lint.py",
    "scripts/autofix.sh",
    "scripts/lib/common.sh",
)


def install_real_hooks(repo: Path) -> None:
    """Copy the real hooks and their helpers into the fixture, a stub gate, hooks switched on.

    The files are committed on develop and pushed while `core.hooksPath` is still `/dev/null`;
    afterwards every commit, merge and push in the fixture runs the real `.husky` hooks.
    """
    for name in HOOK_FILES:
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / name, target)
    gate = repo / "scripts" / "gate.sh"
    gate.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    gate.chmod(gate.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    # The hooks run changelog.py, which leaves a bytecode cache that a clean tree must ignore.
    (repo / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore: add the hooks")
    git(repo, "push", "-q", "origin", "develop")
    git(repo, "config", "core.hooksPath", ".husky")


def traced_release(
    repo: Path, trace: Path, *args: str
) -> subprocess.CompletedProcess[str]:
    """Run release.py with GIT_TRACE on, so the log shows which hooks git ran."""
    env = {**_env(), "GIT_TRACE": str(trace)}
    result = subprocess.run(
        [sys.executable, "scripts/release.py", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, output(result)
    return result


def hook_runs(trace: Path, hook: str) -> int:
    """Count how often git ran a hook, from a GIT_TRACE log."""
    pattern = re.compile(rf"run_command: .*\.husky/{hook}\b")
    return sum(
        1
        for line in trace.read_text(encoding="utf-8").splitlines()
        if pattern.search(line)
    )


def test_release_commits_pass_the_real_commit_msg_pre_commit_and_pre_push_hooks(
    repo: Path, tmp_path: Path
):
    install_real_hooks(repo)
    feat(repo, "a")  # the fixture's own commit already runs the hooks
    git(repo, "push", "-q", "origin", "develop")
    trace = tmp_path / "trace.log"

    result = traced_release(repo, trace, "--yes", "--push")

    assert "pushed main, develop and v0.1.0 to origin" in result.stdout
    assert subject(repo, "main") == "chore(release): v0.1.0"
    assert subject(repo, "main~1") == "chore(merge): merge develop into main"
    # commit-msg ran on the merge commit and on the release commit.
    assert hook_runs(trace, "commit-msg") == 2
    # pre-commit ran on the release commit only: a merge runs commit-msg but there is no
    # pre-merge-commit hook, and develop is fast-forwarded, so no other commit is made.
    assert hook_runs(trace, "pre-commit") == 1
    # pre-push ran once on the atomic push; its changelog check passed for main and develop.
    assert hook_runs(trace, "pre-push") == 1
    assert result.stdout.count("changelog check passed") == 2
    bare = origin_of(repo)
    assert git(bare, "rev-parse", "main") == git(repo, "rev-parse", "main")
    assert git(bare, "rev-parse", "develop") == git(repo, "rev-parse", "develop")
    assert git(bare, "rev-parse", "v0.1.0^{commit}") == git(repo, "rev-parse", "main")


def test_hotfix_release_commits_pass_the_real_hooks_including_the_back_merge(
    repo: Path, tmp_path: Path
):
    install_real_hooks(repo)
    feat(repo, "a")
    git(repo, "push", "-q", "origin", "develop")
    release(repo, "--yes", "--push", expect=0)
    feat(repo, "b")
    git(repo, "push", "-q", "origin", "develop")
    _hotfix_on_main(repo)
    trace = tmp_path / "trace.log"

    result = traced_release(repo, trace, "--yes", "--push")

    assert subject(repo, "main") == "chore(release): v0.1.1"
    assert subject(repo, "develop") == "chore(merge): merge main into develop"
    # The release commit and the back-merge into develop each ran commit-msg; only the
    # release commit ran pre-commit.
    assert hook_runs(trace, "commit-msg") == 2
    assert hook_runs(trace, "pre-commit") == 1
    assert hook_runs(trace, "pre-push") == 1
    assert result.stdout.count("changelog check passed") == 2
    assert git(origin_of(repo), "rev-parse", "v0.1.1^{commit}") == git(
        repo, "rev-parse", "main"
    )
