---
id: T-0007
title: Make task scripts executable
status: done
type: fix
priority: high
depends_on: []
touches: [.agents/tasks/scripts, tests/test_task_scripts.py]
created: 2026-10-03
report: reports/T-0007.md
---

# T-0007 — Make task scripts executable

## Goal

Every Python file under `.agents/tasks/scripts/` that starts with a shebang is committed with the executable bit (git mode 100755), so `ruff check` reports no `EXE001` there on any checkout, including a fresh clone in the devcontainer.

## Context / current verified state

- `git ls-files -s .agents/tasks/scripts/*.py` shows all eight files as mode 100644 on `develop` (verified 2026-10-03).
- T-0006's executor ran `scripts/gate.sh` in a fresh devcontainer clone and got 7 `EXE001` errors from these files; the same gate passes on the host checkout. Re-check which files carry a shebang before changing anything, and report any discrepancy.

## Scope

- Set the executable bit (`git update-index --chmod=+x` plus `chmod +x`) on each shebang-bearing `.py` file in `.agents/tasks/scripts/`.
- Add a test in `tests/test_task_scripts.py` asserting every file there that starts with `#!` is executable in the git index (`git ls-files -s`).

## Non-goals

- Do not change file contents other than mode.
- Do not add or remove ruff rules or edit `pyproject.toml`.
- Do not touch `.devcontainer/`, `.husky/`, `scripts/` or any task file.
- Do not make non-shebang helper modules executable.

## Files to inspect

- `.agents/tasks/scripts/*.py`
- `tests/test_task_scripts.py`

## Required behavior

Shebang-bearing scripts are mode 100755 in the git index; files without a shebang stay 100644.

## Tests required

Add the index-mode test above; confirm it fails before the chmod and passes after. Run `scripts/gate.sh`, and `uv run ruff check --select EXE001 .agents/tasks/scripts` from a fresh clone of the branch.

## Documentation required

None needed; this changes file modes only.

## Acceptance criteria

- [ ] All shebang-bearing files in `.agents/tasks/scripts/` are 100755 in `git ls-files -s`.
- [ ] The new mode test failed before the change and passes after.
- [ ] `ruff check` from a fresh clone of the branch reports no `EXE001`.
- [ ] `scripts/gate.sh` passes.
- [ ] The diff contains only mode changes plus the test and the report.

## Workflow

- Read `AGENTS.md` (and `CLAUDE.md`, if present) first.
- Create a worktree and branch from `develop` as `fix/T-0007-make-task-scripts-executable`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0007.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request.
- Do not edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state.

## Report

Fill in `.agents/tasks/reports/T-0007.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0007
```
