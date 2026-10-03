"""Tests for the report gate on ``task.py set-status``.

Per the task spec, ``set-status`` to ``review``, ``blocked``, ``done`` or
``abandoned`` must refuse unless ``.agents/tasks/reports/<ID>.md`` exists and
passes ``report.py validate``; ``open`` and ``in_progress`` are unaffected by
report state. The report is looked up in the working tree first; if absent, on
the task's branch (a local or ``origin/`` branch matching ``*/<ID>-*``) via git.
A move to ``done`` applies the done-only rules (verify line) as ``validate``
would to a done task. Each test runs the real script as a subprocess against an
isolated copy of the task tooling under ``tmp_path``, so the project's own tasks
and reports are never read or written.
"""

from __future__ import annotations

import os
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

_VERIFY_PENDING = "Independent verify agent (fresh context) :: pending"
_VERIFY_PASSED = (
    "Independent verify agent (fresh context) :: passed (commit abc1234; 1 passed)"
)
_VERIFIED_REPORT = _FILLED_REPORT.replace(_VERIFY_PENDING, _VERIFY_PASSED)

BRANCH = "chore/T-0001-example"


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
    # ``done`` also needs a passed verify line; see the done tests below.
    _write_report(tooling, _VERIFIED_REPORT if status == "done" else _FILLED_REPORT)

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


# --- done applies the done-only rules ----------------------------------------


@pytest.mark.parametrize("status", ["review", "blocked", "abandoned"])
def test_pending_verify_line_is_fine_before_done(tooling, status):
    _write_report(tooling, _FILLED_REPORT)

    result = _task(tooling, "set-status", TASK_ID, status)

    assert result.returncode == 0, result.stderr
    assert _status(tooling) == status


def test_done_with_pending_verify_line_is_refused(tooling):
    _write_report(tooling, _FILLED_REPORT)

    result = _task(tooling, "set-status", TASK_ID, "done")

    assert result.returncode != 0
    assert "'pending'" in result.stderr
    assert "starts with 'passed'" in result.stderr
    assert _status(tooling) == "open"


def test_done_with_passed_verify_line_succeeds_and_validate_agrees(tooling):
    _write_report(tooling, _VERIFIED_REPORT)

    result = _task(tooling, "set-status", TASK_ID, "done")

    assert result.returncode == 0, result.stderr
    assert _status(tooling) == "done"
    script = tooling / ".agents" / "tasks" / "scripts" / "report.py"
    validated = subprocess.run(
        [sys.executable, str(script), "validate", TASK_ID],
        capture_output=True,
        text=True,
        check=False,
        cwd=tooling,
    )
    assert validated.returncode == 0, validated.stderr


def test_done_with_bare_passed_line_is_refused_as_validate_would(tooling):
    """``validate`` rejects a verify line that names no commit on a done task."""
    bare = _FILLED_REPORT.replace(
        _VERIFY_PENDING, "Independent verify agent (fresh context) :: passed"
    )
    _write_report(tooling, bare)

    result = _task(tooling, "set-status", TASK_ID, "done")

    assert result.returncode != 0
    assert "names no commit" in result.stderr
    assert _status(tooling) == "open"


# --- report only on the task branch ------------------------------------------


def _clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        env=_clean_env(),
        capture_output=True,
        text=True,
        check=True,
    )


def _init_repo(root: Path) -> None:
    """Make ``root`` a git repo on ``develop`` that holds the task, not a report."""
    (root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    _git(root, "init", "-b", "develop")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "commit.gpgsign", "false")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "chore: seed")


def _commit_report_on_branch(root: Path, text: str, branch: str = BRANCH) -> None:
    """Commit the report on ``branch`` and return to ``develop`` without it."""
    _git(root, "checkout", "-b", branch)
    _write_report(root, text)
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "docs(tasks): add report")
    _git(root, "checkout", "develop")
    assert not (root / ".agents" / "tasks" / "reports" / f"{TASK_ID}.md").exists()


@pytest.mark.parametrize("status", ["review", "blocked", "abandoned"])
def test_report_only_on_local_branch_is_accepted(tooling, status):
    _init_repo(tooling)
    _commit_report_on_branch(tooling, _FILLED_REPORT)

    result = _task(tooling, "set-status", TASK_ID, status)

    assert result.returncode == 0, result.stderr
    assert _status(tooling) == status


