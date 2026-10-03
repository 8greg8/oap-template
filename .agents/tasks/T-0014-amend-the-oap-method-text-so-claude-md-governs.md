---
id: T-0014
title: Amend the OAP method text so CLAUDE.md governs merge authority
status: in_progress
type: docs
priority: medium
depends_on: []
touches: [strategic_model_init_material.md]
created: 2026-10-03
report: reports/T-0014.md
---

# T-0014 — Amend the OAP method text so CLAUDE.md governs merge authority

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

`strategic_model_init_material.md` (the OAP method text) no longer contradicts this repository's merge rules. Where the text treats every merge as a human decision, it says that a project's `CLAUDE.md` governs, and that in this repository the orchestrator merges task branches into `develop` by default.

## Context / current verified state

- Owner instruction, 2026-10-03: "Amend the method text; CLAUDE.md governs". It follows T-0013, which made orchestrator merge into `develop` the default (`CLAUDE.md` § "Merge authority: orchestrator merges by default").
- T-0013's report records the conflict: line 1917 ("Approval gates") lists "merge to protected branches" as a human approval, and line 2641 says "treat every merge as a human decision".
- Other lines in the method text that mention human merge authority or merge decisions, to check: 1624, 1717, 2606, 2684, 2685, 2918. Lines 576, 725, 1123, 2794 say the agent must not merge its own PR; they stay true.
- The file is ~3100 lines, mostly general doctrine. Re-check every line cited against the file and report any discrepancy.

## Scope

- Add one short note, in the place a reader meets the human gates first (near "Approval gates" or the doctrine chapter, executor's choice), saying: this text is general doctrine; a project's `CLAUDE.md` governs where it differs; in this repository `CLAUDE.md` lets the orchestrator merge verified task branches into `develop` by default, with a human deciding only breaking changes and "Ask first" items, and merges into `main`, tags and releases staying human.
- Amend each sentence that states a merge into `develop` always needs a human (line 2641 and any other found among the lines above) so it reads as the general default with that override, without weakening the rule that an agent never merges its own work or verifies its own change.
- Keep the "Approval gates" list as the general doctrine, adding only a pointer to the note.
- Keep the document's style and length discipline: no new section longer than a short paragraph.

## Non-goals

- Do not change `CLAUDE.md`, `.agents/`, `CONTRIBUTING.md`, `README.md`, scripts, hooks or tests.
- Do not rewrite the method's doctrine, its failure-mode chapter, or any guidance on human review of evidence beyond the sentences named in Scope.
- Do not remove the statements that an agent never merges its own PR.
- Do not reformat the file or touch its front matter, bibliography or build directives.

## Files to inspect

- `strategic_model_init_material.md`, around the lines named in Context
- `CLAUDE.md` § "Merge authority: orchestrator merges by default" (read only)
- `.agents/tasks/reports/T-0013.md` (read only)

## Required behavior

Docs only. After the change, no sentence in `strategic_model_init_material.md` says that a merge into `develop` must always be a human decision, and the file states once that a project's `CLAUDE.md` governs. The agent-never-merges-its-own-work statements are unchanged.

## Tests required

Run `scripts/gate.sh` and `python .agents/tasks/scripts/task.py validate`. Run `grep -n -i "every merge\|merge to protected\|merge authority\|merge decision" strategic_model_init_material.md` and report each hit with a judgment. If the file has a build or link check, run it; otherwise report `not run`.

## Documentation required

The changed method text is the deliverable.

## Acceptance criteria

- [ ] The file states once that a project's `CLAUDE.md` governs where it differs from the general doctrine, and names this repository's rule.
- [ ] No sentence says a merge into `develop` must always be a human decision.
- [ ] Every line named in Context is checked, and each is amended or judged still correct in the report.
- [ ] The agent-never-merges-its-own-work statements are unchanged.
- [ ] Only `strategic_model_init_material.md` and the report change.
- [ ] `scripts/gate.sh` passes.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `docs/T-0014-amend-the-oap-method-text-so-claude-md-governs`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0014.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0014.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0014
```
