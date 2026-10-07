---
id: T-0040
title: Fix: remove the unlicensed bundled OAP text from the release
status: done
type: fix
priority: medium
depends_on: []
touches: [changelog.d/T-0040.fixed.md]
created: 2026-10-07
report: reports/T-0040.md
---

# T-0040 — Fix: remove the unlicensed bundled OAP text from the release

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

A changelog fragment records that the bundled copy of the OAP method text was removed because its license is unconfirmed, so v0.1.1 can be released.

## Context / current verified state

T-0039 (merged, `docs` type) deleted `strategic_model_init_material.md` and linked the source page. `docs` drives no release, so `scripts/release.py --version v0.1.1` refuses with "nothing to release since v0.1.0". `v0.1.0` still ships the file. `changelog.d/` holds only `README.md`.

## Scope

Add `changelog.d/T-0040.fixed.md` with one bullet describing the removal and the new links. The commit type is `fix`, since the removal corrects a redistribution problem in the shipped template.

## Non-goals

- Do not edit any other file, including `CHANGELOG.md`, `README.md` and `NOTICE.md`.
- Do not rewrite git history.
- Do not cut the release. The owner's release run does that.

## Files to inspect

- `changelog.d/README.md` (fragment format and wording rule)

## Required behavior

`scripts/changelog.py check` accepts the fragment. A dry run of `scripts/release.py --version v0.1.1` after merge finds a release.

## Tests required

- `python scripts/changelog.py check`.
- `python .agents/tasks/scripts/task.py validate`.
- The independent verifier runs the full `scripts/gate.sh`.

## Documentation required

The fragment is the documentation. No other change.

## Acceptance criteria

- [ ] `changelog.d/T-0040.fixed.md` exists with one valid bullet.
- [ ] The branch changes only that file, the task file and the report.
- [ ] The commit type is `fix`.
- [ ] Full gate passes.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `fix/T-0040-fix-remove-the-unlicensed-bundled-oap-text-from`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits. Iterate with
  `scripts/gate.sh --fast` and targeted tests and commit freely. Do not spawn a verifier: your own
  gate runs certify nothing.
- Write the report to `.agents/tasks/reports/T-0040.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after one
  independent verify of the pushed branch by a different agent, which runs the full gate itself.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0040.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0040
```
