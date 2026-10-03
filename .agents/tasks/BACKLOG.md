<!-- GENERATED FILE — do not edit by hand.
     Regenerate with: python .agents/tasks/scripts/backlog.py reindex
     The task files in .agents/tasks/ are the source of truth. -->

# Task Backlog

6 task(s). Generated 2026-10-03.

| open: 6 | in_progress: 0 | blocked: 0 | review: 0 | done: 0 | abandoned: 0 |
|---|---|---|---|---|---|

## Tasks

| ID | Title | Status | Prio | Type | Depends on | Report |
|---|---|---|---|---|---|---|
| T-0001 | [Enforce report writing as a pipeline gate, not an agent courtesy](T-0001-enforce-report-writing-as-a-pipeline-gate-not.md) | open | high | chore | T-0003, T-0005 | — |
| T-0002 | [Port git-atomic task filing and backlog fixes](T-0002-port-git-atomic-task-filing-and-backlog-fixes.md) | open | high | fix | — | — |
| T-0003 | [Port report validation, harvest and housekeep checks](T-0003-port-report-validation-harvest-and-housekeep.md) | open | high | fix | T-0002 | — |
| T-0004 | [Reconcile hooks and dev tooling with the merge and push rules](T-0004-reconcile-hooks-and-dev-tooling-with-the-merge.md) | open | high | feat | — | — |
| T-0005 | [Port agent rules, process docs and orchestrator-merge rules](T-0005-port-agent-rules-process-docs-and-orchestrator.md) | open | high | docs | T-0002, T-0003, T-0004, T-0006 | — |
| T-0006 | [Add a devcontainer](T-0006-add-a-devcontainer.md) | open | medium | feat | — | — |

## Ready to dispatch

Dependencies satisfied, not yet started:

- **T-0002** Port git-atomic task filing and backlog fixes — `.agents/tasks/scripts/_git_publish.py`, `.agents/tasks/scripts/_ids.py`, `.agents/tasks/scripts/_schema.py`, `.agents/tasks/scripts/task.py`, `.agents/tasks/scripts/backlog.py`, `tests/test_task_scripts.py`
- **T-0004** Reconcile hooks and dev tooling with the merge and push rules — `.husky`, `scripts`, `DEV_TOOLING_SPEC.md`, `tests/test_hooks.py`, `tests/test_commit_lint.py`
- **T-0006** Add a devcontainer — `.devcontainer`

Suggested conflict-free parallel batch: T-0002, T-0004, T-0006

## Waiting on dependencies

- **T-0001** Enforce report writing as a pipeline gate, not an agent courtesy — needs T-0003, T-0005
- **T-0003** Port report validation, harvest and housekeep checks — needs T-0002
- **T-0005** Port agent rules, process docs and orchestrator-merge rules — needs T-0002, T-0003, T-0004, T-0006
