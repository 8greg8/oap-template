# Agent Task Workflow

Bounded work orders for coding agents, designed so several tasks can run in
parallel on isolated git worktrees without colliding.

The model is the one described in `strategic_model_init_material.md`
(Orchestrated Agentic Programming): a **task file is a work order**, a
**report is the executor's evidence**, the **backlog is project state**, and
`LESSONS.md` is durable memory across tasks.

```
.agents/
  README.md            this file
  LESSONS.md            GENERATED — harvested from reports
  tasks/
    BACKLOG.md         GENERATED — index of all tasks
    T-0001-*.md        one work order per file — the source of truth
    reports/T-0001.md  one report per completed task
    templates/         task.md, report.md
    scripts/           task.py, backlog.py, report.py, housekeep.py (+ private helpers)
    .counter           ID counter, guarded by a lock
```

## The rules that make parallelism safe

1. **Task files are the source of truth.** `BACKLOG.md` and `LESSONS.md` are
   generated artifacts — never hand-edit them; they will be overwritten.
2. **Only the orchestrator writes task state.** A subagent executing a task
   writes exactly one file under `.agents/`: its own report, on its own branch.
   It never edits `BACKLOG.md`, its own task file, or any other task's file.
   This removes concurrent-write races structurally instead of defending
   against them.
3. **`depends_on` gates *when* a task may start.** A task is dispatchable only
   once every dependency has reached `done`.
4. **`touches` gates *what may run alongside it*.** Two tasks whose declared
   file scopes overlap must not run in parallel, or their branches will conflict
   at merge. `backlog.py ready --parallel N` enforces this. A task with an empty
   `touches` list is treated as touching everything and never batches.

## Commands

The scripts are **stdlib-only** and run without a virtualenv:

```bash
python .agents/tasks/scripts/task.py new -t "Fix the thing" -T fix -p high \
    -d T-0001 -f src/<repo_name>/some_module.py tests/test_thing.py
python .agents/tasks/scripts/task.py show T-0004
python .agents/tasks/scripts/task.py set-status T-0004 in_progress
python .agents/tasks/scripts/task.py validate

python .agents/tasks/scripts/backlog.py reindex
python .agents/tasks/scripts/backlog.py list --status open
python .agents/tasks/scripts/backlog.py ready --parallel 3 -v
python .agents/tasks/scripts/backlog.py stats

python .agents/tasks/scripts/report.py new T-0004
python .agents/tasks/scripts/report.py harvest
python .agents/tasks/scripts/report.py lessons --tag <tag>
python .agents/tasks/scripts/report.py validate T-0004
```

`task.py set-status` to `review`, `blocked`, `done` or `abandoned` requires a
report that passes `report.py validate` (see § Task lifecycle).

`task.py new` files the task directly on `develop`: it syncs the primary
checkout to `origin/develop`, allocates an ID under an exclusive lock,
reconciled against the task files actually on disk, writes the file, and
commits and pushes it in the same invocation. No branch or worktree is
created just to file a task. It must therefore be run from the primary
checkout, on `develop`; running it from a secondary worktree or from any
other branch fails fast rather than filing the task somewhere invisible to
everyone else. If a push is rejected because another checkout published a
task in the same window, it resyncs, reallocates the next free ID, and
retries automatically (at most 5 times), so a colliding ID never needs a human
to resolve it. `--no-publish` writes the file locally only, for scripting and
testing contexts where a real push isn't wanted.

> **Why these are not `[project.scripts]` entry points.**
> `PYTHON_CONVENTIONS.md` says CLI entry points belong in `[project.scripts]`.
> This tooling deviates on purpose: a fresh git worktree has no `.venv`, and
> the task scripts must run before anyone has resolved the project's
> dependencies. Depending on the package environment would make the workflow
> unusable exactly where it is needed most.

## The execution loop

0. **File.** `task.py new ...` from the primary checkout on `develop`, for
   each task to add. It publishes straight to `develop` (see § Commands
   above), so it is visible to every worktree before dispatch even starts.
   Filing never uses a worktree or branch; only execution (step 4) does.
