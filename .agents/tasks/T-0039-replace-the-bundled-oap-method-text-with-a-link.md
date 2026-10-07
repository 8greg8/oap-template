---
id: T-0039
title: Replace the bundled OAP method text with a link to its source
status: done
type: docs
priority: medium
depends_on: []
touches: [strategic_model_init_material.md, README.md, .agents/README.md, NOTICE.md]
created: 2026-10-07
report: reports/T-0039.md
---

# T-0039 — Replace the bundled OAP method text with a link to its source

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

The repository no longer contains `strategic_model_init_material.md`. Every pointer to it links to <https://edu.slaif.si/trainings/workshop-orchestrated-agentic-programming> instead. `NOTICE.md` credits the source without claiming a license for the text.

## Context / current verified state

- `strategic_model_init_material.md` is a 3,131-line copy of "Orchestrated Agentic Programming" v1.0.1 by Janez Perš, amended by T-0014.
- No license appears on the file or the source page (`.agents/plans/2026-10-03-public-release-cleanup.md` lines 47-50). Redistribution rights are unconfirmed.
- References: `README.md` lines 4 and 22, `.agents/README.md` line 6, `NOTICE.md` line 5. No code, test or script reads the file.

## Scope

- Delete `strategic_model_init_material.md`.
- `README.md`: link the intro to <https://edu.slaif.si/trainings/workshop-orchestrated-agentic-programming>. Replace the table row with a row for that link, described as the external method text.
- `.agents/README.md`: point line 6 at the same URL.
- `NOTICE.md`: replace the "Third-party material" entry with a "Referenced material" entry. Keep title, version 1.0.1, author and source URL. State that the text is not bundled and that its license is not confirmed. Keep the SLAIF acknowledgement.

## Non-goals

- Do not rewrite git history or remove the file from past commits. That is an "Ask first" action.
- Do not edit historical task, report or plan files under `.agents/tasks/` and `.agents/plans/` that name the file.
- Do not change `CLAUDE.md`, `scripts/`, `pyproject.toml` or any code.
- Do not make the repository public.

## Files to inspect

- `README.md`, `.agents/README.md`, `NOTICE.md`
- `git grep -n strategic_model_init_material` for live references outside `.agents/tasks/` and `.agents/plans/`

## Required behavior

After the change, `git grep strategic_model_init_material -- . ':!.agents/tasks' ':!.agents/plans'` finds nothing. Every link to the method text resolves to the source URL.

## Tests required

- `scripts/gate.sh --fast` while iterating.
- `python .agents/tasks/scripts/task.py validate`.
- The independent verifier runs the full `scripts/gate.sh`.

## Documentation required

The edits above are the documentation change. No changelog fragment: type is `docs`.

## Acceptance criteria

- [ ] `strategic_model_init_material.md` is deleted.
- [ ] The `git grep` above finds nothing.
- [ ] `README.md`, `.agents/README.md` and `NOTICE.md` link to the source URL.
- [ ] `NOTICE.md` does not say the text is MIT-licensed or bundled.
- [ ] Only files in `touches`, plus the report, changed.
- [ ] Full gate passes.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `docs/T-0039-replace-the-bundled-oap-method-text-with-a-link`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits. Iterate with
  `scripts/gate.sh --fast` and targeted tests and commit freely. Do not spawn a verifier: your own
  gate runs certify nothing.
- Write the report to `.agents/tasks/reports/T-0039.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after one
  independent verify of the pushed branch by a different agent, which runs the full gate itself.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0039.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0039
```
