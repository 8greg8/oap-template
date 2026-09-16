#!/usr/bin/env python3
"""Cut a release tag on the main branch. Explicit and deliberate -- never run from a hook.

Per AGENTS.md's "ask first" list, cutting a release tag is a human-in-the-loop action; this
script is the tool for that action, not a way to automate around the requirement to invoke it
on purpose. Without --yes it only previews what it would do.

Usage:
    scripts/release.py                 # dry-run: print the version and commits, tag nothing
    scripts/release.py --yes           # create the annotated tag locally
    scripts/release.py --yes --push    # create the tag and push it to origin
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a git command.

    Args:
        args: Arguments after `git`.
        check: Whether to raise on non-zero exit.

    Returns:
        The completed process (stdout/stderr captured as text).
    """
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


def current_branch() -> str:
    """Return the current git branch name.

    Returns:
        The branch name HEAD points to.
    """
    return run("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def working_tree_clean() -> bool:
    """Check whether the working tree has no uncommitted changes.

    Returns:
        True if `git status --porcelain` is empty.
    """
    return run("status", "--porcelain").stdout.strip() == ""


def read_main_branch() -> str:
    """Read MAIN_BRANCH out of scripts/config/gate.sh.

    Returns:
        The configured main branch name, defaulting to "main" if not found.
    """
    gate_config = SCRIPTS_DIR / "config" / "gate.sh"
    text = gate_config.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("MAIN_BRANCH="):
            return line.split("=", 1)[1].strip('"')
    return "main"


def main(argv: list[str]) -> int:
    """Entry point: compute the next version and, with --yes, tag it.

    Args:
        argv: Command-line arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="actually create the tag")
    parser.add_argument(
        "--push", action="store_true", help="push the tag to origin (implies --yes)"
    )
    args = parser.parse_args(argv)
    if args.push:
        args.yes = True

    main_branch = read_main_branch()
    branch = current_branch()
    if branch != main_branch:
        print(
            f"refusing to release from branch {branch!r}; must be on {main_branch!r} "
            "(merge first per CONTRIBUTING.md)",
            file=sys.stderr,
        )
        return 1

    if not working_tree_clean():
        print("refusing to release: working tree is not clean", file=sys.stderr)
        return 1

    next_version = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "next_version.py")],
        text=True,
        capture_output=True,
        check=False,
    )
    sys.stderr.write(next_version.stderr)
    if next_version.returncode != 0:
        return next_version.returncode
    version = next_version.stdout.strip()

    if not args.yes:
        print(f"\nDRY RUN: would tag {version}. Re-run with --yes to create the tag.")
        return 0

    run("tag", "-a", version, "-m", f"Release {version}")
    print(f"created tag {version}")

    if args.push:
        run("push", "origin", version)
        print(f"pushed tag {version} to origin")
    else:
        print(f"tag created locally only -- push with: git push origin {version}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
