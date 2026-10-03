<!-- GENERATED FILE — do not edit by hand.
     Regenerate with: python .agents/tasks/scripts/backlog.py reindex
     The task files in .agents/tasks/ are the source of truth. -->

# Task Backlog

11 task(s). Generated 2026-10-03.

| open: 3 | in_progress: 0 | blocked: 0 | review: 1 | done: 7 | abandoned: 0 |
|---|---|---|---|---|---|

## Tasks

| ID | Title | Status | Prio | Type | Depends on | Report |
|---|---|---|---|---|---|---|
| T-0001 | [Enforce report writing as a pipeline gate, not an agent courtesy](T-0001-enforce-report-writing-as-a-pipeline-gate-not.md) | review | high | chore | T-0003, T-0005 | — |
| T-0002 | [Port git-atomic task filing and backlog fixes](T-0002-port-git-atomic-task-filing-and-backlog-fixes.md) | done | high | fix | — | [report](reports/T-0002.md) |
| T-0003 | [Port report validation, harvest and housekeep checks](T-0003-port-report-validation-harvest-and-housekeep.md) | done | high | fix | T-0002 | [report](reports/T-0003.md) |
| T-0004 | [Reconcile hooks and dev tooling with the merge and push rules](T-0004-reconcile-hooks-and-dev-tooling-with-the-merge.md) | done | high | feat | — | [report](reports/T-0004.md) |
| T-0005 | [Port agent rules, process docs and orchestrator-merge rules](T-0005-port-agent-rules-process-docs-and-orchestrator.md) | done | high | docs | T-0002, T-0003, T-0004, T-0006 | [report](reports/T-0005.md) |
| T-0007 | [Make task scripts executable](T-0007-make-task-scripts-executable.md) | done | high | fix | — | [report](reports/T-0007.md) |
| T-0006 | [Add a devcontainer](T-0006-add-a-devcontainer.md) | done | medium | feat | — | [report](reports/T-0006.md) |
| T-0008 | [Fix pre-commit re-staging for unusual filenames](T-0008-fix-pre-commit-re-staging-for-unusual-filenames.md) | done | medium | fix | — | [report](reports/T-0008.md) |
| T-0009 | [Drop shebangs from private task script helpers](T-0009-drop-shebangs-from-private-task-script-helpers.md) | open | low | chore | — | — |
| T-0010 | [Fix agent-doc wording and stale AGENTS.md references](T-0010-fix-agent-doc-wording-and-stale-agents-md.md) | open | low | docs | — | — |
| T-0011 | [Support docs and chore task branches in gitflow and fix housekeep worktrees](T-0011-support-docs-and-chore-task-branches-in-gitflow.md) | open | low | fix | — | — |

## Ready to dispatch

Dependencies satisfied, not yet started:

- **T-0009** Drop shebangs from private task script helpers — `.agents/tasks/scripts`, `tests/test_task_scripts.py`
- **T-0010** Fix agent-doc wording and stale AGENTS.md references — `CLAUDE.md`, `CONTRIBUTING.md`, `.agents/README.md`, `DEV_TOOLING_SPEC.md`
- **T-0011** Support docs and chore task branches in gitflow and fix housekeep worktrees — `scripts/gitflow.sh`, `.agents/tasks/scripts/housekeep.py`, `tests/test_report_scripts.py`, `tests/test_hooks.py`

Suggested conflict-free parallel batch: 
