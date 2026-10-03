<!-- GENERATED FILE — do not edit by hand.
     Regenerate with: python .agents/tasks/scripts/report.py harvest
     The reports in .agents/tasks/reports/ are the source of truth. -->

# Lessons Learned

Harvested from task reports. Read the tags relevant to your task before
starting — these are repo-specific traps that already cost someone time.

8 entr(ies) across 8 tag(s). Generated 2026-10-03.

## Tags

- [`backlog`](#backlog) — 1 entr(ies)
- [`devcontainer`](#devcontainer) — 1 entr(ies)
- [`file-modes`](#file-modes) — 1 entr(ies)
- [`git`](#git) — 1 entr(ies)
- [`git-publish`](#git-publish) — 1 entr(ies)
- [`ruff`](#ruff) — 1 entr(ies)
- [`task-tooling`](#task-tooling) — 1 entr(ies)
- [`worktree`](#worktree) — 1 entr(ies)

## backlog

### T-0002 (success)

- The agent worktree started on the initial scaffold commit, not `develop`; fast-forward the new branch to `develop` before reading task files.
- Worktree-isolated Bash refuses commands whose text mentions git alongside other constructs; run git commands as separate plain calls and put multi-line Python in a scratchpad file.

Source: [`reports/T-0002.md`](tasks/reports/T-0002.md)

## devcontainer

### T-0007 (success)

- A fresh clone takes file modes from the git index, so a host checkout can pass ruff `EXE001` while a clone fails; verify mode-sensitive lint in a fresh clone.
- In this harness, a Bash call that combines git with a loop or `&&` chain can be refused for worktree-isolation checks; run git commands as plain separate calls.

Source: [`reports/T-0007.md`](tasks/reports/T-0007.md)

## file-modes

### T-0007 (success)

- A fresh clone takes file modes from the git index, so a host checkout can pass ruff `EXE001` while a clone fails; verify mode-sensitive lint in a fresh clone.
- In this harness, a Bash call that combines git with a loop or `&&` chain can be refused for worktree-isolation checks; run git commands as plain separate calls.

Source: [`reports/T-0007.md`](tasks/reports/T-0007.md)

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

## worktree

### T-0002 (success)

- The agent worktree started on the initial scaffold commit, not `develop`; fast-forward the new branch to `develop` before reading task files.
- Worktree-isolated Bash refuses commands whose text mentions git alongside other constructs; run git commands as separate plain calls and put multi-line Python in a scratchpad file.

Source: [`reports/T-0002.md`](tasks/reports/T-0002.md)
