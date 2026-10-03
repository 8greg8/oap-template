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
- **Filing a task is git-atomic and worktree-free, and comes before creating any worktree for
  it.** Run `task.py new` from the primary checkout on `develop`. It syncs to `origin/develop`,
  allocates the ID, writes the file, and commits and pushes it in the same step, with no branch or
  worktree involved. Only after the task is filed and visible on `develop` do you create the
  worktree and branch for its execution (see `.agents/README.md`). If two agents file a task at
  nearly the same time, the losing push resyncs, reallocates the next free ID and retries, so a
  race never surfaces as a duplicate ID or a merge conflict. Pass `--no-publish` only in
  scripting or testing contexts where writing the file locally without touching git is what is
  wanted.
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
  considering the task finished. This is an enforced gate, not a convention:
  `task.py set-status` refuses `review`, `blocked`, `done` and `abandoned` with a non-zero exit
  unless `.agents/tasks/reports/T-00XX.md` exists and passes the same check as
  `report.py validate`. `open` and `in_progress` are not gated.
- **When executing a task from the backlog, push but do not merge.** Commit the report on the
  task's own branch and push it; leave the merge to `develop` and any PR/MR to the orchestrator or
  human, per `.agents/README.md`'s execution loop. This overrides the general autonomy below, which
  covers a standalone (non-batched) change with no task file. Only an owner grant for a named
  batch changes this (§ "Batch runs: orchestrator merges").
- **Repair work is narrower than feature work.** If a task is fixing a specific broken PR or failing
  check, don't fold in new feature behavior — repair only what's named, report the exact cause and
  fix.

## Autonomy — what agents do without asking

Within a single task, an agent proceeds end-to-end without stopping for confirmation through:

- Creating a worktree and branch for the task (`scripts/gitflow.sh`, see `CONTRIBUTING.md` §
  Worktrees for agents).
- Implementing the change.
- Running (or being run through) the verify/resolve loop until clean.
- Adding a dev-only dependency (linting/testing tooling) needed to do the above.
- Writing the commit per Conventional Commits rules in `CONTRIBUTING.md`.
- Merging to the branch's correct target (`develop` or `main`) and pushing, per branch type —
  **unless** this is a task dispatched from `.agents/tasks/`, in which case push only and leave the
  merge to the orchestrator/human (see § Working unit: the task).
- Removing a worktree and deleting its local branch once that branch is confirmed merged into its
  target (`git worktree remove`, `git branch -d`). This is routine cleanup, not a destructive
  action requiring confirmation; `git branch -d` refuses on an unmerged branch, so the check is
  built into the command.

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
- Any change to `pyproject.toml` `[tool]` sections governing lint/type/test behavior (what
  `ruff`/`ty`/`pytest` actually check). This gates every agent's work, so changes need a human in
  the loop. The same holds for changes to `scripts/` (gate commands in `scripts/config/gate.sh`,
  `scripts/gate.sh`, lint/type/test config, `scripts/commit_lint.py`, release tooling such as
  `scripts/release.py`): they control what the gate checks and how releases are cut, so they
  still need a human. This does **not** cover Husky hook config (`.husky/`, hook-runner wiring in
  `package.json`, commit-message-linter config) or `.github/workflows/` CI pipeline files. Those
  follow normal task autonomy when a task file's own Scope already names them; they govern
  *when* the existing gate runs, not what it checks. An agent that wants to touch
  Husky or CI-workflow config outside what its current task file scopes still needs a task file
  first, per § "Working unit: the task".
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

## Chatter vs. persisted output

Both subagent-dispatch paths in this repo, the task loop's dispatched subagent
(`.agents/README.md` § "The execution loop", step 3) and the independent verify agent
(`CONTRIBUTING.md` § "Agent verify/resolve workflow", step 2), may use terse, caveman-style
chatter (see the user-level `caveman` skill, if active) for anything that is *not* written to a
tracked file: progress narration, intermediate tool-result summaries, and verify pass/fail
narration as it happens.

