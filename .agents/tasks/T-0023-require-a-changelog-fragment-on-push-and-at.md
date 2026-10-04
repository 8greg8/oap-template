---
id: T-0023
title: Require a changelog fragment on push and at finish
status: review
type: feat
priority: high
depends_on: [T-0022]
touches: [.husky/pre-push, scripts/gitflow.sh, tests/test_hooks.py, tests/test_gitflow.py, changelog.d/T-0023.changed.md]
created: 2026-10-04
report: reports/T-0023.md
---

# T-0023 — Require a changelog fragment on push and at finish

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

A push or a `gitflow.sh finish` that carries a `feat`, `fix` or breaking change without a
changelog fragment is rejected, with the ranges and skips the plan defines.

## Context / current verified state

- Plan: `.agents/plans/2026-10-04-changelog-and-versioning.md`, accepted by the owner on 2026-10-04 (D1 to D8). Its § Design is the source of
  truth for behavior; where this file and the plan differ, stop and report.
- The plan's § Approvals records the owner's written approval for the "Ask first" and
  breaking-change items this task touches; the orchestrator cites it at merge.
- Re-check against `develop` before starting and report any discrepancy.
- Depends on T-0022 (`scripts/changelog.py check`).
- `.husky/pre-push` reads `local_ref local_sha remote_ref remote_sha` lines, skips deleted refs
  and `.agents/`-only pushes, and runs `scripts/gate.sh`. `tests/test_hooks.py` covers it.
- `scripts/gitflow.sh finish` runs the gate in the branch worktree, then merges with `--no-ff`.

## Scope

- `.husky/pre-push`: run `changelog.py check` per pushed ref before the gate, as the plan's
  § Fragment check on push defines: branch from `remote_ref`; `main`/`develop` use
  `<remote_sha>..<local_sha>`; a first push of either is not checked; other branches use the
  merge base with `origin/develop` (`origin/main` for `hotfix/*`); tags and deleted refs skipped;
  `.agents/`-only skip kept; an unlistable range skips the fragment check and runs the gate.
- `scripts/gitflow.sh finish`: run the same branch check before merging; stop with a clear
  message on failure.
- Tests in `tests/test_hooks.py` and `tests/test_gitflow.py`.
- `changelog.d/T-0023.changed.md`: this task's entry, describing the new rule as breaking.
- `changelog.py check` exit 2, a failing `git merge-base`, or a missing `origin/develop` /
  `origin/main` ref means the range is unlistable: skip the fragment check for that ref and run
  the gate.
- `gitflow.sh finish` uses `origin/$base` as the base when it exists, else the local `$base`.
- Invoke the tool as `python3 scripts/changelog.py`, as `.husky/commit-msg` does.
- The hook sources `scripts/config/gate.sh` for `MAIN_BRANCH` and `DEVELOP_BRANCH` instead of
  hard-coding branch names.
- Restructure the pre-push loop (today it `break`s on the first non-`.agents/` ref) so the
  fragment check runs for every pushed ref; the `.agents/`-only decision stays per push.
- The `tests/test_hooks.py` and `tests/test_gitflow.py` fixtures copy `scripts/changelog.py`,
  `scripts/next_version.py` and `scripts/config/gate.sh`.

## Non-goals

- Do not change `scripts/changelog.py` behavior (fix bugs only if found, and report them).
- Do not change `scripts/release.py`, `scripts/next_version.py` or the hotfix message (T-0024).
- Do not change the gate commands or `.husky/pre-commit`, `.husky/commit-msg`.
- Do not change documentation (T-0026).

## Files to inspect

- `.agents/plans/2026-10-04-changelog-and-versioning.md`
- `.husky/pre-push`, `scripts/gitflow.sh`, `scripts/changelog.py`
- `tests/test_hooks.py`, `tests/test_gitflow.py`

## Required behavior

Each case in the plan's § Fragment check on push behaves as the plan states. In particular: a
feature push with a fragment passes and without one fails; a fix round on a branch whose range
already adds a fragment passes; pushing `develop` after merging a feat task passes because the
task's commits in `<remote>..<local>` add its fragment; a docs-only branch passes; a `hotfix/*`
branch is ranged from `origin/main`; a release push of `main`, `develop` and the tag passes.

## Tests required

- Hook cases: feat branch without fragment rejected; with fragment passes; fix round on a branch
  that has a fragment passes; docs-only passes; `HEAD:feat/x` push classified by `remote_ref`;
  `hotfix/*` uses `origin/main`; tag ref skipped; first push of `main`/`develop` skipped;
  `.agents/`-only skip kept; unlistable range runs the gate.
- Ranges: pushing `develop` after merging a feat task with its fragment passes; a release push of
  `main`, `develop` and the tag passes.
- `gitflow.sh finish` refuses a feat branch without a fragment and merges one with it; it uses
  `origin/$base` when that ref exists and falls back to the local `$base` when it does not.
- `uv run pytest tests/test_hooks.py tests/test_gitflow.py -v` and `scripts/gate.sh`.

## Documentation required

None in this task; T-0026 documents the rule.

## Acceptance criteria

- [ ] Pre-push applies the fragment check with exactly the ranges and skips the plan defines.
- [ ] `gitflow.sh finish` runs the branch check before merging.
- [ ] The existing pre-push and gitflow tests still pass; `test_task_branch_kinds_start_and_finish_end_to_end[fix]` and `test_feature_kind_is_unchanged` add a fragment, since their commits are `fix` and `feat`.
- [ ] `changelog.d/T-0023.changed.md` exists and `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 on the pushed branch.
- [ ] The commit introducing the hook rule is marked breaking.
- [ ] `uv run pytest tests/test_hooks.py tests/test_gitflow.py -v` passes.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `feat/T-0023-require-a-changelog-fragment-on-push-and-at`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0023.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0023.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0023
```
