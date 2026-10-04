#!/usr/bin/env python3
"""Compute the next SemVer version from Conventional Commits since the last release tag.

Stdlib-only, no dependency on the project's own environment (mirrors .agents/tasks/scripts/'s
"runs before anyone has resolved dependencies" constraint).

Algorithm (see DEV_TOOLING_SPEC.md § Version computation and CONTRIBUTING.md § Versioning):
  1. Find the last `vX.Y.Z` tag (git describe); default v0.0.0 if none exists.
  2. Walk commits since that tag on HEAD.
  3. Classify each commit's header the same way commit_lint.py does:
       breaking (`!` or BREAKING CHANGE: footer) > feat > fix > (unclassified, ignored).
  4. Bump the highest level found off the last tag; print the result.

Bump rule (SemVer 0.x convention, as commitizen's `major_version_zero`): while the last tag's
major version is 0, a breaking change bumps minor, so a project stays on 0.y.z until its owner
moves to 1.0.0 on purpose (`release.py --version v1.0.0`). From major 1 onward a breaking change
bumps major. In every case `feat` bumps minor and `fix` bumps patch.

This script never creates a tag -- it only computes and prints. See release.py for tagging.
"""

from __future__ import annotations

import re
import subprocess
import sys

HEADER_RE = re.compile(
    r"^(?P<type>[a-zA-Z]+)(\([^)]+\))?(?P<bang>!)?: (?P<subject>.+)$"
)
TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
RECORD_SEP = "\x1e"
FIELD_SEP = "\x1f"


def run(*args: str) -> str:
    """Run a git command and return its stripped stdout.

    Args:
        args: Arguments after `git`.

    Returns:
        Stripped stdout of the command.

    Raises:
        subprocess.CalledProcessError: If the command exits non-zero.
    """
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def last_tag() -> str:
    """Find the most recent `vX.Y.Z` tag reachable from HEAD.

    Returns:
        The tag name, or "v0.0.0" if no matching tag exists yet.
    """
    try:
        return run(
            "describe", "--tags", "--match", "v[0-9]*.[0-9]*.[0-9]*", "--abbrev=0"
        )
    except subprocess.CalledProcessError:
        return "v0.0.0"


def commits_since(tag: str) -> list[tuple[str, str]]:
    """List (hash, full message) for every commit since `tag` on HEAD.

    Args:
        tag: The tag to diff from. If it's the synthetic "v0.0.0" default and doesn't exist as
            a real ref, all of HEAD's history is used instead.

    Returns:
        A list of (commit hash, commit message) pairs, oldest first.
    """
    rev_range = f"{tag}..HEAD"
    try:
        run("rev-parse", "--verify", tag)
    except subprocess.CalledProcessError:
        rev_range = "HEAD"

    log = run("log", rev_range, f"--pretty=format:%H{FIELD_SEP}%B{RECORD_SEP}")
    if not log:
        return []

    commits = []
    for record in log.split(RECORD_SEP):
        record = record.strip("\n")
        if not record:
            continue
        commit_hash, _, message = record.partition(FIELD_SEP)
        commits.append((commit_hash, message))
    return commits


def classify(message: str) -> str | None:
    """Classify a commit message as 'breaking', 'feat', 'fix', or None (unclassified).

    Args:
        message: Full commit message (header + body).

    Returns:
        The bump level this commit drives, or None if it doesn't affect versioning.
    """
    lines = message.split("\n")
    header = lines[0] if lines else ""
    match = HEADER_RE.match(header)
    if not match:
        return None

    body = "\n".join(lines[1:])
    if match.group("bang") or re.search(r"^BREAKING CHANGE:", body, re.MULTILINE):
        return "breaking"
    if match.group("type") == "feat":
        return "feat"
    if match.group("type") == "fix":
        return "fix"
    return None


def bump(tag: str, level: str) -> str:
    """Apply a SemVer bump to a `vX.Y.Z` tag.

    While the major version is 0, a breaking change bumps minor instead of major.

    Args:
        tag: The current tag, e.g. "v1.2.3".
        level: One of "breaking", "feat", "fix".

    Returns:
        The bumped tag string.
    """
    match = TAG_RE.match(tag)
    if not match:
        raise ValueError(f"tag {tag!r} is not in vX.Y.Z form")
    major, minor, patch = (int(x) for x in match.groups())
    if level == "breaking":
        if major == 0:
            return f"v0.{minor + 1}.0"
        return f"v{major + 1}.0.0"
    if level == "feat":
        return f"v{major}.{minor + 1}.0"
    return f"v{major}.{minor}.{patch + 1}"


def main(argv: list[str]) -> int:
    """Entry point: compute and print the next version.

    Args:
        argv: Command-line arguments (unused positionally; `--quiet` suppresses the commit list).

    Returns:
        Process exit code: 0 if a version was computed, 1 if there's nothing to release.
    """
    quiet = "--quiet" in argv

    tag = last_tag()
    commits = commits_since(tag)

    best_level: str | None = None
    priority = {"breaking": 3, "feat": 2, "fix": 1}
    driving: list[tuple[str, str]] = []

    for commit_hash, message in commits:
        level = classify(message)
        if level is None:
            continue
        if best_level is None or priority[level] > priority[best_level]:
            best_level = level
        driving.append((commit_hash, message.split("\n")[0]))

    if best_level is None:
        print(
            f"nothing to release since {tag} (no feat/fix/breaking commits)",
            file=sys.stderr,
        )
        return 1

    next_v = bump(tag, best_level)

    if not quiet:
        print(f"last tag: {tag}", file=sys.stderr)
        print(f"bump: {best_level}", file=sys.stderr)
        print("commits considered:", file=sys.stderr)
        for commit_hash, header in driving:
            print(f"  {commit_hash[:8]}  {header}", file=sys.stderr)

    print(next_v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