def test_report_only_on_origin_branch_is_accepted(tooling):
    _init_repo(tooling)
    remote = tooling.with_name(tooling.name + "_remote.git")
    _git(tooling, "init", "--bare", str(remote))
    _git(tooling, "remote", "add", "origin", str(remote))
    _commit_report_on_branch(tooling, _FILLED_REPORT)
    _git(tooling, "push", "origin", BRANCH)
    _git(tooling, "branch", "-D", BRANCH)

    result = _task(tooling, "set-status", TASK_ID, "review")

    assert result.returncode == 0, result.stderr
    assert _status(tooling) == "review"


def test_branch_report_is_validated_like_a_tree_report(tooling):
    _init_repo(tooling)
    _commit_report_on_branch(tooling, _PLACEHOLDER_REPORT)

    result = _task(tooling, "set-status", TASK_ID, "review")

    assert result.returncode != 0
    assert "## Lessons learned" in result.stderr
    assert "placeholder" in result.stderr
    assert _status(tooling) == "open"


def test_done_applies_verify_rule_to_branch_report(tooling):
    _init_repo(tooling)
    _commit_report_on_branch(tooling, _FILLED_REPORT)

    result = _task(tooling, "set-status", TASK_ID, "done")

    assert result.returncode != 0
    assert "starts with 'passed'" in result.stderr
    assert _status(tooling) == "open"


def test_done_accepts_branch_report_with_passed_verify_line(tooling):
    _init_repo(tooling)
    _commit_report_on_branch(tooling, _VERIFIED_REPORT)

    result = _task(tooling, "set-status", TASK_ID, "done")

    assert result.returncode == 0, result.stderr
    assert _status(tooling) == "done"


def test_working_tree_report_wins_over_branch_report(tooling):
    _init_repo(tooling)
    _commit_report_on_branch(tooling, _FILLED_REPORT)
    _write_report(tooling, _PLACEHOLDER_REPORT)

    result = _task(tooling, "set-status", TASK_ID, "review")

    assert result.returncode != 0
    assert "placeholder" in result.stderr
    assert _status(tooling) == "open"


def test_branch_without_report_file_is_refused(tooling):
    _init_repo(tooling)
    _git(tooling, "branch", BRANCH)

    result = _task(tooling, "set-status", TASK_ID, "review")

    assert result.returncode != 0
    assert "no report" in result.stderr
    assert f"report.py new {TASK_ID}" in result.stderr
    assert _status(tooling) == "open"


def test_report_only_on_another_tasks_branch_is_refused(tooling):
    _init_repo(tooling)
    _commit_report_on_branch(tooling, _FILLED_REPORT, branch="chore/T-0002-other")

    result = _task(tooling, "set-status", TASK_ID, "review")

    assert result.returncode != 0
    assert "no report" in result.stderr
    assert _status(tooling) == "open"


def test_no_report_anywhere_in_a_git_repo_is_refused(tooling):
    _init_repo(tooling)

    result = _task(tooling, "set-status", TASK_ID, "review")

    assert result.returncode != 0
    assert "no report" in result.stderr
    assert _status(tooling) == "open"


# --- unparseable report frontmatter ------------------------------------------


@pytest.mark.parametrize("status", GATED_STATUSES)
def test_unparseable_report_frontmatter_is_refused_cleanly(tooling, status):
    broken = _FILLED_REPORT.replace("outcome: success", "outcome: {not: supported}")
    _write_report(tooling, broken)

    result = _task(tooling, "set-status", TASK_ID, status)

    assert result.returncode == 1
    assert result.stderr.startswith("error:")
    assert "unsupported YAML syntax" in result.stderr
    assert "Traceback" not in result.stderr
    assert _status(tooling) == "open"


def test_unparseable_branch_report_frontmatter_is_refused_cleanly(tooling):
    _init_repo(tooling)
    broken = _FILLED_REPORT.replace("outcome: success", "outcome: {not: supported}")
    _commit_report_on_branch(tooling, broken)

    result = _task(tooling, "set-status", TASK_ID, "review")

    assert result.returncode == 1
    assert result.stderr.startswith("error:")
    assert "unsupported YAML syntax" in result.stderr
    assert "Traceback" not in result.stderr
    assert _status(tooling) == "open"
