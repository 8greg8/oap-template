---
id: T-0001
title: Enforce report writing as a pipeline gate, not an agent courtesy
status: in_progress
type: chore
priority: high
depends_on: [T-0003, T-0005]
touches: [CLAUDE.md, .agents/README.md, .agents/tasks/scripts/task.py, .agents/tasks/scripts/report.py, .agents/tasks/scripts/housekeep.py, .agents/tasks/templates/task.md]
created: 2026-09-16
report: reports/T-0001.md
---

# T-0001 — Enforce report writing as a pipeline gate, not an agent courtesy

## Goal

An agent cannot move a task past `in_progress` (to `review`, `blocked`, `done`, or
`abandoned`) without a corresponding report file existing and passing
`report.py validate`. Today, report-writing is documented as mandatory in this
template's `AGENTS.md`/`.agents/README.md`, but nothing in the tooling enforces it —
an agent can skip straight from doing the work to `set-status ... review` with no
report ever created. Because this template is the source every downstream project's
`.agents/` workflow is copied from, the gap propagates to every project generated from
it. Fixing it here fixes it at the source instead of only in each downstream copy (one
downstream instance is separately being fixed in the `downstream-project` project's own
T-0009, but that project's tooling was already forked from this template before the
fix existed, so it needs its own copy of the same change — this task is the upstream
half).

## Context / current verified state

- Amended 2026-10-03 by the workflow-sync bootstrap (`.agents/plans/2026-10-03-workflow-sync.md`
  §3.1). This task now runs after T-0003, which replaces `report.py` and `housekeep.py`,
  and T-0005, which makes `CLAUDE.md` the router and turns `AGENTS.md` into a redirect.
  The points below describe the repository before those tasks. Re-verify each against
  `develop` before starting, and reuse T-0003's `report.py validate`.
- `AGENTS.md` (this repo) states "Every task ends with a report... Run
  `report.py validate T-00XX` before considering the task finished," and
  `.agents/README.md` repeats this and says "Only `done` satisfies a dependency.
  `blocked` and `abandoned` still require a report explaining why." Both are prose
  conventions, not enforced by any script.
- `.agents/tasks/scripts/task.py`'s `set-status` subcommand changes a task's `status`
  frontmatter field directly with no check that `.agents/tasks/reports/<ID>.md` exists,
  let alone that it's filled in (no leftover placeholder text) — confirmed by reading
  `task.py`'s `set-status` handling, which only validates the status value is one of
  the allowed statuses and rewrites frontmatter.
- `.agents/tasks/scripts/report.py` has a `validate T-00XX` subcommand that checks for
  unfilled placeholder sections, but it is only ever invoked manually/voluntarily —
  never called from `task.py set-status`, and never run automatically anywhere in the
  documented execution loop in `.agents/README.md`.
- `.agents/tasks/scripts/housekeep.py`'s `drift` subcommand *does* catch this after the
  fact ("a `done` task with no report") but only when someone remembers to run
  `housekeep.py drift`, and only for `done`, not `review`/`blocked`/`abandoned` per the
  README's own stated rule that those also require a report too.
- This gap was observed in practice in a downstream project built from this template
  (`downstream-project`): agents marked tasks `review`/`done` with no report file ever
  created, because nothing stopped them.

## Scope

- Change `task.py set-status` so that transitioning a task to any of `review`,
  `blocked`, `done`, or `abandoned` requires `.agents/tasks/reports/<ID>.md` to already
  exist and pass the same validation `report.py validate <ID>` performs (no unfilled
  placeholder text left in a required section). If it doesn't exist or doesn't
  validate, `set-status` refuses the transition with an error naming exactly what's
  missing and exits non-zero.
- Transitioning to `open` or `in_progress` is unaffected (no report expected yet).
- Reuse `report.py`'s existing validation logic (import/call it, or factor the shared
  check into `_schema.py`) rather than re-implementing the placeholder check a second
  time.
- Update `.agents/README.md`'s "The execution loop" close step and `CLAUDE.md`'s
  "Every task ends with a report" bullet to describe this as an enforced gate rather
  than a step an agent must remember.

## Non-goals

- Do not change `report.py`'s own validation rules (what counts as a valid report) —
  only wire the existing check into `set-status`.
- Do not add report enforcement to `housekeep.py drift` beyond what it already does;
  `drift` remains a reporting-only tool per its documented contract in
  `.agents/README.md`.
- Do not change the report template (`.agents/tasks/templates/report.md`) itself.
- Do not touch `BACKLOG.md`, `.agents/tasks/scripts/backlog.py`, or `LESSONS.md`.
- Do not add report enforcement to any git hook (`.husky/`) — this is a `task.py`
  CLI-level gate, not a commit-time gate.
- Do not attempt to also patch the downstream `downstream-project` project from here —
  that project already has its own copy of this fix tracked as its own task.

## Files to inspect

- `.agents/tasks/scripts/task.py` (the `set-status` subcommand)
- `.agents/tasks/scripts/report.py` (`validate` subcommand's logic)
- `.agents/tasks/scripts/_schema.py` (shared schema/validation helpers, if the check
  belongs here for reuse)
- `.agents/tasks/scripts/housekeep.py` (`drift`, for how it currently detects a
  report-less `done` task, so the new gate and the existing drift check don't disagree)
- `.agents/README.md`, `CLAUDE.md`

## Required behavior

- `python .agents/tasks/scripts/task.py set-status T-00XX review` (or `blocked`,
  `done`, `abandoned`) exits non-zero and leaves the task's status unchanged if
  `.agents/tasks/reports/T-00XX.md` does not exist or fails validation, printing which
  check failed.
- The same command succeeds and updates status when a valid, fully-filled-in report
  exists.
- `set-status T-00XX in_progress` and `set-status T-00XX open` are unaffected.

## Tests required

Add/extend a test module under `tests/` covering: `set-status` to `review` without a
report fails; `set-status` to `review` with a report still containing an unfilled
placeholder section fails; `set-status` to `review` with a fully-filled report
succeeds; `set-status` to `in_progress`/`open` is unaffected by report state. Run with
`uv run pytest tests/`.

## Documentation required

`CLAUDE.md` and `.agents/README.md` as described in Scope, so the docs describe the
actual (enforced) behavior instead of an honor-system convention. Since this is the
template, this doc change also propagates to every project generated from it going
forward.

## Acceptance criteria

- [ ] `task.py set-status <ID> review` fails with a clear error when no report file
      exists for `<ID>`.
- [ ] `task.py set-status <ID> review` fails when the report file exists but still has
      an unfilled placeholder section.
- [ ] `task.py set-status <ID> review` (and `blocked`, `done`, `abandoned`) succeeds
      when the report is present and fully filled in.
- [ ] `task.py set-status <ID> open` and `in_progress` are unaffected by report state.
- [ ] New/extended tests cover the above and pass: `uv run pytest tests/`.
- [ ] `CLAUDE.md` and `.agents/README.md` describe this as an enforced gate.

## Workflow

- Read `AGENTS.md` (and `CLAUDE.md`, if present) first.
- Create a worktree and branch from `develop` as `chore/T-0001-enforce-report-writing-as-a-pipeline-gate-not`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0001.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request.
- Do not edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state.

## Report

Fill in `.agents/tasks/reports/T-0001.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0001
```
