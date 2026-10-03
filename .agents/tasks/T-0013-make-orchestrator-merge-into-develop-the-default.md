---
id: T-0013
title: Make orchestrator merge into develop the default
status: done
type: docs
priority: high
depends_on: []
touches: [CLAUDE.md, .agents/README.md, CONTRIBUTING.md, .agents/tasks/templates/task.md, README.md]
created: 2026-10-03
report: reports/T-0013.md
---

# T-0013 — Make orchestrator merge into develop the default

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

Merging a verified task branch into `develop` is the orchestrator's default authority, with no per-batch grant. The independent verify is done by an agent other than the executor. A human is involved only for breaking changes and the existing Ask-first items. Executors still push their branch and never merge their own work.

## Context / current verified state

- Owner instruction, 2026-10-03: "Merge into develop must be by default granted to agents. The independent verification must be done by another agent. Human is involved only if breaking changes." The owner also agreed to drop per-task "must not start without approval" clauses from task files.
- `CLAUDE.md` line 66 says an executor pushes and leaves the merge to the orchestrator or human. Its section "Batch runs: orchestrator merges" says the grant is opt-in per batch and never the default.
- `.agents/README.md` execution-loop step 7 says "A human reviews and merges", and its section "Orchestrator merges (opt-in per batch)" repeats the opt-in rule.
- `.agents/tasks/templates/task.md` line 76 tells the executor not to merge. That stays true.
- `strategic_model_init_material.md` (the OAP method text) lists "merge to protected branches" as a human approval gate and says "treat every merge as a human decision". This task does not edit that file. Report the conflict in the report.
- Re-check each point against the current files and report any discrepancy.

## Scope

- `CLAUDE.md`: rewrite the push-but-do-not-merge bullet, the Autonomy list entry on merging, and the section "Batch runs: orchestrator merges" so that:
  - the orchestrator merges a task branch into `develop` by default once a verify by a different agent has passed, with no written grant needed;
  - an executor never merges its own work, and never verifies its own change;
  - the retained safeguards stay: the full gate on `develop` after the merge, revert if red after pushing, a task is `blocked` after three failed verify rounds, no force-push, and the three permitted orchestrator edits to task files;
  - a human decides only for a breaking change and for every item in "Ask first", which this task does not change;
  - merges into `main`, tags and releases remain human steps, outside this default.
- Define a breaking change once, in `CLAUDE.md`: a change that is, or should be, marked breaking under Conventional Commits (`!` or a `BREAKING CHANGE:` footer), meaning it changes a contract downstream projects of this template rely on without backward compatibility. Name examples: the CLI arguments or exit codes of the `.agents/tasks/scripts/` and `scripts/` tools, the task and report file schemas, hook behavior, and the branching or merge rules.
- State in `CLAUDE.md` that task files do not restate Ask-first approvals or add "must not start without approval" clauses; `CLAUDE.md` governs.
- `.agents/README.md`: update execution-loop step 7 and its sentence about PR/MR, replace the section "Orchestrator merges (opt-in per batch)" with the default flow (verify, resolve, merge, rerun the gate), and keep "Rules for every batch" that still apply. Remove wording that makes a grant the precondition.
- `CONTRIBUTING.md`: update the sentence about "a human or orchestrator merges" and any other statement that a grant or a human is the default merger.
- `.agents/tasks/templates/task.md`: keep "Do not merge" for the executor; add that the orchestrator merges after an independent verify.

## Non-goals

- Do not change the Ask-first list, the verify requirement, or the report gate.
- Do not change any script, hook, test, CI file or `pyproject.toml`.
- Do not edit `strategic_model_init_material.md`; report the conflict instead.
- Do not edit any existing task file, including the two done tasks that carry an approval clause (T-0008, T-0011); they are closed records.
- Do not grant or describe merge authority for `main`, release tags or hotfix back-merges.
- Do not edit `.agents/plans/` files; the orchestrator updates the batch review plan.

## Files to inspect

- `CLAUDE.md`, `.agents/README.md`, `CONTRIBUTING.md`, `.agents/tasks/templates/task.md`
- `.agents/plans/2026-10-03-batch-merge-grant.md` (to see what the old grant said)
- `strategic_model_init_material.md` lines near "Approval gates" and "Human complacency" (read only)

## Required behavior

Docs only. After the change, `CLAUDE.md` and `.agents/README.md` say the same thing about merging, once: the orchestrator merges into `develop` by default after a passed verify by a different agent; a human is needed only for a breaking change and for Ask-first items. No sentence still says the grant is opt-in, never the default, or that a human merges by default. Every changed sentence keeps its other meaning.

## Tests required

Run `scripts/gate.sh` and `python .agents/tasks/scripts/task.py validate`. Run `grep -n -i "opt-in\|never the default\|a human merges\|human reviews and merges" CLAUDE.md .agents/README.md CONTRIBUTING.md` and report each remaining hit with a judgment.

## Documentation required

The changed docs are the deliverable.

## Acceptance criteria

- [ ] `CLAUDE.md` and `.agents/README.md` state that the orchestrator merges into `develop` by default after a passed verify by a different agent.
- [ ] Both name the human-only cases: breaking changes and every Ask-first item. `CLAUDE.md` defines a breaking change once.
- [ ] Executors still never merge or verify their own work.
- [ ] Merges into `main`, tags and releases are stated to remain human steps.
- [ ] The safeguards listed in Scope are kept, and the Ask-first list is byte-identical to before.
- [ ] No remaining sentence in the three docs makes a grant or a human the default merger.
- [ ] The report states the conflict with `strategic_model_init_material.md`.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches` plus the report.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `docs/T-0013-make-orchestrator-merge-into-develop-the-default`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0013.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0013.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0013
```
