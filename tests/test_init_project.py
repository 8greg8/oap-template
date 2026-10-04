"""Tests for `init_project.py` (plan: `.agents/plans/2026-10-03-template-init.md`).

Each case builds a scratch copy of the template from the files `git ls-files` lists, plus the
working-tree `init_project.py` and this test file, commits it, gives it a bare `origin`, and runs
the script there. Stub `uv` and `npm` executables sit first on `PATH` and record their arguments,
so most cases need no network. The cases for plan steps 2 to 5 run the script's steps up to the
seeded files only (`_run` without `full`), so they can look at the tree before self-removal and
the commit. The cases for steps 6 to 10 run the whole script; the end-to-end cases at the bottom
use the real `uv`, `npm` and gate, and skip when the lock commands cannot run. Expected values
come from the plan and the task file, not from the script's output.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

UNDO = (
    "git restore --source=HEAD --staged --worktree . && git clean -fd "
    "&& rm -rf src/my_project"
)
LOCK_COMMANDS = ("uv lock", "npm install --package-lock-only --ignore-scripts")
TEMPLATE_STRINGS = ("proj_template", "proj-template", "oap-template")
# Files the task allows to still name the template after `--yes --skip-install` with stubs.
ALLOWED_HITS = {
    "uv.lock",
    "package-lock.json",
    "init_project.py",
    "tests/test_init_project.py",
}


def _env() -> dict[str, str]:
    env: dict[str, str] = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(name, None)
    return env


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=_env(),
    )
    return result.stdout.strip()


@dataclass
class Scratch:
    repo: Path
    bare: Path
    stubs: Path
    log: Path


def _write_stub(path: Path, tool: str) -> None:
    path.write_text(
        "#!/bin/sh\n"
        f'printf \'%s\\n\' "{tool} $*" >> "$STUB_LOG"\n'
        f'exit "${{STUB_FAIL_{tool.upper()}:-0}}"\n',
        encoding="utf-8",
    )
    path.chmod(0o755)


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
        capture_output=True,
        check=True,
        env=_env(),
    ).stdout.decode()
    names = [n for n in out.split("\0") if n]
    for extra in ("init_project.py", "tests/test_init_project.py"):
        if extra not in names:
            names.append(extra)
    return names


def _build(tmp_path: Path, branch: str = "develop") -> Scratch:
    bare = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", branch, str(bare)],
        check=True,
        env=_env(),
    )
    repo = tmp_path / "proj"
    repo.mkdir()
    for rel in _tracked_files():
        src = REPO_ROOT / rel
        if not src.is_file():
            continue
        dest = repo / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())
        dest.chmod(src.stat().st_mode & 0o777)
    _git(repo, "init", "-q", "-b", branch)
    _git(repo, "config", "core.hooksPath", "/dev/null")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "init")
    _git(repo, "remote", "add", "origin", str(bare))
    _git(repo, "push", "-q", "origin", branch)
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for tool in ("uv", "npm"):
        _write_stub(stubs / tool, tool)
    return Scratch(repo=repo, bare=bare, stubs=stubs, log=tmp_path / "stub.log")


@pytest.fixture
def scratch(tmp_path: Path) -> Scratch:
    return _build(tmp_path)


def _args(package: str = "my_project", *extra: str) -> list[str]:
    return [
        "--name",
        "My Project",
        "--package",
        package,
        "--owner",
        "Jane Doe",
        "--description",
        "One sentence.",
        *extra,
    ]


# Steps 2 to 5 only: the earlier cases look at the tree before self-removal, gate and commit.
_THROUGH_SEEDING = (
    "import sys\n"
    "sys.dont_write_bytecode = True\n"
    "repo, *args = sys.argv[1:]\n"
    "sys.path.insert(0, repo)\n"
    "import init_project as m\n"
    "keep = ('step_install', 'step_rename', 'step_reset_tasks', 'step_seed_files')\n"
    "m.STEPS = tuple(f for f in m.STEPS if f.__name__ in keep)\n"
    "m.POST_COMMIT_STEPS = ()\n"
    "sys.exit(m.main(args))\n"
)


def _run(
    s: Scratch,
    *extra: str,
    package: str = "my_project",
    fail: tuple[str, ...] = (),
    full: bool = False,
    real: bool = False,
    path_prefix: Path | None = None,
) -> tuple[subprocess.CompletedProcess[str], str]:
    """Run the script in the scratch copy.

    Without `full`, only plan steps 2 to 5 run. With `full`, the script runs as a user runs it.
    With `real`, the real `uv` and `npm` are used instead of the stubs.
    """
    env = _env()
    if real:
        env.pop("VIRTUAL_ENV", None)
    else:
        env["PATH"] = f"{s.stubs}{os.pathsep}{env['PATH']}"
        env["STUB_LOG"] = str(s.log)
    if path_prefix is not None:
        env["PATH"] = f"{path_prefix}{os.pathsep}{env['PATH']}"
    for tool in fail:
        env[f"STUB_FAIL_{tool.upper()}"] = "1"
    args = _args(package, *extra)
    if full:
        command = [sys.executable, str(s.repo / "init_project.py"), *args]
    else:
        command = [sys.executable, "-c", _THROUGH_SEEDING, str(s.repo), *args]
    result = subprocess.run(
        command,
        cwd=s.repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return result, result.stdout + result.stderr


def _stub_calls(s: Scratch) -> list[str]:
    if not s.log.exists():
        return []
    return s.log.read_text(encoding="utf-8").splitlines()


def _status(repo: Path) -> str:
    return _git(repo, "status", "--porcelain", "--untracked-files=all")


def _assert_refused(
    s: Scratch, result: subprocess.CompletedProcess[str], out: str, needle: str
) -> None:
    assert result.returncode != 0, out
    assert needle in out, out
    assert "git restore --source=HEAD" not in out, out
    assert _stub_calls(s) == []
    assert not (s.repo / "src" / "my_project").exists()


# --- dry run and the --yes gate ---------------------------------------------------------------


def test_dry_run_prints_names_and_change_list_and_changes_nothing(scratch: Scratch):
    result, out = _run(scratch, "--dry-run")

    assert result.returncode == 0, out
    assert "my_project" in out
    assert "my-project" in out
    assert "my-project-dev-tooling" in out
    for path in (
        "src/proj_template",
        "pyproject.toml",
        "package.json",
        "package-lock.json",
        "uv.lock",
        ".devcontainer/devcontainer.json",
        ".devcontainer/spec-blind/devcontainer.json",
        "LICENSE",
        "tests/test_greet.py",
        "tests/test_farewell.py",
    ):
        assert path in out, f"{path} missing from change list:\n{out}"
    assert _status(scratch.repo) == ""
    assert (scratch.repo / "src" / "proj_template").is_dir()
    assert _stub_calls(scratch) == []


def test_without_dry_run_or_yes_prints_changes_then_refuses_and_changes_nothing(
    scratch: Scratch,
):
    result, out = _run(scratch)

    assert result.returncode != 0, out
    assert "--yes" in out
    assert "pyproject.toml" in out
    assert "git restore --source=HEAD" not in out
    assert _status(scratch.repo) == ""
    assert _stub_calls(scratch) == []


# --- preconditions: one refusal each -----------------------------------------------------------


@pytest.mark.parametrize(
    "package",
    ["Bad_Name", "my-project", "1abc", "class", "my project", "", "proj_template"],
)
def test_invalid_package_is_refused(scratch: Scratch, package: str):
    result, out = _run(scratch, "--yes", "--skip-install", package=package)

    _assert_refused(scratch, result, out, "--package")
    assert _status(scratch.repo) == ""


@pytest.mark.parametrize("package", ["_x", "x_", "_", "__x", "x__", "_my_project_"])
def test_package_starting_or_ending_with_underscore_is_refused(
    scratch: Scratch, package: str
):
    result, out = _run(scratch, "--yes", "--skip-install", package=package)

    _assert_refused(scratch, result, out, "--package")
    assert "underscore" in out, out
    assert _status(scratch.repo) == ""


def test_dirty_tracked_file_is_refused(scratch: Scratch):
    (scratch.repo / "README.md").write_text("edited\n", encoding="utf-8")

    result, out = _run(scratch, "--yes", "--skip-install")

    _assert_refused(scratch, result, out, "working tree is not clean")


def test_untracked_file_is_refused(scratch: Scratch):
    (scratch.repo / "stray.txt").write_text("x\n", encoding="utf-8")

    result, out = _run(scratch, "--yes", "--skip-install")

    _assert_refused(scratch, result, out, "working tree is not clean")
    assert (scratch.repo / "stray.txt").exists()


def test_other_branch_than_develop_or_main_is_refused(scratch: Scratch):
    _git(scratch.repo, "switch", "-q", "-c", "feature/x")

    result, out = _run(scratch, "--yes", "--skip-install")

    _assert_refused(scratch, result, out, "must be on develop or main")


def test_missing_origin_is_refused(scratch: Scratch):
    _git(scratch.repo, "remote", "remove", "origin")

    result, out = _run(scratch, "--yes", "--skip-install")

    _assert_refused(scratch, result, out, "origin remote is not set")


def test_missing_template_package_is_refused(scratch: Scratch):
    _git(scratch.repo, "rm", "-rq", "src/proj_template")
    _git(scratch.repo, "commit", "-q", "--no-verify", "-m", "remove package")

    result, out = _run(scratch, "--yes", "--skip-install")

    _assert_refused(scratch, result, out, "src/proj_template/ not found")


def test_main_existing_locally_is_refused_on_develop(scratch: Scratch):
    _git(scratch.repo, "branch", "main")

    result, out = _run(scratch, "--yes", "--skip-install")

    _assert_refused(scratch, result, out, "main already exists locally")


def test_main_existing_on_origin_is_refused_on_develop(scratch: Scratch):
    _git(scratch.repo, "push", "-q", "origin", "develop:main")

    result, out = _run(scratch, "--yes", "--skip-install")

    _assert_refused(scratch, result, out, "main already exists on origin")


def test_develop_existing_locally_is_refused_on_main(tmp_path: Path):
    s = _build(tmp_path, branch="main")
    _git(s.repo, "branch", "develop")

    result, out = _run(s, "--yes", "--skip-install")

    _assert_refused(s, result, out, "develop already exists locally")


def test_develop_existing_on_origin_is_refused_on_main(tmp_path: Path):
    s = _build(tmp_path, branch="main")
    _git(s.repo, "push", "-q", "origin", "main:develop")

    result, out = _run(s, "--yes", "--skip-install")

    _assert_refused(s, result, out, "develop already exists on origin")


# --- rename step ---------------------------------------------------------------------------------


def test_yes_skip_install_renames_every_template_name(scratch: Scratch):
    result, out = _run(scratch, "--yes", "--skip-install")

    assert result.returncode == 0, out
    repo = scratch.repo
    assert not (repo / "src" / "proj_template").exists()
    assert (repo / "src" / "my_project" / "__init__.py").is_file()

    pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "my-project"\n' in pyproject
    assert 'description = "One sentence."\n' in pyproject
    assert 'packages = ["src/my_project"]\n' in pyproject

    package_json = json.loads((repo / "package.json").read_text(encoding="utf-8"))
    assert package_json["name"] == "my-project-dev-tooling"

    devcontainer = (repo / ".devcontainer" / "devcontainer.json").read_text(
        encoding="utf-8"
    )
    assert '"name": "my_project",' in devcontainer
    spec_blind = (
        repo / ".devcontainer" / "spec-blind" / "devcontainer.json"
    ).read_text(encoding="utf-8")
    assert '"name": "my_project (spec-blind)",' in spec_blind

    license_text = (repo / "LICENSE").read_text(encoding="utf-8")
    assert (
        f"Copyright (c) {datetime.now().astimezone().year} Jane Doe\n" in license_text
    )
    assert "8greg8" not in license_text

    smoke = (repo / "tests" / "test_smoke.py").read_text(encoding="utf-8")
    assert "import my_project" in smoke


def test_skip_install_still_runs_the_lock_commands_and_nothing_else(scratch: Scratch):
    result, out = _run(scratch, "--yes", "--skip-install")

    assert result.returncode == 0, out
    assert _stub_calls(scratch) == list(LOCK_COMMANDS)


def test_install_runs_before_the_lock_commands(scratch: Scratch):
    result, out = _run(scratch, "--yes")

    assert result.returncode == 0, out
    assert _stub_calls(scratch) == ["npm ci", "uv sync", *LOCK_COMMANDS]


def test_nothing_is_staged_after_the_run(scratch: Scratch):
    result, out = _run(scratch, "--yes", "--skip-install")

    assert result.returncode == 0, out
    assert _git(scratch.repo, "diff", "--cached", "--name-only") == ""
    assert "pyproject.toml" in _git(scratch.repo, "diff", "--name-only")


def test_template_strings_remain_only_in_allowed_files(scratch: Scratch):
    result, out = _run(scratch, "--yes", "--skip-install")

    assert result.returncode == 0, out
    hits: set[str] = set()
    for path in scratch.repo.rglob("*"):
        rel = path.relative_to(scratch.repo)
        if not path.is_file() or rel.parts[0] in (".git", "node_modules", ".venv"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(s in text for s in TEMPLATE_STRINGS):
            hits.add(rel.as_posix())
    unexpected = {
        h for h in hits if h not in ALLOWED_HITS and not h.startswith(".agents/")
    }
    assert unexpected == set(), sorted(unexpected)


def test_runs_on_main_when_develop_is_absent(tmp_path: Path):
    s = _build(tmp_path, branch="main")

    result, out = _run(s, "--yes", "--skip-install")

    assert result.returncode == 0, out
    assert (s.repo / "src" / "my_project").is_dir()


# --- lock regeneration failure --------------------------------------------------------------------


@pytest.mark.parametrize("tool", ["uv", "npm"])
def test_failing_lock_command_prints_both_commands_and_continues(
    scratch: Scratch, tool: str
):
    result, out = _run(scratch, "--yes", "--skip-install", fail=(tool,))

    assert result.returncode == 0, out
    for command in LOCK_COMMANDS:
        assert command in out, out
    assert (scratch.repo / "src" / "my_project").is_dir()
    assert 'name = "my-project"' in (scratch.repo / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert "git restore --source=HEAD" not in out


# --- failure handler ------------------------------------------------------------------------------


def test_failing_install_exits_nonzero_and_prints_undo(scratch: Scratch):
    result, out = _run(scratch, "--yes", fail=("npm",))

    assert result.returncode != 0, out
    assert UNDO in out, out


def test_failure_in_rename_exits_nonzero_prints_undo_and_undo_restores_tree(
    scratch: Scratch,
):
    pyproject = scratch.repo / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    pyproject.write_text(
        text.replace('packages = ["src/proj_template"]\n', ""), encoding="utf-8"
    )
    _git(scratch.repo, "commit", "-q", "--no-verify", "-am", "drop packages")

    result, out = _run(scratch, "--yes", "--skip-install")

    assert result.returncode != 0, out
    assert UNDO in out, out
    assert _status(scratch.repo) != ""
    subprocess.run(
        ["bash", "-c", UNDO],
        cwd=scratch.repo,
        check=True,
        env=_env(),
        capture_output=True,
    )
    assert _status(scratch.repo) == ""
    assert (scratch.repo / "src" / "proj_template").is_dir()
    assert not (scratch.repo / "src" / "my_project").exists()


# --- task state reset (plan step 4) -------------------------------------------------------------

TASK_SCRIPTS = ".agents/tasks/scripts"


def _tracked_in(repo: Path, *pathspec: str) -> list[str]:
    out = _git(repo, "ls-files", "-z", "--", *pathspec)
    return sorted(n for n in out.split("\0") if n)


def _task_state_files(repo: Path) -> list[str]:
    """Return the files the plan says step 4 removes, as they exist before the run."""
    tasks = [
        n
        for n in _tracked_in(repo, ".agents/tasks")
        if re.fullmatch(r"\.agents/tasks/T-[^/]*\.md", n)
    ]
    reports = [
        n
        for n in _tracked_in(repo, ".agents/tasks/reports")
        if re.fullmatch(r"\.agents/tasks/reports/[^/]*\.md", n)
    ]
    plans = _tracked_in(repo, ".agents/plans")
    return tasks + reports + plans


def _expected_in(files: list[str], directory: str) -> list[str]:
    return [n for n in files if n.startswith(directory + "/")]


def _script(repo: Path, name: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = _env()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, f"{TASK_SCRIPTS}/{name}", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


@pytest.fixture
def initialized(scratch: Scratch) -> Scratch:
    before = _task_state_files(scratch.repo)
    assert before, "the scratch copy should carry task state to remove"
    result, out = _run(scratch, "--yes", "--skip-install")
    assert result.returncode == 0, out
    return scratch


def test_dry_run_lists_every_removed_task_state_file_and_changes_nothing(
    scratch: Scratch,
):
    expected = _task_state_files(scratch.repo)
    assert any("/reports/" in n for n in expected)
    assert any(n.startswith(".agents/plans/") for n in expected)
    assert any(re.search(r"/T-\d{4}-", n) for n in expected)

    result, out = _run(scratch, "--dry-run")

    assert result.returncode == 0, out
    for rel in expected:
        assert rel in out, f"{rel} missing from change list:\n{out}"
    assert ".agents/plans/README.md" in out
    assert ".agents/tasks/.counter" in out
    assert "BACKLOG.md" in out
    assert "LESSONS.md" in out
    assert _status(scratch.repo) == ""
    for rel in expected:
        assert (scratch.repo / rel).is_file()


def test_no_task_files_remain(initialized: Scratch):
    tasks_dir = initialized.repo / ".agents" / "tasks"
    assert sorted(p.name for p in tasks_dir.glob("T-*.md")) == []


def test_no_reports_remain(initialized: Scratch):
    reports = initialized.repo / ".agents" / "tasks" / "reports"
    assert sorted(p.name for p in reports.glob("*.md")) == []


def test_plans_directory_holds_only_a_readme_naming_claude_md_merge_authority(
    initialized: Scratch,
):
    plans = initialized.repo / ".agents" / "plans"
    assert sorted(p.name for p in plans.iterdir()) == ["README.md"]
    text = (plans / "README.md").read_text(encoding="utf-8")
    assert "plans" in text
    assert "approvals" in text
    assert "CLAUDE.md" in text
    assert "Merge authority" in text


def test_counter_is_zero(initialized: Scratch):
    counter = initialized.repo / ".agents" / "tasks" / ".counter"
    assert counter.read_text(encoding="utf-8").strip() == "0"


def test_backlog_lists_no_tasks_and_is_script_generated(initialized: Scratch):
    backlog = initialized.repo / ".agents" / "tasks" / "BACKLOG.md"
    text = backlog.read_text(encoding="utf-8")
    assert "GENERATED FILE" in text
    assert re.search(r"T-\d{4}", text) is None, text
    assert "0 task(s)" in text
    before = _git(initialized.repo, "status", "--porcelain")
    assert _script(initialized.repo, "backlog.py", "reindex").returncode == 0
    assert _git(initialized.repo, "status", "--porcelain") == before
    assert backlog.read_text(encoding="utf-8") == text


def test_lessons_lists_no_lessons_and_is_script_generated(initialized: Scratch):
    lessons = initialized.repo / ".agents" / "LESSONS.md"
    text = lessons.read_text(encoding="utf-8")
    assert "GENERATED FILE" in text
    assert re.search(r"T-\d{4}", text) is None, text
    assert "0 lesson(s)" in text
    assert _script(initialized.repo, "report.py", "harvest").returncode == 0
    assert lessons.read_text(encoding="utf-8") == text


def test_templates_and_task_scripts_are_byte_identical_to_the_template(
    initialized: Scratch,
):
    expected = [
        n
        for n in _tracked_in(REPO_ROOT, ".agents/tasks/templates", TASK_SCRIPTS)
        if (REPO_ROOT / n).is_file()
    ]
    assert expected
    for rel in expected:
        assert (initialized.repo / rel).read_bytes() == (REPO_ROOT / rel).read_bytes()
    for directory in (".agents/tasks/templates", TASK_SCRIPTS):
        actual = sorted(
            p.relative_to(initialized.repo).as_posix()
            for p in (initialized.repo / directory).rglob("*")
            if p.is_file()
        )
        assert actual == sorted(_expected_in(expected, directory)), actual


def test_reports_keepfile_survives_so_git_keeps_the_directory(initialized: Scratch):
    assert (initialized.repo / ".agents" / "tasks" / "reports" / ".gitkeep").is_file()


def test_nothing_is_staged_after_the_reset(initialized: Scratch):
    assert _git(initialized.repo, "diff", "--cached", "--name-only") == ""
    deleted = _git(initialized.repo, "diff", "--name-only", "--diff-filter=D")
    assert ".agents/tasks/reports/T-0001.md" in deleted.splitlines()


def test_task_validate_passes_in_the_initialized_copy(initialized: Scratch):
    result = _script(initialized.repo, "task.py", "validate")
    assert result.returncode == 0, result.stdout + result.stderr


def test_next_task_is_allocated_as_t_0001(initialized: Scratch):
    result = _script(
        initialized.repo,
        "task.py",
        "new",
        "-t",
        "First task",
        "-T",
        "chore",
        "-f",
        "README.md",
        "--no-publish",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    created = sorted(
        p.name for p in (initialized.repo / ".agents" / "tasks").glob("T-*.md")
    )
    assert len(created) == 1
    assert created[0].startswith("T-0001-")


def test_reset_adds_no_stub_calls(initialized: Scratch):
    assert _stub_calls(initialized) == list(LOCK_COMMANDS)


def test_failure_in_task_state_reset_prints_undo_and_undo_restores_tree(
    scratch: Scratch,
):
    backlog = scratch.repo / TASK_SCRIPTS / "backlog.py"
    backlog.write_text("raise SystemExit(3)\n", encoding="utf-8")
    _git(scratch.repo, "commit", "-q", "--no-verify", "-am", "break backlog")

    result, out = _run(scratch, "--yes", "--skip-install")

    assert result.returncode != 0, out
    assert UNDO in out, out
    assert _git(scratch.repo, "diff", "--cached", "--name-only") == ""
    assert _git(scratch.repo, "branch", "--list", "main") == ""
    subprocess.run(
        ["bash", "-c", UNDO],
        cwd=scratch.repo,
        check=True,
        env=_env(),
        capture_output=True,
    )
    assert _status(scratch.repo) == ""
    assert (scratch.repo / "src" / "proj_template").is_dir()
    assert (
        scratch.repo / ".agents" / "plans" / "2026-10-03-template-init.md"
    ).is_file()


# --- seeded project files (plan step 5) ---------------------------------------------------------

TEMPLATE_README_TITLE = "# OAP Template"
TEMPLATE_README_SENTENCE = "This is a **template**, not a working project"
WORKING_UNIT = "## Working unit: the task"
POLICY_FILES = ("CODE_OF_CONDUCT.md", "SECURITY.md")
# The template owner's contacts in those two files; a generated project must not carry them.
OWNER_CONTACTS = ("gregor.koporec@gmail.com", "info@koporec.eu")


def _text(repo: Path, rel: str) -> str:
    return (repo / rel).read_bytes().decode("utf-8")


def _change_lines(out: str) -> list[str]:
    return [line.strip() for line in out.splitlines()]


def test_dry_run_lists_every_seeded_replaced_and_removed_file(scratch: Scratch):
    result, out = _run(scratch, "--dry-run")

    assert result.returncode == 0, out
    lines = _change_lines(out)
    expected = [
        ("replace", "README.md"),
        ("remove", "CODE_OF_CONDUCT.md"),
        ("remove", "SECURITY.md"),
        ("edit", "CLAUDE.md"),
        ("write", "docs/spec/README.md"),
        ("replace", "src/my_project/__init__.py"),
        ("remove", "tests/test_greet.py"),
        ("remove", "tests/test_farewell.py"),
        ("write", "tests/test_smoke.py"),
    ]
    for verb, path in expected:
        assert any(
            line.startswith(f"{verb} ") and path in line.split(":")[0] for line in lines
        ), f"`{verb} {path}` missing from change list:\n{out}"
    assert _status(scratch.repo) == ""
    assert not (scratch.repo / "docs").exists()
    assert (scratch.repo / "tests" / "test_greet.py").is_file()
    for rel in POLICY_FILES:
        assert (scratch.repo / rel).is_file(), rel


def test_readme_is_a_fresh_short_project_readme(initialized: Scratch):
    text = _text(initialized.repo, "README.md")

    assert text.startswith("# My Project\n")
    assert "One sentence." in text
    assert "`CLAUDE.md`" in text
    assert "`.agents/README.md`" in text
    assert "scripts/gate.sh" in text
    assert len(text.splitlines()) <= 30
    assert TEMPLATE_README_TITLE not in text
    assert TEMPLATE_README_SENTENCE not in text
    assert "OAP Template" not in text
    assert not any(s in text for s in TEMPLATE_STRINGS)
    assert "<repo_name>" not in text


def test_claude_md_gains_only_a_project_section_before_the_working_unit(
    initialized: Scratch,
):
    template = _text(REPO_ROOT, "CLAUDE.md")
    text = _text(initialized.repo, "CLAUDE.md")

    assert text != template
    start = text.index("## Project\n")
    end = text.index(WORKING_UNIT)
    assert start < end
    # Removing the section gives the template's file back, byte for byte.
    assert text[:start] + text[end:] == template
    # It is the first `##` section.
    assert re.findall(r"^## .*$", text, re.MULTILINE)[0] == "## Project"
    assert text.count("## Project\n") == 1


def test_claude_md_project_section_has_name_description_and_comment_prompts(
    initialized: Scratch,
):
    text = _text(initialized.repo, "CLAUDE.md")
    section = text[text.index("## Project\n") : text.index(WORKING_UNIT)]

    assert "My Project" in section
    assert "One sentence." in section
    comments = re.findall(r"<!--.*?-->", section, re.DOTALL)
    assert len(comments) >= 3, section
    for topic in ("mission", "architecture", "domain"):
        assert any(topic in c.lower() for c in comments), (
            f"no {topic} prompt:\n{section}"
        )
    # Prompts only: no text outside comments beyond the heading and the filled-in values.
    prose = re.sub(r"<!--.*?-->", "", section, flags=re.DOTALL)
    assert "mission is" not in prose.lower()


def test_spec_readme_exists_and_names_the_spec_first_rule(initialized: Scratch):
    text = _text(initialized.repo, "docs/spec/README.md")

    assert "specification" in text
    assert "CLAUDE.md" in text
    assert "spec-first" in text
    assert len(text.splitlines()) <= 15


def test_sample_package_is_docstring_only(initialized: Scratch):
    init = initialized.repo / "src" / "my_project" / "__init__.py"
    tree = ast.parse(init.read_text(encoding="utf-8"))

    assert len(tree.body) == 1
    node = tree.body[0]
    assert isinstance(node, ast.Expr)
    assert isinstance(node.value, ast.Constant)
    assert isinstance(node.value.value, str)
    assert ast.get_docstring(tree)
    text = init.read_text(encoding="utf-8")
    assert "greet" not in text
    assert "farewell" not in text


def test_sample_tests_are_gone_and_smoke_test_imports_the_package(
    initialized: Scratch,
):
    tests = initialized.repo / "tests"
    assert not (tests / "test_greet.py").exists()
    assert not (tests / "test_farewell.py").exists()
    smoke = tests / "test_smoke.py"
    assert smoke.is_file()
    tree = ast.parse(smoke.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for n in ast.walk(tree)
        if isinstance(n, ast.Import)
        for alias in n.names
    }
    assert "my_project" in imported
    functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    assert any(name.startswith("test_") for name in functions)
    assert "greet" not in smoke.read_text(encoding="utf-8")


def test_code_of_conduct_and_security_policy_are_removed(initialized: Scratch):
    for rel in POLICY_FILES:
        assert not (initialized.repo / rel).exists(), rel


def test_no_owner_contact_remains_outside_the_script_files(initialized: Scratch):
    hits: set[str] = set()
    for path in initialized.repo.rglob("*"):
        rel = path.relative_to(initialized.repo)
        if not path.is_file() or rel.parts[0] in (".git", "node_modules", ".venv"):
            continue
        if rel.as_posix() in SCRIPT_FILES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(contact in text for contact in OWNER_CONTACTS):
            hits.add(rel.as_posix())
    assert hits == set(), sorted(hits)


def test_smoke_test_passes_against_the_renamed_package(initialized: Scratch):
    env = _env()
    env["PYTHONPATH"] = str(initialized.repo / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_smoke.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=initialized.repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_seeding_adds_no_stub_calls_and_stages_nothing(initialized: Scratch):
    assert _stub_calls(initialized) == list(LOCK_COMMANDS)
    assert _git(initialized.repo, "diff", "--cached", "--name-only") == ""
    untracked = _git(initialized.repo, "ls-files", "--others", "--exclude-standard")
    assert {"docs/spec/README.md", "tests/test_smoke.py"} <= set(untracked.splitlines())


def test_failure_in_seeding_prints_undo_and_undo_restores_tree(scratch: Scratch):
    claude_md = scratch.repo / "CLAUDE.md"
    text = claude_md.read_text(encoding="utf-8")
    claude_md.write_text(
        text.replace(WORKING_UNIT, "## Something else"), encoding="utf-8"
    )
    _git(
        scratch.repo, "commit", "-q", "--no-verify", "-am", "drop working unit heading"
    )

    result, out = _run(scratch, "--yes", "--skip-install")

    assert result.returncode != 0, out
    assert UNDO in out, out
    assert _git(scratch.repo, "diff", "--cached", "--name-only") == ""
    assert _git(scratch.repo, "branch", "--list", "main") == ""
    subprocess.run(
        ["bash", "-c", UNDO],
        cwd=scratch.repo,
        check=True,
        env=_env(),
        capture_output=True,
    )
    assert _status(scratch.repo) == ""
    assert (scratch.repo / "src" / "proj_template").is_dir()
    assert (scratch.repo / "tests" / "test_greet.py").is_file()
    assert not (scratch.repo / "docs").exists()


# --- script hygiene ---------------------------------------------------------------------------------


def test_script_imports_only_the_standard_library():
    source = (REPO_ROOT / "init_project.py").read_text(encoding="utf-8")
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".")[0])
    assert modules <= set(sys.stdlib_module_names), sorted(
        modules - set(sys.stdlib_module_names)
    )


def test_script_names_template_strings_plainly():
    source = (REPO_ROOT / "init_project.py").read_text(encoding="utf-8")
    for template in (*TEMPLATE_STRINGS, "oap-template-dev-tooling", "8greg8"):
        assert template in source


# --- self-removal, gate, commit, branch and checklist (plan steps 6 to 10) ----------------------

COMMIT_MESSAGE = "chore: initialize project from OAP template"
SCRIPT_FILES = ("init_project.py", "tests/test_init_project.py")
LICENSE_POINTER = "Third-party material in this repository is listed in NOTICE.md."


def _stub_gate(s: Scratch, code: int = 0) -> None:
    """Replace the copy's `scripts/gate.sh` with a stub, committed so the tree stays clean."""
    gate = s.repo / "scripts" / "gate.sh"
    gate.write_text(f"#!/bin/sh\necho 'stub gate ran'\nexit {code}\n", encoding="utf-8")
    gate.chmod(0o755)
    _git(s.repo, "commit", "-q", "--no-verify", "-am", "stub gate")


