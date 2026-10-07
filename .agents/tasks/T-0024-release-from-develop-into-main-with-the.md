---
id: T-0024
title: Release from develop into main with the changelog
status: done
type: feat
priority: high
depends_on: [T-0023]
touches: [scripts/release.py, scripts/next_version.py, scripts/gitflow.sh, tests/test_release.py, tests/test_next_version.py, tests/test_gitflow.py, changelog.d/T-0024.changed.md]
created: 2026-10-04
report: reports/T-0024.md
---

# T-0024 — Release from develop into main with the changelog

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

`scripts/release.py` releases `develop` into `main` (or a pushed hotfix on `main`) with the
changelog section, the tag and `develop` brought up to date, as the plan's § Release defines,
and `next_version.py` follows the 0.x rule (D8).

## Context / current verified state

- Plan: `.agents/plans/2026-10-04-changelog-and-versioning.md`, accepted by the owner on 2026-10-04 (D1 to D8). Its § Design is the source of
  truth for behavior; where this file and the plan differ, stop and report.
- The plan's § Approvals records the owner's written approval for the "Ask first" and
  breaking-change items this task touches; the orchestrator cites it at merge.
- Re-check against `develop` before starting and report any discrepancy.
- Depends on T-0023.
- `scripts/release.py` today only tags `main` and refuses other branches; `scripts/next_version.py`
  uses `git describe --abbrev=0` and bumps major on breaking. No `tests/test_release.py` or
  `tests/test_next_version.py` exists.
- `scripts/gitflow.sh` hotfix finish prints a reminder to run `release.py` (near line 82).

## Scope

- `scripts/next_version.py`: while the latest tag's major is 0, breaking bumps minor; `feat`
  minor; `fix` patch. Update its docstring.
- `scripts/release.py`: dry run by default; `--yes` sequence (merge from `develop` with
  `chore(merge): merge develop into main`, `changelog.py assemble`, `chore(release): vX.Y.Z`,
  annotated tag on that commit, fast-forward or `--no-ff` back-merge of `develop`);
  `--version vX.Y.Z` (must be higher than the latest tag); `--push` as
  `git push --atomic origin main develop vX.Y.Z`; `git fetch origin` first and every refusal the
  plan lists (dirty tree, either branch not equal to origin, either branch checked out in another
  worktree, nothing to release). Refusals happen before any change.
- `scripts/gitflow.sh`: the hotfix finish message per the plan (push both branches, then run
  `release.py --yes` on `main`).
- Tests: `tests/test_release.py`, `tests/test_next_version.py`, `tests/test_gitflow.py` (message).
- `changelog.d/T-0024.changed.md`: this task's entry, describing the new release flow as breaking.
- No new tracked file (`tests/test_release.py`, `tests/test_next_version.py`, the fragment)
  contains `proj_template`, `proj-template`, `oap-template`, `8greg8` or the owner's email.
- The dry run calls `python3 scripts/changelog.py preview <version>`.
- On a failure after the first change (merge conflict, a hook failing on the release commit, a
  rejected push), stop, print the current state and the exact commands to finish or undo by
  hand; never reset or force anything. On a rejected `--push`, print the
  `git push --atomic origin <main> <develop> vX.Y.Z` retry command.
- Fast-forward versus `--no-ff` back-merge of `develop` is chosen by
  `git merge-base --is-ancestor develop main`, not by the starting branch.
- Refuse any starting branch other than `main` or `develop`. End with the starting branch checked
  out.
- For the `--version` check only, "latest tag" means the highest `vX.Y.Z` tag by SemVer
  (`v0.0.0` when none); `--version` accepts only the `vX.Y.Z` form. `next_version.py` keeps its
  `git describe` lookup; only its bump rule changes (D8).
- Release commit: stage with `git add -A -- CHANGELOG.md changelog.d` after `assemble`.

## Non-goals

- Do not change `scripts/changelog.py` behavior (fix bugs only if found, and report them).
- Do not change `.husky/` hooks or the gate.
- Do not add CI, GitHub Release creation or any network call other than `git fetch`/`git push`.
- Do not change documentation (T-0026).

## Files to inspect

- `.agents/plans/2026-10-04-changelog-and-versioning.md`
- `scripts/release.py`, `scripts/next_version.py`, `scripts/gitflow.sh`, `scripts/changelog.py`,
  `scripts/config/gate.sh` (branch names)
- `tests/test_gitflow.py` (bare-remote fixtures)

## Required behavior

The plan's § Release steps 1 to 4 work end to end against a bare remote, from `develop` (normal
release) and from `main` after a pushed hotfix (step 1 skipped, `--no-ff` back-merge). After a
release, `main` and `develop` contain the tagged `chore(release)` commit, no fragment remains,
the next release does not fold anything twice, and the atomic push lands all three refs or none.

## Tests required

- `tests/test_next_version.py`: 0.x rule cases and the >= 1.0 rules unchanged.
- `tests/test_release.py`: dry run changes nothing; normal release; hotfix release; first release
  from no tags is `v0.1.0` with a breaking commit; `--version` higher and lower; each refusal;
  `--push` to a bare remote is atomic (a rejected ref leaves the remote unchanged).
- `uv run pytest tests/test_release.py tests/test_next_version.py tests/test_gitflow.py -v` and
  `scripts/gate.sh`.
- Tests use only temporary repositories and fixtures; none reads this repository's `CHANGELOG.md`
  or `changelog.d/` contents. They pass in a project produced by `init_project.py`.
- The atomic-push test uses an `update` hook in the bare remote that rejects only
  `refs/tags/*`, then asserts `main` and `develop` on the remote are unchanged.

## Documentation required

None in this task beyond docstrings; T-0026 documents the flow.

## Acceptance criteria

- [ ] `next_version.py` applies the 0.x rule and its docstring says so.
- [ ] `release.py` performs the plan's `--yes` sequence from `develop` and from `main` after a hotfix.
- [ ] `release.py` refuses every case the plan lists before changing anything.
- [ ] `--version` and `--push` behave as specified.
- [ ] The hotfix finish message matches the plan.
- [ ] `changelog.d/T-0024.changed.md` exists and `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 on the pushed branch. The behavior commit is marked breaking.
- [ ] `uv run pytest tests/test_release.py tests/test_next_version.py tests/test_gitflow.py -v` passes.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `feat/T-0024-release-from-develop-into-main-with-the`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0024.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0024.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0024
```
