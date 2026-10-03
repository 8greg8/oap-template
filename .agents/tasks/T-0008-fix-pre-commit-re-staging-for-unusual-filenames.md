---
id: T-0008
title: Fix pre-commit re-staging for unusual filenames
status: open
type: fix
priority: medium
depends_on: []
touches: [.husky/pre-commit, tests/test_hooks.py]
created: 2026-10-03
report: reports/T-0008.md
---

# T-0008 — Fix pre-commit re-staging for unusual filenames

## Goal

TODO: one paragraph. What must be true when this task is finished? Write it so a
reviewer can tell success from failure without reading the diff.

## Context / current verified state

TODO: what is true in the repo *right now*. Cite files and line numbers. If this
contradicts what you find when you start, stop and report the difference rather
than building on a stale assumption.

## Scope

TODO: the specific changes this task covers.

## Non-goals

TODO: what this task must NOT do. Name files not to touch, APIs not to change,
features not to add, refactors not to start. This section is a guardrail, not a
formality — an empty Non-goals section fails validation.

## Files to inspect

TODO: paths to read before editing. Keep this aligned with `touches`.

## Required behavior

TODO: the concrete behavior the implementation must exhibit.

## Tests required

TODO: name the tests to add or run, and the exact commands. A skipped test is
not a passing test; a test that was not run is not evidence.

## Documentation required

TODO: which docs must change with this behavior (`README.md`, `CLAUDE.md`,
`AGENTS.md`, `CONTRIBUTING.md`, `PYTHON_CONVENTIONS.md`), or "none needed" with
a reason.

## Acceptance criteria

TODO: a checklist a reviewer can walk. Each item must be objectively checkable.

- [ ] ...

## Workflow

- Read `AGENTS.md` (and `CLAUDE.md`, if present) first.
- Create a worktree and branch from `develop` as `fix/T-0008-fix-pre-commit-re-staging-for-unusual-filenames`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0008.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request.
- Do not edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state.

## Report

Fill in `.agents/tasks/reports/T-0008.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0008
```
