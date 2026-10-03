<!-- GENERATED FILE — do not edit by hand.
     Regenerate with: python .agents/tasks/scripts/backlog.py reindex
     The task files in .agents/tasks/ are the source of truth. -->

# Task Backlog

9 task(s). Generated 2026-10-03.

| open: 4 | in_progress: 1 | blocked: 0 | review: 0 | done: 4 | abandoned: 0 |
|---|---|---|---|---|---|

## Tasks

| ID | Title | Status | Prio | Type | Depends on | Report |
|---|---|---|---|---|---|---|
| T-0001 | [Enforce report writing as a pipeline gate, not an agent courtesy](T-0001-enforce-report-writing-as-a-pipeline-gate-not.md) | open | high | chore | T-0003, T-0005 | — |
| T-0002 | [Port git-atomic task filing and backlog fixes](T-0002-port-git-atomic-task-filing-and-backlog-fixes.md) | done | high | fix | — | [report](reports/T-0002.md) |
| T-0003 | [Port report validation, harvest and housekeep checks](T-0003-port-report-validation-harvest-and-housekeep.md) | in_progress | high | fix | T-0002 | — |
| T-0004 | [Reconcile hooks and dev tooling with the merge and push rules](T-0004-reconcile-hooks-and-dev-tooling-with-the-merge.md) | done | high | feat | — | [report](reports/T-0004.md) |
| T-0005 | [Port agent rules, process docs and orchestrator-merge rules](T-0005-port-agent-rules-process-docs-and-orchestrator.md) | open | high | docs | T-0002, T-0003, T-0004, T-0006 | — |
| T-0007 | [Make task scripts executable](T-0007-make-task-scripts-executable.md) | done | high | fix | — | [report](reports/T-0007.md) |
| T-0006 | [Add a devcontainer](T-0006-add-a-devcontainer.md) | done | medium | feat | — | [report](reports/T-0006.md) |
| T-0008 | [Fix pre-commit re-staging for unusual filenames](T-0008-fix-pre-commit-re-staging-for-unusual-filenames.md) | open | medium | fix | — | — |
| T-0009 | [Drop shebangs from private task script helpers](T-0009-drop-shebangs-from-private-task-script-helpers.md) | open | low | chore | — | — |

## Ready to dispatch

Dependencies satisfied, not yet started:

- **T-0008** Fix pre-commit re-staging for unusual filenames — `.husky/pre-commit`, `tests/test_hooks.py`
- **T-0009** Drop shebangs from private task script helpers — `.agents/tasks/scripts`, `tests/test_task_scripts.py`

Suggested conflict-free parallel batch: T-0008

## Waiting on dependencies

- **T-0001** Enforce report writing as a pipeline gate, not an agent courtesy — needs T-0003, T-0005
- **T-0005** Port agent rules, process docs and orchestrator-merge rules — needs T-0002, T-0003, T-0004, T-0006
