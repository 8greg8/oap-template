---
id: T-0033
title: Record gate passes and add gate.sh --if-needed
status: open
type: feat
priority: high
depends_on: []
touches: [scripts/gate.sh, scripts/config/gate.sh, .husky/pre-push, .husky/pre-commit, scripts/gitflow.sh, tests/test_gate.py, tests/test_hooks.py, tests/test_gitflow.py, tests/test_release.py, scripts/README.md, DEV_TOOLING_SPEC.md, changelog.d/T-0033.added.md]
created: 2026-10-05
report: reports/T-0033.md
---

# T-0033 — Record gate passes and add gate.sh --if-needed

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

A full, clean gate run writes a record keyed by the code and the tool versions; `scripts/gate.sh
--if-needed` reuses it; the pre-push hook, `gitflow.sh finish` and the post-merge check stop
re-running the gate on code that already passed; and task-branch pushes run only `--fast`.

## Context / current verified state

- Plan: `.agents/plans/2026-10-05-verification-cost.md`, accepted by the owner on 2026-10-05 (V1 to V9 as recommended). Its § Design is the
  source of truth and its § Approvals is the owner's written approval for this task's "Ask first"
  and breaking items; cite it in the report. Where this file and the plan differ, stop and report.
- Sync first (`git pull --ff-only origin develop`) and re-check every cited line against
  `develop`; report any discrepancy.
- `scripts/gate.sh` has `--fast` and `--staged` and no record. `.husky/pre-push` runs the full
  gate for any push with a non-`.agents/` file or a new remote branch; `.husky/pre-commit` and
  `.husky/pre-push` skip every `.agents/` path except `.agents/tasks/scripts/`.
  `scripts/gitflow.sh:96` runs the full gate in `finish`. `scripts/release.py` pushes `main`,
  `develop` and the tag atomically, possibly with the `develop` back-merge not checked out.

## Scope

Implement the plan's § "Gate records keyed by code, not by bookkeeping" and § "Pre-push on task
branches" exactly:
- `RECORD_PATHS` in `scripts/config/gate.sh` (the plan's list); both hooks use it for their skip
  rule instead of the current `.agents/` rule.
- The record: key = hash of the tree with `RECORD_PATHS` filtered out plus `uv --version`,
  `uv run python -VV`, `node -v`, `git --version`; written under
  `$(git rev-parse --git-common-dir)/gate-pass/` only after a full run on a tree that is clean
  (`git status --porcelain --untracked-files=all` empty) before and after. The record notes whether
  slow tests ran (always yes until T-0034 lands).
- `scripts/gate.sh --if-needed [<commit>...]`: as the plan specifies, including gating a commit
  that is not checked out in a temporary detached worktree (removed afterwards); never refuses for
  want of a checkout.
- `.husky/pre-push`: `develop` and `main` call `--if-needed` with every pushed non-deleted
  `local_sha`; any other branch runs `scripts/gate.sh --fast`. The changelog check is unchanged.
- `scripts/gitflow.sh finish`: `--if-needed` instead of the full gate.
- `scripts/README.md` and `DEV_TOOLING_SPEC.md`: the gate and hook sections, matching the code.
- Tests: `tests/test_gate.py` (new) for keys, filtering, clean checks, tool-version changes,
  `--if-needed` on several commits and on a non-checked-out commit; hook and gitflow tests; a test
  in `tests/test_release.py` that a hotfix `release.py --yes --push` passes the new hook.
- `changelog.d/T-0033.added.md`. The behavior commit is marked breaking (`feat(gate)!:`) with a
  footer naming the new pre-push behavior.
- The task's fragment holds only bullet and indented continuation lines and no placeholder words.

## Non-goals

- Do not add the slow marker or any test selection (T-0034).
- Do not change `scripts/release.py`, `scripts/changelog.py`, the gate commands or `STAGED_GLOB`.
- Do not change `CLAUDE.md`, `CONTRIBUTING.md` or `.agents/README.md` (T-0036).
- Do not commit records or add them to the tree.
- No new or edited tracked file contains `proj_template`, `proj-template`, `oap-template`, `8greg8`
  or the owner's email.

## Files to inspect

- `.agents/plans/2026-10-05-verification-cost.md`
- Every file in `touches`; `scripts/release.py` (push step), `tests/test_init_project.py` (runs the gate in scratch projects)

## Required behavior

The cases in Scope behave as the plan states. A push of `develop` whose code already passed runs
no gate; a push of a task branch runs only `--fast`; a hotfix release push passes.

## Tests required

- `uv run pytest tests/test_gate.py tests/test_hooks.py tests/test_gitflow.py tests/test_release.py -v`.
- `scripts/gate.sh` (full).

## Documentation required

`scripts/README.md` and `DEV_TOOLING_SPEC.md`, as in Scope.

## Acceptance criteria

- [ ] A full, clean run writes a record; `--fast`, `--staged` and a dirty run never do.
- [ ] Changing a `RECORD_PATHS` file keeps the key; changing any other tracked file or a tool version changes it.
- [ ] `--if-needed` skips only when every named commit has a record, and gates a non-checked-out commit in a temporary worktree.
- [ ] Both hooks use `RECORD_PATHS` for their skip rule.
- [ ] Pre-push: `develop`/`main` use `--if-needed`; other branches run `--fast`.
- [ ] `gitflow.sh finish` uses `--if-needed`.
- [ ] A hotfix `release.py --yes --push` passes the new hook in a test.
- [ ] `changelog.d/T-0033.added.md` exists and `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 on the pushed branch.
- [ ] `uv run pytest tests/test_gate.py tests/test_hooks.py tests/test_gitflow.py tests/test_release.py -v` passes.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `feat/T-0033-record-gate-passes-and-add-gate-sh-if-needed`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0033.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0033.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0033
```
