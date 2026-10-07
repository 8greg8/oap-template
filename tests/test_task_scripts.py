"""Tests for the git-atomic task-filing path and the backlog selection fixes.

`_git_publish.publish_task` is exercised against real, throwaway git
repositories (a bare "origin" plus one or more clones) built fresh under
`tmp_path` -- no mocked git, because process-level behavior is only faithfully
exercised by actually running it. `task.py new` itself is exercised the same
way, as a real subprocess, against an isolated clone so `TASKS_DIR` and
`COUNTER_FILE` resolve from that clone's own copy of the scripts rather than
this project's real `.agents/tasks/`.

`create_task`/`allocate_id`'s allocation behavior is covered separately via
`monkeypatch`, since that function is git-free by design (the publish/retry
loop stays outside it).
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

sys.path.insert(0, str(SCRIPTS_DIR))

import _git_publish  # ty: ignore[unresolved-import]
import _ids  # ty: ignore[unresolved-import]  # sys.path-inserted, like the script's own import
import backlog as backlog_module  # ty: ignore[unresolved-import]
import task as task_module  # ty: ignore[unresolved-import]
from _git_publish import PublishError, publish_task  # ty: ignore[unresolved-import]
from _schema import Task  # ty: ignore[unresolved-import]

# --- git test-repo helpers ----------------------------------------------------


# Git environment variables that, if inherited from the invoking process (e.g.
# a git hook, which sets these for the processes it spawns), take precedence
# over an explicit `-C <path>` for repository discovery and can redirect these
# test fixtures onto an unrelated, real repository. Stripped (popped, not just
# blanked -- an empty string is not always equivalent to unset for these) from
# every git subprocess's environment so `-C`/cwd is always what decides which
# repository is used.
_GIT_ENV_VARS_TO_STRIP = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES",
)


def _git(repo: Path | None, *args: str) -> subprocess.CompletedProcess[str]:
    cmd = ["git"] if repo is None else ["git", "-C", str(repo)]
    env = dict(os.environ)
    for name in _GIT_ENV_VARS_TO_STRIP:
        env.pop(name, None)
    result = subprocess.run(
        cmd + list(args), capture_output=True, text=True, check=False, env=env
    )
    assert result.returncode == 0, f"git {args} failed: {result.stderr}"
    return result


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    _git(path, "init", "-q", "-b", "develop")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    return path


def _seed_origin(tmp_path: Path) -> Path:
    """Build a bare `origin.git` with one commit already on `develop`."""
    seed = _init_repo(tmp_path / "seed")
    (seed / "README.md").write_text("seed\n", encoding="utf-8")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "-q", "-m", "chore: seed")

    origin = tmp_path / "origin.git"
    _git(None, "init", "--bare", "-q", str(origin))
    _git(seed, "remote", "add", "origin", str(origin))
    _git(seed, "push", "-q", "origin", "develop")
    return origin


def _clone(
    tmp_path: Path, origin: Path, name: str, *, with_scripts: bool = False
) -> Path:
    dest = tmp_path / name
    _git(None, "clone", "-q", str(origin), str(dest))
    _git(dest, "checkout", "-q", "develop")
    _git(dest, "config", "user.email", "test@example.com")
    _git(dest, "config", "user.name", "Test")
    if with_scripts:
        shutil.copytree(SCRIPTS_DIR, dest / ".agents" / "tasks" / "scripts")
        shutil.copytree(TEMPLATES_DIR, dest / ".agents" / "tasks" / "templates")
        for cache in (dest / ".agents").rglob("__pycache__"):
            shutil.rmtree(cache)
        # Commit the scripts/templates themselves so they're not mistaken for
        # part of whatever `task.py new` writes when a test inspects status.
        _git(dest, "add", ".agents")
        _git(dest, "commit", "-q", "-m", "chore: seed task-tooling copy")
        _git(dest, "push", "-q", "origin", "develop")
    return dest


def _write_bare_task(tasks_dir: Path, task_id: str, slug: str = "test") -> Path:
    tasks_dir.mkdir(parents=True, exist_ok=True)
    path = tasks_dir / f"{task_id}-{slug}.md"
    path.write_text(f"---\nid: {task_id}\n---\n\n# {task_id}\n", encoding="utf-8")
    return path


def _next_id(tasks_dir: Path) -> str:
    return f"T-{_ids.highest_existing_id(tasks_dir) + 1:04d}"


# --- _git() env isolation regression ---------------------------------


def test_git_helper_ignores_ambient_git_dir_and_work_tree(tmp_path, monkeypatch):
    """`_git()` must never resolve onto a repo pointed at by ambient
    GIT_DIR/GIT_WORK_TREE -- only the explicit `repo`/`-C` argument decides
    which repository is touched.

    Regression test for an incident: a `pre-push` hook
    invocation sets GIT_DIR/GIT_WORK_TREE in the environment of the `pytest`
    subprocess it spawns, and git's env vars take precedence over `-C` for
    repository discovery. Without stripping them, these fixture helpers landed
    on the real, invoking repository's `.git` instead of the intended
    `tmp_path` fixture repo.
    """
    decoy_dir = tmp_path / "decoy"
    decoy_dir.mkdir()
    _git(decoy_dir, "init", "-q", "-b", "develop")
    decoy_git_dir = decoy_dir / ".git"
    decoy_head_before = (decoy_git_dir / "HEAD").read_text(encoding="utf-8")
    decoy_config_before = (decoy_git_dir / "config").read_text(encoding="utf-8")

    monkeypatch.setenv("GIT_DIR", str(decoy_git_dir))
    monkeypatch.setenv("GIT_WORK_TREE", str(decoy_dir))

    real_repo = _init_repo(tmp_path / "real")
    (real_repo / "README.md").write_text("real\n", encoding="utf-8")
    _git(real_repo, "add", "README.md")
    _git(real_repo, "commit", "-q", "-m", "chore: seed")

    # The decoy repo must be completely untouched: no commit landed there, and
    # neither HEAD nor config (where `_init_repo`'s `git config` calls would
    # have written) changed.
    assert (decoy_git_dir / "HEAD").read_text(encoding="utf-8") == decoy_head_before
    assert (decoy_git_dir / "config").read_text(encoding="utf-8") == decoy_config_before
    decoy_log = subprocess.run(
        ["git", "-C", str(decoy_dir), "log", "--oneline"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert decoy_log.returncode != 0 or decoy_log.stdout.strip() == ""

    # The real fixture repo, addressed explicitly via `-C`, got the commit.
    real_log = _git(real_repo, "log", "--oneline")
    assert "chore: seed" in real_log.stdout


# --- _git_publish._git() env isolation regression --------------------


def test_git_publish_git_helper_ignores_ambient_git_dir_and_work_tree(
    tmp_path, monkeypatch
):
    """`_git_publish._git()` must never resolve onto a repo pointed at by
    ambient GIT_DIR/GIT_WORK_TREE -- only the explicit `repo_root`/`-C`
    argument decides which repository is touched.

    Regression test, the production counterpart of the test-fixture version: this
    is the `_git()` helper `task.py new`'s git-atomic publishing path
    actually uses against real `develop`, so a leak here is higher
    blast-radius than the test-fixture version.
    """
    decoy_dir = tmp_path / "decoy"
    decoy_dir.mkdir()
    _git(decoy_dir, "init", "-q", "-b", "develop")
    decoy_git_dir = decoy_dir / ".git"
    decoy_head_before = (decoy_git_dir / "HEAD").read_text(encoding="utf-8")
    decoy_config_before = (decoy_git_dir / "config").read_text(encoding="utf-8")

    monkeypatch.setenv("GIT_DIR", str(decoy_git_dir))
    monkeypatch.setenv("GIT_WORK_TREE", str(decoy_dir))

    real_repo = _init_repo(tmp_path / "real")
    _git_publish._git(real_repo, "config", "user.email", "test@example.com")
    _git_publish._git(real_repo, "config", "user.name", "Test")
    (real_repo / "README.md").write_text("real\n", encoding="utf-8")
    _git_publish._git(real_repo, "add", "README.md")
    commit_result = _git_publish._git(real_repo, "commit", "-q", "-m", "chore: seed")
    assert commit_result.returncode == 0, commit_result.stderr

    # The decoy repo must be completely untouched: no commit landed there, and
    # neither HEAD nor config (where the `git config` calls above would have
    # written, had they leaked onto the decoy) changed.
    assert (decoy_git_dir / "HEAD").read_text(encoding="utf-8") == decoy_head_before
    assert (decoy_git_dir / "config").read_text(encoding="utf-8") == decoy_config_before
    decoy_log = subprocess.run(
        ["git", "-C", str(decoy_dir), "log", "--oneline"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert decoy_log.returncode != 0 or decoy_log.stdout.strip() == ""

    # The real fixture repo, addressed explicitly via `repo_root`, got the
    # commit.
    real_log = _git_publish._git(real_repo, "log", "--oneline")
    assert "chore: seed" in real_log.stdout


# --- create_task() / allocate_id() regression (git-free) ----------------------


def test_create_task_allocates_sequential_ids(tmp_path, monkeypatch):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    monkeypatch.setattr(task_module, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(_ids, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(_ids, "COUNTER_FILE", tasks_dir / ".counter")
    monkeypatch.setattr(_ids, "LOCK_FILE", tasks_dir / ".counter.lock")

    first = task_module.create_task(title="First", task_type="fix")
    second = task_module.create_task(title="Second", task_type="feat")

    assert first.name.startswith("T-0001-")
    assert second.name.startswith("T-0002-")
    assert first.exists() and second.exists()


def test_create_task_reconciles_against_files_on_disk(tmp_path, monkeypatch):
    """A stale counter can never hand out an ID that already exists on disk."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _write_bare_task(tasks_dir, "T-0005")
    monkeypatch.setattr(task_module, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(_ids, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(_ids, "COUNTER_FILE", tasks_dir / ".counter")
    monkeypatch.setattr(_ids, "LOCK_FILE", tasks_dir / ".counter.lock")

    created = task_module.create_task(title="Next", task_type="fix")

    assert created.name.startswith("T-0006-")


# --- publish_task(): guard rails -----------------------------------------------


def test_publish_task_rejects_non_develop_branch(tmp_path):
    origin = _seed_origin(tmp_path)
    clone = _clone(tmp_path, origin, "clone")
    _git(clone, "checkout", "-q", "-b", "fix/not-develop")

    with pytest.raises(PublishError, match="develop"):
        publish_task(
            lambda: _write_bare_task(clone / ".agents" / "tasks", "T-0001"),
            repo_root=clone,
        )


def test_publish_task_rejects_secondary_worktree(tmp_path):
    origin = _seed_origin(tmp_path)
    clone = _clone(tmp_path, origin, "clone")
    worktree = tmp_path / "clone-worktree"
    _git(clone, "worktree", "add", "-q", "-b", "fix/wt", str(worktree))

    with pytest.raises(PublishError, match="worktree"):
        publish_task(
            lambda: _write_bare_task(worktree / ".agents" / "tasks", "T-0001"),
            repo_root=worktree,
        )


# --- publish_task(): happy path and the race/retry it exists for --------------


def test_publish_task_commits_and_pushes_to_develop(tmp_path):
    origin = _seed_origin(tmp_path)
    clone = _clone(tmp_path, origin, "clone")
    tasks_dir = clone / ".agents" / "tasks"

    published = publish_task(
        lambda: _write_bare_task(tasks_dir, _next_id(tasks_dir)), repo_root=clone
    )

    assert published.name.startswith("T-0001-")
    log = _git(clone, "log", "--oneline", "origin/develop").stdout
    assert "T-0001" in _git(clone, "show", "--stat", "HEAD").stdout
    assert len(log.strip().splitlines()) == 2  # seed commit + published task


def test_publish_task_retries_on_concurrent_publish(tmp_path):
    """Two agents race to file a task from separate clones.

    `clone_b` syncs once (inside `publish_task`) and then, in the window
    between that sync and its own push, `clone_a` files and pushes its own
    task straight to `origin` -- simulating another agent finishing first.
    `clone_b`'s push is rejected as non-fast-forward; `publish_task` must
    resync, reallocate, and retry rather than erroring or clobbering
    `clone_a`'s task.
    """
    origin = _seed_origin(tmp_path)
    clone_a = _clone(tmp_path, origin, "clone_a")
    clone_b = _clone(tmp_path, origin, "clone_b")
    tasks_dir_b = clone_b / ".agents" / "tasks"

    attempts: list[str] = []

    def _create_for_b() -> Path:
        if not attempts:
            # Simulate a concurrent agent (clone_a) winning the race: it
            # syncs, allocates, commits, and pushes to origin before
            # clone_b's own push happens.
            tasks_dir_a = clone_a / ".agents" / "tasks"
            task_id_a = _next_id(tasks_dir_a)
            # Distinct slug from clone_b's own task below: two different
            # titles racing for the same next ID, not a literal duplicate
            # (which could otherwise commit to an identical tree/commit hash
            # and mask the race this test means to exercise).
            path_a = _write_bare_task(tasks_dir_a, task_id_a, slug="race-winner")
            _git(clone_a, "add", str(path_a))
            _git(clone_a, "commit", "-q", "-m", f"chore(tasks): file {task_id_a} test")
            _git(clone_a, "push", "-q", "origin", "develop")

        task_id_b = _next_id(tasks_dir_b)
        path_b = _write_bare_task(tasks_dir_b, task_id_b)
        attempts.append(task_id_b)
        return path_b

    published = publish_task(_create_for_b, repo_root=clone_b)

    published_id = "-".join(published.stem.split("-", 2)[:2])
    assert len(attempts) == 2, "clone_b must retry exactly once after the race"
    assert attempts[1] == published_id, (
        "the retry's ID is the one that actually got published"
    )
    assert attempts[0] != attempts[1], "the retry must not repeat the colliding ID"

    remote_ids = {
        "-".join(p.stem.split("-", 2)[:2]) for p in tasks_dir_b.glob("T-*.md")
    }
    assert len(remote_ids) == 2, (
        "both clone_a's and clone_b's tasks must be present, with distinct IDs"
    )


# --- CLI: `task.py new` guard rails and --no-publish ---------------------------


def _run_cli(clone: Path, *args: str) -> subprocess.CompletedProcess[str]:
    script = clone / ".agents" / "tasks" / "scripts" / "task.py"
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=clone,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_cli_new_no_publish_writes_local_file_only(tmp_path):
    origin = _seed_origin(tmp_path)
    clone = _clone(tmp_path, origin, "clone", with_scripts=True)
    before = _git(clone, "rev-parse", "HEAD").stdout

    result = _run_cli(clone, "new", "-t", "Local only", "-T", "fix", "--no-publish")

    assert result.returncode == 0, result.stderr
    after = _git(clone, "rev-parse", "HEAD").stdout
    assert before == after, "no commit should have been made"
    status = _git(clone, "status", "--porcelain").stdout
    assert "T-0001" in status


def test_cli_new_publishes_to_develop_by_default(tmp_path):
    origin = _seed_origin(tmp_path)
    clone = _clone(tmp_path, origin, "clone", with_scripts=True)
    before = len(
        _git(clone, "log", "--oneline", "origin/develop").stdout.strip().splitlines()
    )

    result = _run_cli(clone, "new", "-t", "Published task", "-T", "fix")

    assert result.returncode == 0, result.stderr
    after = len(
        _git(clone, "log", "--oneline", "origin/develop").stdout.strip().splitlines()
    )
    assert after == before + 1, "exactly one new commit must land on origin/develop"
    status = _git(clone, "status", "--porcelain").stdout
    assert status.strip() == "", (
        "the published task file must be committed, not left dirty"
    )


def test_cli_new_rejects_non_develop_branch(tmp_path):
    origin = _seed_origin(tmp_path)
    clone = _clone(tmp_path, origin, "clone", with_scripts=True)
    _git(clone, "checkout", "-q", "-b", "fix/not-develop")

    result = _run_cli(clone, "new", "-t", "Should fail", "-T", "fix")

    assert result.returncode == 1
    assert "develop" in result.stderr
    assert not list((clone / ".agents" / "tasks").glob("T-*.md"))


# --- abandoned duplicates, per-task report links, one entry per lesson --


def _meta_task(tmp_path: Path, name: str, **meta) -> Task:
    return Task(path=tmp_path / name, meta={"title": "t", **meta}, body="")


def test_list_ids_skips_abandoned_duplicate(monkeypatch, capsys, tmp_path):
    tasks = [
        _meta_task(tmp_path, "T-0109-a.md", id="T-0109", status="done"),
        _meta_task(tmp_path, "T-0109-b.md", id="T-0109", status="abandoned"),
        _meta_task(tmp_path, "T-0110-c.md", id="T-0110", status="ready"),
    ]
    monkeypatch.setattr(task_module, "load_tasks", lambda: tasks)
    assert task_module.main(["list-ids"]) == 0
    assert capsys.readouterr().out.split() == ["T-0109", "T-0110"]


def _write_task_file(tasks_dir: Path, name: str, task_id: str, status: str) -> None:
    (tasks_dir / name).write_text(
        f"---\nid: {task_id}\ntitle: t\nstatus: {status}\n---\n\nbody\n",
        encoding="utf-8",
    )


def test_validate_flags_live_duplicate_but_not_abandoned(monkeypatch, tmp_path):
    monkeypatch.setattr(task_module, "TASKS_DIR", tmp_path)
    _write_task_file(tmp_path, "T-0109-a.md", "T-0109", "done")
    _write_task_file(tmp_path, "T-0109-b.md", "T-0109", "abandoned")
    assert not any("duplicate id" in p for p in task_module._collect_problems())
    _write_task_file(tmp_path, "T-0109-c.md", "T-0109", "ready")
    assert any("duplicate id" in p for p in task_module._collect_problems())


def test_backlog_links_each_row_to_its_own_report(monkeypatch, tmp_path):
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "T-0109.md").write_text("x", encoding="utf-8")
    (tmp_path / "reports" / "T-0109-migrate.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(backlog_module, "TASKS_DIR", tmp_path)
    tasks = [
        _meta_task(
            tmp_path,
            "T-0109-a.md",
            id="T-0109",
            status="done",
            priority="low",
            type="fix",
            report="reports/T-0109-migrate.md",
        ),
        _meta_task(
            tmp_path,
            "T-0109-b.md",
            id="T-0109",
            status="abandoned",
            priority="low",
            type="fix",
            report="reports/T-0109.md",
        ),
    ]
    text = backlog_module.render_backlog(tasks)
    rows = {
        line.split("|")[2].strip(): line
        for line in text.splitlines()
        if "T-0109-" in line
    }
    assert "(reports/T-0109-migrate.md)" in rows["[t](T-0109-a.md)"]
    assert "(reports/T-0109.md)" in rows["[t](T-0109-b.md)"]


# --- blocked tasks and in-flight overlap --


def test_blocked_task_is_not_ready(tmp_path):
    tasks = [
        _meta_task(tmp_path, "T-0300-a.md", id="T-0300", status="blocked"),
        _meta_task(tmp_path, "T-0301-b.md", id="T-0301", status="open"),
    ]
    assert [t.id for t in backlog_module.ready_tasks(tasks)] == ["T-0301"]


def test_parallel_batch_excludes_overlap_with_in_progress_task(tmp_path):
    running = _meta_task(
        tmp_path, "T-0300-a.md", id="T-0300", status="in_progress", touches=["src/a"]
    )
    clash = _meta_task(
        tmp_path, "T-0301-b.md", id="T-0301", status="open", touches=["src/a/x.py"]
    )
    free = _meta_task(
        tmp_path, "T-0302-c.md", id="T-0302", status="open", touches=["docs"]
    )
    batch = backlog_module.parallel_batch([clash, free], 3, active=[running])
    assert [t.id for t in batch] == ["T-0302"]


def test_ready_parallel_cli_excludes_overlap_with_in_progress_task(
    monkeypatch, capsys, tmp_path
):
    tasks = [
        _meta_task(
            tmp_path,
            "T-0300-a.md",
            id="T-0300",
            status="in_progress",
            touches=["src/a"],
        ),
        _meta_task(
            tmp_path, "T-0301-b.md", id="T-0301", status="open", touches=["src/a"]
        ),
        _meta_task(
            tmp_path, "T-0302-c.md", id="T-0302", status="open", touches=["docs"]
        ),
    ]
    monkeypatch.setattr(backlog_module, "load_tasks", lambda: tasks)
    assert backlog_module.main(["ready", "--parallel", "3"]) == 0
    assert capsys.readouterr().out.split() == ["T-0302"]


def test_parallel_batch_excludes_overlap_with_review_task(tmp_path):
    in_review = _meta_task(
        tmp_path, "T-0300-a.md", id="T-0300", status="review", touches=["src/a"]
    )
    clash = _meta_task(
        tmp_path, "T-0301-b.md", id="T-0301", status="open", touches=["src/a/x.py"]
    )
    free = _meta_task(
        tmp_path, "T-0302-c.md", id="T-0302", status="open", touches=["docs"]
    )
    batch = backlog_module.parallel_batch([clash, free], 3, active=[in_review])
    assert [t.id for t in batch] == ["T-0302"]


def test_ready_parallel_cli_excludes_overlap_with_review_task(
    monkeypatch, capsys, tmp_path
):
    tasks = [
        _meta_task(
            tmp_path, "T-0300-a.md", id="T-0300", status="review", touches=["src/a"]
        ),
        _meta_task(
            tmp_path, "T-0301-b.md", id="T-0301", status="open", touches=["src/a"]
        ),
        _meta_task(
            tmp_path, "T-0302-c.md", id="T-0302", status="open", touches=["docs"]
        ),
    ]
    monkeypatch.setattr(backlog_module, "load_tasks", lambda: tasks)
    assert backlog_module.main(["ready", "--parallel", "3"]) == 0
    assert capsys.readouterr().out.split() == ["T-0302"]


# --- commit message: slug truncation ---------------------------------------------


def test_commit_message_keeps_a_short_slug_whole():
    assert (
        _git_publish._commit_message("T-0007", "short-slug")
        == "chore(tasks): file T-0007 short-slug"
    )


def test_commit_message_truncates_a_long_slug_to_fit_the_header_limit():
    message = _git_publish._commit_message("T-0007", "very-long-slug-" * 20)
    assert len(message) <= _git_publish.MAX_HEADER_LENGTH
    assert message.startswith("chore(tasks): file T-0007 very-long-slug-")
    assert not message.endswith("-")


def test_publish_task_commit_header_fits_the_limit_for_a_long_slug(tmp_path):
    origin = _seed_origin(tmp_path)
    clone = _clone(tmp_path, origin, "clone")
    tasks_dir = clone / ".agents" / "tasks"
    slug = "a-very-long-task-title-" * 8

    publish_task(
        lambda: _write_bare_task(tasks_dir, _next_id(tasks_dir), slug=slug),
        repo_root=clone,
    )

    header = _git(clone, "log", "-1", "--format=%s").stdout.strip()
    assert len(header) <= _git_publish.MAX_HEADER_LENGTH
    assert header.startswith("chore(tasks): file T-0001 ")


# --- executable bit on shebang-bearing scripts ---------------------------------


def test_shebang_task_scripts_are_executable_in_git_index():
    """Every script under `.agents/tasks/scripts/` that starts with `#!` is mode 100755.

    ruff's EXE001 fires on a shebang file without the executable bit, and a fresh clone
    takes its file modes from the git index, not from the author's working tree.
    """
    listing = subprocess.run(
        ["git", "ls-files", "-s", "--", ".agents/tasks/scripts/*.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert listing, "git ls-files returned no task scripts"

    wrong = {}
    for line in listing:
        meta, path = line.split("\t", 1)
        mode = meta.split()[0]
        has_shebang = (REPO_ROOT / path).read_bytes().startswith(b"#!")
        expected = "100755" if has_shebang else "100644"
        if mode != expected:
            wrong[path] = f"{mode} (expected {expected})"
    assert not wrong, f"wrong git index modes: {wrong}"