def _commit_count(repo: Path) -> int:
    return int(_git(repo, "rev-list", "--count", "HEAD"))


def _refs(repo: Path) -> str:
    return _git(repo, "for-each-ref", "--format=%(refname) %(objectname)")


def _run_undo(repo: Path) -> None:
    subprocess.run(
        ["bash", "-c", UNDO], cwd=repo, check=True, env=_env(), capture_output=True
    )


def _assert_no_commit_or_branch(
    s: Scratch, head_before: str, other: str = "main"
) -> None:
    assert _git(s.repo, "rev-parse", "HEAD") == head_before
    assert _git(s.repo, "branch", "--list", other) == ""
    assert _git(s.repo, "diff", "--cached", "--name-only") == ""


def test_dry_run_lists_self_removal_and_steps_7_to_10_in_order(scratch: Scratch):
    result, out = _run(scratch, "--dry-run", full=True)

    assert result.returncode == 0, out
    lines = _change_lines(out)

    def index(verb: str, needle: str) -> int:
        hits = [
            i
            for i, line in enumerate(lines)
            if line.startswith(f"{verb} ") and needle in line
        ]
        assert hits, f"`{verb} ... {needle}` missing from change list:\n{out}"
        return hits[0]

    seeded = index("write", "tests/test_smoke.py")
    removed_script = index("remove", "init_project.py")
    removed_tests = index("remove", "tests/test_init_project.py")
    gate = index("run", "scripts/gate.sh")
    commit = index("commit", COMMIT_MESSAGE)
    branch = index("create", "main")
    checklist = index("print", "checklist")
    assert "new commit" in lines[branch]
    assert seeded < removed_script < gate < commit < branch < checklist
    assert seeded < removed_tests < gate
    assert _status(scratch.repo) == ""
    assert (scratch.repo / "init_project.py").is_file()
    assert _git(scratch.repo, "branch", "--list", "main") == ""


