#!/usr/bin/env python3
"""Shared paths, vocabulary, and validation rules for the agent task workflow.

This module is the single source of truth for what a well-formed task or report
looks like. ``task.py``, ``backlog.py`` and ``report.py`` all defer to it so the
three CLIs cannot drift apart.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from _frontmatter import FrontmatterError, read

# --- Locations ---------------------------------------------------------------

TASKS_DIR = Path(__file__).resolve().parent.parent
AGENTS_DIR = TASKS_DIR.parent
REPO_ROOT = AGENTS_DIR.parent

REPORTS_DIR = TASKS_DIR / "reports"
TEMPLATES_DIR = TASKS_DIR / "templates"
TASK_TEMPLATE = TEMPLATES_DIR / "task.md"
REPORT_TEMPLATE = TEMPLATES_DIR / "report.md"
BACKLOG_FILE = TASKS_DIR / "BACKLOG.md"
LESSONS_FILE = AGENTS_DIR / "LESSONS.md"
COUNTER_FILE = TASKS_DIR / ".counter"
LOCK_FILE = TASKS_DIR / ".counter.lock"

TASK_GLOB = "T-*.md"
ID_RE = re.compile(r"^T-(\d{4,})$")

# --- Vocabulary --------------------------------------------------------------

#: Task lifecycle states. ``blocked`` and ``abandoned`` are terminal-ish states
#: that still require a report explaining why.
STATUSES: Sequence[str] = (
    "open",
    "in_progress",
    "blocked",
    "review",
    "done",
    "abandoned",
)

#: Statuses that count as "finished successfully" when resolving dependencies.
DONE_STATUSES = frozenset({"done"})

#: Statuses that mean a task must not be dispatched again.
INACTIVE_STATUSES = frozenset({"in_progress", "review", "done", "abandoned"})

#: Conventional Commits types; a task's type drives its git branch prefix.
TYPES: Sequence[str] = (
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
)

PRIORITIES: Sequence[str] = ("high", "medium", "low")

OUTCOMES: Sequence[str] = ("success", "partial", "blocked", "failed")

#: Frontmatter keys every task file must carry.
REQUIRED_TASK_KEYS: Sequence[str] = (
    "id",
    "title",
    "status",
    "type",
    "priority",
    "depends_on",
    "touches",
    "created",
    "report",
)

#: Section headings every task file must carry, in order.
REQUIRED_TASK_SECTIONS: Sequence[str] = (
    "Goal",
    "Context",
    "Scope",
    "Non-goals",
    "Files to inspect",
    "Required behavior",
    "Tests required",
    "Documentation required",
    "Acceptance criteria",
    "Workflow",
    "Report",
)

#: Sections that must contain real content, not just the template placeholder.
NON_EMPTY_TASK_SECTIONS: Sequence[str] = (
    "Goal",
    "Scope",
    "Non-goals",
    "Acceptance criteria",
)

REQUIRED_REPORT_KEYS: Sequence[str] = ("task", "outcome", "branch", "commit", "tags")

REQUIRED_REPORT_SECTIONS: Sequence[str] = (
    "Summary",
    "What was done",
    "Files changed",
    "Tests run",
    "Documentation impact",
    "Safety confirmations",
    "Known limitations",
    "Follow-up recommended",
    "Lessons learned",
)

PLACEHOLDER = "TODO"

_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


class ValidationError(ValueError):
    """Raised when a task or report violates the schema."""


@dataclass
class Task:
    """A parsed task work order.

    Attributes:
        path: Location of the task file on disk.
        meta: Parsed frontmatter mapping.
        body: Markdown body following the frontmatter.
    """

    path: Path
    meta: dict[str, Any]
    body: str

    @property
    def id(self) -> str:
        """The task identifier, e.g. ``T-0004``."""
        return str(self.meta.get("id", ""))

    @property
    def title(self) -> str:
        """The one-line task title."""
        return str(self.meta.get("title", ""))

    @property
    def status(self) -> str:
        """Current lifecycle status."""
        return str(self.meta.get("status", ""))

    @property
    def type(self) -> str:
        """Conventional Commits type, used as the branch prefix."""
        return str(self.meta.get("type", ""))

    @property
    def priority(self) -> str:
        """Priority bucket."""
        return str(self.meta.get("priority", ""))

    @property
    def depends_on(self) -> list[str]:
        """IDs of tasks that must reach ``done`` before this one may start."""
        return _as_list(self.meta.get("depends_on"))

    @property
    def touches(self) -> list[str]:
        """Repo-relative paths or prefixes this task is expected to modify."""
        return _as_list(self.meta.get("touches"))

    @property
    def branch(self) -> str:
        """The git branch name a subagent should create for this task."""
        return f"{self.type}/{self.id}-{slugify(self.title)}"

    @property
    def report_path(self) -> Path:
        """Absolute path to this task's report file."""
        return REPORTS_DIR / f"{self.id}.md"

    def sections(self) -> list[str]:
        """Return the ``##`` headings present in the body, in order."""
        return _SECTION_RE.findall(self.body)

    def section_text(self, heading: str) -> str:
        """Return the body text under a given ``##`` heading.

        Args:
            heading: Heading text to look for. Matching is prefix-based and
                case-insensitive, so ``"Context"`` matches
                ``"Context / current verified state"``.

        Returns:
            The section's text with surrounding whitespace stripped, or an empty
            string when the heading is absent.
        """
        wanted = heading.lower()
        matches = list(_SECTION_RE.finditer(self.body))
        for index, match in enumerate(matches):
            if match.group(1).lower().startswith(wanted):
                end = (
                    matches[index + 1].start()
                    if index + 1 < len(matches)
                    else len(self.body)
                )
                return self.body[match.end() : end].strip()
        return ""


