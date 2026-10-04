#!/usr/bin/env python3
"""Check, preview and assemble changelog fragments.

Stdlib-only, no dependency on the project's own environment (same constraint as
next_version.py and commit_lint.py).

A change that needs a changelog entry adds one fragment file, `changelog.d/<id>.<category>.md`,
holding one or more bullet lines. `<id>` is the task ID (`T-0023`) or the branch topic.
`<category>` is one of the six Keep a Changelog categories, lowercase. Only files with that name
shape are fragments; `changelog.d/README.md` is documentation and is never checked, folded or
deleted. Because each change owns its own file, parallel branches never conflict on
`CHANGELOG.md`, which changes only when a release folds the fragments in.

Subcommands:
  check <base> <tip>
      Look at the non-merge commits in `<base>..<tip>`. Fail when one is `feat`, `fix` or
      breaking (classified by next_version.py's own `classify`) and no commit in the range adds a
      fragment. Also fail on any invalid fragment present at `<tip>`: bad name, unknown
      category, no bullet line, or placeholder text.
  preview [version] [--date YYYY-MM-DD]
      Print the section a release would write. Changes nothing. Without `version`, the next
      version comes from next_version.py.
  assemble <version> [--date YYYY-MM-DD]
      Write `## [X.Y.Z] - date` under `## [Unreleased]` in CHANGELOG.md, with the fragments
      grouped by category in Keep a Changelog order, then delete the folded fragments. Refuses
      when `[Unreleased]` is not empty, so nothing is ever stranded there.

Exit codes: 0 success; 1 the check failed or the command refused to run (the reason is printed to
stderr); 2 usage error or a git failure.

See CONTRIBUTING.md § Versioning and .agents/plans/2026-10-04-changelog-and-versioning.md.
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

FRAGMENT_DIR = "changelog.d"
README_NAME = "README.md"
CHANGELOG_NAME = "CHANGELOG.md"
UNRELEASED_HEADING = "## [Unreleased]"

# Keep a Changelog 1.1.0 order.
CATEGORIES = ("added", "changed", "deprecated", "removed", "fixed", "security")

FRAGMENT_RE = re.compile(
    rf"^(?P<id>[A-Za-z0-9][A-Za-z0-9_-]*)\.(?P<category>{'|'.join(CATEGORIES)})\.md$"
)
# A name shaped like `<id>.<something>.md`, used to tell a bad category from a bad name.
SHAPED_RE = re.compile(r"^(?P<id>[A-Za-z0-9][A-Za-z0-9_-]*)\.(?P<category>[^.]+)\.md$")
BULLET_RE = re.compile(r"^[-*] +\S")
PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO|TBD|FIXME|XXX)\b|(?i:lorem ipsum|describe (?:the|your) change)"
)
VERSION_RE = re.compile(r"^v?(\d+\.\d+\.\d+)$")
# A Keep a Changelog footer link definition such as `[1.0.0]: https://...`.
LINK_DEF_RE = re.compile(r"^\[[^\]]+\]:\s")

RECORD_SEP = "\x1e"
FIELD_SEP = "\x1f"


class ChangelogError(Exception):
    """A failure with a message for the user; `exit_code` is the process exit code."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        """Store the message and the exit code to report it with.

        Args:
            message: Text to print to stderr.
            exit_code: Process exit code; 1 for a failed check or refusal, 2 for a git failure.
        """
        super().__init__(message)
        self.exit_code = exit_code


class Fragment(NamedTuple):
    """A valid changelog fragment.

    Attributes:
        name: File name, e.g. `T-0023.changed.md`.
        category: One of CATEGORIES.
        text: The fragment body with surrounding blank lines and trailing spaces removed.
    """

    name: str
    category: str
    text: str


def _load_next_version() -> ModuleType:
    """Load the sibling next_version.py so commits are classified by the same code.

    Returns:
        The loaded module.

    Raises:
        ImportError: If the file cannot be loaded.
    """
    path = Path(__file__).resolve().with_name("next_version.py")
    spec = importlib.util.spec_from_file_location("next_version", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_NEXT_VERSION = _load_next_version()


def classify(message: str) -> str | None:
    """Classify a commit message exactly as next_version.py does.

    Args:
        message: Full commit message (header and body).

    Returns:
        'breaking', 'feat', 'fix', or None when the commit drives no version bump.
    """
    return _NEXT_VERSION.classify(message)


def git(*args: str, cwd: Path | None = None) -> str:
    """Run a git command and return its stdout.

    Args:
        args: Arguments after `git`.
        cwd: Directory to run in; defaults to the current directory.

    Returns:
        Stdout of the command, unmodified.

    Raises:
        ChangelogError: With exit code 2 if git fails or is missing.
    """
    try:
        result = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=False, cwd=cwd
        )
    except OSError as exc:
        raise ChangelogError(f"cannot run git: {exc}", 2) from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        raise ChangelogError(f"git {' '.join(args)} failed: {detail}", 2)
    return result.stdout


def repo_root() -> Path:
    """Find the top level of the repository containing the current directory.

    Returns:
        The repository root.

    Raises:
        ChangelogError: With exit code 2 outside a git repository.
    """
    return Path(git("rev-parse", "--show-toplevel").strip())


def validate_fragment(name: str, text: str) -> tuple[str | None, list[str]]:
    """Validate one fragment's file name and content.

    Args:
        name: The file name inside `changelog.d/`.
        text: The file content.

    Returns:
        The category (None when the name is invalid) and a list of problems (empty when valid).
    """
    problems: list[str] = []
    match = FRAGMENT_RE.match(name)
    category: str | None = None
    if match:
        category = match.group("category")
    else:
        shaped = SHAPED_RE.match(name)
        if shaped:
            problems.append(
                f"unknown category {shaped.group('category')!r}; "
                f"use one of: {', '.join(CATEGORIES)}"
            )
        else:
            problems.append("name must be `<id>.<category>.md`, e.g. `T-0023.added.md`")

    lines = text.splitlines()
    if not any(BULLET_RE.match(line) for line in lines):
        problems.append("no bullet line (start a line with `- `)")
    placeholder = PLACEHOLDER_RE.search(text)
    if placeholder:
        problems.append(f"placeholder text {placeholder.group(0)!r}")
    return category, problems


def normalize_body(text: str) -> str:
    """Trim a fragment body to its content lines.

    Args:
        text: The raw file content.

    Returns:
        The text with trailing spaces removed and leading and trailing blank lines dropped.
    """
    return "\n".join(line.rstrip() for line in text.strip("\n").splitlines()).strip(
        "\n"
    )


def format_problems(problems: list[tuple[str, list[str]]]) -> str:
    """Render fragment problems for stderr.

    Args:
        problems: (path, problem list) pairs.

    Returns:
        A multi-line message.
    """
    lines = ["invalid changelog fragment(s):"]
    for path, items in problems:
        for item in items:
            lines.append(f"  {path}: {item}")
    return "\n".join(lines)


def read_working_fragments(root: Path) -> list[Fragment]:
    """Read and validate the fragments in the working tree.

    Hidden files and `README.md` are not fragments. Any other file in `changelog.d/` must be a
    valid fragment.

    Args:
        root: Repository root.

    Returns:
        Valid fragments sorted by file name; empty when `changelog.d/` is missing or has none.

    Raises:
        ChangelogError: If any fragment is invalid.
    """
    directory = root / FRAGMENT_DIR
    if not directory.is_dir():
        return []
    fragments: list[Fragment] = []
    problems: list[tuple[str, list[str]]] = []
    for path in sorted(directory.iterdir()):
        if path.name == README_NAME or path.name.startswith("."):
            continue
        relative = f"{FRAGMENT_DIR}/{path.name}"
        if not path.is_file():
            problems.append((relative, ["not a file; fragments are files"]))
            continue
        text = path.read_text(encoding="utf-8")
        category, errors = validate_fragment(path.name, text)
        if errors or category is None:
            problems.append((relative, errors))
        else:
            fragments.append(Fragment(path.name, category, normalize_body(text)))
    if problems:
        raise ChangelogError(format_problems(problems))
    return fragments


def build_section(version: str, date: str, fragments: list[Fragment]) -> str:
    """Build a release section from fragments.

    Args:
        version: Version without a leading `v`, e.g. "1.2.3", or a label such as "Unreleased".
        date: ISO date for the heading.
        fragments: Valid fragments.

    Returns:
        The section text ending in one newline: a heading, then one `###` group per used
        category in Keep a Changelog order, each holding its fragments' bullets by file name.
    """
    parts = [f"## [{version}] - {date}"]
    for category in CATEGORIES:
        bodies = [f.text for f in fragments if f.category == category]
        if bodies:
            parts.append(f"### {category.capitalize()}\n\n" + "\n".join(bodies))
    return "\n\n".join(parts) + "\n"


def split_changelog(text: str) -> tuple[list[str], list[str], list[str]]:
    """Split CHANGELOG.md around the `[Unreleased]` section.

    Args:
        text: The file content.

    Returns:
        (lines up to and including the `[Unreleased]` heading, the lines of that section's
        body, the lines from the next section or footer link onward).

    Raises:
        ChangelogError: If there is no `## [Unreleased]` heading.
    """
    lines = text.splitlines()
    try:
        start = next(
            i for i, line in enumerate(lines) if line.rstrip() == UNRELEASED_HEADING
        )
    except StopIteration:
        raise ChangelogError(
            f"{CHANGELOG_NAME} has no `{UNRELEASED_HEADING}` heading"
        ) from None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## ") or LINK_DEF_RE.match(lines[i]):
            end = i
            break
    return lines[: start + 1], lines[start + 1 : end], lines[end:]


def resolve_date(value: str | None) -> str:
    """Return a validated ISO date, defaulting to today.

    Args:
        value: The `--date` argument, or None.

    Returns:
        The date as `YYYY-MM-DD`.

    Raises:
        ChangelogError: If the value is not a valid ISO date.
    """
    if value is None:
        return datetime.datetime.now().astimezone().date().isoformat()
    try:
        return datetime.date.fromisoformat(value).isoformat()
    except ValueError:
        raise ChangelogError(f"--date {value!r} is not a YYYY-MM-DD date") from None


def resolve_version(value: str) -> str:
    """Normalise a version argument.

    Args:
        value: `X.Y.Z` or `vX.Y.Z`.

    Returns:
        The version without the leading `v`.

    Raises:
        ChangelogError: If the value is not in that form.
    """
    match = VERSION_RE.match(value)
    if not match:
        raise ChangelogError(f"version {value!r} is not in X.Y.Z or vX.Y.Z form")
    return match.group(1)


def assemble(root: Path, version: str, date: str) -> str:
    """Fold the fragments into CHANGELOG.md and delete them.

    Args:
        root: Repository root.
        version: Version without a leading `v`.
        date: ISO date for the heading.

    Returns:
        The section that was written.

    Raises:
        ChangelogError: If CHANGELOG.md is missing or malformed, `[Unreleased]` is not empty,
            the version already has a section, a fragment is invalid, or there are no fragments.
    """
    changelog = root / CHANGELOG_NAME
    if not changelog.is_file():
        raise ChangelogError(f"{CHANGELOG_NAME} not found at {root}")
    text = changelog.read_text(encoding="utf-8")
    head, unreleased, tail = split_changelog(text)
    if any(line.strip() for line in unreleased):
        raise ChangelogError(
            f"`{UNRELEASED_HEADING}` in {CHANGELOG_NAME} is not empty; move its entries into "
            f"changelog.d/ fragments first, so nothing is left behind"
        )
    if re.search(rf"^## \[{re.escape(version)}\]", text, re.MULTILINE):
        raise ChangelogError(f"{CHANGELOG_NAME} already has a section for {version}")
    fragments = read_working_fragments(root)
    if not fragments:
        raise ChangelogError(f"no fragments in {FRAGMENT_DIR}/ to assemble")

    section = build_section(version, date, fragments)
    out = "\n".join(head) + "\n\n" + section
    if tail:
        out += "\n" + "\n".join(tail) + "\n"
    changelog.write_text(out, encoding="utf-8")
    for fragment in fragments:
        (root / FRAGMENT_DIR / fragment.name).unlink()
    return section


def next_version_label(root: Path) -> str:
    """Ask next_version.py for the version the next release would carry.

    Args:
        root: Repository root to run in.

    Returns:
        The version without a leading `v`, or "Unreleased" when nothing is releasable.
    """
    script = Path(__file__).resolve().with_name("next_version.py")
    result = subprocess.run(
        [sys.executable, str(script), "--quiet"],
        capture_output=True,
        text=True,
        check=False,
        cwd=root,
    )
    match = VERSION_RE.match(result.stdout.strip())
    if result.returncode != 0 or not match:
        print(
            "note: next_version.py found no version to release; "
            "pass a version to preview one",
            file=sys.stderr,
        )
        return "Unreleased"
    return match.group(1)


def commits_in_range(base: str, tip: str, root: Path) -> list[tuple[str, str]]:
    """List the non-merge commits in `base..tip`.

    Args:
        base: Exclusive start of the range.
        tip: Inclusive end of the range.
        root: Repository root.

    Returns:
        (hash, full message) pairs, newest first.

    Raises:
        ChangelogError: With exit code 2 if the range cannot be listed.
    """
    log = git(
        "log",
        "--no-merges",
        f"--format=%H{FIELD_SEP}%B{RECORD_SEP}",
        f"{base}..{tip}",
        cwd=root,
    )
    commits: list[tuple[str, str]] = []
    for record in log.split(RECORD_SEP):
        record = record.strip("\n")
        if not record:
            continue
        commit_hash, _, message = record.partition(FIELD_SEP)
        commits.append((commit_hash, message))
    return commits


def fragments_added_in_range(base: str, tip: str, root: Path) -> list[str]:
    """List the fragment paths added by any non-merge commit in `base..tip`.

    A fragment added and deleted again inside the range (for example folded in by a release)
    still counts, because each commit is inspected on its own.

    Args:
        base: Exclusive start of the range.
        tip: Inclusive end of the range.
        root: Repository root.

    Returns:
        Paths of added files named like a fragment.
    """
    out = git(
        "log",
        "--no-merges",
        "--no-renames",
        "--diff-filter=A",
        "--name-only",
        "--format=",
        f"{base}..{tip}",
        "--",
        f"{FRAGMENT_DIR}/",
        cwd=root,
    )
    added = []
    for path in out.splitlines():
        directory, _, name = path.rpartition("/")
        if directory == FRAGMENT_DIR and FRAGMENT_RE.match(name):
            added.append(path)
    return added


def tip_fragment_problems(tip: str, root: Path) -> list[tuple[str, list[str]]]:
    """Validate every fragment present in the tree at `tip`.

    Args:
        tip: The revision to read.
        root: Repository root.

    Returns:
        (path, problem list) pairs for the invalid fragments; empty when all are valid.
    """
    listing = git(
        "ls-tree", "-r", "--name-only", "-z", tip, "--", f"{FRAGMENT_DIR}/", cwd=root
    )
    problems: list[tuple[str, list[str]]] = []
    for path in sorted(p for p in listing.split("\0") if p):
        directory, _, name = path.rpartition("/")
        if directory != FRAGMENT_DIR:
            problems.append(
                (path, ["nested path; fragments sit directly in changelog.d/"])
            )
            continue
        if name == README_NAME or name.startswith("."):
            continue
        text = git("show", f"{tip}:{path}", cwd=root)
        _, errors = validate_fragment(name, text)
        if errors:
            problems.append((path, errors))
    return problems


def run_check(base: str, tip: str) -> int:
    """Run the `check` subcommand.

    Args:
        base: Exclusive start of the range.
        tip: Inclusive end of the range.

    Returns:
        0 when the range passes, 1 when it does not.
    """
    root = repo_root()
    failures: list[str] = []

    driving = [
        (commit_hash, message.split("\n")[0], level)
        for commit_hash, message in commits_in_range(base, tip, root)
        if (level := classify(message)) is not None
    ]
    if driving and not fragments_added_in_range(base, tip, root):
        lines = [
            f"{base}..{tip} has versioned commits but adds no changelog fragment:",
        ]
        lines += [f"  {h[:8]}  {header}  [{level}]" for h, header, level in driving]
        lines.append(
            f"add {FRAGMENT_DIR}/<id>.<category>.md with a bullet line "
            f"(category: {', '.join(CATEGORIES)}); see {FRAGMENT_DIR}/{README_NAME}"
        )
        failures.append("\n".join(lines))

    problems = tip_fragment_problems(tip, root)
    if problems:
        failures.append(format_problems(problems))

    if failures:
        print("\n\n".join(failures), file=sys.stderr)
        return 1
    print(f"changelog check passed for {base}..{tip}")
    return 0


def run_preview(version: str | None, date: str | None) -> int:
    """Run the `preview` subcommand.

    Args:
        version: Version to show, or None to ask next_version.py.
        date: Heading date, or None for today.

    Returns:
        0 on success (including when there are no fragments), 1 when a fragment is invalid.
    """
    root = repo_root()
    fragments = read_working_fragments(root)
    if not fragments:
        print(f"no fragments in {FRAGMENT_DIR}/; nothing to preview", file=sys.stderr)
        return 0
    label = resolve_version(version) if version else next_version_label(root)
    sys.stdout.write(build_section(label, resolve_date(date), fragments))
    return 0


def run_assemble(version: str, date: str | None) -> int:
    """Run the `assemble` subcommand.

    Args:
        version: Version to write.
        date: Heading date, or None for today.

    Returns:
        0 on success.
    """
    root = repo_root()
    resolved = resolve_version(version)
    section = assemble(root, resolved, resolve_date(date))
    count = section.count("\n- ") + section.count("\n* ")
    print(
        f"assembled {resolved} into {CHANGELOG_NAME} ({count} bullet(s)); fragments deleted"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        The parser with the `check`, `preview` and `assemble` subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="changelog.py",
        description="Check, preview and assemble changelog fragments.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser(
        "check", help="verify versioned commits in a range add a fragment"
    )
    check.add_argument("base", help="exclusive start of the range")
    check.add_argument("tip", help="inclusive end of the range")

    preview = sub.add_parser("preview", help="print the section a release would write")
    preview.add_argument(
        "version", nargs="?", help="X.Y.Z; default: from next_version.py"
    )
    preview.add_argument("--date", help="heading date, YYYY-MM-DD; default: today")

    assemble_cmd = sub.add_parser(
        "assemble", help="fold the fragments into CHANGELOG.md and delete them"
    )
    assemble_cmd.add_argument("version", help="X.Y.Z or vX.Y.Z")
    assemble_cmd.add_argument("--date", help="heading date, YYYY-MM-DD; default: today")
    return parser


def main(argv: list[str]) -> int:
    """Entry point.

    Args:
        argv: Command-line arguments after the program name.

    Returns:
        Process exit code: 0 success, 1 failed check or refusal, 2 usage or git error.
    """
    args = build_parser().parse_args(argv)
    try:
        if args.command == "check":
            return run_check(args.base, args.tip)
        if args.command == "preview":
            return run_preview(args.version, args.date)
        return run_assemble(args.version, args.date)
    except ChangelogError as exc:
        print(f"changelog.py: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