def test_dry_run_on_main_creates_develop(tmp_path: Path):
    s = _build(tmp_path, branch="main")

    result, out = _run(s, "--dry-run", full=True)

    assert result.returncode == 0, out
    assert any(
        line.startswith("create ") and "develop" in line and "new commit" in line
        for line in _change_lines(out)
    ), out


def test_full_run_makes_one_commit_and_both_branches_point_at_it(scratch: Scratch):
    _stub_gate(scratch)
    head_before = _git(scratch.repo, "rev-parse", "HEAD")
    count_before = _commit_count(scratch.repo)
    refs_before = _refs(scratch.bare)
    notice = (scratch.repo / "NOTICE.md").read_bytes()

    result, out = _run(scratch, "--yes", "--skip-install", full=True)

    assert result.returncode == 0, out
    repo = scratch.repo
    head = _git(repo, "rev-parse", "HEAD")
    assert head != head_before
    assert _commit_count(repo) == count_before + 1
    assert _git(repo, "log", "-1", "--format=%P") == head_before
    assert _git(repo, "log", "-1", "--format=%B") == COMMIT_MESSAGE
    assert _git(repo, "rev-parse", "develop") == head
    assert _git(repo, "rev-parse", "main") == head
    assert _git(repo, "symbolic-ref", "--short", "HEAD") == "develop"
    assert _status(repo) == ""
    assert "stub gate ran" in out
    assert _stub_calls(scratch) == list(LOCK_COMMANDS)
    # Self-removal.
    tracked = set(_git(repo, "ls-files").splitlines())
    for rel in SCRIPT_FILES:
        assert not (repo / rel).exists()
        assert rel not in tracked
    # Never pushes or tags.
    assert _refs(scratch.bare) == refs_before
    assert _git(repo, "tag", "--list") == ""
    assert _git(scratch.bare, "tag", "--list") == ""
    # NOTICE.md and the LICENSE pointer line survive the run.
    assert (repo / "NOTICE.md").read_bytes() == notice
    license_text = _text(repo, "LICENSE")
    assert LICENSE_POINTER in license_text.splitlines()
    assert f"Copyright (c) {datetime.now().astimezone().year} Jane Doe" in license_text
    assert "8greg8" not in license_text


