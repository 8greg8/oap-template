---
id: T-0002
title: Port git-atomic task filing and backlog fixes
status: in_progress
type: fix
priority: high
depends_on: []
touches: [.agents/tasks/scripts/_git_publish.py, .agents/tasks/scripts/_ids.py, .agents/tasks/scripts/_schema.py, .agents/tasks/scripts/task.py, .agents/tasks/scripts/backlog.py, tests/test_task_scripts.py]
created: 2026-10-03
report: reports/T-0002.md
---

# T-0002 — Port git-atomic task filing and backlog fixes

## Goal

`task.py new` files a task directly on `develop` and pushes it, and concurrent filings from
several checkouts never produce a duplicate ID. `backlog.py ready` never offers a `blocked`
task, or a task whose `touches` overlap a task already `in_progress` or in `review`.

## Context / current verified state

- Plan: `.agents/plans/2026-10-03-workflow-sync.md` §1.3, §3.3, Appendix A, B.1–B.5. Source: `source-project` at `87f9edf` (sibling checkout `../source-project`).
- The template's `_ids.py`, `_schema.py`, `backlog.py` and `task.py` are older versions of
  source-project's: every template-only line in a diff is an earlier form of a source-project line (verified
  2026-10-03).
- `.agents/tasks/scripts/_git_publish.py` does not exist here.
- `_schema.INACTIVE_STATUSES` lacks `blocked`; `backlog.parallel_batch` ignores tasks in
  flight; `task.py validate` accepts duplicate IDs.
- There are no tests for the task tooling; `tests/` holds two sample tests.

## Scope

- Copy `_git_publish.py`, `_ids.py`, `_schema.py`, `backlog.py` and `task.py` from source-project with
  the commands in plan Appendix A.
- Apply plan A.2: add `INTEGRATION_BRANCH = "develop"` to `_schema.py` (B.1) and use it for
  every `develop` literal in `_git_publish.py`; rename `_sync_develop` to
  `_sync_integration_branch`; remove the comment citing source-project's `T-0092`.
- Truncate the slug in `_git_publish.py`'s commit message so the header is at most 100
  characters.
- Port the tests listed in plan A.3 for these files into `tests/test_task_scripts.py`.

## Non-goals

- Do not edit `report.py`, `housekeep.py`, either template, or any doc; T-0003 and T-0005
  own them.
- Do not edit `.husky/` or `scripts/`; T-0004 owns them.
- Do not add behavior source-project lacks, except the slug truncation above.
- Do not port source-project tests for `report.py`, harvest or the source-project product (`test_task_new.py`,
  `test_task_status.py`, `test_backlog_build.py`).

## Files to inspect

- `../source-project/.agents/tasks/scripts/{_git_publish,_ids,_schema,backlog,task}.py`
- `../source-project/tests/test_task_scripts.py`
- The same five files here, before copying.

## Required behavior

- `task.py new` refuses to run from a secondary worktree or off `develop`; otherwise it
  syncs to `origin/develop`, allocates, commits `chore(tasks): file <ID> <slug>` and pushes.
- On a rejected push it discards its own unpushed commit, resyncs and reallocates, at most
  5 times.
- `--no-publish` writes the file only.
- Git subprocesses ignore `GIT_DIR`, `GIT_WORK_TREE` and related variables inherited from
  hooks.
- `task.py validate` rejects two non-abandoned tasks with one ID; `task.py list` hides
  abandoned duplicates.

## Tests required

Port from `source-project:tests/test_task_scripts.py`: git-environment, `create_task`, `publish_task`,
CLI `new`, duplicate-ID, backlog report-link, blocked-not-ready and `parallel_batch` tests.
Publish tests use a bare remote in `tmp_path`. Add a test for slug truncation. Run
`scripts/gate.sh`.

## Documentation required

None in this task; T-0005 documents the filing flow.

## Acceptance criteria

- [ ] Two concurrent `task.py new` runs against one bare remote produce two distinct IDs and no conflict.
- [ ] `task.py new` fails fast outside the primary checkout or off `develop`.
- [ ] `--no-publish` writes locally and touches no git state.
- [ ] `backlog.py ready` omits `blocked` tasks; `--parallel` omits candidates overlapping an `in_progress` or `review` task.
- [ ] `task.py validate` rejects a non-abandoned duplicate ID.
- [ ] No `develop` literal remains in `_git_publish.py` outside `INTEGRATION_BRANCH`.
- [ ] `scripts/gate.sh` passes.

## Workflow

- Read `AGENTS.md` (and `CLAUDE.md`, if present) first.
- Create a worktree and branch from `develop` as `fix/T-0002-port-git-atomic-task-filing-and-backlog-fixes`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0002.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request.
- Do not edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state.

## Report

Fill in `.agents/tasks/reports/T-0002.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0002
```
