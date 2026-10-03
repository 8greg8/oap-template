---
id: T-0010
title: Fix agent-doc wording and stale AGENTS.md references
status: done
type: docs
priority: low
depends_on: []
touches: [CLAUDE.md, CONTRIBUTING.md, .agents/README.md, DEV_TOOLING_SPEC.md]
created: 2026-10-03
report: reports/T-0010.md
---

# T-0010 — Fix agent-doc wording and stale AGENTS.md references

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

The agent docs say one consistent thing about who may edit task files, the hand-written task-branch command does not break a bare `git push`, and `DEV_TOOLING_SPEC.md` no longer cites `AGENTS.md` for rules that now live in `CLAUDE.md`.

## Context / current verified state

- T-0005's independent verify (2026-10-03) found: `CLAUDE.md` (Batch runs section) says the orchestrator "never edits a task file except through `task.py set-status`", while `.agents/README.md` (orchestrator-merge steps) lets it widen a task's `touches` and record why, and the pre-batch review step amends task files.
- `CONTRIBUTING.md` (Worktrees for agents) gives `git worktree add ... -b <type>/T-NNNN-<slug> origin/develop`. Branching from a remote-tracking ref sets the upstream to `origin/develop`; with `push.default=simple` a bare `git push` then refuses. Untested; reproduce before changing.
- `DEV_TOOLING_SPEC.md` lines 7, 45, 203 and 241 cite `AGENTS.md` for the Ask-first and verification rules. `AGENTS.md` is now a redirect to `CLAUDE.md`.
- Re-check each against current files and report any discrepancy.

## Scope

- Reconcile the wording in `CLAUDE.md` and `.agents/README.md` so the permitted orchestrator edits to task files are listed once and identically.
- Reproduce the upstream-tracking problem in a scratch repo; if real, add `--no-track` (or `git push -u origin <branch>`) to the command in `CONTRIBUTING.md`, and say so in the report.
- Replace the four `AGENTS.md` citations in `DEV_TOOLING_SPEC.md` with `CLAUDE.md`.

## Non-goals

- Do not change `scripts/release.py` (its line-4 docstring also cites `AGENTS.md`); `scripts/` is human-gated and needs the owner's explicit approval as a separate task.
- Do not change any rule's meaning, including the Ask-first list.
- Do not edit code, hooks, `pyproject.toml` or any task file.

## Files to inspect

- `CLAUDE.md`, `.agents/README.md`, `CONTRIBUTING.md`, `DEV_TOOLING_SPEC.md`

## Required behavior

Docs only. Every changed sentence keeps its previous meaning except the two corrected inconsistencies.

## Tests required

Run `scripts/gate.sh` and `python .agents/tasks/scripts/task.py validate`. Show the reproduction of the push behavior with exact commands and output.

## Documentation required

The changed docs are the deliverable.

## Acceptance criteria

- [ ] `CLAUDE.md` and `.agents/README.md` list the same orchestrator edits to task files.
- [ ] The push-tracking behavior is reproduced or shown not to occur, and `CONTRIBUTING.md` matches the finding.
- [ ] `grep -n AGENTS.md DEV_TOOLING_SPEC.md` returns nothing.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches` plus the report.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `docs/T-0010-fix-agent-doc-wording-and-stale-agents-md`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0010.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0010.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0010
```