1. **Select.** `backlog.py ready --parallel 3` → a conflict-free batch of IDs.
   Candidates whose `touches` overlap a task already `in_progress` or `review`
   are left out, and `blocked` tasks are never listed.
2. **Mark.** `task.py set-status T-00XX in_progress` for each, then
   `backlog.py reindex`.
3. **Dispatch.** One subagent per task, each on its own git worktree (see
   `CONTRIBUTING.md` § Worktrees for agents), prompted with: *read
   `CLAUDE.md`, then execute `.agents/tasks/T-00XX-*.md`.* Also tell the
   subagent that its ephemeral status/progress chatter (not anything it writes
   to disk) may be terse, caveman-style, if that mode is available; see
   `CLAUDE.md` § "Chatter vs. persisted output" for what stays full prose
   regardless.
4. **Execute.** The subagent creates a worktree and branches from `develop` as
   `<type>/T-00XX-<slug>` (Conventional Commits type as the prefix, per
   `CONTRIBUTING.md`), does the work, writes and commits its report, and
   pushes. It does not merge.
5. **Collect.** The orchestrator reads the report without leaving the main tree:
   ```bash
   git show <branch>:.agents/tasks/reports/T-00XX.md
   ```
6. **Close.** `task.py set-status T-00XX review` (or `blocked`), then
   `backlog.py reindex` and `report.py harvest`. `set-status` enforces the
   report gate (see § Task lifecycle): it fails unless the task's report passes
   `report.py validate`. It finds the report in the working tree, or, when run
   on `develop` before the merge, on the task's branch.
