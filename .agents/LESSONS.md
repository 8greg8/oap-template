<!-- GENERATED FILE — do not edit by hand.
     Regenerate with: python .agents/tasks/scripts/report.py harvest
     The reports in .agents/tasks/reports/ are the source of truth. -->

# Lessons Learned

Harvested from task reports. Read the tags relevant to your task before
starting — these are repo-specific traps that already cost someone time.

17 entr(ies) across 15 tag(s). Generated 2026-10-03.

## Tags

- [`backlog`](#backlog) — 1 entr(ies)
- [`commit-lint`](#commit-lint) — 1 entr(ies)
- [`devcontainer`](#devcontainer) — 2 entr(ies)
- [`docker`](#docker) — 1 entr(ies)
- [`file-modes`](#file-modes) — 1 entr(ies)
- [`gate`](#gate) — 1 entr(ies)
- [`git`](#git) — 1 entr(ies)
- [`git-publish`](#git-publish) — 1 entr(ies)
- [`gitflow`](#gitflow) — 1 entr(ies)
- [`hooks`](#hooks) — 1 entr(ies)
- [`husky`](#husky) — 2 entr(ies)
- [`ruff`](#ruff) — 1 entr(ies)
- [`task-tooling`](#task-tooling) — 1 entr(ies)
- [`uv`](#uv) — 1 entr(ies)
- [`worktree`](#worktree) — 1 entr(ies)

## backlog

### T-0002 (success)

- The agent worktree started on the initial scaffold commit, not `develop`; fast-forward the new branch to `develop` before reading task files.
- Worktree-isolated Bash refuses commands whose text mentions git alongside other constructs; run git commands as separate plain calls and put multi-line Python in a scratchpad file.

Source: [`reports/T-0002.md`](tasks/reports/T-0002.md)

## commit-lint

### T-0004 (success)

- A worktree shares `core.hooksPath` with the primary checkout, so hooks run from the primary checkout's `.husky/_` (files from the checked-out branch there), not the worktree's edited hooks.
- The sibling `../source-project` path does not resolve from inside `.claude/worktrees/<id>/`; use the absolute path `/path/to/source-project`.

Source: [`reports/T-0004.md`](tasks/reports/T-0004.md)

## devcontainer

### T-0006 (success)

- The `mcr.microsoft.com/devcontainers/base:ubuntu` image (Ubuntu 26.04) has only
  `python3-minimal`; `uv` selects it and builds fail on missing `tomllib`. Set
  `UV_PYTHON_PREFERENCE=only-managed`.
- A git worktree's `.git` file points to a host path, so git does not work in a container opened
  on a worktree; test devcontainers from a normal clone.
- `devcontainer up --experimental-lockfile` writes the lock file next to the config used, so run
  it once per configuration.

Source: [`reports/T-0006.md`](tasks/reports/T-0006.md)

### T-0007 (success)

- A fresh clone takes file modes from the git index, so a host checkout can pass ruff `EXE001` while a clone fails; verify mode-sensitive lint in a fresh clone.
- In this harness, a Bash call that combines git with a loop or `&&` chain can be refused for worktree-isolation checks; run git commands as plain separate calls.

Source: [`reports/T-0007.md`](tasks/reports/T-0007.md)

## docker

### T-0006 (success)

- The `mcr.microsoft.com/devcontainers/base:ubuntu` image (Ubuntu 26.04) has only
  `python3-minimal`; `uv` selects it and builds fail on missing `tomllib`. Set
  `UV_PYTHON_PREFERENCE=only-managed`.
- A git worktree's `.git` file points to a host path, so git does not work in a container opened
  on a worktree; test devcontainers from a normal clone.
- `devcontainer up --experimental-lockfile` writes the lock file next to the config used, so run
  it once per configuration.

Source: [`reports/T-0006.md`](tasks/reports/T-0006.md)

## file-modes

### T-0007 (success)

- A fresh clone takes file modes from the git index, so a host checkout can pass ruff `EXE001` while a clone fails; verify mode-sensitive lint in a fresh clone.
- In this harness, a Bash call that combines git with a loop or `&&` chain can be refused for worktree-isolation checks; run git commands as plain separate calls.

Source: [`reports/T-0007.md`](tasks/reports/T-0007.md)

## gate

### T-0004 (success)

- A worktree shares `core.hooksPath` with the primary checkout, so hooks run from the primary checkout's `.husky/_` (files from the checked-out branch there), not the worktree's edited hooks.
- The sibling `../source-project` path does not resolve from inside `.claude/worktrees/<id>/`; use the absolute path `/path/to/source-project`.

Source: [`reports/T-0004.md`](tasks/reports/T-0004.md)

## git

### T-0007 (success)

- A fresh clone takes file modes from the git index, so a host checkout can pass ruff `EXE001` while a clone fails; verify mode-sensitive lint in a fresh clone.
- In this harness, a Bash call that combines git with a loop or `&&` chain can be refused for worktree-isolation checks; run git commands as plain separate calls.

Source: [`reports/T-0007.md`](tasks/reports/T-0007.md)

## git-publish

### T-0002 (success)

- The agent worktree started on the initial scaffold commit, not `develop`; fast-forward the new branch to `develop` before reading task files.
- Worktree-isolated Bash refuses commands whose text mentions git alongside other constructs; run git commands as separate plain calls and put multi-line Python in a scratchpad file.

Source: [`reports/T-0002.md`](tasks/reports/T-0002.md)

## gitflow

### T-0004 (success)

- A worktree shares `core.hooksPath` with the primary checkout, so hooks run from the primary checkout's `.husky/_` (files from the checked-out branch there), not the worktree's edited hooks.
- The sibling `../source-project` path does not resolve from inside `.claude/worktrees/<id>/`; use the absolute path `/path/to/source-project`.

Source: [`reports/T-0004.md`](tasks/reports/T-0004.md)

## hooks

### T-0004 (success)

- A worktree shares `core.hooksPath` with the primary checkout, so hooks run from the primary checkout's `.husky/_` (files from the checked-out branch there), not the worktree's edited hooks.
- The sibling `../source-project` path does not resolve from inside `.claude/worktrees/<id>/`; use the absolute path `/path/to/source-project`.

Source: [`reports/T-0004.md`](tasks/reports/T-0004.md)

## husky

### T-0004 (success)

- A worktree shares `core.hooksPath` with the primary checkout, so hooks run from the primary checkout's `.husky/_` (files from the checked-out branch there), not the worktree's edited hooks.
- The sibling `../source-project` path does not resolve from inside `.claude/worktrees/<id>/`; use the absolute path `/path/to/source-project`.

Source: [`reports/T-0004.md`](tasks/reports/T-0004.md)

### T-0006 (success)

- The `mcr.microsoft.com/devcontainers/base:ubuntu` image (Ubuntu 26.04) has only
  `python3-minimal`; `uv` selects it and builds fail on missing `tomllib`. Set
  `UV_PYTHON_PREFERENCE=only-managed`.
- A git worktree's `.git` file points to a host path, so git does not work in a container opened
  on a worktree; test devcontainers from a normal clone.
- `devcontainer up --experimental-lockfile` writes the lock file next to the config used, so run
  it once per configuration.

Source: [`reports/T-0006.md`](tasks/reports/T-0006.md)

## ruff

### T-0007 (success)

- A fresh clone takes file modes from the git index, so a host checkout can pass ruff `EXE001` while a clone fails; verify mode-sensitive lint in a fresh clone.
- In this harness, a Bash call that combines git with a loop or `&&` chain can be refused for worktree-isolation checks; run git commands as plain separate calls.

Source: [`reports/T-0007.md`](tasks/reports/T-0007.md)

## task-tooling

### T-0002 (success)

- The agent worktree started on the initial scaffold commit, not `develop`; fast-forward the new branch to `develop` before reading task files.
- Worktree-isolated Bash refuses commands whose text mentions git alongside other constructs; run git commands as separate plain calls and put multi-line Python in a scratchpad file.

Source: [`reports/T-0002.md`](tasks/reports/T-0002.md)

## uv

### T-0006 (success)

- The `mcr.microsoft.com/devcontainers/base:ubuntu` image (Ubuntu 26.04) has only
  `python3-minimal`; `uv` selects it and builds fail on missing `tomllib`. Set
  `UV_PYTHON_PREFERENCE=only-managed`.
- A git worktree's `.git` file points to a host path, so git does not work in a container opened
  on a worktree; test devcontainers from a normal clone.
- `devcontainer up --experimental-lockfile` writes the lock file next to the config used, so run
  it once per configuration.

Source: [`reports/T-0006.md`](tasks/reports/T-0006.md)

## worktree

### T-0002 (success)

- The agent worktree started on the initial scaffold commit, not `develop`; fast-forward the new branch to `develop` before reading task files.
- Worktree-isolated Bash refuses commands whose text mentions git alongside other constructs; run git commands as separate plain calls and put multi-line Python in a scratchpad file.

Source: [`reports/T-0002.md`](tasks/reports/T-0002.md)
