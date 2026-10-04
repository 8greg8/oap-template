#!/usr/bin/env python3
"""Release `develop` into `main` with the changelog, a tag, and `develop` brought up to date.

Explicit and deliberate -- never run from a hook. Per CLAUDE.md's "ask first" list, cutting a
release tag is a human-in-the-loop action; this script is the tool for that action, not a way to
automate around the requirement to invoke it on purpose. Run it on a clean `develop`, or on
`main` after `gitflow.sh hotfix finish` (and after pushing both branches).

Usage:
    scripts/release.py                         # dry run: print the version, commits, changelog
    scripts/release.py --yes                   # release locally; nothing is pushed
    scripts/release.py --yes --push            # release and push main, develop and the tag
    scripts/release.py --yes --version v1.0.0  # override the computed version (must be higher
                                               # than the highest vX.Y.Z tag)

With --yes the sequence is:
  1. From `develop`: check out `main` and merge `develop` into it with --no-ff
     (`chore(merge): merge develop into main`). From `main` this step is skipped.
  2. Run `changelog.py assemble <version>` and commit `chore(release): vX.Y.Z` on `main`.
  3. Create the annotated tag `vX.Y.Z` on that commit.
  4. Bring `develop` up to `main`: a fast-forward when `develop` is an ancestor of `main`,
     otherwise a --no-ff merge of `main` into `develop` (`chore(merge): merge main into develop`).
  Then the starting branch is checked out again. With --push, `git push --atomic origin main
  develop vX.Y.Z` lands all three refs or none.

The version comes from next_version.py (SemVer 0.x rule: while the major is 0 a breaking change
bumps minor). `git fetch origin` runs first. Nothing is changed, and the script exits 1, when:
  - the starting branch is not `main` or `develop`;
  - the working tree is dirty;
  - local `main` or `develop` differs from its `origin` counterpart (behind, ahead or diverged);
  - `main` or `develop` is checked out in another worktree;
  - there is nothing to release (no feat/fix/breaking commit, or no changelog fragment), the
    fragments are invalid, or the version is not higher than the highest tag (--version) or
    already exists as a tag.
If a step fails after the first change (merge conflict, a hook rejecting the release commit, a
rejected push) the script stops, prints the current state and the exact commands to finish or
undo by hand, and exits 1. It never resets, forces or retries anything.

This script uses the network only through `git fetch origin` and `git push`.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
# Canonical SemVer numbers only: ASCII digits, no leading zeros (`v01.0.0` is not a version).
VERSION_RE = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
REMOTE = "origin"


class Refusal(Exception):
    """A precondition failed before any change was made."""


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a git command in the current directory.

    Args:
        args: Arguments after `git`.
        check: Whether to raise on non-zero exit.

    Returns:
        The completed process (stdout/stderr captured as text).
    """
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


def git_ok(*args: str) -> bool:
    """Tell whether a git command exits 0.

    Args:
        args: Arguments after `git`.

    Returns:
        True when the exit code is 0.
    """
    return run(*args, check=False).returncode == 0