This terseness never applies to anything a subagent writes to disk. In particular, the following
stay full, plain prose, always:

- commit messages (per the Conventional Commits rules in `CONTRIBUTING.md`);
- the task file (`.agents/tasks/T-00XX-*.md`);
- the report file (`.agents/tasks/reports/T-00XX.md`), including the exact status words
  (passed/failed/skipped/not run/blocked) required above.

## Concise prose in task and report files

Task files and report files must use concise prose: short sentences, no filler, and no narration
of process that the diff, the commit, or the required status words already convey. This keeps both
documents fast to read for the next agent or human who has to verify the work.

This is not the chatter compression described in § "Chatter vs. persisted output" above. That
section covers unpersisted narration only, and task and report files are explicitly excluded from
it. Concise prose still reads as normal, grammatical English; it just carries no padding.

Every literal required token stays intact and unabbreviated regardless of this requirement: the
exact status words (passed/failed/skipped/not run/blocked), spec citations, the full content of a
Non-goals section, and every acceptance-criteria checklist item. Tightening prose never means
cutting or paraphrasing these.

## Spec-first test authoring: never fit an assertion to observed output

Applies to any `type: test` task, and to any other task whose Scope says a behavior is derived
from the specification under `docs/spec/` rather than from the implementation under
`src/<repo_name>/`. When sources disagree, the order is the spec, then the code.

**The trap:** writing a spec-derived assertion, running it, watching it fail, and rewriting the
expected value to match whatever the test run actually printed is *not* blind testing, even
though no source file was ever opened. A pytest failure's expected-vs-actual diff carries the
same information reading the source would, through a different channel. Iterating that loop to
green produces a suite that is tautologically true of whatever the code currently does, not a
test of whether the code matches the spec, and silently destroys the one signal this exercise
exists to produce: a documented divergence between spec and implementation.

Three categories, handled differently:

1. **Expected values and fixture shapes** must come from the spec text alone, decided before
   ever running anything. If a task file quotes spec text, that quote is the source of truth; do
   not "correct" it because a test run suggested otherwise.
2. **Mechanical test-authoring mistakes** (an import error, a stale hardcoded path after a
   fixture changed shape, a subprocess invoked with the wrong flag) are fine to iterate on
   freely; this is fixing your own test code, not discovering business logic.
3. **A spec-derived, business-logic assertion that fails against the real code** is not edited
   to match what was observed. That failure is the finding. Keep the spec-derived expectation,
   mark the case `xfail(strict=True)` with a `reason=` stating what the spec says versus what is
   actually true, and write it up in the report as a real divergence. Only remove an xfail when
   spec text (or a cited prior report) gives independent reason to expect it now passes, never
   because a run showed it passing.

A task whose report cannot state, per new assertion, "this came from spec text" or "this is a
pinned divergence with reason X" has not followed this discipline, whatever its pytest output
says.

For blind authoring, `.devcontainer/spec-blind/` is a second dev container configuration that
shadows `src/` with an empty tmpfs, so the implementation cannot be read. It is for authoring
only; tests cannot run there. See `.devcontainer/README.md`.

## Batch runs: orchestrator merges

By default an executor pushes its task branch and a human merges it. The owner may grant the
orchestrator merge authority for a named batch of tasks, in writing (a plan under
`.agents/plans/` or the dispatch instruction). The grant is opt-in per batch, covers only that
batch, and is never the default. Every rule under "Ask first" still applies; a task that can only
be finished by crossing one is set `blocked`.

Under a grant, the orchestrator follows `.agents/README.md` § "The execution loop", including the
orchestrator-merge steps. It never merges without a passed independent verify, never
force-pushes, and never edits a task file except through `task.py set-status`.

## File boundaries

- Never read, log, or modify `.env` files or anything matching a secrets pattern.
- Never hand-edit `uv.lock` — only `uv` commands (per `PYTHON_CONVENTIONS.md`) may change it.
