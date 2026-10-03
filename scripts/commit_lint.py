#!/usr/bin/env python3
"""Validate a commit message against Conventional Commits + this repo's breaking-change rule.

Invoked by .husky/commit-msg as: commit_lint.py "$1" (the path Git gives the commit-msg hook).
Stdlib-only -- no npm/commitlint dependency required.

Rules enforced (see CONTRIBUTING.md § Commits):
  - Header matches: type(scope)!: subject
  - type is one of the Conventional Commits types below.
  - subject is non-empty and does not end with a period.
  - Header, body and footer lines are each <=100 chars.
  - Everything below git's scissors line (`git commit -v`) is ignored.
  - If the header has `!`, the body must contain a `BREAKING CHANGE:` footer, and vice versa --
    a breaking change must be marked both ways, never just one.

Git's own auto-generated merge commit messages ("Merge branch 'x' into y", "Merge pull request
#N ...") stay exempt for merges git writes itself; this matches commitlint's default behavior.
This repo's own merges (scripts/gitflow.sh) use the Conventional form
`chore(merge): merge task NNNN into develop`, which is linted like any other header.
"""

from __future__ import annotations

import re
import sys

MERGE_MESSAGE_RE = re.compile(
    r"^Merge (branch|pull request|remote-tracking branch|tag) "
)

ALLOWED_TYPES = {
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
}

HEADER_RE = re.compile(
    r"^(?P<type>[a-zA-Z]+)(\((?P<scope>[^)]+)\))?(?P<bang>!)?: (?P<subject>.+)$"
)
MAX_HEADER_LEN = 100
MAX_LINE_LEN = 100
SCISSORS_RE = re.compile(r"^# -+ >8 -+$")


def strip_comments(message: str) -> str:
    """Drop Git's `# ...` comment lines and everything below its scissors line.

    `git commit -v` appends the staged diff below a scissors line; the commit-msg hook sees
    the file before git strips it, and the diff's long lines must not be linted.

    Args:
        message: Raw commit message file contents.

    Returns:
        The message with comment lines and the scissors section removed.
    """
    kept: list[str] = []
    for line in message.splitlines():
        if SCISSORS_RE.match(line):
            break
        if not line.startswith("#"):
            kept.append(line)
    return "\n".join(kept)


def lint(message: str) -> list[str]:
    """Check a commit message against the rules described in the module docstring.

    Args:
        message: Full commit message text (header + optional body/footers).

    Returns:
        A list of human-readable violation messages; empty if the message is valid.
    """
    errors: list[str] = []
    cleaned = strip_comments(message).strip("\n")
    lines = cleaned.split("\n")
    header = lines[0] if lines else ""

    if MERGE_MESSAGE_RE.match(header):
        return errors

    if len(header) > MAX_HEADER_LEN:
        errors.append(
            f"header is {len(header)} chars, must be <= {MAX_HEADER_LEN}: {header!r}"
        )

    for number, line in enumerate(lines[1:], start=2):
        if len(line) > MAX_LINE_LEN:
            errors.append(
                f"line {number} is {len(line)} chars, must be <= {MAX_LINE_LEN}: "
                f"{line[:40]!r}..."
            )

    match = HEADER_RE.match(header)
    if not match:
        errors.append(
            "header does not match 'type(scope)!: subject' or 'type!: subject' or "
            f"'type: subject': {header!r}"
        )
        return errors

    commit_type = match.group("type")
    if commit_type not in ALLOWED_TYPES:
        errors.append(
            f"type {commit_type!r} is not one of: {', '.join(sorted(ALLOWED_TYPES))}"
        )

    subject = match.group("subject")
    if not subject.strip():
        errors.append("subject is empty")
    elif subject.endswith("."):
        errors.append(f"subject must not end with a period: {subject!r}")

    body = "\n".join(lines[1:])
    has_bang = match.group("bang") is not None
    has_breaking_footer = bool(re.search(r"^BREAKING CHANGE:", body, re.MULTILINE))

    if has_bang and not has_breaking_footer:
        errors.append(
            "header has '!' but body has no 'BREAKING CHANGE:' footer -- "
            "CONTRIBUTING.md requires both"
        )
    if has_breaking_footer and not has_bang:
        errors.append(
            "body has a 'BREAKING CHANGE:' footer but header has no '!' -- "
            "CONTRIBUTING.md requires both"
        )

    return errors


def main(argv: list[str]) -> int:
    """Entry point: read the commit message file named in argv[1] and lint it.

    Args:
        argv: Command-line arguments (argv[1] is the commit message file path).

    Returns:
        Process exit code: 0 if valid, 1 otherwise.
    """
    if len(argv) != 2:
        print("usage: commit_lint.py <commit-message-file>", file=sys.stderr)
        return 2

    with open(argv[1], encoding="utf-8") as f:
        message = f.read()

    errors = lint(message)
    if not errors:
        return 0

    print("Commit message does not follow Conventional Commits:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    print(
        "\nExpected form: type(scope)?: subject   e.g. feat(auth): add token refresh\n"
        "Allowed types: " + ", ".join(sorted(ALLOWED_TYPES)),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
