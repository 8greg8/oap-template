"""Lock-safe allocation of sequential task identifiers.

Task creation may happen from several sessions or worktrees at once, so the
counter is guarded by an exclusively-created lock file. The allocator is also
self-healing: it takes the maximum of the stored counter and the highest ID
actually present on disk, so a lost or merge-clobbered ``.counter`` can never
cause a duplicate ID.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path

from _schema import COUNTER_FILE, ID_RE, LOCK_FILE, TASK_GLOB, TASKS_DIR

logger = logging.getLogger(__name__)

#: Matches the ``T-NNNN`` prefix of a task filename.
_FILENAME_ID_RE = re.compile(r"^T-(\d{4,})(?:-|\.md$)")

#: A lock older than this is assumed to belong to a crashed process.
STALE_LOCK_SECONDS = 30.0

#: How long to keep retrying before giving up on a contended lock.
ACQUIRE_TIMEOUT_SECONDS = 20.0

ID_WIDTH = 4


class LockTimeout(RuntimeError):
    """Raised when the counter lock cannot be acquired within the timeout."""


def format_id(number: int) -> str:
    """Render an integer as a task ID.

    Args:
        number: Positive counter value.

    Returns:
        The zero-padded identifier, e.g. ``T-0004``.
    """
    return f"T-{number:0{ID_WIDTH}d}"


def parse_id(task_id: str) -> int | None:
    """Extract the numeric part of a task ID.

    Args:
        task_id: Identifier such as ``T-0004``.

    Returns:
        The integer value, or ``None`` when the string is not a task ID.
    """
    match = ID_RE.match(task_id.strip().upper())
    return int(match.group(1)) if match else None


def highest_existing_id(tasks_dir: Path = TASKS_DIR) -> int:
    """Scan task filenames for the highest ID currently on disk.

    Args:
        tasks_dir: Directory holding the task files.

    Returns:
        The highest ID found, or ``0`` when there are no tasks.
    """
    highest = 0
    for path in tasks_dir.glob(TASK_GLOB):
        match = _FILENAME_ID_RE.match(path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest


def _acquire(lock_file: Path, timeout: float) -> int:
    """Acquire the counter lock, breaking it if it is stale.

    Args:
        lock_file: Path of the lock file to create exclusively.
        timeout: Seconds to keep retrying before raising.

    Returns:
        An open file descriptor for the lock file.

    Raises:
        LockTimeout: If the lock is still held when the timeout expires.
    """
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    delay = 0.01
    while True:
        try:
            return os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            try:
                age = time.time() - lock_file.stat().st_mtime
            except FileNotFoundError:
                continue  # Released between our attempt and the stat; retry now.
            if age > STALE_LOCK_SECONDS:
                logger.warning("breaking stale task-id lock (%.0fs old)", age)
                lock_file.unlink(missing_ok=True)
                continue
            if time.monotonic() >= deadline:
                raise LockTimeout(
                    f"could not acquire {lock_file} within {timeout:.0f}s"
                ) from None
            time.sleep(delay)
            delay = min(delay * 2, 0.2)


def allocate_id(
    tasks_dir: Path | None = None,
    counter_file: Path | None = None,
    lock_file: Path | None = None,
    timeout: float = ACQUIRE_TIMEOUT_SECONDS,
) -> str:
    """Reserve and return the next unused task identifier.

    The counter file is updated under an exclusive lock, and reconciled against
    the task files actually present so that a stale counter cannot hand out an
    ID that is already taken.

    Args:
        tasks_dir: Directory holding the task files. Defaults to this
            module's ``TASKS_DIR``, resolved at call time (not import time),
            so tests can point it elsewhere via ``monkeypatch.setattr``.
        counter_file: File storing the last allocated number. Same
            call-time-default behavior as ``tasks_dir``.
        lock_file: Lock guarding the counter. Same call-time-default
            behavior as ``tasks_dir``.
        timeout: Seconds to wait for the lock.

    Returns:
        The newly allocated identifier, e.g. ``T-0009``.

    Raises:
        LockTimeout: If the lock cannot be acquired in time.
    """
    if tasks_dir is None:
        tasks_dir = TASKS_DIR
    if counter_file is None:
        counter_file = COUNTER_FILE
    if lock_file is None:
        lock_file = LOCK_FILE

    fd = _acquire(lock_file, timeout)
    try:
        stored = 0
        if counter_file.exists():
            text = counter_file.read_text(encoding="utf-8").strip()
            if text.isdigit():
                stored = int(text)
            else:
                logger.warning(
                    "counter file %s is unreadable; rebuilding", counter_file
                )

        next_number = max(stored, highest_existing_id(tasks_dir)) + 1

        # Write via a temporary file so a crash mid-write cannot truncate the
        # counter to an empty string.
        temp = counter_file.with_suffix(".tmp")
        temp.write_text(f"{next_number}\n", encoding="utf-8")
        os.replace(temp, counter_file)
        return format_id(next_number)
    finally:
        os.close(fd)
        lock_file.unlink(missing_ok=True)
