<!-- GENERATED FILE — do not edit by hand.
     Regenerate with: python .agents/tasks/scripts/report.py harvest
     The reports in .agents/tasks/reports/ are the source of truth. -->

# Lessons Learned

Harvested from task reports. Read the tags relevant to your task before
starting — these are repo-specific traps that already cost someone time.

8 lesson(s) across 7 section(s). Generated 2026-10-03.

## Tag index

Each lesson appears once, under its first tag; the index links every tag
to all lessons that carry it.

- `agent-rules` — [T-0005](#t-0005-success)
- `backlog` — [T-0002](#t-0002-success)
- `bash` — [T-0012](#t-0012-success)
- `commit-lint` — [T-0004](#t-0004-success)
- `devcontainer` — [T-0006](#t-0006-success), [T-0007](#t-0007-success)
- `docker` — [T-0006](#t-0006-success)
- `docs` — [T-0005](#t-0005-success)
- `file-modes` — [T-0007](#t-0007-success)
- `gate` — [T-0004](#t-0004-success)
- `git` — [T-0007](#t-0007-success), [T-0012](#t-0012-success)
- `git-pathspec` — [T-0008](#t-0008-success)
- `git-publish` — [T-0002](#t-0002-success)
- `gitflow` — [T-0004](#t-0004-success)
- `hooks` — [T-0004](#t-0004-success), [T-0008](#t-0008-success)
- `housekeep` — [T-0003](#t-0003-success)
- `husky` — [T-0004](#t-0004-success), [T-0006](#t-0006-success), [T-0008](#t-0008-success)
- `nul-safe` — [T-0012](#t-0012-success)
- `orchestrator` — [T-0005](#t-0005-success)
- `port` — [T-0003](#t-0003-success)
- `pre-commit` — [T-0008](#t-0008-success)
- `process` — [T-0005](#t-0005-success)
- `report-validation` — [T-0003](#t-0003-success)
- `ruff` — [T-0007](#t-0007-success)
- `scripts` — [T-0012](#t-0012-success)
- `staged-files` — [T-0012](#t-0012-success)
- `task-tooling` — [T-0002](#t-0002-success)
- `uv` — [T-0006](#t-0006-success)
- `worktree` — [T-0002](#t-0002-success)

## devcontainer

### T-0006 (success)

- The `mcr.microsoft.com/devcontainers/base:ubuntu` image (Ubuntu 26.04) has only
  `python3-minimal`; `uv` selects it and builds fail on missing `tomllib`. Set
  `UV_PYTHON_PREFERENCE=only-managed`.
- A git worktree's `.git` file points to a host path, so git does not work in a container opened
  on a worktree; test devcontainers from a normal clone.
- `devcontainer up --experimental-lockfile` writes the lock file next to the config used, so run
  it once per configuration.

Tags: `devcontainer`, `uv`, `husky`, `docker`

Source: [`reports/T-0006.md`](tasks/reports/T-0006.md)

## docs

### T-0005 (success)

`scripts/gitflow.sh` cannot create `docs/` or `chore/` task branches, so a task branch of those
types needs a hand-written `git worktree add ... origin/develop`, and `node_modules` is not
symlinked into it. `npm ci` is needed before its first commit if the hooks are to run.

Tags: `docs`, `agent-rules`, `process`, `orchestrator`

Source: [`reports/T-0005.md`](tasks/reports/T-0005.md)

## git

### T-0007 (success)

- A fresh clone takes file modes from the git index, so a host checkout can pass ruff `EXE001` while a clone fails; verify mode-sensitive lint in a fresh clone.
- In this harness, a Bash call that combines git with a loop or `&&` chain can be refused for worktree-isolation checks; run git commands as plain separate calls.

Tags: `git`, `ruff`, `file-modes`, `devcontainer`

Source: [`reports/T-0007.md`](tasks/reports/T-0007.md)

## hooks

### T-0004 (success)

- A worktree shares `core.hooksPath` with the primary checkout, so hooks run from the primary checkout's `.husky/_` (files from the checked-out branch there), not the worktree's edited hooks.
- The sibling `../source-project` path does not resolve from inside `.claude/worktrees/<id>/`; use the absolute path `/path/to/source-project`.

Tags: `hooks`, `husky`, `gate`, `commit-lint`, `gitflow`

Source: [`reports/T-0004.md`](tasks/reports/T-0004.md)

### T-0008 (success)

- A rename is invisible to a `--diff-filter=ACMR` listing as anything but its new path. Use `--no-renames` and no filter when deciding on "what did this commit touch", as `pre-push` does.
- `git add -- <name>` treats `[`, `*` and `?` in a name as pathspec globs, so a test that stages `a[1].py` must use `:(literal)a[1].py`, and the hook must set `GIT_LITERAL_PATHSPECS=1`.
- Hook tests with stub `autofix.sh`/`gate.sh` cannot show problems inside the real scripts. Check unusual names against the real `staged_files` too.

Tags: `hooks`, `husky`, `pre-commit`, `git-pathspec`

Source: [`reports/T-0008.md`](tasks/reports/T-0008.md)

## report-validation

### T-0003 (success)

`housekeep.py` reads module-level `REPO_ROOT` and `_schema.REPORTS_DIR` (via `Task.report_path`); tests must patch both to point at a tmp repo.

Tags: `report-validation`, `housekeep`, `port`

Source: [`reports/T-0003.md`](tasks/reports/T-0003.md)

## scripts

### T-0012 (success)

- `git diff --cached --name-only` without `-z` C-quotes only names with a double quote, backslash, control character or non-ASCII byte. Spaces and single quotes pass through, so a test with only those names proves nothing about quoting.

Tags: `scripts`, `bash`, `git`, `nul-safe`, `staged-files`

Source: [`reports/T-0012.md`](tasks/reports/T-0012.md)

## task-tooling

### T-0002 (success)

- The agent worktree started on the initial scaffold commit, not `develop`; fast-forward the new branch to `develop` before reading task files.
- Worktree-isolated Bash refuses commands whose text mentions git alongside other constructs; run git commands as separate plain calls and put multi-line Python in a scratchpad file.

Tags: `task-tooling`, `git-publish`, `backlog`, `worktree`

Source: [`reports/T-0002.md`](tasks/reports/T-0002.md)
