# Batch merge grant, 2026-10-03

The owner granted the orchestrator merge authority for this batch, in writing, in the dispatch
instruction of 2026-10-03:

> I grant you merge authority for this batch. Also granted the fixups. Run other tasks until
> finished and merge. All merge and decision authorisation is granted. Use recommended decisions
> if followups or fixes are needed. The goal is to finish all tasks with no new followups.

Earlier in the same session the owner approved the Husky hook change (T-0008) and the
`scripts/gitflow.sh` change (T-0011).

## Batch

T-0001, T-0008, T-0009, T-0010, T-0011, and any task filed to resolve a finding of these.

## Terms

- The orchestrator follows `.agents/README.md` § "Orchestrator merges (opt-in per batch)".
- The grant covers this batch only.
- "Ask first" rules in `CLAUDE.md` still stand, except where the owner approved the specific
  change named above or filed a task for it under this grant. No force-push, no tag edits, no
  remote branch deletion.
- A task that fails verification three times is `blocked` and not merged.

## Task-file edits under this grant

The owner's "all merge and decision authorisation is granted" covers the orchestrator's task-file
edits listed in `CLAUDE.md` § "Batch runs: orchestrator merges": `task.py set-status`, widening a
task's `touches` with the reason recorded, and a pre-dispatch amendment of a task file.

## Later instruction: merge by default (T-0013)

The owner then wrote, later on 2026-10-03:

> Merge into develop must be by default granted to agents. The independent verification must be
> done by another agent. Human is involved only if breaking changes.
> ... Agree on dropping the per-task "must not start without approval" clauses from task files.

T-0013 writes this into `CLAUDE.md` and `.agents/README.md`. This instruction is the grant for
T-0013 itself, which the orchestrator merges after an independent verify. Until T-0013 is merged,
the grant above covers only the first batch.
