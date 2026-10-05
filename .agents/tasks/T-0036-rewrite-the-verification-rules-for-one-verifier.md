---
id: T-0036
title: Rewrite the verification rules for one verifier per change
status: open
type: docs
priority: medium
depends_on: [T-0033, T-0034, T-0035]
touches: [CLAUDE.md, CONTRIBUTING.md, .agents/README.md, .agents/tasks/templates/task.md, PYTHON_CONVENTIONS.md, README.md, DEV_TOOLING_SPEC.md, scripts/README.md, changelog.d/T-0036.added.md]
created: 2026-10-05
report: reports/T-0036.md
---

# T-0036 — Rewrite the verification rules for one verifier per change

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

The process documents state one independent verifier per change, at branch level, whose own full
gate run is canonical, and match the code from T-0033 to T-0035.

## Context / current verified state

- Plan: `.agents/plans/2026-10-05-verification-cost.md`, accepted by the owner on 2026-10-05 (V1 to V9 as recommended). Its § Design is the
  source of truth and its § Approvals is the owner's written approval for this task's "Ask first"
  and breaking items; cite it in the report. Where this file and the plan differ, stop and report.
- Sync first (`git pull --ff-only origin develop`) and re-check every cited line against
  `develop`; report any discrepancy.
- Depends on T-0033, T-0034 and T-0035; document the merged code and report any difference from
  the plan.
- `CLAUDE.md` § "Verification is not optional" points to the per-commit loop in `CONTRIBUTING.md`
  § "Agent verify/resolve workflow" (which opens "Before any commit is written…"); the section "Verify, resolve, merge" in
  `.agents/README.md` has the branch-level verifier and the post-merge gate rerun.
  `PYTHON_CONVENTIONS.md` and `README.md` also describe the per-commit verifier or the full
  pre-push gate.
- `scripts/README.md` is under `scripts/` and is treated as an "Ask first" item (T-0026 precedent).
  The plan assigns it to this task, and the owner's acceptance ("proceed with the steps") covers
  the plan's tasks. Cite both in the report.

## Scope

- `CLAUDE.md` § "Verification is not optional" and § Merge authority: V1, V2, V7, V9. Keep
  `## Working unit: the task` as the first `##` heading.
- `CONTRIBUTING.md` § "Agent verify/resolve workflow": implement, iterate with `--fast` and
  targeted tests, commit freely; one independent verify of the finished branch; resolve; merge.
  The hooks section: records, `--if-needed`, task-branch `--fast`, slow-test selection.
- `.agents/README.md`, section "Verify, resolve, merge": the verifier works in a detached worktree of the
  orchestrator's checkout, always runs the full gate itself, does the judgment checks, and writes
  the new verify line; fix rounds per V7; one verifier per task per round in the foreground (V8);
  the post-merge check uses `--if-needed`.
- `.agents/tasks/templates/task.md`, `PYTHON_CONVENTIONS.md`, `README.md`, `DEV_TOOLING_SPEC.md`,
  `scripts/README.md`: remove the per-commit verifier and describe the new flow.
- `changelog.d/T-0036.added.md`. The `CLAUDE.md` commit is `docs(claude)!:` with a footer naming
  the new verification rule.
- The task's fragment holds only bullet and indented continuation lines and no placeholder words.
- `.agents/README.md`, Housekeeping, the `worktrees` bullet: the findings T-0035 added and their
  exit status.
- `CONTRIBUTING.md`: gate records are written only by `scripts/gate.sh`; never create, copy or edit
  them by hand.
- The fragment follows `changelog.d/README.md`, section "Before the first release": category
  `added`, and no "Breaking:", "no longer", "used to" or "now".

## Non-goals

- Do not change any script, hook, test or `init_project.py`.
- Do not change the "Ask first" list. Change other `CLAUDE.md` sections only to fix references to
  the verify loop (the Autonomy bullets that describe it and the Chatter section's step reference).
- Do not change the task or report schema.
- No new or edited tracked file contains `proj_template`, `proj-template`, `oap-template`, `8greg8`
  or the owner's email.

## Files to inspect

- `.agents/plans/2026-10-05-verification-cost.md`
- Every file in `touches`; the merged `scripts/gate.sh`, `scripts/config/gate.sh`, `.husky/pre-push`,
  `.agents/tasks/scripts/housekeep.py`, `.agents/tasks/scripts/report.py`

## Required behavior

An agent following only the documents spawns no verifier per commit, runs exactly one
independent verifier per change, and every documented gate behavior matches the code.

## Tests required

- `scripts/gate.sh` (the init test checks the `CLAUDE.md` anchor).
- `python .agents/tasks/scripts/task.py validate`.

## Documentation required

The files in `touches`, as in Scope.

## Acceptance criteria

- [ ] No document requires an independent verifier per commit.
- [ ] `CLAUDE.md` and `.agents/README.md` require exactly one independent verifier per change, running the full gate itself.
- [ ] Fix rounds, foreground verifiers and bookkeeping commits are described as the plan states.
- [ ] Every documented gate and hook behavior matches the merged code.
- [ ] `CLAUDE.md`'s first `##` heading is unchanged.
- [ ] `changelog.d/T-0036.added.md` exists and `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 on the pushed branch.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `docs/T-0036-rewrite-the-verification-rules-for-one-verifier`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0036.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0036.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0036
```