def test_init_commit_message_passes_the_commit_linter(scratch: Scratch, tmp_path: Path):
    _stub_gate(scratch)
    result, out = _run(scratch, "--yes", "--skip-install", full=True)
    assert result.returncode == 0, out
    message = tmp_path / "message.txt"
    message.write_text(_git(scratch.repo, "log", "-1", "--format=%B") + "\n")

    lint = subprocess.run(
        [sys.executable, "scripts/commit_lint.py", str(message)],
        cwd=scratch.repo,
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )

    assert lint.returncode == 0, lint.stdout + lint.stderr


def test_full_run_prints_the_human_checklist(scratch: Scratch):
    _stub_gate(scratch)

    result, out = _run(scratch, "--yes", "--skip-install", full=True)

    assert result.returncode == 0, out
    head = _git(scratch.repo, "rev-parse", "HEAD")
    assert head in out
    lowered = out.lower()
    assert any(
        "push" in line and "develop" in line and "main" in line
        for line in lowered.splitlines()
    ), out
    assert "default branch" in lowered
    # The default branch is named `develop`, with the reason and the role of `main`.
    # The checklist item, not the dry-run summary line that also mentions the default branch.
    default_line = next(
        line
        for line in lowered.splitlines()
        if "default branch" in line and line.strip().startswith("2.")
    )
    assert "`develop`" in default_line, default_line
    assert "task.py" in default_line, default_line
    assert "origin/develop" in default_line, default_line
    assert "main" in default_line and "release" in default_line, default_line
    assert "branch protection" in lowered
    assert "CLAUDE.md" in out
    assert "## Project" in out
    assert "first spec" in lowered
    assert "docs/spec" in out
    policy_line = next(
        line for line in lowered.splitlines() if line.strip().startswith("5.")
    )
    assert "code of conduct" in policy_line, policy_line
    assert "security policy" in policy_line, policy_line
    assert "CODE_OF_CONDUCT.md" in out
    assert "SECURITY.md" in out
    assert not (scratch.repo / "CODE_OF_CONDUCT.md").exists()
    assert not (scratch.repo / "SECURITY.md").exists()
    assert "git restore --source=HEAD" not in out


