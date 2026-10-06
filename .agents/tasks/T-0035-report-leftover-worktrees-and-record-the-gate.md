---
id: T-0035
title: Report leftover worktrees and record the gate in the verify line
status: done
type: feat
priority: medium
depends_on: []
touches: [.agents/tasks/scripts/housekeep.py, .agents/tasks/scripts/report.py, .agents/tasks/templates/report.md, tests/test_task_scripts.py, tests/test_report_scripts.py, changelog.d/T-0035.added.md]
created: 2026-10-05
report: reports/T-0035.md
---

# T-0035 — Report leftover worktrees and record the gate in the verify line

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

`housekeep.py` reports leftover worktrees and local branches of finished tasks, and the report's
verify line can name the gate record the verifier wrote.

## Context / current verified state

- Plan: `.agents/plans/2026-10-05-verification-cost.md`, accepted by the owner on 2026-10-05 (V1 to V9 as recommended). Its § Design is the
  source of truth and its § Approvals is the owner's written approval for this task's "Ask first"
  and breaking items; cite it in the report. Where this file and the plan differ, stop and report.
- Sync first (`git pull --ff-only origin develop`) and re-check every cited line against
  `develop`; report any discrepancy.
- `.agents/tasks/scripts/housekeep.py:396` `check_worktrees()` flags worktrees of merged
  branches and `develop`/`main` checked out in a secondary worktree. Its tests are in
  `tests/test_report_scripts.py`.
- `.agents/tasks/scripts/report.py:65-71` (`VERIFY_LINE_RE`, `VERIFY_COMMIT_RE`) and
  `.agents/tasks/templates/report.md` define the verify line `passed (commit <hash>; ...)`.

## Scope

- Extend `check_worktrees()`: also report worktrees and local branches whose task is `done` or
  `abandoned`, including unmerged ones and branches with no worktree. Keep the documented exit
  status rules; if a new finding changes the exit status of `housekeep.py worktrees` or `all`,
  say so in the report as a CLI change.
- Verify line: `passed (commit <hash>; gate <record-key>; <counts>)` per the plan's § "The verify
  line". `report.py validate` accepts it and keeps accepting the existing form for old reports.
  The template documents it.
- Tests in `tests/test_report_scripts.py` (and `tests/test_task_scripts.py` if the task scripts'
  shared helpers change).
- `changelog.d/T-0035.added.md`. The behavior commit is marked breaking (`feat(tasks)!:`), as the
  plan's § Approvals lists the verify-line format as breaking. Its footer names the new verify-line
  form and the new `housekeep.py worktrees` findings, which make `worktrees` and `all` exit 1 where
  they exited 0. Old reports keep validating.
- Key format (from T-0033): 40 or 64 lowercase hex characters. The verify line cites it as
  `gate <key>` with at least 12 characters. `report.py validate` rejects a `gate` token that does
  not match `\bgate [0-9a-f]{12,64}\b`, and does not require one.
- The fragment follows `changelog.d/README.md`, section "Before the first release": category
  `added`, and no "Breaking:", "no longer", "used to" or "now".
- The task's fragment holds only bullet and indented continuation lines and no placeholder words.

## Non-goals

- Do not delete or remove anything; report only.
- Do not change the task schema or `task.py`.
- Do not change process documents (T-0036).
- No new or edited tracked file contains `proj_template`, `proj-template`, `oap-template`, `8greg8`
  or the owner's email.

## Files to inspect

- `.agents/plans/2026-10-05-verification-cost.md`
- Every file in `touches`

## Required behavior

`housekeep.py worktrees` lists every leftover the Scope names; every report that passes
`report.py validate` at the branch's merge base still passes (T-0002, T-0004, T-0006 and T-0007
already fail and are out of scope); a report with the new verify line validates.

## Tests required

- `uv run pytest tests/test_report_scripts.py tests/test_task_scripts.py -v`.
- `python .agents/tasks/scripts/report.py validate` lists the same findings at the merge base and
  at the branch head.
- `scripts/gate.sh`.

## Documentation required

`.agents/tasks/templates/report.md`, as in Scope.

## Acceptance criteria

- [ ] `housekeep.py worktrees` reports worktrees and branches of `done` or `abandoned` tasks, merged or not, with or without a worktree.
- [ ] The new verify-line form validates, and `report.py validate` lists the same findings at the merge base and at the branch head.
- [ ] The report template documents the new form.
- [ ] Any exit-status change of `housekeep.py` is stated in the report.
- [ ] `changelog.d/T-0035.added.md` exists and `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 on the pushed branch.
- [ ] `uv run pytest tests/test_report_scripts.py tests/test_task_scripts.py -v` passes.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `feat/T-0035-report-leftover-worktrees-and-record-the-gate`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0035.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0035.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0035
```
