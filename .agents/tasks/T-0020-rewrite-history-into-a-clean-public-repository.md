---
id: T-0020
title: Rewrite history into a clean public repository copy
status: open
type: chore
priority: high
depends_on: [T-0015, T-0016, T-0017, T-0018, T-0019]
touches: [.agents/tasks, .agents/plans, .agents/LESSONS.md]
created: 2026-10-03
report: reports/T-0020.md
---

# T-0020 — Rewrite history into a clean public repository copy

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

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
`CONTRIBUTING.md`, `PYTHON_CONVENTIONS.md`), or "none needed" with
a reason.

## Acceptance criteria

TODO: a checklist a reviewer can walk. Each item must be objectively checkable.

- [ ] ...

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `chore/T-0020-rewrite-history-into-a-clean-public-repository`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0020.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0020.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0020
```