def run_script(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a sibling Python script from `scripts/`.

    Args:
        name: File name, e.g. `changelog.py`.
        args: Arguments for the script.

    Returns:
        The completed process (stdout/stderr captured as text).
    """
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / name), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def current_branch() -> str:
    """Return the current git branch name.

    Returns:
        The branch name HEAD points to, or `HEAD` when detached.
    """
    return run("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def working_tree_clean() -> bool:
    """Check whether the working tree has no uncommitted changes.

    Returns:
        True if `git status --porcelain` is empty.
    """
    return run("status", "--porcelain").stdout.strip() == ""


def merge_in_progress() -> bool:
    """Tell whether a merge is waiting to be completed or aborted.

    Returns:
        True when `MERGE_HEAD` exists.
    """
    return git_ok("rev-parse", "-q", "--verify", "MERGE_HEAD")


def read_config_value(name: str, default: str) -> str:
    """Read a shell variable assignment out of scripts/config/gate.sh.

    Args:
        name: Variable name, e.g. `MAIN_BRANCH`.
        default: Value to use when the assignment is not found.

    Returns:
        The configured value.
    """
    gate_config = SCRIPTS_DIR / "config" / "gate.sh"
    text = gate_config.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip('"')
    return default


def parse_version(tag: str) -> tuple[int, int, int] | None:
    """Parse a `vX.Y.Z` string.

    Args:
        tag: The candidate string.

    Returns:
        (major, minor, patch), or None when the string is not exactly `vX.Y.Z` with canonical
        numbers (no leading zeros).
    """
    match = VERSION_RE.fullmatch(tag)
    if not match:
        return None
    major, minor, patch = (int(x) for x in match.groups())
    return major, minor, patch


def highest_tag() -> str:
    """Find the highest `vX.Y.Z` tag by SemVer, whichever branch it is on.

    Returns:
        The tag name, or `v0.0.0` when there is none.
    """
    best = (0, 0, 0)
    name = "v0.0.0"
    for tag in run("tag", "--list", "v*").stdout.split():
        parsed = parse_version(tag)
        if parsed is not None and parsed > best:
            best, name = parsed, tag
    return name


def sha(ref: str) -> str | None:
    """Resolve a ref to a commit hash.

    Args:
        ref: Any git revision.

    Returns:
        The full hash, or None when the ref does not exist.
    """
    result = run("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def checked_out_elsewhere(branches: list[str]) -> dict[str, str]:
    """Find branches that another worktree has checked out.

    Args:
        branches: Branch names to look for.

    Returns:
        A map of branch name to the path of the other worktree holding it.
    """
    here = Path(run("rev-parse", "--show-toplevel").stdout.strip()).resolve()
    found: dict[str, str] = {}
    path: str | None = None
    for line in run("worktree", "list", "--porcelain").stdout.splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree ") :]
        elif line.startswith("branch refs/heads/") and path is not None:
            branch = line[len("branch refs/heads/") :]
            if branch in branches and Path(path).resolve() != here:
                found[branch] = path
    return found


def check_matches_origin(branch: str) -> None:
    """Refuse unless a local branch equals its `origin` counterpart.

    Args:
        branch: The branch name.

    Raises:
        Refusal: If either ref is missing or they differ (behind, ahead or diverged).
    """
    local = sha(f"refs/heads/{branch}")
    remote = sha(f"refs/remotes/{REMOTE}/{branch}")
    if local is None:
        raise Refusal(f"local branch {branch!r} does not exist")
    if remote is None:
        raise Refusal(
            f"{REMOTE}/{branch} does not exist; push {branch} to {REMOTE} before releasing"
        )
    if local == remote:
        return
    if git_ok("merge-base", "--is-ancestor", local, remote):
        state = f"behind {REMOTE}/{branch}; pull it first"
    elif git_ok("merge-base", "--is-ancestor", remote, local):
        state = f"ahead of {REMOTE}/{branch}; push it first"
    else:
        state = f"diverged from {REMOTE}/{branch}; reconcile it first"
    raise Refusal(f"local {branch!r} is {state}")


def compute_version() -> tuple[str, str]:
    """Run next_version.py on HEAD.

    Returns:
        (the computed version, the report next_version.py printed to stderr).

    Raises:
        Refusal: If there is nothing to release or the script fails.
    """
    result = run_script("next_version.py")
    if result.returncode != 0:
        raise Refusal(result.stderr.strip() or "next_version.py failed")
    return result.stdout.strip(), result.stderr


def preview_section(version: str) -> str:
    """Run `changelog.py preview` for a version.

    Args:
        version: The release version, `vX.Y.Z`.

    Returns:
        The section the release would write.

    Raises:
        Refusal: If a fragment is invalid or there are no fragments to release.
    """
    result = run_script("changelog.py", "preview", version)
    if result.returncode != 0:
        raise Refusal(result.stderr.strip() or "changelog.py preview failed")
    if not result.stdout.strip():
        raise Refusal(
            "no changelog fragments in changelog.d/; a release needs at least one "
            "(changelog.py assemble would refuse)"
        )
    return result.stdout


@dataclass
class Release:
    """The plan of one release run and the facts needed to report a failure.

    Attributes:
        version: The `vX.Y.Z` being released.
        start: The branch the run started on.
        main: The main branch name.
        develop: The develop branch name.
        main_before: Hash of main before any change.
        develop_before: Hash of develop before any change.
        tag_created: Whether the tag exists yet.
    """

    version: str
    start: str
    main: str
    develop: str
    main_before: str
    develop_before: str
    tag_created: bool = False

    @property
    def push_command(self) -> str:
        """The atomic push command line."""
        return f"git push --atomic {REMOTE} {self.main} {self.develop} {self.version}"

    @property
    def merge_to_main(self) -> list[str]:
        """The commands for step 1."""
        return [
            f"git checkout {self.main}",
            f'git merge --no-ff {self.develop} -m "chore(merge): merge develop into main"',
        ]

    def release_commit(self, assembled: bool = False) -> list[str]:
        """The commands for step 2.

        Args:
            assembled: Whether `changelog.py assemble` already ran, so its result is in the
                working tree or the index; assembling again would refuse.

        Returns:
            The assemble (unless already done), stage and commit command lines.
        """
        return [
            *(
                []
                if assembled
                else [f"python3 scripts/changelog.py assemble {self.version}"]
            ),
            "git add -A -- CHANGELOG.md changelog.d",
            f'git commit -m "chore(release): {self.version}"',
        ]

    @property
    def tag_command(self) -> list[str]:
        """The command for step 3."""
        return [f'git tag -a {self.version} -m "Release {self.version}"']

    def update_develop(self, fast_forward: bool) -> list[str]:
        """The commands for step 4.

        Args:
            fast_forward: Whether develop is an ancestor of main.

        Returns:
            The checkout and merge command lines.
        """
        merge = (
            f"git merge --ff-only {self.main}"
            if fast_forward
            else f'git merge --no-ff {self.main} -m "chore(merge): merge main into develop"'
        )
        return [f"git checkout {self.develop}", merge]

    @property
    def return_to_start(self) -> list[str]:
        """The command that ends the run on the starting branch."""
        return [f"git checkout {self.start}"]


def describe_state(plan: Release) -> str:
    """Describe the repository for a failure report.

    Args:
        plan: The release in progress.

    Returns:
        A multi-line description: branch, HEAD, branch tips, tag, and `git status --short`.
    """
    short = run("status", "--short").stdout.rstrip() or "(clean)"
    lines = [
        f"  current branch: {current_branch()}",
        f"  HEAD: {sha('HEAD')}",
        f"  {plan.main}: {sha(f'refs/heads/{plan.main}')} (was {plan.main_before})",
        f"  {plan.develop}: {sha(f'refs/heads/{plan.develop}')} (was {plan.develop_before})",
        f"  tag {plan.version}: {'created' if plan.tag_created else 'not created'}",
        f"  merge in progress: {'yes' if merge_in_progress() else 'no'}",
        "  git status --short:",
        *(f"    {line}" for line in short.splitlines()),
    ]
    return "\n".join(lines)


def undo_commands(plan: Release, step: str) -> list[str]:
    """List the commands that put the repository back as it was before the run.

    Args:
        plan: The release in progress.
        step: The step that failed (`merge-main`, `release-commit`, `tag`, `develop`, `back`).

    Returns:
        Command lines for a human to run, in order. The script never runs them.
    """
    commands: list[str] = []
    if merge_in_progress():
        commands.append("git merge --abort")
    elif step == "release-commit":
        commands.append(
            "git restore --source=HEAD --staged --worktree -- CHANGELOG.md changelog.d"
        )
    commands.extend(plan.return_to_start)
    if plan.tag_created:
        commands.append(f"git tag -d {plan.version}")
    for branch, before in (
        (plan.main, plan.main_before),
        (plan.develop, plan.develop_before),
    ):
        if sha(f"refs/heads/{branch}") == before:
            continue
        if branch == plan.start:
            commands.append(f"git reset --hard {before}")
        else:
            commands.append(f"git branch -f {branch} {before}")
    return commands


def changelog_assembled() -> bool:
    """Tell whether `changelog.py assemble` already left its result in the tree or the index.

    Returns:
        True when `CHANGELOG.md` or `changelog.d` has uncommitted changes.
    """
    return (
        run("status", "--porcelain", "--", "CHANGELOG.md", "changelog.d").stdout.strip()
        != ""
    )


def finish_commands(plan: Release, step: str, push: bool) -> list[str]:
    """List the commands that complete the release by hand after a failed step.

    The list starts at the failed step, leaves out work that is already done, and picks the
    `develop` update from the state as it is now (or as it will be once a pending merge into
    `main` completes), by `git merge-base --is-ancestor`, not by the starting branch.

    Args:
        plan: The release in progress.
        step: The step that failed (`merge-main`, `release-commit`, `tag`, `develop`, `back`).
        push: Whether the run was asked to push at the end.

    Returns:
        Command lines for a human to run, in order. The script never runs them.
    """
    resolve = ["(resolve the conflicts and git add them)", "git commit --no-edit"]
    # Once the merge of develop into main is complete, develop is an ancestor of main.
    develop_ff = step == "merge-main" or git_ok(
        "merge-base", "--is-ancestor", plan.develop, plan.main
    )
    commands: list[str] = []
    if step == "merge-main":
        commands += resolve if merge_in_progress() else plan.merge_to_main
    if step in ("merge-main", "release-commit"):
        # Only a failed release commit can follow an assemble; a pending merge also leaves the
        # incoming fragments staged, which must not be mistaken for an assemble result.
        commands += plan.release_commit(
            assembled=step == "release-commit" and changelog_assembled()
        )
    if step in ("merge-main", "release-commit", "tag"):
        commands += plan.tag_command
    if step == "develop" and merge_in_progress():
        commands += resolve
    elif step != "back":
        commands += plan.update_develop(develop_ff)
    commands += plan.return_to_start
    if push:
        commands.append(plan.push_command)
    return commands


def stop_after_failure(
    plan: Release,
    step: str,
    result: subprocess.CompletedProcess[str],
    push: bool,
) -> int:
    """Print the state and recovery commands after a failed step.

    Args:
        plan: The release in progress.
        step: Name of the failed step (see `undo_commands`).
        result: The failed command's result.
        push: Whether the run was asked to push, so the finish list ends with the push.

    Returns:
        The exit code, always 1.
    """
    out = [
        f"release FAILED at step '{step}'. Nothing has been reset or forced.",
        "",
        (result.stderr or result.stdout).rstrip(),
        "",
        "Current state:",
        describe_state(plan),
        "",
        "To finish by hand (fix the problem first), run in order:",
        *(f"  {command}" for command in finish_commands(plan, step, push)),
        "",
        "To undo what this run changed instead, run in order:",
        *(f"  {command}" for command in undo_commands(plan, step)),
    ]
    print("\n".join(out), file=sys.stderr)
    return 1


def merge_into(
    target: str, source: str, message: str
) -> subprocess.CompletedProcess[str]:
    """Check out `target` and merge `source` into it with --no-ff.

    Args:
        target: Branch to check out.
        source: Branch to merge.
        message: Merge commit message.

    Returns:
        The result of the first command that failed, or of the merge.
    """
    step = run("checkout", target, check=False)
    if step.returncode != 0:
        return step
    return run("merge", "--no-ff", source, "-m", message, check=False)


def execute(plan: Release, push: bool) -> int:
    """Run the release steps after every refusal check has passed.

    Args:
        plan: The release to perform.
        push: Whether to push main, develop and the tag at the end.

    Returns:
        The process exit code.
    """
    if plan.start == plan.develop:
        step = merge_into(
            plan.main, plan.develop, "chore(merge): merge develop into main"
        )
        if step.returncode != 0:
            return stop_after_failure(plan, "merge-main", step, push)
        print(f"merged {plan.develop} into {plan.main}")

    step = run_script("changelog.py", "assemble", plan.version)
    if step.returncode == 0:
        step = run("add", "-A", "--", "CHANGELOG.md", "changelog.d", check=False)
    if step.returncode == 0:
        step = run("commit", "-m", f"chore(release): {plan.version}", check=False)
    if step.returncode != 0:
        return stop_after_failure(plan, "release-commit", step, push)
    print(f"committed chore(release): {plan.version} on {plan.main}")

    step = run("tag", "-a", plan.version, "-m", f"Release {plan.version}", check=False)
    if step.returncode != 0:
        return stop_after_failure(plan, "tag", step, push)
    plan.tag_created = True
    print(f"created tag {plan.version}")

    # Decided by ancestry, not by the starting branch: after a hotfix develop has diverged.
    fast_forward = git_ok("merge-base", "--is-ancestor", plan.develop, plan.main)
    if fast_forward:
        step = run("checkout", plan.develop, check=False)
        if step.returncode == 0:
            step = run("merge", "--ff-only", plan.main, check=False)
    else:
        step = merge_into(
            plan.develop, plan.main, "chore(merge): merge main into develop"
        )
    if step.returncode != 0:
        return stop_after_failure(plan, "develop", step, push)
    if fast_forward:
        print(f"fast-forwarded {plan.develop} to {plan.main}")
    else:
        print(f"merged {plan.main} into {plan.develop}")

    step = run("checkout", plan.start, check=False)
    if step.returncode != 0:
        return stop_after_failure(plan, "back", step, push)

    if not push:
        print(f"released {plan.version} locally -- push with: {plan.push_command}")
        return 0

    pushed = subprocess.run(
        ["git", "push", "--atomic", REMOTE, plan.main, plan.develop, plan.version],
        check=False,
    )
    if pushed.returncode != 0:
        print(
            f"\npush rejected: none of {plan.main}, {plan.develop} and {plan.version} "
            f"reached {REMOTE}. The release is complete locally. Fix the cause (for example "
            f"`git fetch {REMOTE}` and look at what changed), then retry:\n"
            f"  {plan.push_command}",
            file=sys.stderr,
        )
        return 1
    print(f"pushed {plan.main}, {plan.develop} and {plan.version} to {REMOTE}")
    return 0


def prepare(requested_version: str | None) -> tuple[Release, str, str]:
    """Run every refusal check and compute the release.

    Args:
        requested_version: The `--version` value, or None to use next_version.py.

    Returns:
        (the release plan, next_version.py's report, the changelog section preview).

    Raises:
        Refusal: If any precondition fails. Nothing has been changed except remote-tracking
            refs updated by `git fetch`.
    """
    main_branch = read_config_value("MAIN_BRANCH", "main")
    develop_branch = read_config_value("DEVELOP_BRANCH", "develop")

    start = current_branch()
    if start not in (main_branch, develop_branch):
        raise Refusal(
            f"cannot release from branch {start!r}; start on {develop_branch!r} (a normal "
            f"release) or {main_branch!r} (after a pushed hotfix), per CONTRIBUTING.md"
        )

    fetched = run("fetch", REMOTE, check=False)
    if fetched.returncode != 0:
        raise Refusal(f"git fetch {REMOTE} failed:\n{fetched.stderr.strip()}")

    if not working_tree_clean():
        raise Refusal("working tree is not clean; commit or stash your changes first")

    check_matches_origin(main_branch)
    check_matches_origin(develop_branch)

    elsewhere = checked_out_elsewhere([main_branch, develop_branch])
    if elsewhere:
        held = ", ".join(f"{b!r} in {p}" for b, p in sorted(elsewhere.items()))
        raise Refusal(
            f"{held} is checked out in another worktree; the release checks out both "
            f"{main_branch!r} and {develop_branch!r}, so free them first"
        )

    version, report = compute_version()
    if requested_version is not None:
        version = requested_version
        latest = highest_tag()
        parsed, latest_parsed = parse_version(version), parse_version(latest)
        if parsed is None or latest_parsed is None or parsed <= latest_parsed:
            raise Refusal(
                f"--version {version} must be higher than the latest tag {latest}"
            )
    if sha(f"refs/tags/{version}") is not None:
        raise Refusal(f"tag {version} already exists")

    section = preview_section(version)

    main_sha = sha(f"refs/heads/{main_branch}")
    develop_sha = sha(f"refs/heads/{develop_branch}")
    if main_sha is None or develop_sha is None:
        raise Refusal("cannot resolve the main and develop branches")
    plan = Release(
        version=version,
        start=start,
        main=main_branch,
        develop=develop_branch,
        main_before=main_sha,
        develop_before=develop_sha,
    )
    return plan, report, section


def main(argv: list[str]) -> int:
    """Entry point: compute the next version and, with --yes, release it.

    Args:
        argv: Command-line arguments.

    Returns:
        Process exit code: 0 on success or a dry run, 1 on a refusal or a failed step,
        2 on a usage error.
    """
    parser = argparse.ArgumentParser(
        description="Release develop into main with the changelog.",
        epilog="See the module docstring (or scripts/README.md) for the full sequence.",
    )
    parser.add_argument("--yes", action="store_true", help="actually release (locally)")
    parser.add_argument(
        "--push",
        action="store_true",
        help="push main, develop and the tag atomically (implies --yes)",
    )
    parser.add_argument(
        "--version",
        metavar="vX.Y.Z",
        help="override the computed version; must be higher than the highest tag",
    )
    args = parser.parse_args(argv)
    if args.push:
        args.yes = True
    if args.version is not None and parse_version(args.version) is None:
        parser.error(f"--version {args.version!r} is not in vX.Y.Z form")

    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if top.returncode != 0:
        print("refusing to release: not inside a git repository", file=sys.stderr)
        return 1
    os.chdir(top.stdout.strip())

    try:
        plan, report, section = prepare(args.version)
    except Refusal as exc:
        print(f"refusing to release: {exc}", file=sys.stderr)
        return 1

    sys.stderr.write(report)
    if not args.yes:
        print(f"\nChangelog section for {plan.version}:\n\n{section}")
        print(
            f"DRY RUN: would release {plan.version} from {plan.start!r}. "
            "Re-run with --yes to do it."
        )
        return 0

    return execute(plan, args.push)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
