---
id: T-0004
title: Reconcile hooks and dev tooling with the merge and push rules
status: open
type: feat
priority: high
depends_on: []
touches: [.husky, scripts, DEV_TOOLING_SPEC.md, tests/test_hooks.py, tests/test_commit_lint.py]
created: 2026-10-03
report: reports/T-0004.md
---

# T-0004 — Reconcile hooks and dev tooling with the merge and push rules

## Goal

Hooks and `scripts/` follow the new commit and push rules. `pre-commit` checks only staged
files without tests. Commits and pushes that touch only `.agents/` records skip the gate,
but tooling code never does. Commit messages keep every line at or under 100 characters.
`gitflow.sh` writes `chore(merge)` merge messages.

## Context / current verified state

- Plan: `.agents/plans/2026-10-03-workflow-sync.md` §1.2, §2, §3.3, Appendix C (code). Owner decisions D1 and D2 (2026-10-03).
- `.husky/pre-commit` runs `scripts/autofix.sh`, re-stages, then the full `scripts/gate.sh`
  including tests.
- `.husky/pre-push` runs the full `scripts/gate.sh`.
- `scripts/commit_lint.py` checks only the header length (100) and exempts git's default
  merge messages.
- `scripts/gitflow.sh finish` merges with `Merge branch '<branch>' into <base>`.
- `scripts/README.md` says `core.hooksPath` prints `.husky`; Husky 9 sets `.husky/_`.
- The current `AGENTS.md` "Ask first" list covers Husky changes. The owner's approval of
  the plan on 2026-10-03 is that sign-off for this task.

## Scope

- `scripts/config/gate.sh`: add `STAGED_GLOB` (C.1).
- `scripts/lib/common.sh`: add `staged_files` and `run_on_files` (C.2).
- `scripts/gate.sh --staged` (C.3) and `scripts/autofix.sh --staged` (C.4).
- `.husky/pre-commit` (C.5) and `.husky/pre-push` (C.6). Both skip only when every file is
  under `.agents/` and none is under `.agents/tasks/scripts/`.
- `scripts/commit_lint.py`: scissors cut-off and the 100-character line rule (C.7).
- `scripts/gitflow.sh`: `merge_message` for both merges in `finish` (C.8).
- `DEV_TOOLING_SPEC.md` and `scripts/README.md` describe the above; fix the
  `core.hooksPath` note.

## Non-goals

- Do not adopt npm commitlint (D2).
- Do not change `pyproject.toml` `[tool]` sections, CI workflows or `scripts/release.py`.
- Do not edit `.agents/`, `CONTRIBUTING.md` or the agent docs; T-0005 documents the rules.
- Do not change which gates `gate.sh` runs without flags.

## Files to inspect

- `.husky/*`, `scripts/*`, `DEV_TOOLING_SPEC.md`
- `../source-project/.husky/pre-push`, `../source-project/tests/test_pre_push_hook.py`

## Required behavior

As in plan Appendix C. In particular:

- `gate.sh --staged` and `autofix.sh --staged` act only on staged files matching
  `STAGED_GLOB`, exit 0 when none match, and never run tests.
- The pre-push skip is computed per pushed commit; a new remote branch or an unlistable
  range always runs the gate.
- The scripts run under bash 3.2.

## Tests required

- `tests/test_hooks.py`: all 12 cases ported from `source-project:tests/test_pre_push_hook.py`, with a
  stub `scripts/gate.sh` that writes a marker. Add `.agents/tasks/scripts/` cases for both
  hooks and pre-commit cases for skip, staged-only and re-staging.
- `tests/test_commit_lint.py`: line length, scissors, `chore(merge)` headers, and the
  `merge_message` outputs below.

Run `scripts/gate.sh`.

## Documentation required

`DEV_TOOLING_SPEC.md` and `scripts/README.md`, as in Scope.

## Acceptance criteria

- [ ] Each hook rule above has a test, modeled on `source-project:tests/test_pre_push_hook.py`.
- [ ] A `.agents/`-only commit and push run no tests; one file outside `.agents/` runs the full gate.
- [ ] A push or commit that changes only `.agents/tasks/scripts/*.py` runs the gate.
- [ ] `merge_message` gives `chore(merge): merge task 0002 into develop` for `fix/T-0002-x` and `chore(merge): merge feat/x into develop` for `feat/x`; both pass `commit_lint.py`, and the first matches T-0003's merge lookup.
- [ ] `gate.sh` and `autofix.sh` run under bash 3.2 (macOS default): no `mapfile`, no empty-array expansion under `set -u`.
- [ ] `scripts/gate.sh` passes.

## Workflow

- Read `AGENTS.md` (and `CLAUDE.md`, if present) first.
- Create a worktree and branch from `develop` as `feat/T-0004-reconcile-hooks-and-dev-tooling-with-the-merge`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0004.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request.
- Do not edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state.

## Report

Fill in `.agents/tasks/reports/T-0004.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0004
```