def test_full_run_on_main_creates_develop_at_the_commit(tmp_path: Path):
    s = _build(tmp_path, branch="main")
    _stub_gate(s)

    result, out = _run(s, "--yes", "--skip-install", full=True)

    assert result.returncode == 0, out
    head = _git(s.repo, "rev-parse", "HEAD")
    assert _git(s.repo, "symbolic-ref", "--short", "HEAD") == "main"
    assert _git(s.repo, "rev-parse", "develop") == head
    assert _status(s.repo) == ""


def test_failing_gate_stops_without_commit_or_branch_and_undo_restores_tree(
    scratch: Scratch,
):
    _stub_gate(scratch, code=1)
    head_before = _git(scratch.repo, "rev-parse", "HEAD")
    refs_before = _refs(scratch.bare)

    result, out = _run(scratch, "--yes", "--skip-install", full=True)

    assert result.returncode != 0, out
    assert "stub gate ran" in out
    assert UNDO in out, out
    _assert_no_commit_or_branch(scratch, head_before)
    assert _refs(scratch.bare) == refs_before
    assert _status(scratch.repo) != ""
    _run_undo(scratch.repo)
    assert _status(scratch.repo) == ""
    assert _git(scratch.repo, "rev-parse", "HEAD") == head_before
    for rel in SCRIPT_FILES:
        assert (scratch.repo / rel).is_file()
    assert (scratch.repo / "src" / "proj_template").is_dir()
    assert not (scratch.repo / "src" / "my_project").exists()