def _as_list(value: Any) -> list[str]:
    """Coerce a frontmatter value into a list of strings.

    Args:
        value: A list, a scalar, or ``None``.

    Returns:
        A list of non-empty strings.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def slugify(text: str, max_length: int = 48) -> str:
    """Convert a title into a lowercase hyphenated slug for filenames.

    Args:
        text: Arbitrary title text.
        max_length: Maximum slug length; the result is trimmed at a hyphen
            boundary where possible.

    Returns:
        A slug containing only ``[a-z0-9-]``, never empty.
    """
    slug = _SLUG_STRIP_RE.sub("-", text.lower()).strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rsplit("-", 1)[0] or slug[:max_length]
    return slug.strip("-") or "task"


def task_files() -> list[Path]:
    """Return every task file in the tasks directory, sorted by ID.

    Returns:
        Sorted list of paths matching ``T-*.md``.
    """
    return sorted(TASKS_DIR.glob(TASK_GLOB))


def load_task(path: Path) -> Task:
    """Load and parse a single task file.

    Args:
        path: Task file to read.

    Returns:
        The parsed :class:`Task`.

    Raises:
        FrontmatterError: If the frontmatter cannot be parsed.
    """
    meta, body = read(path)
    return Task(path=path, meta=meta, body=body)


def load_tasks() -> list[Task]:
    """Load every task in the tasks directory.

    Returns:
        Tasks sorted by ID.

    Raises:
        FrontmatterError: If any task file has unparseable frontmatter.
    """
    return [load_task(path) for path in task_files()]


def find_task(task_id: str, tasks: Iterable[Task] | None = None) -> Task:
    """Look up one task by ID.

    Args:
        task_id: Identifier such as ``T-0004``. Case-insensitive.
        tasks: Optional pre-loaded task list, to avoid re-reading the directory.

    Returns:
        The matching :class:`Task`.

    Raises:
        ValidationError: If no task with that ID exists.
    """
    wanted = task_id.strip().upper()
    for task in tasks if tasks is not None else load_tasks():
        if task.id.upper() == wanted:
            return task
    raise ValidationError(f"no task with id {task_id!r}")


def paths_overlap(left: str, right: str) -> bool:
    """Report whether two ``touches`` entries could refer to the same files.

    Comparison is prefix-based on path segments, so ``src/pkg`` overlaps
    ``src/pkg/mod.py`` but not ``src/pkgtools``.

    Args:
        left: First repo-relative path or directory prefix.
        right: Second repo-relative path or directory prefix.

    Returns:
        ``True`` when the two entries intersect.
    """
    a = left.strip().strip("/").split("/")
    b = right.strip().strip("/").split("/")
    return a[: len(b)] == b or b[: len(a)] == a


def tasks_conflict(left: Task, right: Task) -> bool:
    """Report whether two tasks declare overlapping file scopes.

    A task with an empty ``touches`` list is treated as touching everything, so
    it conflicts with every other task.

    Args:
        left: First task.
        right: Second task.

    Returns:
        ``True`` when the two tasks must not run in parallel.
    """
    if not left.touches or not right.touches:
        return True
    return any(paths_overlap(a, b) for a in left.touches for b in right.touches)


def validate_task(task: Task, known_ids: Iterable[str] | None = None) -> list[str]:
    """Check one task against the schema.

    Args:
        task: The task to check.
        known_ids: All task IDs in the backlog, used to resolve ``depends_on``.
            When ``None``, dependency targets are not checked.

    Returns:
        A list of human-readable problems; empty means the task is valid.
    """
    problems: list[str] = []

    for key in REQUIRED_TASK_KEYS:
        if key not in task.meta:
            problems.append(f"missing frontmatter key '{key}'")

    if not ID_RE.match(task.id):
        problems.append(f"id {task.id!r} does not match T-NNNN")
    elif task.path.name != f"{task.id}-{slugify(task.title)}.md":
        problems.append(
            f"filename {task.path.name!r} does not match id and title "
            f"(expected {task.id}-{slugify(task.title)}.md)"
        )

    if task.status not in STATUSES:
        problems.append(f"status {task.status!r} not in {list(STATUSES)}")
    if task.type not in TYPES:
        problems.append(f"type {task.type!r} not in {list(TYPES)}")
    if task.priority not in PRIORITIES:
        problems.append(f"priority {task.priority!r} not in {list(PRIORITIES)}")
    if not task.title.strip():
        problems.append("title is empty")

    headings = [heading.lower() for heading in task.sections()]
    for required in REQUIRED_TASK_SECTIONS:
        if not any(heading.startswith(required.lower()) for heading in headings):
            problems.append(f"missing required section '## {required}'")

    for required in NON_EMPTY_TASK_SECTIONS:
        text = task.section_text(required)
        if not text or PLACEHOLDER in text:
            problems.append(f"section '## {required}' is empty or still a placeholder")

    if known_ids is not None:
        known = {item.upper() for item in known_ids}
        for dependency in task.depends_on:
            if dependency.upper() not in known:
                problems.append(f"depends_on references unknown task {dependency!r}")
            if dependency.upper() == task.id.upper():
                problems.append("task depends on itself")

    return problems


# --- Section-citation checking ------------------------------------------------

#: Matches ``<path>.md § <Section Name>``, tracking whether the path was wrapped
#: in a single backtick that is (or isn't) closed before the ``§``. That distinction
#: is what separates a real citation from an inline-code example of one.
_CITATION_RE = re.compile(r"(`?)([A-Za-z0-9_][A-Za-z0-9_./-]*\.md)(`?)\s+§\s+")

#: A Markdown ATX heading, any level, e.g. ``## Validation rules a config must satisfy``.
_HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)

_WORD_RE = re.compile(r"[A-Za-z0-9]+")

#: How much text after a ``§`` is considered when looking for the cited section's
#: name. Generous relative to the longest heading in the docs (~10 words) --
#: the word-by-word matching in :func:`_matched_word_count` stops on its own at
#: the first word that no longer continues any real heading, so this is a safety
#: cap against scanning arbitrarily far into unrelated prose, not the mechanism
#: that finds the citation's real boundary.
_CITATION_TAIL_CHARS = 600


@dataclass(frozen=True)
class Citation:
    """A ``<path> § <Section Name>`` reference found in a task file's body.

    Attributes:
        path: Repo-relative Markdown file path as written in the citation.
        snippet: The raw text immediately following ``§``, for error messages --
            not necessarily just the section name, since prose runs on with no
            delimiter (see :func:`_matched_word_count`).
    """

    path: str
    snippet: str


def _words(text: str) -> tuple[str, ...]:
    """Tokenize text into lowercase alphanumeric words, punctuation dropped.

    Args:
        text: Arbitrary heading or citation text.

    Returns:
        Word tokens in order.
    """
    return tuple(match.group(0).lower() for match in _WORD_RE.finditer(text))


def _matched_word_count(
    cited_words: Sequence[str], headings: Sequence[Sequence[str]]
) -> int:
    """Find how many leading words of a citation name a real heading's start.

    Task citations sit in free-form sentences with no reliable delimiter
    between the section name and whatever prose follows it -- sometimes a
    comma or period, sometimes nothing at all (``...§ Metric is ambiguous...``
    is task prose running straight on from the citation, not two heading
    words). Rather than guess a punctuation boundary, this walks the cited
    words one at a time, keeping only the headings still consistent with
    everything matched so far, and stops the moment none are -- which is
    exactly the point past which the citation could no longer be naming that
    heading, however much further the sentence runs on.

    Args:
        cited_words: Word tokens captured after a ``§`` marker.
        headings: Word-tokenized headings from the cited file.

    Returns:
        The number of leading words that matched some heading's own leading
        words, ``0`` if the very first word matches no heading at all.
    """
    candidates = [heading for heading in headings if heading]
    matched = 0
    for word in cited_words:
        next_candidates = [
            h for h in candidates if len(h) > matched and h[matched] == word
        ]
        if not next_candidates:
            break
        candidates = next_candidates
        matched += 1
    return matched


def _citation_matches_heading(
    cited_words: Sequence[str], headings: Sequence[Sequence[str]]
) -> bool:
    """Report whether a citation's words name the start of a real heading.

    A single matched word is accepted only when it uniquely identifies one
    heading (its first word matches no other heading in the file) -- a lone
    common word like "The" matching by coincidence is not enough evidence,
    but a distinctive one-word citation such as ``§ Metric`` or
    ``§ Commands`` is.

    Args:
        cited_words: Word tokens captured after a ``§`` marker.
        headings: Word-tokenized headings from the cited file.

    Returns:
        ``True`` when the citation names the start of some heading.
    """
    matched = _matched_word_count(cited_words, headings)
    if matched >= 2:
        return True
    if matched == 1:
        first_words = [h[0] for h in headings if h]
        return first_words.count(cited_words[0]) == 1
    return False


def _citation_tail(body: str, start: int) -> str:
    """Pull the raw text following a ``§`` marker, bounded for safety.

    Stops at the first paragraph break (a blank line), since a citation and
    whatever names it never span one, and otherwise at
    :data:`_CITATION_TAIL_CHARS`.

    Args:
        body: The task body being scanned.
        start: Index into ``body`` immediately after ``"§ "``.

    Returns:
        The raw tail text, unprocessed.
    """
    window = body[start : start + _CITATION_TAIL_CHARS]
    blank = re.search(r"\n[ \t]*\n", window)
    if blank:
        window = window[: blank.start()]
    return window


def find_citations(body: str) -> list[Citation]:
    """Find every real ``<path> § <Section Name>`` citation in task body text.

    Ignores:
      * a bare ``§`` not immediately preceded by whitespace and a ``<path>.md``
        token (prose merely containing the character, or a second ``§`` in a
        list that shares an earlier citation's path);
      * a citation whose ``path § Section Name`` sits entirely inside one
        inline single-backtick code span, e.g. `` `docs/architecture.md § Foo` ``
        -- that is an example quoted to describe the syntax (as this very task
        file's own § Scope and § Required behavior do), not a real citation.

    Args:
        body: A task file's Markdown body.

    Returns:
        Every real citation found, in document order.
    """
    citations = []
    for match in _CITATION_RE.finditer(body):
        opened, path, closed = match.group(1), match.group(2), match.group(3)
        if opened == "`" and not closed:
            continue  # the whole "path § section" is one code span: an example
        snippet = _citation_tail(body, match.end()).strip()
        if snippet:
            citations.append(Citation(path=path, snippet=snippet))
    return citations


@cache
def _heading_words_in_file(path: str) -> tuple[tuple[str, ...], ...]:
    """Extract every ATX heading from a file as word tokens, cached.

    Args:
        path: Absolute path to a Markdown file, as a string (cache key).

    Returns:
        One word-token tuple per heading, in document order; empty if the
        file can't be read.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return ()
    return tuple(_words(heading) for heading in _HEADING_RE.findall(text))


def validate_citations(task: Task) -> list[str]:
    """Check that every ``<path> § <Section Name>`` citation in a task resolves.

    Args:
        task: The task whose body to scan.

    Returns:
        Human-readable problems, one per broken citation; empty means every
        citation in the body named a real file and a real (or real-prefixed)
        heading in it.
    """
    problems: list[str] = []
    for citation in find_citations(task.body):
        target = REPO_ROOT / citation.path
        if not target.is_file():
            problems.append(f"citation to nonexistent file {citation.path!r}")
            continue
        headings = _heading_words_in_file(str(target))
        cited_words = _words(citation.snippet)
        if not cited_words or not _citation_matches_heading(cited_words, headings):
            shown = citation.snippet.splitlines()[0][:80]
            problems.append(
                f"citation {citation.path} § {shown!r} matches no heading in {citation.path}"
            )
    return problems


def detect_cycles(tasks: Sequence[Task]) -> list[list[str]]:
    """Find dependency cycles across the backlog.

    Args:
        tasks: All tasks to consider.

    Returns:
        A list of cycles, each given as the sequence of task IDs involved.
    """
    graph = {task.id.upper(): [d.upper() for d in task.depends_on] for task in tasks}
    cycles: list[list[str]] = []
    #: 0 = unvisited, 1 = on the current path, 2 = fully explored.
    state: dict[str, int] = {}

    def walk(node: str, path: list[str]) -> None:
        state[node] = 1
        for neighbour in graph.get(node, []):
            if neighbour not in graph:
                continue
            if state.get(neighbour, 0) == 1:
                cycle = path[path.index(neighbour) :] + [neighbour]
                if cycle not in cycles:
                    cycles.append(cycle)
            elif state.get(neighbour, 0) == 0:
                walk(neighbour, path + [neighbour])
        state[node] = 2

    for node in graph:
        if state.get(node, 0) == 0:
            walk(node, [node])
    return cycles


@dataclass
class Report:
    """A parsed executor report.

    Attributes:
        path: Location of the report file.
        meta: Parsed frontmatter mapping.
        body: Markdown body following the frontmatter.
    """

    path: Path
    meta: dict[str, Any] = field(default_factory=dict)
    body: str = ""

    @property
    def task_id(self) -> str:
        """ID of the task this report belongs to."""
        return str(self.meta.get("task", ""))

    @property
    def outcome(self) -> str:
        """Reported outcome of the task."""
        return str(self.meta.get("outcome", ""))

    @property
    def tags(self) -> list[str]:
        """Topic tags used to group harvested lessons."""
        return _as_list(self.meta.get("tags"))

    def section_text(self, heading: str) -> str:
        """Return the body text under a given ``##`` heading.

        Args:
            heading: Heading text; matching is prefix-based, case-insensitive.

        Returns:
            The section's stripped text, or an empty string when absent.
        """
        return Task(self.path, self.meta, self.body).section_text(heading)


def load_reports() -> list[Report]:
    """Load every report in the reports directory.

    Returns:
        Reports sorted by filename. Files with invalid frontmatter are skipped.
    """
    if not REPORTS_DIR.is_dir():
        return []
    reports: list[Report] = []
    for path in sorted(REPORTS_DIR.glob("T-*.md")):
        try:
            meta, body = read(path)
        except FrontmatterError:
            continue
        reports.append(Report(path=path, meta=meta, body=body))
    return reports
