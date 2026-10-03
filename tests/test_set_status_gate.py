"""Tests for the report gate on ``task.py set-status``.

Per the task spec, ``set-status`` to ``review``, ``blocked``, ``done`` or
``abandoned`` must refuse unless ``.agents/tasks/reports/<ID>.md`` exists and
passes ``report.py validate``; ``open`` and ``in_progress`` are unaffected by
report state. Each test runs the real script as a subprocess against an isolated
copy of the task tooling under ``tmp_path``, so the project's own tasks and
reports are never read or written.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".agents" / "tasks" / "scripts"
TEMPLATES_DIR = REPO_ROOT / ".agents" / "tasks" / "templates"

GATED_STATUSES = ["review", "blocked", "done", "abandoned"]
UNGATED_STATUSES = ["open", "in_progress"]

TASK_ID = "T-0001"

_FILLED_REPORT = """\
---
task: T-0001
outcome: success
branch: chore/T-0001-example
commit: abc1234
tags: [workflow]
---

# Report — T-0001: Example

## Summary

The change was made and the acceptance criteria are met.

## What was done

Edited one file.

## Files changed

example.py: the change.

## Tests run

uv run pytest tests :: 1 passed

Independent verify agent (fresh context) :: pending

## Documentation impact

none needed.

## Safety confirmations

- [x] Branch pushed; nothing merged.

## Known limitations

None.

## Follow-up recommended

None.

## Lessons learned

None specific.
"""

_PLACEHOLDER_REPORT = _FILLED_REPORT.replace(
    "None specific.", "TODO: write the lesson."
)


@pytest.fixture
def tooling(tmp_path: Path) -> Path:
    """An isolated copy of ``.agents/tasks`` holding one task, T-0001, ``open``."""
    tasks_dir = tmp_path / ".agents" / "tasks"
    shutil.copytree(
        SCRIPTS_DIR,
        tasks_dir / "scripts",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    shutil.copytree(TEMPLATES_DIR, tasks_dir / "templates")
    _task(tmp_path, "new", "-t", "Example", "-T", "chore", "--no-publish")
    return tmp_path


def _task(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    script = root / ".agents" / "tasks" / "scripts" / "task.py"
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=root,
    )


def _task_file(root: Path) -> Path:
    (path,) = (root / ".agents" / "tasks").glob(f"{TASK_ID}-*.md")
    return path


def _status(root: Path) -> str:
    for line in _task_file(root).read_text(encoding="utf-8").splitlines():
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError("no status line in task file")


def _write_report(root: Path, text: str) -> None:
    path = root / ".agents" / "tasks" / "reports" / f"{TASK_ID}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.mark.parametrize("status", GATED_STATUSES)
def test_gated_status_without_report_is_refused(tooling, status):
    result = _task(tooling, "set-status", TASK_ID, status)

    assert result.returncode != 0
    assert "no report" in result.stderr
    assert f"report.py new {TASK_ID}" in result.stderr
    assert _status(tooling) == "open"


@pytest.mark.parametrize("status", GATED_STATUSES)
def test_gated_status_with_placeholder_report_is_refused(tooling, status):
    _write_report(tooling, _PLACEHOLDER_REPORT)

    result = _task(tooling, "set-status", TASK_ID, status)

    assert result.returncode != 0
    assert "## Lessons learned" in result.stderr
    assert "placeholder" in result.stderr
    assert _status(tooling) == "open"


@pytest.mark.parametrize("status", GATED_STATUSES)
def test_gated_status_with_filled_report_succeeds(tooling, status):
    _write_report(tooling, _FILLED_REPORT)

    result = _task(tooling, "set-status", TASK_ID, status)

    assert result.returncode == 0, result.stderr
    assert _status(tooling) == status


def test_report_skeleton_from_report_py_new_is_refused(tooling):
    """A freshly generated, unfilled skeleton must not satisfy the gate."""
    script = tooling / ".agents" / "tasks" / "scripts" / "report.py"
    created = subprocess.run(
        [sys.executable, str(script), "new", TASK_ID],
        capture_output=True,
        text=True,
        check=False,
        cwd=tooling,
    )
    assert created.returncode == 0, created.stderr

    result = _task(tooling, "set-status", TASK_ID, "review")

    assert result.returncode != 0
    assert "placeholder" in result.stderr
    assert _status(tooling) == "open"


@pytest.mark.parametrize("status", UNGATED_STATUSES)
def test_ungated_status_ignores_missing_report(tooling, status):
    _task(tooling, "set-status", TASK_ID, "in_progress")

    result = _task(tooling, "set-status", TASK_ID, status)

    assert result.returncode == 0, result.stderr
    assert _status(tooling) == status


@pytest.mark.parametrize("status", UNGATED_STATUSES)
def test_ungated_status_ignores_placeholder_report(tooling, status):
    _write_report(tooling, _PLACEHOLDER_REPORT)

    result = _task(tooling, "set-status", TASK_ID, status)

    assert result.returncode == 0, result.stderr
    assert _status(tooling) == status