7. **Verify, resolve, merge.** The orchestrator merges the branch into `develop` by default,
   with no per-batch grant (`CLAUDE.md` § "Merge authority: orchestrator merges by default"). It
   does so only after a verify by an independent verifier has passed, per
   § "Verify, resolve, merge" below, and with the merge commit header
   `chore(merge): merge task NNNN into develop` (`CONTRIBUTING.md`'s branching model). A human
   decides only a breaking change (defined in `CLAUDE.md`) and every "Ask first" item; a task that
   needs either is `blocked`. This default does not extend to `main`, release tags or releases.
   Whether a PR/MR is opened automatically depends on whether a git-host CLI (`gh`, `glab`, etc.)
   is available in the environment. Where it isn't, no PR/MR is needed: the orchestrator merges
   locally and pushes `develop`. Executors never merge their own work (see `CLAUDE.md`).
8. **Clean up.** Whoever performed the merge in step 7 also removes the
   now-merged branch's worktree (`git worktree remove <path>`) and deletes
   the local branch (`git branch -d <branch>`, which refuses on an unmerged
   branch, making this safe by construction). The dispatched subagent from
   step 4 is long gone by this point, so this step belongs to the merger, not
   the executor. `housekeep.py worktrees` (see § Housekeeping) exists to catch
   this step being skipped.

### Verify, resolve, merge

Step 7 runs as follows, for every task:

   - A separate fresh agent verifies the pushed branch: the full gate
     (`scripts/gate.sh`), every acceptance criterion checked against the
     files, `git diff --name-only` against `touches`, and, for test changes,
     that each expected value comes from spec text. It reports every failure
     and fixes nothing. It must also check and report whether the change is a
     breaking change (as `CLAUDE.md` defines it) or crosses any "Ask first"
     item, including edits to `scripts/`, `pyproject.toml` `[tool]` sections or
     hooks outside the task's own scope. If either is true, the orchestrator
     does not merge and the task is set `blocked` for a human.
   - The verifier is independent as `CLAUDE.md` § "Merge authority:
     orchestrator merges by default" defines it.
   - On a failure, a fresh executor fixes the findings on the same branch and
     a new verifier checks again. After three failed rounds the task is
     `blocked` and is not merged.
   - On a clean verify, the orchestrator records it in the report's verify
     line (`passed (commit <hash>; <counts>)`), commits that on the task
     branch, and merges with `chore(merge): merge task NNNN into develop`.
   - It reruns `scripts/gate.sh` on `develop`. Green: push. Red before
     pushing: `git reset --merge ORIG_HEAD` and block the task. Red after
     pushing: `git revert -m 1 <merge>` as a new commit, push, and block the
     task. It never force-pushes.
   - Before the next dispatch: `git pull --ff-only origin develop`.

Rules for every batch:

- An executor that meets an ambiguity its task file does not settle records it
  under the report's open questions and stops; the orchestrator blocks the
  task. Nobody guesses an owner decision.
- Every other "Ask first" rule in `CLAUDE.md` stands. A task that would cross
  one is `blocked`.
- Executors never regenerate `BACKLOG.md` or `LESSONS.md` on a task branch;
  the orchestrator does it on `develop` when it changes a status.
- Orchestrator edits to task files are limited to these three: `task.py set-status`;
  widening a task's `touches`, with the reason recorded in the task's report; and, before
  dispatch, amending a task file with the findings of a pre-batch review, on a `docs/`
  branch.
- A worktree not made by `scripts/gitflow.sh` needs `npm ci` before its first
  commit, so the hooks run.
- Commit body lines stay at or under 100 characters.
- Optionally, before dispatch, a fresh agent reviews the batch's task files
  against the repository.

## Task lifecycle

```
open ──> in_progress ──> review ──> done
             │              │
             └──> blocked   └──> (repair task)
                     │
                     └──> abandoned
```

Only `done` satisfies a dependency. `blocked` and `abandoned` still require a
report explaining why.

**The report is an enforced gate.** `task.py set-status` refuses a transition
to `review`, `blocked`, `done` or `abandoned` unless the task's report exists
and passes the same check as `report.py validate T-00XX` (no placeholder left
in a required section, valid outcome, and the other rules `validate` applies).
On refusal it exits non-zero, names each problem, and leaves the task file
unchanged. Transitions to `open` and `in_progress` are not gated.

The gate looks for `.agents/tasks/reports/T-00XX.md` in the working tree of
the checkout the command runs in. If it is absent there, it falls back to the
task's branch through git: a local or `origin/` branch matching `*/T-00XX-*`
(local first), read with `git show <branch>:.agents/tasks/reports/T-00XX.md`.
That is what lets step 6 of the execution loop run on `develop` before the
merge, when the report exists only on the task branch. The content found is
validated the same way whichever source it came from. A report in neither place,
or an unparseable one, is refused.

A move to `done` is checked as `validate` checks a done task: the verify line
must start with `passed` and name its commit, and the summary must not call the
verify pending. The touches rule applies once the task's merge commit is
reachable from `HEAD`, and is skipped before that, exactly as in `validate`.
`review`, `blocked` and `abandoned` accept a `pending` verify line. The gate
reuses `report.py`'s validation rather than defining a second one, so the two
cannot disagree on what counts as a valid report.

## Writing a good task

`task.py validate` enforces the mechanical parts — required frontmatter keys,
required sections, filename matching the ID and title, resolvable dependencies,
no dependency cycles, and no unfilled `TODO` left in Goal, Scope, Non-goals, or
Acceptance criteria. It cannot tell you whether the task is *well scoped*.

The sections that matter most, and the ones agents most often get wrong:

- **Context / current verified state** — cite files and line numbers you have
  actually looked at. Instruct the agent to report a discrepancy rather than
  build on a stale assumption.
- **Non-goals** — the real guardrail. Name files not to touch, APIs not to
  change, refactors not to start, claims not to make. Validation rejects an
  empty Non-goals section for this reason.
- **Acceptance criteria** — objectively checkable items, not aspirations. If a
  reviewer cannot tick it from the report, rewrite it.
- **Tests required** — name the exact commands. For a bug fix, require that the
  new test *fails before the fix* and say so.

## Reports

A report is evidence, not a victory lap. The vocabulary for test results is
fixed: **passed / failed / skipped / not run / blocked**. Never write "all tests
passed" unless the full relevant suite actually ran.

> A skipped test is not a passing test. A test that was not run is not evidence.

`report.py validate` checks that no section is still a placeholder.

The **Lessons learned** section is harvested into `.agents/LESSONS.md`, grouped
by the report's `tags`. Write only what is specific to this repo — a wrong
assumption that cost time, a non-obvious constraint, a command that does not
work here and what does instead. Generic advice makes the file worth less. Read
the tags relevant to your task before starting.

## Housekeeping

`housekeep.py` answers "is this project still on the rails?" It is a reporting
tool only — it never fixes anything it finds, and never edits task files,
`BACKLOG.md`, or `LESSONS.md`. Like the rest of `.agents/tasks/scripts/`, it is
stdlib-only and runs with no virtualenv.

```bash
python .agents/tasks/scripts/housekeep.py touches [<branch> ...]
python .agents/tasks/scripts/housekeep.py drift [--review-days N]
python .agents/tasks/scripts/housekeep.py setup
python .agents/tasks/scripts/housekeep.py worktrees
python .agents/tasks/scripts/housekeep.py all
```

- **`touches`** — diffs each task branch (or, with no arguments, every local
  branch matching `<type>/T-00XX-<slug>`) against `develop` and reports any
  changed file outside that task's declared `touches`. The task's own report
  file (`.agents/tasks/reports/T-00XX.md`) is in scope, because the workflow
  requires the subagent to write it, and a declared path the branch never
  touched is not reported. Reuses `_schema.paths_overlap`, the same
  prefix-matching semantics `backlog.py ready --parallel` uses to decide what
  may run together, so the two checks cannot disagree. A branch with no
  common history with `develop`, or that does not exist, is reported rather
  than crashing the check.
- **`drift`** — reports staleness: a `BACKLOG.md` that no longer matches the
  task files on disk, a `done` task with no report (the task branch is checked via
  `git show <branch>:.agents/tasks/reports/T-00XX.md` before the report is
  declared missing), an `in_progress` task
  whose branch does not exist or has no commits ahead of `develop`, a
  `review` task older than `--review-days` (default 7), and a `depends_on`
  reference to a task that is `in_progress` rather than `done`.
- **`setup`** — verifies the quality gate is actually installed: `.husky/`
  exists with executable hook scripts and `core.hooksPath` is configured (see
  `CONTRIBUTING.md` § Agent verify/resolve workflow). A "not configured yet"
  finding on a fresh checkout of this template is the tool working correctly,
  not a bug — it just means the repo's Husky install step hasn't run yet.
- **`worktrees`** — lists every secondary worktree whose branch is already
  merged into `develop` but was never removed with `git worktree remove` (step 8
  of the execution loop), and separately every worktree other than the primary
  checkout that has `develop` or `main` checked out (forbidden per
  `CONTRIBUTING.md` § Worktrees for agents). It automates the manual
  `git worktree list` / `git branch --merged develop` sweep.
- **`all`** — runs all four and prints a compact per-section summary. Every
  subcommand, `all` included, exits non-zero when it finds a problem and
  prints one line per finding, in a form that can be pasted directly into a
  report.

Cadence: run `housekeep.py all` **before dispatching a new batch** (so a stale
backlog or an already-drifted task doesn't get built on), **after collecting a
batch's reports** (so `touches` conformance is checked while the branches are
still fresh), and **before any merge to `develop`** (so drift is caught before
it compounds across a merge).

## Testing the tooling

The tooling is tested under `tests/` (`tests/test_task_scripts.py` for task
filing, IDs, backlog and batching; `tests/test_report_scripts.py` for report
validation, harvest and `housekeep.py`; `tests/test_set_status_gate.py` for the
report gate on `set-status`). Run it the same way as the rest of the
suite, normally through the gate:

```bash
scripts/gate.sh
uv run pytest tests/test_task_scripts.py tests/test_report_scripts.py \
    tests/test_set_status_gate.py -v
```
