---
id: T-0005
title: Port agent rules, process docs and orchestrator-merge rules
status: done
type: docs
priority: high
depends_on: [T-0002, T-0003, T-0004, T-0006]
touches: [CLAUDE.md, AGENTS.md, CONTRIBUTING.md, .agents/README.md, .agents/tasks/templates/task.md, README.md]
created: 2026-10-03
report: reports/T-0005.md
---

# T-0005 — Port agent rules, process docs and orchestrator-merge rules

## Goal

The template's agent and process docs describe the workflow that T-0002, T-0003, T-0004
and T-0006 implement. `CLAUDE.md` is the router, and the orchestrator-merge rules for
batch runs are stated as an opt-in owner grant.

## Context / current verified state

- Plan: `.agents/plans/2026-10-03-workflow-sync.md` §1.1, §1.2, §1.4, §1.5, §3.3, Appendix E. Owner decisions D3, D4, D6 and D7
  (2026-10-03).
- `AGENTS.md` here is an older copy of `source-project:CLAUDE.md`; there is no `CLAUDE.md`.
- `CONTRIBUTING.md` has no rules for worktrees, merge commits, accepted history or hook
  installation. It still names `app/<AgentName>/`.
- `.agents/README.md` has no filing step, cleanup step, `worktrees` check or batch rules.
- Re-verify the commands and flags the docs cite against `develop` once the dependencies
  have merged.

## Scope

- Move `AGENTS.md` content to `CLAUDE.md`; `AGENTS.md` becomes the redirect in plan E.1.
- Port the §1.1 and §1.2 rows marked "yes" into `CLAUDE.md` and `CONTRIBUTING.md`:
  - use `<repo_name>` and `docs/spec/` placeholders;
  - cite `scripts/gate.sh` instead of four raw commands, and `scripts/gitflow.sh` instead
    of hand-written worktree commands;
  - make the spec-first section generic (D6), pointing at
    `.devcontainer/spec-blind/` for blind authoring.
- Add an empty "Accepted history" list to `CONTRIBUTING.md`, stating the principle.
- Add plan E.2 to `CLAUDE.md` and E.3 to `.agents/README.md`, with the filing step (step 0)
  and the cleanup step (step 8).
- Copy `templates/task.md` from source-project (plan Appendix A).
- `README.md`: list `CLAUDE.md`, `.devcontainer/` and `.agents/plans/`; update getting
  started.

## Non-goals

- No batch-plan or run-summary template (D7).
- No source-project-specific content (plan §2.1).
- No code changes.
- Do not edit source-project.

## Files to inspect

- `../source-project/CLAUDE.md`, `../source-project/CONTRIBUTING.md`, `../source-project/.agents/README.md`
- `../source-project/.agents/tasks/templates/task.md`
- This repo's `AGENTS.md`, `CONTRIBUTING.md`, `.agents/README.md`, `README.md`,
  `DEV_TOOLING_SPEC.md`

## Required behavior

None; this is a documentation task.

## Tests required

`scripts/gate.sh` passes. For every command and flag the changed docs cite, run it with
`--help` or a dry run and record the result.

## Documentation required

The files in `touches`.

## Acceptance criteria

- [ ] No file names `AGENTS.md` as the primary router, `app/<AgentName>/` or `proj-template` worktree paths.
- [ ] Every command and flag the docs cite exists after T-0002 to T-0004 and T-0006.
- [ ] Orchestrator merging is stated as opt-in per batch, never the default.
- [ ] `CLAUDE.md` contains the generic spec-first test rule, with no source-project paths.
- [ ] `scripts/gate.sh` passes.

## Workflow

- Read `AGENTS.md` (and `CLAUDE.md`, if present) first.
- Create a worktree and branch from `develop` as `docs/T-0005-port-agent-rules-process-docs-and-orchestrator`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0005.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request.
- Do not edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state.

## Report

Fill in `.agents/tasks/reports/T-0005.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0005
```
