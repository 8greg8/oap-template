---
id: T-0003
title: Port report validation, harvest and housekeep checks
status: done
type: fix
priority: high
depends_on: [T-0002]
touches: [.agents/tasks/scripts/report.py, .agents/tasks/scripts/housekeep.py, .agents/tasks/templates/report.md, tests/test_report_scripts.py]
created: 2026-10-03
report: reports/T-0003.md
---

# T-0003 — Port report validation, harvest and housekeep checks

## Goal

`report.py validate` rejects a `done` task whose report lacks a passed independent verify
naming a commit, mentions the verify in `## Summary`, or claims `touches` compliance that
the merge commit contradicts. `housekeep.py` reports stale worktrees, and `report.py
harvest` lists each lesson once.

## Context / current verified state

- Plan: `.agents/plans/2026-10-03-workflow-sync.md` §1.3, §1.4, §3.3, Appendix A, B.3, B.6, B.7. Source: `source-project` at `87f9edf` (sibling checkout `../source-project`).
- The template's `report.py` and `housekeep.py` are older versions of source-project's (verified
  2026-10-03).
- source-project exempts older tasks with `STRICT_AFTER_ID = 170` and `COMMIT_REQUIRED_AFTER_ID = 202`;
  this template has no history to exempt.
- source-project has no tests for `housekeep.py`.
- Depends on T-0002 for `_schema.INTEGRATION_BRANCH`.

## Scope

- Copy `report.py`, `housekeep.py` and `templates/report.md` from source-project (plan Appendix A).
- Apply plan A.2:
  - delete `STRICT_AFTER_ID`, `COMMIT_REQUIRED_AFTER_ID`, both comparisons and
    `_numeric_id`, so every `done` task is checked (B.3);
  - import `INTEGRATION_BRANCH` from `_schema` in both scripts, including
    `merge_commit_for`'s subject;
  - remove the comments citing source-project's `T-0054` and `T-0170`;
  - drop "(ID above T-0170)" from `report.md`.
- Port the report and harvest tests from `source-project:tests/test_task_scripts.py` into
  `tests/test_report_scripts.py` (plan A.3), copying the helpers they need.
- Write tests for `housekeep.py touches`, `drift` and `worktrees`.

## Non-goals

- Do not gate `task.py set-status` on reports; T-0001 owns that.
- Do not edit `task.py`, `backlog.py`, `_schema.py`, `_ids.py` or `_git_publish.py`.
- Do not edit docs other than `templates/report.md`; T-0005 owns them.
- Do not port source-project tests that check source-project's own report history.

## Files to inspect

- `../source-project/.agents/tasks/scripts/{report,housekeep}.py`
- `../source-project/.agents/tasks/templates/report.md`
- `../source-project/tests/test_task_scripts.py` (report, harvest and verify tests)

## Required behavior

- A `done` report needs `Independent verify agent (fresh context) :: passed (commit <hash>; …)`
  in `## Tests run`.
- `## Summary` must not call the verify pending, not run or excepted.
- With the touches box ticked, the diff of the task's `chore(merge): merge task NNNN into
  develop` commit against its first parent must stay inside `touches`, the task's report
  and the task file. With no merge commit yet, the check is skipped.
- `housekeep.py touches` treats the task's own report as in scope.
- `housekeep.py drift` looks on the task branch before calling a report missing.
- `housekeep.py worktrees` flags merged, unremoved worktrees and `develop`/`main` in a
  secondary worktree; `all` runs four checks.
- `report.py harvest` files each lesson under its first tag and builds a tag index.

## Tests required

`tests/test_report_scripts.py` with the ported report and harvest tests (threshold tests
made unconditional) and new `housekeep.py` tests using a git repository in `tmp_path`. Run
`scripts/gate.sh`.

## Documentation required

`templates/report.md` as copied. `.agents/README.md` is updated in T-0005.

## Acceptance criteria

- [ ] A `done` report without a `passed (commit <hash>; …)` verify line fails `report.py validate`.
- [ ] A verify mention in `## Summary` fails validation.
- [ ] A merged diff outside `touches` fails validation; the task's own report does not.
- [ ] `housekeep.py worktrees` reports a merged, unremoved worktree and `develop`/`main` in a secondary worktree.
- [ ] `housekeep.py touches` does not report the task's own report file; `drift` finds a report that exists only on the task branch.
- [ ] `report.py harvest` lists each lesson once.
- [ ] No `STRICT_AFTER_ID`, `COMMIT_REQUIRED_AFTER_ID` or source-project task ID remains in the two scripts.
- [ ] `scripts/gate.sh` passes.

## Workflow

- Read `AGENTS.md` (and `CLAUDE.md`, if present) first.
- Create a worktree and branch from `develop` as `fix/T-0003-port-report-validation-harvest-and-housekeep`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0003.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request.
- Do not edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state.

## Report

Fill in `.agents/tasks/reports/T-0003.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0003
```
