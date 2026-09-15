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

`task.py new` allocates an ID under an exclusive lock, so several sessions or
worktrees can create tasks simultaneously without colliding. The allocator also
reconciles against the task files actually on disk, so a lost or
merge-clobbered `.counter` cannot hand out a duplicate.

> **Why these are not `[project.scripts]` entry points.**
> `PYTHON_CONVENTIONS.md` says CLI entry points belong in `[project.scripts]`.
> This tooling deviates on purpose: a fresh git worktree has no `.venv`, and
> the task scripts must run before anyone has resolved the project's
> dependencies. Depending on the package environment would make the workflow
> unusable exactly where it is needed most.

## The execution loop

1. **Select.** `backlog.py ready --parallel 3` → a conflict-free batch of IDs.
2. **Mark.** `task.py set-status T-00XX in_progress` for each, then
   `backlog.py reindex`.
3. **Dispatch.** One subagent per task, each on its own git worktree (see
   `CONTRIBUTING.md` § Worktrees), prompted with: *read `AGENTS.md`, then
   execute `.agents/tasks/T-00XX-*.md`.*
4. **Execute.** The subagent creates a worktree and branches from `develop` as
   `<type>/T-00XX-<slug>` (Conventional Commits type as the prefix, per
   `CONTRIBUTING.md`), does the work, writes and commits its report, and
   pushes. It does not merge.
5. **Collect.** The orchestrator reads the report without leaving the main tree:
   ```bash
   git show <branch>:.agents/tasks/reports/T-00XX.md
   ```
6. **Close.** `task.py set-status T-00XX review` (or `blocked`), then
   `backlog.py reindex` and `report.py harvest`.
7. **Merge.** A human reviews and merges the branch into `develop`, per
   `CONTRIBUTING.md`'s branching model. Whether a PR/MR is opened
   automatically depends on whether a git-host CLI (`gh`, `glab`, etc.) is
   available in the environment — where it isn't, a task ends at *branch
   pushed, report committed*, and opening the PR/MR stays a human step, same
   as agents never merging their own work (see `AGENTS.md`).

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
python .agents/tasks/scripts/housekeep.py all
```

- **`touches`** — diffs each task branch (or, with no arguments, every local
  branch matching `<type>/T-00XX-<slug>`) against `develop` and reports any
  changed file outside that task's declared `touches`, plus any declared path
  the branch never touched. Reuses `_schema.paths_overlap`, the same
  prefix-matching semantics `backlog.py ready --parallel` uses to decide what
  may run together, so the two checks cannot disagree. A branch with no
  common history with `develop`, or that does not exist, is reported rather
  than crashing the check.
- **`drift`** — reports staleness: a `BACKLOG.md` that no longer matches the
  task files on disk, a `done` task with no report, an `in_progress` task
  whose branch does not exist or has no commits ahead of `develop`, a
  `review` task older than `--review-days` (default 7), and a `depends_on`
  reference to a task that is `in_progress` rather than `done`.
- **`setup`** — verifies the quality gate is actually installed: `.husky/`
  exists with executable hook scripts and `core.hooksPath` is configured (see
  `CONTRIBUTING.md` § Agent verify/resolve workflow). A "not configured yet"
  finding on a fresh checkout of this template is the tool working correctly,
  not a bug — it just means the repo's Husky install step hasn't run yet.
- **`all`** — runs all three and prints a compact per-section summary. Every
  subcommand, `all` included, exits non-zero when it finds a problem and
  prints one line per finding, in a form that can be pasted directly into a
  report.

Cadence: run `housekeep.py all` **before dispatching a new batch** (so a stale
backlog or an already-drifted task doesn't get built on), **after collecting a
batch's reports** (so `touches` conformance is checked while the branches are
still fresh), and **before any merge to `develop`** (so drift is caught before
it compounds across a merge).

## Testing the tooling

This tooling has no test suite in the template by default. If you add one, it
belongs under `tests/` per `PYTHON_CONVENTIONS.md` (e.g.
`tests/test_task_scripts.py`), and should cover at minimum: frontmatter
parsing (including everything it must reject), ID allocation under both
thread and process concurrency, scope-overlap detection, dependency-cycle
detection, and the readiness/batching queries — plus an assertion that every
committed task validates and that `BACKLOG.md` is not stale. Run it the same
way as the rest of the suite:

```bash
uv run pytest tests/test_task_scripts.py -v
uv run ruff check .agents/tasks/scripts tests
```
