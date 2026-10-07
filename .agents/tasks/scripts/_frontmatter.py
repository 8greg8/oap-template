"""Strict parser and serializer for the ``---`` frontmatter used by task files.

The supported syntax is deliberately a small subset of YAML so that the agent
tooling stays dependency-free (no PyYAML). Exactly two value shapes are legal:

- scalars: ``key: some value``
- inline lists: ``key: [a, b, c]`` (``[]`` for empty)

Anything else -- nested mappings, block lists, anchors, multi-line scalars --
raises :class:`FrontmatterError` rather than being silently misread.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

DELIMITER = "---"

_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(?:[ \t](.*))?$")


class FrontmatterError(ValueError):
    """Raised when a document's frontmatter is missing or outside the subset."""


def _parse_value(raw: str, key: str, lineno: int) -> Any:
    """Convert a single raw frontmatter value into a string or list of strings.

    Args:
        raw: The text following ``key:`` on the line, already stripped.
        key: The key being parsed, used for error messages.
        lineno: 1-based line number within the file, used for error messages.

    Returns:
        The value as a ``str``, or as a ``list[str]`` for inline-list syntax.

    Raises:
        FrontmatterError: If the value uses syntax outside the supported subset.
    """
    if raw.startswith("["):
        if not raw.endswith("]"):
            raise FrontmatterError(
                f"line {lineno}: unterminated inline list for key '{key}'"
            )
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [item.strip() for item in inner.split(",") if item.strip()]

    if raw.startswith(("{", "&", "*", "|", ">")):
        raise FrontmatterError(
            f"line {lineno}: unsupported YAML syntax for key '{key}'; "
            "only scalars and inline lists are allowed"
        )

    # Strip a single layer of matching quotes, if present.
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Split a document into its frontmatter mapping and its body.

    Args:
        text: Full file contents, expected to open with a ``---`` line.

    Returns:
        A ``(metadata, body)`` tuple. ``body`` retains its original formatting
        with no leading blank line.

    Raises:
        FrontmatterError: If the frontmatter block is missing, unterminated, or
            contains unsupported syntax.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != DELIMITER:
        raise FrontmatterError("document does not start with a '---' frontmatter block")

    try:
        end = next(
            i for i, line in enumerate(lines[1:], start=1) if line.strip() == DELIMITER
        )
    except StopIteration:
        raise FrontmatterError("frontmatter block is never closed with '---'") from None

    metadata: dict[str, Any] = {}
    for offset, line in enumerate(lines[1:end], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t":
            raise FrontmatterError(
                f"line {offset}: indented frontmatter is not supported"
            )
        match = _KEY_RE.match(line)
        if not match:
            raise FrontmatterError(
                f"line {offset}: expected 'key: value', got {line!r}"
            )
        key, raw = match.group(1), (match.group(2) or "").strip()
        if key in metadata:
            raise FrontmatterError(f"line {offset}: duplicate key '{key}'")
        metadata[key] = _parse_value(raw, key, offset)

    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return metadata, body


def serialize(metadata: dict[str, Any], body: str) -> str:
    """Render a metadata mapping and body back into a frontmatter document.

    Args:
        metadata: Mapping of scalar or list-of-scalar values. Insertion order is
            preserved in the output.
        body: Document body to place after the closing delimiter.

    Returns:
        The complete document text, ending with a single trailing newline.
    """
    lines = [DELIMITER]
    for key, value in metadata.items():
        if isinstance(value, (list, tuple)):
            lines.append(f"{key}: [{', '.join(str(item) for item in value)}]")
        else:
            lines.append(f"{key}: {value}")
    lines.append(DELIMITER)
    return "\n".join(lines) + "\n\n" + body.strip("\n") + "\n"


def read(path: Path) -> tuple[dict[str, Any], str]:
    """Parse the frontmatter document at ``path``.

    Args:
        path: File to read.

    Returns:
        A ``(metadata, body)`` tuple.

    Raises:
        FrontmatterError: If the file's frontmatter is invalid. The message is
            prefixed with the file path.
    """
    try:
        return parse(path.read_text(encoding="utf-8"))
    except FrontmatterError as exc:
        raise FrontmatterError(f"{path}: {exc}") from None


def write(path: Path, metadata: dict[str, Any], body: str) -> None:
    """Serialize and write a frontmatter document to ``path``.

    Args:
        path: Destination file; parent directories are created as needed.
        metadata: Frontmatter mapping.
        body: Document body.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize(metadata, body), encoding="utf-8")
