"""Tests for `init_project.py` (plan: `.agents/plans/2026-10-03-template-init.md`).

Each case builds a scratch copy of the template from the files `git ls-files` lists, plus the
working-tree `init_project.py` and this test file, commits it, gives it a bare `origin`, and runs
the script there. Stub `uv` and `npm` executables sit first on `PATH` and record their arguments,
so no case needs the network. Expected values come from the plan and the task file, not from
the script's output.
"""

from __future__ import annotations

import ast
import json
import os
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
LOCK_COMMANDS = ("uv lock", "npm install --package-lock-only")
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


def _run(
    s: Scratch, *extra: str, package: str = "my_project", fail: tuple[str, ...] = ()
) -> tuple[subprocess.CompletedProcess[str], str]:
    env = _env()
    env["PATH"] = f"{s.stubs}{os.pathsep}{env['PATH']}"
    env["STUB_LOG"] = str(s.log)
    for tool in fail:
        env[f"STUB_FAIL_{tool.upper()}"] = "1"
    result = subprocess.run(
        [sys.executable, str(s.repo / "init_project.py"), *_args(package, *extra)],
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

    greet = (repo / "tests" / "test_greet.py").read_text(encoding="utf-8")
    farewell = (repo / "tests" / "test_farewell.py").read_text(encoding="utf-8")
    assert "from my_project import greet" in greet
    assert "from my_project import farewell" in farewell


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
    for line in _status(scratch.repo).splitlines():
        assert line[0] in " ?", f"staged entry: {line!r}"


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
