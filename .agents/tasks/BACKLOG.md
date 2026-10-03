<!-- GENERATED FILE — do not edit by hand.
     Regenerate with: python .agents/tasks/scripts/backlog.py reindex
     The task files in .agents/tasks/ are the source of truth. -->

# Task Backlog

6 task(s). Generated 2026-10-03.

| open: 3 | in_progress: 3 | blocked: 0 | review: 0 | done: 0 | abandoned: 0 |
|---|---|---|---|---|---|

## Tasks

| ID | Title | Status | Prio | Type | Depends on | Report |
|---|---|---|---|---|---|---|
| T-0001 | [Enforce report writing as a pipeline gate, not an agent courtesy](T-0001-enforce-report-writing-as-a-pipeline-gate-not.md) | open | high | chore | T-0003, T-0005 | — |
| T-0002 | [Port git-atomic task filing and backlog fixes](T-0002-port-git-atomic-task-filing-and-backlog-fixes.md) | in_progress | high | fix | — | — |
| T-0003 | [Port report validation, harvest and housekeep checks](T-0003-port-report-validation-harvest-and-housekeep.md) | open | high | fix | T-0002 | — |
| T-0004 | [Reconcile hooks and dev tooling with the merge and push rules](T-0004-reconcile-hooks-and-dev-tooling-with-the-merge.md) | in_progress | high | feat | — | — |
| T-0005 | [Port agent rules, process docs and orchestrator-merge rules](T-0005-port-agent-rules-process-docs-and-orchestrator.md) | open | high | docs | T-0002, T-0003, T-0004, T-0006 | — |
| T-0006 | [Add a devcontainer](T-0006-add-a-devcontainer.md) | in_progress | medium | feat | — | — |

## Ready to dispatch

*Nothing ready — every open task is blocked or already in flight.*

## Waiting on dependencies

- **T-0001** Enforce report writing as a pipeline gate, not an agent courtesy — needs T-0003, T-0005
- **T-0003** Port report validation, harvest and housekeep checks — needs T-0002
- **T-0005** Port agent rules, process docs and orchestrator-merge rules — needs T-0002, T-0003, T-0004, T-0006
