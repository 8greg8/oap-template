"""Tests for ``report.py`` (validate, harvest) and ``housekeep.py`` (touches, drift, worktrees).

Git behavior is exercised against real throwaway repositories under ``tmp_path``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".agents" / "tasks" / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import _schema  # ty: ignore[unresolved-import]
import housekeep as housekeep_module  # ty: ignore[unresolved-import]
import report as report_module  # ty: ignore[unresolved-import]
from _schema import Report, Task  # ty: ignore[unresolved-import]

# --- git test-repo helpers ----------------------------------------------------

_GIT_ENV_VARS_TO_STRIP = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES",
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in _GIT_ENV_VARS_TO_STRIP}
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, f"git {args} failed: {result.stderr}"
    return result


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    _git(path, "init", "-q", "-b", "develop")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    _git(path, "config", "commit.gpgsign", "false")
    return path


def _seeded_repo(path: Path) -> Path:
    repo = _init_repo(path)
    (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "chore: seed")
    return repo


def _commit_files(repo: Path, names: list[str], message: str) -> None:
    for name in names:
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n", encoding="utf-8")
        _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", message)


# --- report.py validate -------------------------------------------------------

_VERIFY_PASSED = (
    "Independent verify agent (fresh context) :: passed (commit abc1234; 10 passed)"
)
_TOUCHES_TICKED = "- [x] No files changed outside the task's declared `touches` scope."
_TOUCHES_UNTICKED = (
    "- [ ] No files changed outside the task's declared `touches` scope."
)


def _done_task(task_id: str, touches: list[str], status: str = "done") -> Task:
    return Task(
        Path(f"{task_id}-x.md"),
        {"id": task_id, "status": status, "touches": touches},
        "",
    )


def _report_for(
    task_id: str, verify_line: str, touches_line: str, summary: str = "s"
) -> Report:
    lines = [
        "## Summary",
        summary,
        "## What was done",
        "w",
        "## Files changed",
        "f",
        "## Tests run",
        "```",
        "uv run pytest :: 1 passed",
        verify_line,
        "```",
        "## Documentation impact",
        "none",
        "## Safety confirmations",
        touches_line,
        "## Known limitations",
        "k",
        "## Follow-up recommended",
        "f",
        "## Lessons learned",
        "l",
    ]
    meta = {"task": task_id, "outcome": "success"}
    return Report(Path(f"{task_id}.md"), meta, "\n".join(lines))


def _merged_repo(tmp_path: Path, task_id: str, changed: list[str]) -> Path:
    """Repo whose develop holds a task merge commit changing `changed` files."""
    repo = _seeded_repo(tmp_path / "repo")
    _git(repo, "checkout", "-q", "-b", "feat/task")
    _commit_files(repo, changed, "feat: change")
    _git(repo, "checkout", "-q", "develop")
    number = task_id.removeprefix("T-")
    _git(
        repo,
        "merge",
        "--no-ff",
        "-q",
        "feat/task",
        "-m",
        f"chore(merge): merge task {number} into develop",
    )
    return repo


def test_done_report_with_not_run_verify_fails():
    task = _done_task("T-0001", ["src"])
    report = _report_for(
        "T-0001",
        "Independent verify agent (fresh context) :: not run (skipped)",
        _TOUCHES_UNTICKED,
    )
    assert any("verify" in p for p in report_module.validate_report(report, task))


def test_done_report_with_passed_verify_is_accepted():
    task = _done_task("T-0001", ["src"])
    report = _report_for("T-0001", _VERIFY_PASSED, _TOUCHES_UNTICKED)
    assert report_module.validate_report(report, task) == []


_GATE_KEY = (
    "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"  # gitleaks:allow
)


def _verify_line(status: str) -> str:
    return f"Independent verify agent (fresh context) :: {status}"


def test_done_report_with_gate_record_verify_line_is_accepted():
    task = _done_task("T-0001", ["src"])
    line = _verify_line(f"passed (commit abc1234; gate {_GATE_KEY}; 10 passed)")
    report = _report_for("T-0001", line, _TOUCHES_UNTICKED)
    assert report_module.validate_report(report, task) == []


@pytest.mark.parametrize(
    "key", ["0123456789ab", "0123456789abcdef0123456789abcdef01234567"]
)
def test_done_report_accepts_gate_key_of_12_to_64_characters(key):
    task = _done_task("T-0001", ["src"])
    line = _verify_line(f"passed (commit abc1234; gate {key}; 551 passed)")
    report = _report_for("T-0001", line, _TOUCHES_UNTICKED)
    assert report_module.validate_report(report, task) == []


@pytest.mark.parametrize(
    "status",
    [
        "passed (commit abc1234; gate pending; 10 passed)",
        "passed (commit abc1234; gate ; 10 passed)",
        "passed (commit abc1234; gate xyz; 10 passed)",
        "passed (commit abc1234; gate 0123; 10 passed)",
        "passed (commit abc1234; gate 0123456789a; 10 passed)",
        "passed (commit abc1234; gate 0123456789ABCDEF; 10 passed)",
        f"passed (commit abc1234; gate {_GATE_KEY}0; 10 passed)",
    ],
)
def test_done_report_rejects_malformed_gate_record(status):
    task = _done_task("T-0001", ["src"])
    report = _report_for("T-0001", _verify_line(status), _TOUCHES_UNTICKED)
    assert any("gate" in p for p in report_module.validate_report(report, task))


def test_done_report_with_gate_record_still_needs_a_commit():
    task = _done_task("T-0001", ["src"])
    line = _verify_line(f"passed (gate {_GATE_KEY}; 10 passed)")
    report = _report_for("T-0001", line, _TOUCHES_UNTICKED)
    assert any("commit" in p for p in report_module.validate_report(report, task))


def test_done_report_with_gate_record_but_failed_verify_fails():
    task = _done_task("T-0001", ["src"])
    line = _verify_line(f"failed (commit abc1234; gate {_GATE_KEY}; 3 failed)")
    report = _report_for("T-0001", line, _TOUCHES_UNTICKED)
    assert any("verify" in p for p in report_module.validate_report(report, task))


def test_done_report_without_gate_part_in_free_text_is_accepted():
    task = _done_task("T-0001", ["src"])
    line = _verify_line("passed (commit abc1234; gate.sh passed, 551 tests passed)")
    report = _report_for("T-0001", line, _TOUCHES_UNTICKED)
    assert report_module.validate_report(report, task) == []


def test_report_template_documents_the_gate_record_form():
    template = (REPO_ROOT / ".agents/tasks/templates/report.md").read_text(
        encoding="utf-8"
    )
    assert "passed (commit <hash>; gate <record-key>;" in template


def test_done_report_without_verify_line_fails():
    task = _done_task("T-0001", ["src"])
    report = _report_for("T-0001", "uv run ruff check :: passed", _TOUCHES_UNTICKED)
    assert any("verify" in p for p in report_module.validate_report(report, task))


def test_done_report_with_pending_verify_fails():
    task = _done_task("T-0001", ["src"])
    report = _report_for(
        "T-0001",
        "Independent verify agent (fresh context) :: pending",
        _TOUCHES_UNTICKED,
    )
    assert any("verify" in p for p in report_module.validate_report(report, task))


@pytest.mark.parametrize("status", ["failed", "blocked", "skipped"])
def test_done_report_with_non_passed_verify_fails(status):
    task = _done_task("T-0001", ["src"])
    report = _report_for(
        "T-0001",
        f"Independent verify agent (fresh context) :: {status}",
        _TOUCHES_UNTICKED,
    )
    assert any("verify" in p for p in report_module.validate_report(report, task))


def test_verify_rule_ignores_tasks_that_are_not_done():
    task = _done_task("T-0001", ["src"], status="in_progress")
    report = _report_for(
        "T-0001",
        "Independent verify agent (fresh context) :: not run",
        _TOUCHES_UNTICKED,
    )
    assert report_module.validate_report(report, task) == []


@pytest.mark.parametrize(
    "verify_line",
    [
        "Independent verify agent (fresh context) :: passed",
        "Independent verify agent (fresh context) :: passed (10 passed)",
        "Independent verify agent (fresh context) :: passed (commit abc12; 10 passed)",
        "Independent verify agent (fresh context) :: passed (abc1234; 10 passed)",
    ],
)
@pytest.mark.parametrize("task_id", ["T-0001", "T-0300"])
def test_done_report_needs_verified_commit_hash(task_id, verify_line):
    task = _done_task(task_id, ["src"])
    report = _report_for(task_id, verify_line, _TOUCHES_UNTICKED)
    assert any("commit" in p for p in report_module.validate_report(report, task))


@pytest.mark.parametrize(
    "summary",
    [
        "All criteria are met except the independent verify, which is pending.",
        "Every criterion is met except the independent verify line, which is pending.",
        "The independent verification has not run yet.",
        "Done. Acceptance holds except the independent verify of this task.",
    ],
)
def test_done_report_with_stale_verify_wording_in_summary_fails(summary):
    task = _done_task("T-0001", ["src"])
    report = _report_for("T-0001", _VERIFY_PASSED, _TOUCHES_UNTICKED, summary)
    assert any("Summary" in p for p in report_module.validate_report(report, task))


@pytest.mark.parametrize(
    "summary",
    [
        "All acceptance criteria are met.",
        "Pending items are listed under Known limitations. The verify agent passed.",
        "Verification is recorded below. A pending change remains in docs.",
    ],
)
def test_done_report_with_consistent_summary_passes(summary):
    task = _done_task("T-0001", ["src"])
    report = _report_for("T-0001", _VERIFY_PASSED, _TOUCHES_UNTICKED, summary)
    assert report_module.validate_report(report, task) == []


def test_summary_rule_ignores_tasks_that_are_not_done():
    stale = "Met except the independent verify, which is pending."
    task = _done_task("T-0001", ["src"], status="in_progress")
    report = _report_for("T-0001", _VERIFY_PASSED, _TOUCHES_UNTICKED, stale)
    assert report_module.validate_report(report, task) == []


def test_ticked_touches_box_with_out_of_touches_merge_diff_fails(tmp_path):
    repo = _merged_repo(tmp_path, "T-0001", ["src/a.py", "docs/other.md"])
    task = _done_task("T-0001", ["src"])
    report = _report_for("T-0001", _VERIFY_PASSED, _TOUCHES_TICKED)
    problems = report_module.validate_report(report, task, repo)
    assert any("docs/other.md" in p for p in problems)
    assert not any("src/a.py" in p for p in problems)


def test_ticked_touches_box_with_in_touches_merge_diff_passes(tmp_path):
    repo = _merged_repo(
        tmp_path,
        "T-0001",
        [
            "src/pkg/a.py",
            ".agents/tasks/reports/T-0001.md",
            ".agents/tasks/T-0001-some-slug.md",
        ],
    )
    task = _done_task("T-0001", ["src"])
    report = _report_for("T-0001", _VERIFY_PASSED, _TOUCHES_TICKED)
    assert report_module.validate_report(report, task, repo) == []


def test_unticked_touches_box_is_not_checked_against_merge_diff(tmp_path):
    repo = _merged_repo(tmp_path, "T-0001", ["docs/other.md"])
    task = _done_task("T-0001", ["src"])
    report = _report_for("T-0001", _VERIFY_PASSED, _TOUCHES_UNTICKED)
    assert report_module.validate_report(report, task, repo) == []


def test_touches_check_is_skipped_when_no_merge_commit_exists(tmp_path):
    repo = _seeded_repo(tmp_path / "repo")
    task = _done_task("T-0001", ["src"])
    report = _report_for("T-0001", _VERIFY_PASSED, _TOUCHES_TICKED)
    assert report_module.validate_report(report, task, repo) == []


def test_no_source_project_thresholds_remain_in_scripts():
    text = (SCRIPTS_DIR / "report.py").read_text(encoding="utf-8")
    text += (SCRIPTS_DIR / "housekeep.py").read_text(encoding="utf-8")
    assert "STRICT_AFTER_ID" not in text
    assert "COMMIT_REQUIRED_AFTER_ID" not in text
    assert "T-0054" not in text
    assert "T-0170" not in text


# --- report.py harvest --------------------------------------------------------


def test_harvest_lists_each_lesson_once_with_tag_index(monkeypatch, tmp_path):
    reports = []
    for task_id, tags in [("T-0157", ["alpha", "beta"]), ("T-0158", ["beta"])]:
        reports.append(
            Report(
                path=tmp_path / f"{task_id}.md",
                meta={"task": task_id, "outcome": "passed", "tags": tags},
                body=f"## Lessons learned\n\nLesson text {task_id}.\n",
            )
        )
    monkeypatch.setattr(report_module, "load_reports", lambda: reports)
    text = report_module.render_lessons(report_module.collect_lessons())
    assert text.count("Lesson text T-0157.") == 1
    assert text.count("Lesson text T-0158.") == 1
    assert text.index("## alpha") < text.index("Lesson text T-0157.")
    assert "## beta" in text
    assert "- `beta` — [T-0157](#t-0157-passed), [T-0158](#t-0158-passed)" in text
    assert "- `alpha` — [T-0157](#t-0157-passed)" in text


# --- housekeep.py -------------------------------------------------------------


def _hk_task(task_id: str, touches: list[str], status: str = "in_progress") -> Task:
    return Task(
        Path(f"{task_id}-x.md"),
        {
            "id": task_id,
            "title": "demo",
            "type": "feat",
            "status": status,
            "touches": touches,
        },
        "",
    )


@pytest.fixture
def hk_repo(tmp_path, monkeypatch):
    # housekeep's git helper inherits the environment; a git hook exports GIT_DIR etc.
    for name in _GIT_ENV_VARS_TO_STRIP:
        monkeypatch.delenv(name, raising=False)
    repo = _seeded_repo(tmp_path / "repo")
    monkeypatch.setattr(housekeep_module, "REPO_ROOT", repo)
    monkeypatch.setattr(_schema, "REPORTS_DIR", repo / ".agents/tasks/reports")
    # No task files in the scratch repo; tests that need tasks patch ``load_tasks``.
    monkeypatch.setattr(housekeep_module, "load_tasks", list)
    return repo


def test_housekeep_touches_flags_out_of_scope_and_allows_own_report(
    hk_repo, monkeypatch
):
    task = _hk_task("T-0001", ["src"])
    monkeypatch.setattr(housekeep_module, "find_task", lambda _id: task)
    _git(hk_repo, "checkout", "-q", "-b", "feat/T-0001-demo")
    _commit_files(
        hk_repo,
        ["src/a.py", ".agents/tasks/reports/T-0001.md", "docs/other.md"],
        "feat: change",
    )
    findings = housekeep_module.check_touches(["feat/T-0001-demo"])
    assert len(findings) == 1
    assert "docs/other.md" in findings[0]
    assert not any("reports/T-0001.md" in f for f in findings)


def test_housekeep_touches_clean_when_only_own_report_and_scope(hk_repo, monkeypatch):
    task = _hk_task("T-0001", ["src"])
    monkeypatch.setattr(housekeep_module, "find_task", lambda _id: task)
    _git(hk_repo, "checkout", "-q", "-b", "feat/T-0001-demo")
    _commit_files(hk_repo, ["src/a.py", ".agents/tasks/reports/T-0001.md"], "feat: x")
    assert housekeep_module.check_touches(["feat/T-0001-demo"]) == []


def test_housekeep_drift_finds_report_only_on_task_branch(hk_repo, monkeypatch):
    task = _hk_task("T-0001", ["src"], status="done")
    other = _hk_task("T-0002", ["src"], status="done")
    monkeypatch.setattr(housekeep_module, "load_tasks", lambda: [task, other])
    monkeypatch.setattr(housekeep_module, "backlog_is_stale", lambda _t: False)
    _git(hk_repo, "checkout", "-q", "-b", task.branch)
    _commit_files(hk_repo, [".agents/tasks/reports/T-0001.md"], "docs: report")
    _git(hk_repo, "checkout", "-q", "develop")
    findings = housekeep_module.check_drift()
    assert not any("T-0001" in f for f in findings)
    assert any("T-0002" in f and "no report" in f for f in findings)


def test_housekeep_worktrees_flags_merged_unremoved_worktree(hk_repo):
    merged = hk_repo.parent / "wt-merged"
    _git(hk_repo, "worktree", "add", "-q", "-b", "feat/T-0001-demo", str(merged))
    _commit_files(merged, ["src/a.py"], "feat: work")
    _git(hk_repo, "merge", "-q", "--no-ff", "feat/T-0001-demo", "-m", "merge")
    findings = housekeep_module.check_worktrees()
    assert any(str(merged) in f and "never removed" in f for f in findings)


def test_housekeep_worktrees_ignores_empty_branch_at_develop_tip(hk_repo):
    wt = hk_repo.parent / "wt-empty"
    _git(hk_repo, "worktree", "add", "-q", "-b", "feat/T-0001-demo", str(wt))
    assert housekeep_module.check_worktrees() == []


def test_housekeep_worktrees_ignores_unmerged_worktree(hk_repo):
    wt = hk_repo.parent / "wt-open"
    _git(hk_repo, "worktree", "add", "-q", "-b", "feat/T-0001-demo", str(wt))
    _commit_files(wt, ["src/a.py"], "feat: work")
    assert housekeep_module.check_worktrees() == []


def test_housekeep_worktrees_flags_develop_in_secondary_worktree(hk_repo):
    _git(hk_repo, "checkout", "-q", "-b", "scratch")
    wt = hk_repo.parent / "wt-develop"
    _git(hk_repo, "worktree", "add", "-q", str(wt), "develop")
    findings = housekeep_module.check_worktrees()
    assert any(str(wt) in f and "'develop'" in f for f in findings)


def _set_tasks(monkeypatch, *tasks: Task) -> None:
    monkeypatch.setattr(housekeep_module, "load_tasks", lambda: list(tasks))


@pytest.mark.parametrize("status", ["done", "abandoned"])
def test_housekeep_worktrees_flags_unmerged_worktree_of_finished_task(
    hk_repo, monkeypatch, status
):
    _set_tasks(monkeypatch, _hk_task("T-0001", ["src"], status=status))
    wt = hk_repo.parent / "wt-unmerged"
    _git(hk_repo, "worktree", "add", "-q", "-b", "feat/T-0001-demo", str(wt))
    _commit_files(wt, ["src/a.py"], "feat: work")
    findings = housekeep_module.check_worktrees()
    assert len(findings) == 1
    assert str(wt) in findings[0]
    assert "T-0001" in findings[0] and status in findings[0]
    assert "not merged" in findings[0]


def test_housekeep_worktrees_flags_worktree_of_finished_task_at_develop_tip(
    hk_repo, monkeypatch
):
    _set_tasks(monkeypatch, _hk_task("T-0001", ["src"], status="abandoned"))
    wt = hk_repo.parent / "wt-empty"
    _git(hk_repo, "worktree", "add", "-q", "-b", "feat/T-0001-demo", str(wt))
    findings = housekeep_module.check_worktrees()
    assert len(findings) == 1
    assert str(wt) in findings[0] and "abandoned" in findings[0]


def test_housekeep_worktrees_merged_worktree_of_done_task_is_one_finding(
    hk_repo, monkeypatch
):
    _set_tasks(monkeypatch, _hk_task("T-0001", ["src"], status="done"))
    wt = hk_repo.parent / "wt-merged"
    _git(hk_repo, "worktree", "add", "-q", "-b", "feat/T-0001-demo", str(wt))
    _commit_files(wt, ["src/a.py"], "feat: work")
    _git(hk_repo, "merge", "-q", "--no-ff", "feat/T-0001-demo", "-m", "merge")
    findings = housekeep_module.check_worktrees()
    # One for the worktree; the branch is already covered by it.
    assert len(findings) == 1
    assert str(wt) in findings[0] and "never removed" in findings[0]
    assert "T-0001" in findings[0]


@pytest.mark.parametrize("status", ["in_progress", "review", "open", "blocked"])
def test_housekeep_worktrees_ignores_worktree_of_unfinished_task(
    hk_repo, monkeypatch, status
):
    _set_tasks(monkeypatch, _hk_task("T-0001", ["src"], status=status))
    wt = hk_repo.parent / "wt-open"
    _git(hk_repo, "worktree", "add", "-q", "-b", "feat/T-0001-demo", str(wt))
    _commit_files(wt, ["src/a.py"], "feat: work")
    assert housekeep_module.check_worktrees() == []


@pytest.mark.parametrize("status", ["done", "abandoned"])
def test_housekeep_worktrees_flags_unmerged_branch_without_worktree(
    hk_repo, monkeypatch, status
):
    _set_tasks(monkeypatch, _hk_task("T-0001", ["src"], status=status))
    _git(hk_repo, "checkout", "-q", "-b", "feat/T-0001-demo")
    _commit_files(hk_repo, ["src/a.py"], "feat: work")
    _git(hk_repo, "checkout", "-q", "develop")
    findings = housekeep_module.check_worktrees()
    assert len(findings) == 1
    assert "feat/T-0001-demo" in findings[0]
    assert "T-0001" in findings[0] and status in findings[0]
    assert "not merged" in findings[0] and "no secondary worktree" in findings[0]


def test_housekeep_worktrees_flags_merged_branch_without_worktree(hk_repo, monkeypatch):
    _set_tasks(monkeypatch, _hk_task("T-0001", ["src"], status="done"))
    _git(hk_repo, "checkout", "-q", "-b", "feat/T-0001-demo")
    _commit_files(hk_repo, ["src/a.py"], "feat: work")
    _git(hk_repo, "checkout", "-q", "develop")
    _git(hk_repo, "merge", "-q", "--no-ff", "feat/T-0001-demo", "-m", "merge")
    findings = housekeep_module.check_worktrees()
    assert len(findings) == 1
    assert "feat/T-0001-demo" in findings[0] and "merged into develop" in findings[0]
    assert "not merged" not in findings[0]


def test_housekeep_worktrees_ignores_branch_of_unfinished_or_unknown_task(
    hk_repo, monkeypatch
):
    _set_tasks(monkeypatch, _hk_task("T-0001", ["src"], status="in_progress"))
    for branch in ("feat/T-0001-demo", "feat/T-0002-other", "scratch"):
        _git(hk_repo, "branch", branch)
    assert housekeep_module.check_worktrees() == []


def test_housekeep_worktrees_branch_leftover_makes_cli_exit_nonzero(
    hk_repo, monkeypatch, capsys
):
    _set_tasks(monkeypatch, _hk_task("T-0001", ["src"], status="done"))
    _git(hk_repo, "branch", "feat/T-0001-demo")
    assert housekeep_module.main(["worktrees"]) == 1
    assert "feat/T-0001-demo" in capsys.readouterr().out
    assert housekeep_module.main(["all"]) == 1


def test_housekeep_worktrees_reports_only_and_removes_nothing(hk_repo, monkeypatch):
    _set_tasks(monkeypatch, _hk_task("T-0001", ["src"], status="done"))
    wt = hk_repo.parent / "wt-keep"
    _git(hk_repo, "worktree", "add", "-q", "-b", "feat/T-0001-demo", str(wt))
    _git(hk_repo, "branch", "feat/T-0001-other")
    housekeep_module.check_worktrees()
    assert wt.is_dir()
    branches = _git(hk_repo, "branch", "--format=%(refname:short)").stdout.split()
    assert "feat/T-0001-demo" in branches and "feat/T-0001-other" in branches
