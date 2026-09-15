# Agent Instructions

This repo is built to be worked on by autonomous coding agents. Required reading before making any
change:

- [`CONTRIBUTING.md`](CONTRIBUTING.md) — branching, commits, versioning, and the verify/resolve/
  merge workflow. This is the process every agent follows, not just a human guideline.
- [`PYTHON_CONVENTIONS.md`](PYTHON_CONVENTIONS.md) — environment setup, commands, project layout,
  dependency management, and code style.
- [`.agents/README.md`](.agents/README.md) — the task/report/backlog workflow and its tooling
  (`task.py`, `backlog.py`, `report.py`, `housekeep.py`), described below at the level needed to
  act on it; that file has the full command reference.
- [`.agents/tasks/templates/task.md`](.agents/tasks/templates/task.md) and
  [`.agents/tasks/templates/report.md`](.agents/tasks/templates/report.md) — the unit of work and
  its required output.

This file adds agent-only behavioral rules on top of those. It does not repeat their content —
if something is covered there, follow it from there.

## Working unit: the task

Work happens as **tasks**, not open-ended requests. A task is PR-sized: one worktree, one branch,
one agent context, one reviewable change. This only works once there's a real specification or
architecture to decompose — if the thing being asked for doesn't have a clear goal and scope yet,
that's a discovery/design conversation with the human first, not a task to start coding against.

Tasks are tracked as files, not just prose in a chat — see `.agents/README.md` for the full model.
In brief:

- **Before implementing anything non-trivial**, create a task file with
  `python .agents/tasks/scripts/task.py new -t "<title>" -T <type> -f <paths...>` (schema in
  `.agents/tasks/templates/task.md`) — goal, scope, explicit non-goals, files to inspect, required
  tests. A one-line request like "fix the bug" or "add the feature" is not a task; turn it into one
  (and confirm scope with the human if genuinely ambiguous) before writing code. Run
  `task.py validate` before starting work on it.
- **Non-goals are load-bearing, not decoration.** Agents default toward being helpful, which left
  unchecked becomes scope creep. If a task doesn't name a boundary, don't assume it's permission —
  ask, or stay narrow. `task.py validate` rejects a task with an empty Non-goals section for this
  reason.
- **`touches` is what makes parallel tasks safe.** It declares the files/paths a task will modify;
  `backlog.py ready --parallel N` uses it to pick a conflict-free batch. Keep a task's actual edits
  inside its declared `touches` — `housekeep.py touches` audits this after the fact.
- **One task, one context.** Don't carry assumptions from a previous task into a new one without
  re-verifying current repository state — a task's "Context / current verified state" section
  should be checked against reality, not trusted from memory or an earlier handoff.
- **Every task ends with a report**, created via `python .agents/tasks/scripts/report.py new
  T-00XX` and fully filled out (schema in `.agents/tasks/templates/report.md`). The report is the
  interface between what the agent did and what anyone — human or another agent — can verify
  afterward. Use exact status words (passed / failed / skipped / not run / blocked) instead of
  vague claims like "all tests passed" or "looks good." Run `report.py validate T-00XX` before
  considering the task finished.
- **When executing a task from the backlog, push but do not merge.** Commit the report on the
  task's own branch and push it; leave the merge to `develop` and any PR/MR to the orchestrator or
  human, per `.agents/README.md`'s execution loop. This overrides the general autonomy below, which
  covers a standalone (non-batched) change with no task file.
- **Repair work is narrower than feature work.** If a task is fixing a specific broken PR or failing
  check, don't fold in new feature behavior — repair only what's named, report the exact cause and
  fix.

## Autonomy — what agents do without asking

Within a single task, an agent proceeds end-to-end without stopping for confirmation through:

- Creating a worktree and branch for the task.
- Implementing the change.
- Running (or being run through) the verify/resolve loop until clean.
- Adding a dev-only dependency (linting/testing tooling) needed to do the above.
- Writing the commit per Conventional Commits rules in `CONTRIBUTING.md`.
- Merging to the branch's correct target (`develop` or `main`) and pushing, per branch type —
  **unless** this is a task dispatched from `.agents/tasks/`, in which case push only and leave the
  merge to the orchestrator/human (see § Working unit: the task).

This is the default flow — do not pause mid-workflow to ask "should I commit now?" or "should I
merge now?" if the verify/resolve loop is clean and the branch/commit rules in `CONTRIBUTING.md`
are being followed exactly.

## Ask first — what agents never do unilaterally

- Force-pushing, `git reset --hard`, rewriting or dropping commits that already exist on a shared
  branch (`main`, `develop`), or deleting remote branches/tags.
- Cutting a release tag by hand (outside the tagging step defined in `CONTRIBUTING.md`) or editing
  an existing tag.
- Adding a new **runtime** dependency not clearly required by the task, or upgrading a dependency
  across a major version.
- Any change to CI/hook configuration (Husky config, `.github/workflows/`, `pyproject.toml`
  `[tool]` sections governing lint/type/test behavior) — these gate every agent's work, so changes
  need a human in the loop.
- Restructuring `src/<repo_name>/` into multiple `uv` workspace packages (see
  `PYTHON_CONVENTIONS.md`) — that's an architectural decision, not something to do as a side effect
  of a task. If the repo does grow into a multi-package workspace, treat each member package as its
  own ownership boundary and don't reach into another package's internals uninvited.
- Merging a `hotfix/*` branch's back-merge into `develop` in a way that silently overwrites
  `develop`-only work — if the back-merge produces non-trivial conflicts, stop and ask rather than
  resolving them by guessing intent.
- Starting implementation on a non-trivial or ambiguous request without first shaping it into a task
  (see § Working unit: the task) — if goal or scope genuinely can't be determined from the request
  and the repo, ask rather than guessing and building on the wrong assumption.

If a task's instructions conflict with one of these boundaries, stop and ask rather than
reinterpreting the instructions to fit.

## Verification is not optional

An agent never certifies its own change as done. The verify step in `CONTRIBUTING.md`'s
verify/resolve loop must be run by an independent agent invocation (fresh context) — an agent
should not skip straight from "I made the edit" to "I'm committing" without that separate check
having actually run and reported clean. That outcome then belongs in the task's report (see
`.agents/tasks/templates/report.md`), gate by gate — not summarized away.

## File boundaries

- Never read, log, or modify `.env` files or anything matching a secrets pattern.
- Never hand-edit `uv.lock` — only `uv` commands (per `PYTHON_CONVENTIONS.md`) may change it.
