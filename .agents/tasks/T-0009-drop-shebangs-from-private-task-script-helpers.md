---
id: T-0009
title: Drop shebangs from private task script helpers
status: done
type: chore
priority: low
depends_on: []
touches: [.agents/tasks/scripts, tests/test_task_scripts.py]
created: 2026-10-03
report: reports/T-0009.md
---

# T-0009 — Drop shebangs from private task script helpers

## Goal

The four private helper modules in `.agents/tasks/scripts/` (`_frontmatter.py`, `_git_publish.py`, `_ids.py`, `_schema.py`) have no shebang and are mode 100644; only the four CLI entry scripts keep a shebang and mode 100755.

## Context / current verified state

- After T-0007 all eight `.py` files in `.agents/tasks/scripts/` are mode 100755 and all start with `#!` (T-0007's executor and verifier, 2026-10-03). The underscore-prefixed helpers are only imported, never run.
- T-0006's container gate flagged 7 EXE001 errors versus 8 files; the difference was never explained. Do not try to explain it here.
- Re-check which files have a shebang before editing and report any discrepancy.

## Scope

- Remove the shebang line from each of the four private helpers and set their git mode to 100644 (`git update-index --chmod=-x`).
- Keep `task.py`, `backlog.py`, `report.py` and `housekeep.py` as they are.
- Check that `tests/test_task_scripts.py::test_shebang_task_scripts_are_executable_in_git_index` (which requires shebang-less files to be 100644) passes unchanged.

## Non-goals

- Do not change any other content of these files.
- Do not touch `report.py` or `housekeep.py` logic; T-0003 owns their content. If T-0003 is not merged yet, expect no conflict because only the shebang line and mode change.
- Do not edit ruff configuration or `pyproject.toml`.

## Files to inspect

- `.agents/tasks/scripts/_frontmatter.py`, `_git_publish.py`, `_ids.py`, `_schema.py`
- `tests/test_task_scripts.py`

## Required behavior

The four helpers import and behave exactly as before; `python .agents/tasks/scripts/task.py validate` still works.

## Tests required

Run `uv run pytest tests/test_task_scripts.py -v` and `scripts/gate.sh`. Confirm `ruff check` is clean from a fresh clone of the branch.

## Documentation required

None needed; no documented behavior changes.

## Acceptance criteria

- [ ] The four helpers have no shebang and are 100644 in `git ls-files -s`.
- [ ] The four CLI scripts keep a shebang and 100755.
- [ ] The existing mode test passes unchanged.
- [ ] `scripts/gate.sh` passes.
- [ ] The diff contains only shebang-line removals and mode changes, plus the report.

## Workflow

- Read `AGENTS.md` (and `CLAUDE.md`, if present) first.
- Create a worktree and branch from `develop` as `chore/T-0009-drop-shebangs-from-private-task-script-helpers`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0009.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request.
- Do not edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state.

## Report

Fill in `.agents/tasks/reports/T-0009.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0009
```