def test_failing_commit_prints_undo_and_leaves_no_commit_or_branch(scratch: Scratch):
    _stub_gate(scratch)
    hooks = scratch.repo.parent / "hooks"
    hooks.mkdir()
    hook = hooks / "pre-commit"
    hook.write_text("#!/bin/sh\necho 'hook says no' >&2\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    _git(scratch.repo, "config", "core.hooksPath", str(hooks))
    head_before = _git(scratch.repo, "rev-parse", "HEAD")

    result, out = _run(scratch, "--yes", "--skip-install", full=True)

    assert result.returncode != 0, out
    assert "hook says no" in out
    assert UNDO in out, out
    assert _git(scratch.repo, "rev-parse", "HEAD") == head_before
    assert _git(scratch.repo, "branch", "--list", "main") == ""
    _run_undo(scratch.repo)
    assert _status(scratch.repo) == ""
    for rel in SCRIPT_FILES:
        assert (scratch.repo / rel).is_file()


def test_failure_creating_the_branch_prints_hash_and_command_but_not_undo(
    scratch: Scratch, tmp_path: Path
):
    _stub_gate(scratch)
    real_git = shutil.which("git")
    assert real_git
    shim = tmp_path / "gitshim"
    shim.mkdir()
    wrapper = shim / "git"
    wrapper.write_text(
        "#!/bin/sh\n"
        'for a in "$@"; do\n'
        '  if [ "$a" = branch ]; then echo "fatal: simulated failure" >&2; exit 1; fi\n'
        "done\n"
        f'exec {real_git} "$@"\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    result, out = _run(scratch, "--yes", "--skip-install", full=True, path_prefix=shim)

    assert result.returncode != 0, out
    head = _git(scratch.repo, "rev-parse", "HEAD")
    assert _git(scratch.repo, "log", "-1", "--format=%s") == COMMIT_MESSAGE
    assert head in out
    assert f"git branch main {head}" in out
    assert "git restore --source=HEAD" not in out
    assert "git clean" not in out
    assert _git(scratch.repo, "branch", "--list", "main") == ""
    assert _status(scratch.repo) == ""
    # The printed command completes the run.
    _git(scratch.repo, "branch", "main", head)
    assert _git(scratch.repo, "rev-parse", "main") == head


# --- a failed lock command stops before the commit -----------------------------------------------

FINISH_MARKER = "To finish by hand"


def _finish_lines(out: str) -> list[str]:
    """Return the non-empty lines after the finish marker, the last block of the output."""
    lines = out.splitlines()
    start = next(i for i, line in enumerate(lines) if FINISH_MARKER in line)
    return [line.strip() for line in lines[start + 1 :] if line.strip()]


@pytest.mark.parametrize(
    ("failing", "failed_commands"),
    [
        (("uv",), [LOCK_COMMANDS[0]]),
        (("npm",), [LOCK_COMMANDS[1]]),
        (("uv", "npm"), list(LOCK_COMMANDS)),
    ],
)
def test_failed_lock_command_stops_before_the_commit_and_prints_finish_commands(
    scratch: Scratch, failing: tuple[str, ...], failed_commands: list[str]
):
    _stub_gate(scratch)
    head_before = _git(scratch.repo, "rev-parse", "HEAD")
    refs_before = _refs(scratch.bare)

    result, out = _run(scratch, "--yes", "--skip-install", full=True, fail=failing)

    assert result.returncode != 0, out
    # The remaining steps ran through the gate, then the run stopped.
    assert "stub gate ran" in out
    assert _git(scratch.repo, "rev-parse", "HEAD") == head_before
    assert _git(scratch.repo, "branch", "--list", "main") == ""
    assert _git(scratch.repo, "diff", "--cached", "--name-only") == ""
    assert _refs(scratch.bare) == refs_before
    # The tree is valid, so it is left as it is and no undo command is offered.
    assert "git restore --source=HEAD" not in out
    assert "git clean" not in out
    assert (scratch.repo / "src" / "my_project").is_dir()
    for rel in SCRIPT_FILES:
        assert not (scratch.repo / rel).exists()
    assert _status(scratch.repo) != ""
    # The message names the failed commands, then the exact commands to finish.
    assert _finish_lines(out) == [
        *failed_commands,
        "git add -A",
        f'git commit -m "{COMMIT_MESSAGE}"',
        "git branch main",
    ]
    stopped = out[: out.index(FINISH_MARKER)]
    for command in failed_commands:
        assert command in stopped, out


def test_finish_commands_after_a_lock_failure_complete_the_run(scratch: Scratch):
    _stub_gate(scratch)
    head_before = _git(scratch.repo, "rev-parse", "HEAD")
    count_before = _commit_count(scratch.repo)
    result, out = _run(scratch, "--yes", "--skip-install", full=True, fail=("uv",))
    assert result.returncode != 0, out

    env = _env()
    env["PATH"] = f"{scratch.stubs}{os.pathsep}{env['PATH']}"
    env["STUB_LOG"] = str(scratch.log)
    for command in _finish_lines(out):
        subprocess.run(
            ["bash", "-c", command],
            cwd=scratch.repo,
            check=True,
            capture_output=True,
            env=env,
        )

    head = _git(scratch.repo, "rev-parse", "HEAD")
    assert _commit_count(scratch.repo) == count_before + 1
    assert _git(scratch.repo, "log", "-1", "--format=%P") == head_before
    assert _git(scratch.repo, "log", "-1", "--format=%s") == COMMIT_MESSAGE
    assert _git(scratch.repo, "rev-parse", "main") == head
    assert _status(scratch.repo) == ""


def test_finish_commands_name_develop_when_the_run_started_on_main(tmp_path: Path):
    s = _build(tmp_path, branch="main")
    _stub_gate(s)

    result, out = _run(s, "--yes", "--skip-install", full=True, fail=("npm",))

    assert result.returncode != 0, out
    assert _finish_lines(out)[-1] == "git branch develop"
    assert _git(s.repo, "branch", "--list", "develop") == ""


def test_failed_lock_command_with_a_red_gate_still_prints_the_undo_command(
    scratch: Scratch,
):
    _stub_gate(scratch, code=1)

    result, out = _run(scratch, "--yes", "--skip-install", full=True, fail=("uv",))

    assert result.returncode != 0, out
    assert UNDO in out, out
    assert FINISH_MARKER not in out


# --- template README --------------------------------------------------------------------------


def test_template_readme_getting_started_describes_the_script_and_checklist():
    text = _text(REPO_ROOT, "README.md")
    start = text.index("## Getting started with a new project")
    end = text.index("\n## ", start + 1)
    section = text[start:end]

    assert "template" in section
    assert "python init_project.py" in section
    assert "--dry-run" in section
    # Create the repository without "Include all branches": unrelated histories otherwise.
    assert "Include all branches" in section
    assert "without" in section
    assert "unrelated histories" in section
    assert "checklist" in section
    assert "--name" in section
    assert "--package" in section
    # The manual renaming steps are gone.
    assert "Rename the package" not in section
    assert "replace `<repo_name>`" not in section
    # Other sections stay.
    for heading in ("## What's in here", "## Design principles", "## License"):
        assert heading in text


# --- end to end: a template copy becomes a working project ------------------------------------


def _require_lock_tools(repo: Path) -> None:
    """Skip the case when the script's two lock commands cannot run here.

    The commands are the script's own (`--ignore-scripts` keeps `husky` out of it, so a copy
    without `node_modules/` works). They leave tracked files changed, so those are restored.
    """
    env = _env()
    env.pop("VIRTUAL_ENV", None)
    for command in (
        ["uv", "lock"],
        ["npm", "install", "--package-lock-only", "--ignore-scripts"],
    ):
        try:
            probe = subprocess.run(
                command,
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
        except FileNotFoundError:
            pytest.skip(f"`{command[0]}` is not installed")
        if probe.returncode != 0:
            _git(repo, "checkout", "-q", "--", ".")
            pytest.skip(
                f"`{' '.join(command)}` failed (no network?): "
                f"{(probe.stdout + probe.stderr).strip()[-300:]}"
            )
    _git(repo, "checkout", "-q", "--", ".")
    assert _status(repo) == ""


def test_end_to_end_template_copy_becomes_a_working_project(scratch: Scratch):
    repo = scratch.repo
    _require_lock_tools(repo)
    head_before = _git(repo, "rev-parse", "HEAD")
    count_before = _commit_count(repo)

    result, out = _run(scratch, "--yes", "--skip-install", full=True, real=True)

    assert result.returncode == 0, out
    assert "gate clean" in out, out
    head = _git(repo, "rev-parse", "HEAD")
    assert _commit_count(repo) == count_before + 1
    assert _git(repo, "log", "-1", "--format=%P") == head_before
    assert _git(repo, "log", "-1", "--format=%s") == COMMIT_MESSAGE
    assert _git(repo, "rev-parse", "develop") == head
    assert _git(repo, "rev-parse", "main") == head
    assert _status(repo) == ""
    for rel in SCRIPT_FILES:
        assert not (repo / rel).exists()
    for rel in POLICY_FILES:
        assert not (repo / rel).exists(), rel

    # No template name survives in a tracked file, uv.lock and package-lock.json included.
    tracked = [n for n in _git(repo, "ls-files", "-z").split("\0") if n]
    assert "uv.lock" in tracked
    hits = {
        rel: [t for t in TEMPLATE_STRINGS if t in _text(repo, rel)]
        for rel in tracked
        if (repo / rel).is_file()
    }
    assert {rel: found for rel, found in hits.items() if found} == {}

    # Gitflow works: `main` exists, so a hotfix can start from it.
    hotfix = subprocess.run(
        ["bash", "scripts/gitflow.sh", "hotfix", "start", "x"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )
    assert hotfix.returncode == 0, hotfix.stdout + hotfix.stderr
    worktree = repo.parent / "proj-hotfix-x"
    assert _git(worktree, "rev-parse", "--abbrev-ref", "HEAD") == "hotfix/x"
    assert _git(worktree, "rev-parse", "HEAD") == head

    # `task.py new` syncs with origin/develop, so push develop first.
    _git(repo, "push", "-q", "origin", "develop")
    first = _script(
        repo, "task.py", "new", "-t", "First task", "-T", "chore", "-f", "README.md"
    )
    assert first.returncode == 0, first.stdout + first.stderr
    created = sorted(p.name for p in (repo / ".agents" / "tasks").glob("T-*.md"))
    assert len(created) == 1
    assert created[0].startswith("T-0001-")


def test_end_to_end_failing_gate_leaves_no_commit_or_branch(scratch: Scratch):
    repo = scratch.repo
    planted = repo / "tests" / "test_planted_failure.py"
    planted.write_text(
        '"""A test that always fails, planted to turn the gate red."""\n\n\n'
        "def test_planted_failure() -> None:\n"
        '    raise AssertionError("planted failure")\n',
        encoding="utf-8",
    )
    _git(repo, "add", "tests/test_planted_failure.py")
    _git(repo, "commit", "-q", "--no-verify", "-m", "test: plant a failing test")
    _require_lock_tools(repo)
    head_before = _git(repo, "rev-parse", "HEAD")

    result, out = _run(scratch, "--yes", "--skip-install", full=True, real=True)

    assert result.returncode != 0, out
    failed = re.findall(r"^FAILED (\S+)", out, re.MULTILINE)
    assert failed == ["tests/test_planted_failure.py::test_planted_failure"], out
    assert UNDO in out, out
    _assert_no_commit_or_branch(scratch, head_before)
    _run_undo(repo)
    assert _status(repo) == ""
    assert _git(repo, "rev-parse", "HEAD") == head_before
    for rel in SCRIPT_FILES:
        assert (repo / rel).is_file()
    assert (repo / "src" / "proj_template").is_dir()
    assert not (repo / "src" / "my_project").exists()
