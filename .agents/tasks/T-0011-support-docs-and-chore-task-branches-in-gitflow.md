---
id: T-0011
title: Support docs and chore task branches in gitflow and fix housekeep worktrees
status: open
type: fix
priority: low
depends_on: []
touches: [scripts/gitflow.sh, .agents/tasks/scripts/housekeep.py, tests/test_report_scripts.py, tests/test_hooks.py]
created: 2026-10-03
report: reports/T-0011.md
---

# T-0011 — Support docs and chore task branches in gitflow and fix housekeep worktrees

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

`scripts/gitflow.sh` can start and finish `docs/`, `chore/` and `fix/` task branches, not only `feat/`, `bugfix/` and `hotfix/`, and `housekeep.py worktrees` no longer calls a branch with no commits merged.

## Context / current verified state

- T-0005's independent verify found `gitflow.sh` derives the branch from the kind (feat/bugfix/hotfix), so it cannot start or finish a `docs/` task branch. `CONTRIBUTING.md` (Worktrees for agents) documents a hand-written `git worktree add` fallback and says nothing else changes about finish, which is misleading.
- `merge_message` in `scripts/lib/common.sh` already handles any `<type>/T-NNNN-` branch name.
- `housekeep.py`'s `is_branch_merged` is ancestor-based, so a branch tip equal to `develop` counts as merged; T-0005's own worktree was flagged before its first commit.
- Re-check both against current code and report any discrepancy.

## Scope

- `scripts/gitflow.sh`: add task-branch kinds (`docs`, `chore`, `fix`) to start and finish, using `merge_message`, without changing the existing three kinds.
- `housekeep.py worktrees`: treat a branch with no commits ahead of `develop` as not merged.
- Tests: a gitflow test using a scratch repo and bare remote, and a `housekeep` test for the empty-branch case, each failing before the change.

## Non-goals

- Do not change hooks, `scripts/gate.sh`, `scripts/autofix.sh`, `scripts/commit_lint.py`, `scripts/release.py`, CI or `pyproject.toml`.
- Do not change merge-commit message formats.
- Do not edit docs; if `CONTRIBUTING.md` needs updating, say so in the report for a separate docs task.
- This task edits `scripts/gitflow.sh`, which is human-gated under CLAUDE.md: the executor must not start without the owner's explicit approval recorded in the dispatch instruction, and must stop and ask if the change grows beyond branch-kind handling.

## Files to inspect

- `scripts/gitflow.sh`, `scripts/lib/common.sh`
- `.agents/tasks/scripts/housekeep.py`
- `tests/test_report_scripts.py`, `tests/test_hooks.py`

## Required behavior

`gitflow.sh <kind> start <name>` and `finish` work for the new kinds with the same worktree, symlink and hook behavior as `feat`. An empty branch is not reported merged. Scripts run under bash 3.2.

## Tests required

New gitflow and housekeep tests, each shown failing before and passing after. Run `scripts/gate.sh`. If Docker is available, also run the new paths under `docker run bash:3.2`.

## Documentation required

None in this task; report the needed `CONTRIBUTING.md` change.

## Acceptance criteria

- [ ] `gitflow.sh` starts and finishes a `docs/T-NNNN-x` branch end to end in a scratch repo.
- [ ] Existing `feat`, `bugfix` and `hotfix` behavior is unchanged.
- [ ] A branch with no commits ahead of `develop` is not reported merged by `housekeep.py worktrees`.
- [ ] New tests failed before the change and pass after.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches` plus the report.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `fix/T-0011-support-docs-and-chore-task-branches-in-gitflow`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0011.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0011.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0011
```
