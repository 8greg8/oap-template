---
id: T-0034
title: Mark the slow init tests and skip them for safe-list changes
status: open
type: feat
priority: high
depends_on: [T-0033]
touches: [pyproject.toml, tests/test_init_project.py, scripts/gate.sh, scripts/config/gate.sh, .husky/pre-push, tests/test_gate.py, tests/test_hooks.py, scripts/README.md, DEV_TOOLING_SPEC.md, tests/test_release.py, changelog.d/T-0034.added.md]
created: 2026-10-05
report: reports/T-0034.md
---

# T-0034 — Mark the slow init tests and skip them for safe-list changes

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

The two end-to-end init tests run only when a change can affect them: the gate skips them for
safe-list-only changes, always runs them for `main` and `--all`, and records which it did.

## Context / current verified state

- Plan: `.agents/plans/2026-10-05-verification-cost.md`, accepted by the owner on 2026-10-05 (V1 to V9 as recommended). Its § Design is the
  source of truth and its § Approvals is the owner's written approval for this task's "Ask first"
  and breaking items; cite it in the report. Where this file and the plan differ, stop and report.
- Sync first (`git pull --ff-only origin develop`) and re-check every cited line against
  `develop`; report any discrepancy.
- Depends on T-0033 (records, `--if-needed`, `RECORD_PATHS`).
- The two slow cases are the end-to-end tests in `tests/test_init_project.py` (about 250 to 300 s
  together); the file's other tests take about 40 s. `pyproject.toml` has no `[tool.pytest]`
  section. `TEST_CMD` is `uv run pytest`.
- `scripts/README.md` is under `scripts/` and is treated as an "Ask first" item (T-0026 precedent).
  The plan assigns it to this task, and the owner's acceptance ("proceed with the steps") covers
  the plan's tasks. Cite both in the report.

## Scope

Implement the plan's § "Slow tests run unless the change is provably safe" exactly:
- Mark the two end-to-end cases `slow`; register the marker in `pyproject.toml`
  `[tool.pytest.ini_options]`.
- `SLOW_SAFE_PATHS` in `scripts/config/gate.sh` (the plan's list). `scripts/gate.sh` runs
  `-m "not slow"` only when every path changed since the base is on it; `--all` runs everything.
  The base: merge base with `origin/$DEVELOP_BRANCH` (`origin/$MAIN_BRANCH` for `hotfix/*`),
  falling back to the local branch.
- The record notes whether slow tests ran; `--if-needed` treats a record without them as
  insufficient for `main` and for any commit whose change is not safe-list-only.
- `.husky/pre-push`: a push to `main` always requires slow tests.
- A fast (not `slow`) test that greps the safe-listed docs for the template-name strings.
- `scripts/README.md`, `DEV_TOOLING_SPEC.md`: the selection rule.
- Tests in `tests/test_gate.py` and `tests/test_hooks.py`.
- `changelog.d/T-0034.added.md`. The behavior commit is marked breaking (`feat(gate)!:`) with a
  footer saying the default gate may skip the slow tests.
- The task's fragment holds only bullet and indented continuation lines and no placeholder words.
- `scripts/config/gate.sh` gets `TEST_SKIP_SLOW_ARGS='-m "not slow"'`; `gate.sh` appends it to
  `TEST_CMD` only when skipping. `SLOW_SAFE_PATHS` uses the `RECORD_PATHS` pathspec syntax;
  fragments are `changelog.d/*.*.md` (which leaves out `README.md`). Variables are read as `${VAR-}`.
- Changed paths: for a working-tree run, `git diff --name-only --no-renames <base>` plus
  `git ls-files --others --exclude-standard`; for a named commit,
  `git diff --name-only --no-renames <base> <commit>`. An empty set runs the slow tests.
- The `hotfix/*` base applies only when `git symbolic-ref -q --short HEAD` names a `hotfix/`
  branch; a detached HEAD uses the `develop` base.
- `--if-needed --all <sha>...` treats a `slow=no` record as insufficient and gates with `--all`.
  Pre-push calls it separately for `main`'s SHA, so `release.py --push` makes two calls; update the
  hotfix release test in `tests/test_release.py` accordingly.
- `tests/test_hooks.py:950-954` asserts an exact test call; adapt it.
- The fragment follows `changelog.d/README.md`, section "Before the first release": category
  `added`, and no "Breaking:", "no longer", "used to" or "now".

## Non-goals

- Do not change which tests exist or what they assert, beyond the marker and the new grep test.
- Do not add `pytest-xdist` or any dependency (V6).
- Do not change the gate commands other than test selection.
- Do not change `CLAUDE.md`, `CONTRIBUTING.md` or `.agents/README.md` (T-0036).
- No new or edited tracked file contains `proj_template`, `proj-template`, `oap-template`, `8greg8`
  or the owner's email.

## Files to inspect

- `.agents/plans/2026-10-05-verification-cost.md`
- Every file in `touches`; `init_project.py` (what it copies, edits and removes)

## Required behavior

A change only to safe-listed paths runs the gate without the two slow tests; any other change, a
`main` push and `--all` run them; a record without slow tests never satisfies a check that needs
them.

## Tests required

- `uv run pytest -m slow --co -q` lists exactly the two end-to-end cases.
- `uv run pytest tests/test_gate.py tests/test_hooks.py -v`.
- `scripts/gate.sh --all`.

## Documentation required

`scripts/README.md` and `DEV_TOOLING_SPEC.md`, as in Scope.

## Acceptance criteria

- [ ] Exactly the two end-to-end cases are marked `slow` and the marker is registered.
- [ ] Safe-list-only changes skip them; other changes, `main` pushes and `--all` run them.
- [ ] The base is defined as the plan states, with the local fallback.
- [ ] Records carry the slow flag and `--if-needed` honors it.
- [ ] A fast test greps the safe-listed docs for the template-name strings.
- [ ] `changelog.d/T-0034.added.md` exists and `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 on the pushed branch.
- [ ] `uv run pytest tests/test_gate.py tests/test_hooks.py -v` passes.
- [ ] `scripts/gate.sh --all` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `feat/T-0034-mark-the-slow-init-tests-and-skip-them-for-safe`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0034.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0034.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0034
```
