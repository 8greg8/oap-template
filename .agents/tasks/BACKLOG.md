<!-- GENERATED FILE — do not edit by hand.
     Regenerate with: python .agents/tasks/scripts/backlog.py reindex
     The task files in .agents/tasks/ are the source of truth. -->

# Task Backlog

20 task(s). Generated 2026-10-03.

| open: 4 | in_progress: 1 | blocked: 0 | review: 0 | done: 15 | abandoned: 0 |
|---|---|---|---|---|---|

## Tasks

| ID | Title | Status | Prio | Type | Depends on | Report |
|---|---|---|---|---|---|---|
| T-0001 | [Enforce report writing as a pipeline gate, not an agent courtesy](T-0001-enforce-report-writing-as-a-pipeline-gate-not.md) | done | high | chore | T-0003, T-0005 | [report](reports/T-0001.md) |
| T-0002 | [Port git-atomic task filing and backlog fixes](T-0002-port-git-atomic-task-filing-and-backlog-fixes.md) | done | high | fix | — | [report](reports/T-0002.md) |
| T-0003 | [Port report validation, harvest and housekeep checks](T-0003-port-report-validation-harvest-and-housekeep.md) | done | high | fix | T-0002 | [report](reports/T-0003.md) |
| T-0004 | [Reconcile hooks and dev tooling with the merge and push rules](T-0004-reconcile-hooks-and-dev-tooling-with-the-merge.md) | done | high | feat | — | [report](reports/T-0004.md) |
| T-0005 | [Port agent rules, process docs and orchestrator-merge rules](T-0005-port-agent-rules-process-docs-and-orchestrator.md) | done | high | docs | T-0002, T-0003, T-0004, T-0006 | [report](reports/T-0005.md) |
| T-0007 | [Make task scripts executable](T-0007-make-task-scripts-executable.md) | done | high | fix | — | [report](reports/T-0007.md) |
| T-0013 | [Make orchestrator merge into develop the default](T-0013-make-orchestrator-merge-into-develop-the-default.md) | done | high | docs | — | [report](reports/T-0013.md) |
| T-0019 | [Scrub private references and attribute the method text](T-0019-scrub-private-references-and-attribute-the.md) | done | high | docs | — | [report](reports/T-0019.md) |
| T-0020 | [Rewrite history into a clean public repository copy](T-0020-rewrite-history-into-a-clean-public-repository.md) | open | high | chore | T-0015, T-0016, T-0017, T-0018, T-0019 | — |
| T-0006 | [Add a devcontainer](T-0006-add-a-devcontainer.md) | done | medium | feat | — | [report](reports/T-0006.md) |
| T-0008 | [Fix pre-commit re-staging for unusual filenames](T-0008-fix-pre-commit-re-staging-for-unusual-filenames.md) | done | medium | fix | — | [report](reports/T-0008.md) |
| T-0012 | [Make staged-file handling NUL-safe in gate and autofix scripts](T-0012-make-staged-file-handling-nul-safe-in-gate-and.md) | done | medium | fix | — | [report](reports/T-0012.md) |
| T-0014 | [Amend the OAP method text so CLAUDE.md governs merge authority](T-0014-amend-the-oap-method-text-so-claude-md-governs.md) | done | medium | docs | — | [report](reports/T-0014.md) |
| T-0015 | [Add init script CLI, preconditions, names and rename step](T-0015-add-init-script-cli-preconditions-names-and.md) | in_progress | medium | feat | — | — |
| T-0016 | [Reset task state in the init script](T-0016-reset-task-state-in-the-init-script.md) | open | medium | feat | T-0015 | — |
| T-0017 | [Seed project files in the init script](T-0017-seed-project-files-in-the-init-script.md) | open | medium | feat | T-0016 | — |
| T-0018 | [Finish the init script with gate, commit, branch and self-removal](T-0018-finish-the-init-script-with-gate-commit-branch.md) | open | medium | feat | T-0017 | — |
| T-0009 | [Drop shebangs from private task script helpers](T-0009-drop-shebangs-from-private-task-script-helpers.md) | done | low | chore | — | [report](reports/T-0009.md) |
| T-0010 | [Fix agent-doc wording and stale AGENTS.md references](T-0010-fix-agent-doc-wording-and-stale-agents-md.md) | done | low | docs | — | [report](reports/T-0010.md) |
| T-0011 | [Support docs and chore task branches in gitflow and fix housekeep worktrees](T-0011-support-docs-and-chore-task-branches-in-gitflow.md) | done | low | fix | — | [report](reports/T-0011.md) |

## Ready to dispatch

*Nothing ready — every open task is blocked or already in flight.*

## Waiting on dependencies

- **T-0020** Rewrite history into a clean public repository copy — needs T-0015, T-0016, T-0017, T-0018, T-0019
- **T-0016** Reset task state in the init script — needs T-0015
- **T-0017** Seed project files in the init script — needs T-0016
- **T-0018** Finish the init script with gate, commit, branch and self-removal — needs T-0017
