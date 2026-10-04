# Plan: sync the development workflow from source-project into this template

This plan brings the agent workflow, task tooling, batch-merge rules and devcontainer from
`source-project` (2026-09-21 to 2026-10-02) into this template. Only the development lifecycle
is in scope. Product code, specs and source-project's history are not.

- **Source:** `source-project` at `develop` `87f9edf`. Paths without a prefix refer to this
  template; `source-project:` marks a source-project path.
- **Template baseline:** `develop` `ddaea40`. The template has its own `scripts/` tooling
  bundle (`DEV_TOOLING_SPEC.md`), which source-project never adopted. That bundle stays and
  absorbs source-project's hook and merge rules.
- **Owner decisions (2026-10-03):**
  - D1: `pre-commit` checks only staged files and runs no tests; `pre-push` runs the full gate.
  - D2: keep the stdlib `scripts/commit_lint.py`; do not adopt npm commitlint.
  - D3: `CLAUDE.md` is the primary router; `AGENTS.md` redirects to it.
  - D4: orchestrator merging is an opt-in grant per batch, never the default.
  - D5: include a devcontainer.
  - D6: the spec-first test rule becomes a generic template rule.
  - D7: batch runs get general orchestrator-merge rules in `CLAUDE.md` and
    `.agents/README.md`; there is no reusable batch-plan template.

## 1. What changed in source-project

### 1.1 Agent instructions (`source-project:CLAUDE.md`, `source-project:AGENTS.md`)

| Change | Carried over |
|---|---|
| `CLAUDE.md` is the primary router; `AGENTS.md` is a one-line redirect. The task template and `.agents/README.md` name `CLAUDE.md`. | yes (D3) |
| Filing a task is git-atomic and worktree-free: `task.py new` runs in the primary checkout on `develop`, commits and pushes. Worktrees come only after filing. | yes |
| Removing a merged worktree and deleting its merged local branch is routine cleanup that needs no confirmation. | yes |
| "Ask first" narrowed: only `pyproject.toml` `[tool]` sections need a human. Husky and CI-workflow files follow normal task autonomy when the task's Scope names them. | yes |
| Chatter vs. persisted output: subagents may chat tersely; commits, task files and reports stay full prose. | yes |
| Concise prose in task and report files; required literal tokens stay intact. | yes |
| Spec-first test authoring: expected values come from spec text, never from observed output; a divergence becomes `xfail(strict=True)` with a reason and a report entry. | yes (D6), spec paths as placeholders |
| Source-of-truth order (meta rulebooks, `docs/spec`, code). | as a placeholder: spec, then code |
| `docs/skill-package-layout.md` reading item; `agentskills.io` reference. | no |

### 1.2 Process (`source-project:CONTRIBUTING.md`, `source-project:.agents/README.md`)

| Change | Carried over |
|---|---|
| `develop`/`main` never live in a secondary worktree; read them with `git fetch` + `git log origin/<branch>`. Whoever merges removes the worktree and local branch. Task filing is the one exception that works on `develop` in the primary checkout. | yes |
| Execution loop gains step 0 (file on `develop`) and step 8 (the merger cleans up). The dispatch prompt names `CLAUDE.md`. | yes |
| Merge commits use `chore(merge): merge task NNNN into develop`, not git's default `Merge branch …`. | yes |
| Commits already in history that fail commit linting are listed and accepted, never rewritten. | the principle, with an empty list |
| Hook install documented: `npm install` per checkout and per worktree. | yes, adapted to `gitflow.sh`, which symlinks `node_modules` into new worktrees |
| `pre-push` skips tests when every pushed commit touches only `.agents/`. It checks per commit with `--no-renames` and `--diff-merges=first-parent`. A new remote branch or an unlistable range always runs the suite. | yes, but code under `.agents/tasks/scripts/` no longer counts as skippable: in source-project a push that changes only the tooling scripts runs no tests |
| `pre-commit` checks only staged Python files. | yes (D1), stack-agnostic |
| `tests-base` branch for spec-first tests; `npm run release`. | no; the template's `scripts/release.py` covers releases |

### 1.3 Task tooling (`source-project:.agents/tasks/scripts/`)

| Change | Bug it fixes |
|---|---|
| New `_git_publish.py`: sync to `origin/develop`, allocate an ID, commit and push. On a rejected push it resyncs and reallocates (at most 5 retries). Strips `GIT_DIR`/`GIT_WORK_TREE` inherited from hooks. `task.py new --no-publish` for tests. | Several sessions filing tasks got duplicate IDs and merge conflicts; tasks filed on a branch were invisible to others |
| `task.py validate` rejects a duplicate ID unless all but one copy is `abandoned`; `list` hides abandoned duplicates. | Collisions left from before the fix |
| `_ids.allocate_id` resolves default paths at call time. | Testability |
| `_schema.INACTIVE_STATUSES` includes `blocked`. | `backlog.py ready` listed blocked tasks |
| `backlog.parallel_batch` excludes candidates whose `touches` overlap an `in_progress` or `review` task. | Parallel batches conflicting with tasks already in flight |
| Dates use local time; the backlog's report link honors the task's `report:` field. | Wrong dates near midnight |
| `report.py validate` for `done` tasks: requires `Independent verify agent (fresh context) :: passed (commit <hash>; …)` in `## Tests run`; rejects a verify mention in `## Summary`; checks the merged diff, found by its `chore(merge)` subject, against `touches`. source-project grandfathers older tasks with `STRICT_AFTER_ID = 170` and `COMMIT_REQUIRED_AFTER_ID = 202`. | Self-certified or unrecorded verify; false touches claims |
| `report.py harvest` lists each lesson once and builds a tag index. | Duplicate lessons |
| `housekeep.py`: `touches` treats the task's own report as in scope and ignores declared but unmodified paths; `drift` looks for a missing report on the task branch; new `worktrees` check; `all` runs four checks. | False positives; stale worktrees |

### 1.4 Task and report templates

- `task.md`: concise-prose note; read `CLAUDE.md` first; regenerating `BACKLOG.md` with
  `backlog.py reindex` for the task's own status is not a hand edit.
- `report.md`: concise-prose note; the independent-verify line in its exact form, with
  `pending` until the orchestrator fills it.

### 1.5 Batch runs

`source-project:.agents/plans/2026-09-30-overnight-production-readiness.md` and
`source-project:.agents/reviews/2026-10-01-overnight-run-summary.md` (§6) define the model. The
general rules carried over (D7):

- The orchestrator merges only under an owner grant for a named batch. Every other "Ask
  first" rule stands. A task that would cross one is `blocked`.
- Select with `backlog.py ready --parallel N`, mark `in_progress` on `develop`, and
  dispatch one fresh executor per task. Executors push and never merge.
- A separate fresh agent verifies. At most 3 resolve rounds, then `blocked`.
- Merge with `chore(merge)` and rerun the full gate on `develop`. If it is red before the
  push, run `git reset --merge ORIG_HEAD`. If it is red after the push, run
  `git revert -m 1`. Never force-push.
- The orchestrator writes the verify result into the report's verify line, then closes the
  task, cleans up and refreshes from `origin/develop` before the next dispatch.
- An ambiguity the task file does not settle goes under the report's open questions, and
  the task is blocked. Nobody guesses an owner decision.
- Settled from the run's lessons:
  - executors never regenerate `BACKLOG.md` or `LESSONS.md` on a branch;
  - only the orchestrator may widen `touches`, and it records why;
  - a worktree not made by `gitflow.sh` needs `npm ci` before its first commit;
  - commit body lines stay at or under 100 characters.
- Optional pre-batch task review: a fresh agent checks the task files against the repo,
  and the findings are amended into the task files before dispatch.

### 1.6 Devcontainer (`source-project:.devcontainer/`, unchanged since 2026-09-21)

| Part | Carried over |
|---|---|
| Ubuntu base image; features `git`, `node`, `common-utils` (zsh), `tmux`, `claude-code`; `devcontainer-lock.json` pins them | yes; the lock file is regenerated, not copied |
| `postCreate.sh` clones a personal dotfiles repo, tolerates missing credentials, and falls back to symlinks | the pattern only; the repo URL becomes an optional `DOTFILES_REPO` variable, and setup is skipped when it is unset |
| `src/` shadowed by an empty tmpfs so blind spec-first test authoring cannot read the implementation | yes, as an opt-in second configuration (D6). The editable install points at `src/`, so tests cannot run in it; it is for authoring only |
| `"name": "test"`; the comment citing source-project's `T-0002` | no |
| Missing in source-project: `uv`, `uv sync`, `npm ci` | added |

## 2. Gap analysis

| Area | Template today | Action |
|---|---|---|
| Router | `AGENTS.md` primary, no `CLAUDE.md` | Swap (D3) — T-0005 |
| Agent rules | source-project's older text | Port §1.1 — T-0005 |
| `CONTRIBUTING.md` | No worktree, merge-commit, accepted-history or hook-install rules | Port §1.2 against `scripts/gitflow.sh` and `scripts/gate.sh` — T-0005 |
| `.agents/README.md` | No filing step, cleanup step, `worktrees` check or batch rules | Port §1.2, §1.5 — T-0005 |
| Task scripts | All §1.3 bugs present; no `_git_publish.py` | Port — T-0002, T-0003 |
| Tooling tests | None; `tests/` holds only sample tests | Port source-project's tests, adapted — T-0002, T-0003, T-0004 |
| `commit-msg` | `commit_lint.py`; exempts git's default merge messages | Add line-length rules; accept `chore(merge)` — T-0004 |
| `pre-commit` | autofix, then the full `gate.sh` including tests | Staged-files mode, no tests, skip for `.agents/`-only commits (D1) — T-0004 |
| `pre-push` | full `gate.sh` | Add the `.agents/`-only skip — T-0004 |
| `gitflow.sh finish` | `Merge branch '…' into …` | `chore(merge)` messages — T-0004 |
| Devcontainer | None | Add (D5) — T-0006 |
| Pending T-0001 | On branch `chore/T-0001-…` only, filed under the old flow; `.counter` is not on `develop` | The allocator reconciles only against files on disk, so the next `task.py new` on `develop` would reuse `T-0001`. Merge it in the bootstrap (§3.1) |

### 2.1 Excluded on purpose

The `tests-base` branch; source-project's list of accepted commit failures; `docs/skill-package-layout.md`;
the `agentskills.io` reference; `source-project:scripts/release.mjs`; npm commitlint (D2); a reusable
batch-plan or run-summary template (D7); source-project's personal dotfiles URL; every `src/source_project`
path.

### 2.2 Drift found in source-project (for a separate source-project task)

- `source-project:CONTRIBUTING.md` names `../proj-template-*` worktrees and `app/<AgentName>/`.
- `source-project:CONTRIBUTING.md` step 2 cites `AGENTS.md` § "Chatter vs. persisted output", which
  lives in `CLAUDE.md`.
- `source-project:CLAUDE.md` has `src/<repo_name>//` and an unclosed `**` in the "When executing a task
  from the backlog" bullet.
- `source-project:.devcontainer/` has no `uv` and no `npm ci`, so hooks are not installed in the container.
- `source-project:.husky/pre-push` skips tests for a push that changes only `.agents/tasks/scripts/*.py`,
  so tooling code can reach `develop` untested.

## 3. Execution

### 3.1 Bootstrap (before any task runs)

The template's `task.py new` cannot publish to `develop` until T-0002 lands, so the first
filing uses the template's current flow:

1. Commit this plan on `docs/workflow-sync-plan`.
2. Merge `origin/chore/T-0001-enforce-report-writing-as-a-pipeline-gate-not` into it, so
   T-0001 and `.counter` (value `1`) reach `develop`.
3. File T-0002 to T-0006 with `task.py new` on the same branch and fill them in from §3.3.
   Write `touches` as literal paths: the `{a,b}` brace lists in §3.3 are shorthand and
   must be expanded.
4. Amend T-0001, whose `touches` overlap T-0002, T-0003 and T-0005:
   - `depends_on: [T-0003, T-0005]`;
   - in `touches` and in its text, `AGENTS.md` becomes `CLAUDE.md`, which T-0005 makes the
     router;
   - its "Context / current verified state" quotes the old `AGENTS.md`. Add one line saying
     the executor re-verifies it after T-0005.
5. Run `task.py validate` and `backlog.py reindex`, then merge with
   `chore(merge): merge docs/workflow-sync-plan into develop` and push. The template's hooks
   at this point are the old ones, so the commit runs the full gate.
6. Delete `chore/T-0001-…` locally. The remote branch stays unless the owner asks.

From T-0002 onward, new tasks are filed with the ported `task.py new`.

### 3.2 Order

| Task | Title | Depends on |
|---|---|---|
| T-0002 | Port git-atomic task filing and backlog fixes | — |
| T-0004 | Reconcile hooks and dev tooling with the merge and push rules | — |
| T-0006 | Add a devcontainer | — |
| T-0003 | Port report validation, harvest and housekeep checks | T-0002 |
| T-0005 | Port agent rules, process docs and orchestrator-merge rules | T-0002, T-0003, T-0004, T-0006 |
| T-0001 | Report gate on `set-status` (existing) | T-0003, T-0005 |

Wave 1: T-0002, T-0004 and T-0006 in parallel. Wave 2: T-0003. Wave 3: T-0005. Wave 4:
T-0001. IDs assume no other task is filed first. The waves follow from `depends_on` and
`touches`; `paths_overlap` compares path segments, so `scripts/` does not overlap
`.agents/tasks/scripts/`.

### 3.3 Task specifications

Every task forks from `develop`, stays inside `touches`, and ends with a report whose
independent-verify line is filled by the merger.

**T-0002 — Port git-atomic task filing and backlog fixes** (`type: fix`, high)

- Touches: `.agents/tasks/scripts/{_git_publish,_ids,_schema,task,backlog}.py`,
  `tests/test_task_scripts.py`.
- Scope: copy the files listed in Appendix A as they are and apply A.2. Add
  `INTEGRATION_BRANCH` to `_schema.py` (B.1). Port the matching tests from
  `source-project:tests/test_task_scripts.py` (A.3). Publish tests use a throwaway bare remote.
- Non-goals: `report.py`, `housekeep.py`, docs, hooks; any behavior source-project lacks.
- Acceptance:
  - [ ] Two concurrent `task.py new` runs against one bare remote produce two distinct IDs and no conflict.
  - [ ] `task.py new` fails fast outside the primary checkout or off `develop`.
  - [ ] `--no-publish` writes locally and touches no git state.
  - [ ] `backlog.py ready` omits `blocked` tasks; `--parallel` omits candidates overlapping an `in_progress` or `review` task.
  - [ ] `task.py validate` rejects a non-abandoned duplicate ID.

**T-0003 — Port report validation, harvest and housekeep checks** (`type: fix`, high)

- Touches: `.agents/tasks/scripts/{report,housekeep}.py`,
  `.agents/tasks/templates/report.md`, `tests/test_report_scripts.py`.
- Scope: copy the files listed in Appendix A and apply A.2 and B.3. Every `done` task is
  checked; there are no grandfathering thresholds. The merge lookup matches the
  `chore(merge)` subjects that T-0004 writes. Port the report and harvest tests (A.3) into
  `tests/test_report_scripts.py`, copying the helpers they need from
  `tests/test_task_scripts.py`. source-project has no `housekeep.py` tests at all; write them.
- Non-goals: `set-status` gating (T-0001); docs; `task.py`.
- Acceptance:
  - [ ] A `done` report without a `passed (commit <hash>; …)` verify line fails `report.py validate`.
  - [ ] A verify mention in `## Summary` fails validation.
  - [ ] A merged diff outside `touches` fails validation; the task's own report does not.
  - [ ] `housekeep.py worktrees` reports a merged, unremoved worktree and `develop`/`main` in a secondary worktree.
  - [ ] `housekeep.py touches` does not report the task's own report file; `drift` finds a report that exists only on the task branch.
  - [ ] `report.py harvest` lists each lesson once.

**T-0004 — Reconcile hooks and dev tooling with the merge and push rules** (`type: feat`, high)

- Touches: `.husky/`, `scripts/`, `DEV_TOOLING_SPEC.md`, `tests/test_hooks.py`,
  `tests/test_commit_lint.py`.
- Scope (code in Appendix C):
  - `gate.sh --staged`: lint, format check and typecheck on staged files matching a new
    `STAGED_GLOB` in `scripts/config/gate.sh`; no tests.
  - `pre-commit`: exit 0 when every staged file is under `.agents/` and none is under
    `.agents/tasks/scripts/`; otherwise autofix the staged files, re-stage them, then run
    `gate.sh --staged` (D1).
  - `pre-push`: source-project's per-commit skip, with the same `.agents/tasks/scripts/` exception,
    then `gate.sh`.
  - Owner approval of this plan (2026-10-03) is the human sign-off that the template's
    current "Ask first" rule requires for Husky changes. After T-0005 that rule no longer
    covers hooks named in a task's Scope.
  - `commit_lint.py`: header, body and footer lines at or under 100 characters; ignore
    everything below git's scissors line (`git commit -v` puts the diff there, and the
    `commit-msg` hook sees the file before git strips it); accept
    `chore(merge): merge task NNNN into develop`; keep the default-merge exemption for
    merges made by git itself.
  - `gitflow.sh finish`: `chore(merge): merge task NNNN into <base>` for a
    `<type>/T-NNNN-<slug>` branch, otherwise `chore(merge): merge <branch> into <base>`,
    also for the hotfix back-merge.
  - `DEV_TOOLING_SPEC.md` and `scripts/README.md` describe all of the above.
    `scripts/README.md` also stops saying `core.hooksPath` prints `.husky`: Husky 9
    sets `.husky/_`.
- Non-goals: npm commitlint (D2); `pyproject.toml` `[tool]`; CI workflows; `release.py`.
- Acceptance:
  - [ ] Each hook rule above has a test, modeled on `source-project:tests/test_pre_push_hook.py`.
  - [ ] A `.agents/`-only commit and push run no tests; one file outside `.agents/` runs the full gate.
  - [ ] `merge_message` gives `chore(merge): merge task 0002 into develop` for `fix/T-0002-x` and `chore(merge): merge feat/x into develop` for `feat/x`; both pass `commit_lint.py`, and the first matches T-0003's merge lookup.
  - [ ] A push or commit that changes only `.agents/tasks/scripts/*.py` runs the gate.
  - [ ] `gate.sh` and `autofix.sh` run under bash 3.2 (macOS default): no `mapfile`, no empty-array expansion under `set -u`.

**T-0005 — Port agent rules, process docs and orchestrator-merge rules** (`type: docs`, high)

- Touches: `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `.agents/README.md`,
  `.agents/tasks/templates/task.md`, `README.md`.
- Scope:
  - Move `AGENTS.md` content to `CLAUDE.md`; `AGENTS.md` becomes a redirect.
  - Port the §1.1 and §1.2 rows marked "yes"; use `<repo_name>` and `docs/spec/`
    placeholders, `scripts/gate.sh` instead of four raw commands, and `scripts/gitflow.sh`
    instead of hand-written worktree commands.
  - Add an empty "Accepted history" list to `CONTRIBUTING.md`, stating the principle.
  - Add §1.5 to `CLAUDE.md` (authority, D4) and `.agents/README.md` (execution loop).
  - Mention the devcontainer and its blind variant in `README.md` and in the spec-first
    section.
  - Port the §1.4 `task.md` changes.
  - Text snippets for the router and the merge rules are in Appendix E.
- Non-goals: a batch-plan template (D7); source-project-specific content (§2.1); code changes.
- Acceptance:
  - [ ] No file names `AGENTS.md` as the primary router, `app/<AgentName>/` or `proj-template` worktree paths.
  - [ ] Every command and flag the docs cite exists after T-0002 to T-0004 and T-0006.
  - [ ] Orchestrator merging is stated as opt-in per batch, never the default.

**T-0006 — Add a devcontainer** (`type: feat`, medium)

- Touches: `.devcontainer/`.
- Scope (code in Appendix D):
  - `devcontainer.json` named `<repo_name>`, with §1.6's features. `uv` comes from the
    official installer in `postCreate.sh` (D.3); a pinned devcontainer feature is an
    acceptable alternative if the report records why.
  - `postCreate.sh` runs `uv sync` and `npm ci`, then checks that
    `git config core.hooksPath` ends in `.husky/_` (Husky 9's value). It applies dotfiles
    only when `DOTFILES_REPO` is set, and a failure there never fails the container.
  - A regenerated `devcontainer-lock.json`.
  - `.devcontainer/spec-blind/devcontainer.json`: the same, plus the tmpfs over `src/`,
    with a comment stating it is for authoring only.
  - `.devcontainer/README.md`: when to use each configuration.
- Non-goals: CI; Codespaces prebuilds; any personal dotfiles URL.
- Acceptance:
  - [ ] Both configurations build, and `gate.sh` passes in the default one. If no container runtime is available, report this as not run.
  - [ ] In the blind configuration `src/` is empty while the host's `src/` is unchanged.
  - [ ] With `DOTFILES_REPO` unset, `postCreate.sh` exits 0.

**T-0001 — existing.** Runs last, as amended in §3.1 step 4.

## 4. Out of scope

- Changes to `pyproject.toml` `[tool]` sections.
- New runtime dependencies.
- Edits to source-project (§2.2 lists them for a separate task there).
- CI workflow files.

## Appendix A. Porting map

source-project's `.agents/tasks/scripts/*.py` and templates are a strict superset of the
template's copies: every template-only line in a diff is an older version of a source-project line.
So these files are copied whole from the pinned commit and then adapted, not merged by
hand. Run the commands from the template root, with source-project checked out next to it:

```bash
SRC=../source-project; REF=87f9edf
for f in _git_publish _ids _schema backlog task report housekeep; do
  git -C "$SRC" show "$REF:.agents/tasks/scripts/$f.py" > ".agents/tasks/scripts/$f.py"
done
for f in task report; do
  git -C "$SRC" show "$REF:.agents/tasks/templates/$f.md" > ".agents/tasks/templates/$f.md"
done
```

Each task copies only the files in its own `touches`.

### A.1 Files

| Template file | Task | Method |
|---|---|---|
| `.agents/tasks/scripts/_git_publish.py` | T-0002 | new; copy, then A.2 |
| `.agents/tasks/scripts/_ids.py` | T-0002 | copy as is |
| `.agents/tasks/scripts/_schema.py` | T-0002 | copy, then add B.1 |
| `.agents/tasks/scripts/backlog.py` | T-0002 | copy as is |
| `.agents/tasks/scripts/task.py` | T-0002 | copy, then A.2 |
| `.agents/tasks/scripts/report.py` | T-0003 | copy, then A.2 and B.3 |
| `.agents/tasks/scripts/housekeep.py` | T-0003 | copy, then A.2 |
| `.agents/tasks/templates/report.md` | T-0003 | copy, then A.2 |
| `.agents/tasks/templates/task.md` | T-0005 | copy as is |
| `.husky/pre-push` | T-0004 | adapt source-project's hook (C.6) |
| everything else in Appendix C and D | T-0004, T-0006 | new code |

### A.2 Adaptations after copying

- **Integration branch.** Replace the literal `develop` in `_git_publish.py` (fetch, merge,
  push, branch check, error messages), in `report.merge_commit_for`'s subject and in
  `housekeep.INTEGRATION_BRANCH` with `_schema.INTEGRATION_BRANCH` (B.1).
- **No source-project task IDs in code.** Remove the comment and docstring references to source-project tasks:
  `housekeep.py` ("per T-0054"), `_git_publish.py` ("in T-0092"), and `report.py`
  ("T-0170" in two places). Generic examples such as ``T-0004`` stay. Keep the explanation and drop the
  citation.
- **No grandfathering.** In `report.py`, delete `STRICT_AFTER_ID`,
  `COMMIT_REQUIRED_AFTER_ID`, both comparisons against them (B.3), and `_numeric_id`,
  which nothing else uses. In
  `report.md`, change "A `done` task (ID above T-0170) whose line says…" to "A `done` task
  whose line says…".
- **Commit message in `_git_publish.py`.** Keep `chore(tasks): file <ID> <slug>`. A long
  slug can push the header past 100 characters; truncate the slug so the header fits
  (new behavior, with a test).

### A.3 Tests

source-project's `tests/test_task_new.py`, `test_task_status.py` and `test_backlog_build.py`
test the source-project product's own `task` command, not this tooling, so they are not ported. Port:

- From `source-project:tests/test_task_scripts.py` to `tests/test_task_scripts.py` (T-0002): the
  git-environment, `create_task`, `publish_task`, CLI `new`, duplicate-ID, backlog-link,
  blocked-not-ready and `parallel_batch` tests. Keep its `_init_repo`, `_seed_origin` and
  `_clone` helpers; they build a bare remote and a clone in `tmp_path`.
- From the same file to `tests/test_report_scripts.py` (T-0003): the verify-line, summary,
  touches-against-merge-diff and harvest tests. Rewrite the threshold tests
  (`*_up_to_t0170_*`, `*_above_t0202_*`) as unconditional. Drop
  `test_commit_hash_rule_does_not_apply_up_to_t0202` and
  `test_reports_t0171_to_t0202_name_their_commit_and_have_clean_summaries`; they test source-project
  history. Add tests for `housekeep.py worktrees`; source-project has none.
- From `source-project:tests/test_pre_push_hook.py` to `tests/test_hooks.py` (T-0004): all 12
  cases. The template hook ends in `exec scripts/gate.sh`, so the test repo gets a stub
  `scripts/gate.sh` that writes a marker file. The assertion becomes "the marker exists"
  instead of "pytest ran".

## Appendix B. Key ported code (reference)

These excerpts show what the copied files do, so a reviewer can check behavior without
opening source-project. They are condensed: `_git_diff_names` stands in for an inlined
`git diff --name-only`, `_sync_integration_branch` is source-project's `_sync_develop` renamed by A.2,
and existence checks and docstrings are left out. The copy commands in Appendix A are
authoritative.

### B.1 `_schema.py`

```python
#: Branch that task branches fork from and merge into, and that task filing
#: publishes to. Mirrors DEVELOP_BRANCH in scripts/config/gate.sh.
INTEGRATION_BRANCH = "develop"

#: Statuses that keep a task out of `backlog.py ready`.
INACTIVE_STATUSES = frozenset({"in_progress", "blocked", "review", "done", "abandoned"})
```

### B.2 `_git_publish.publish_task` (core loop, after A.2)

```python
def publish_task(create, repo_root=REPO_ROOT, max_retries=MAX_PUBLISH_RETRIES) -> Path:
    if not is_primary_checkout(repo_root):  # `.git` is a directory, not a file
        raise PublishError(
            "task.py new must run from the primary checkout, not a git worktree"
        )
    branch = current_branch(repo_root)
    if branch != INTEGRATION_BRANCH:
        raise PublishError(
            f"task.py new must run on {INTEGRATION_BRANCH} (currently on {branch!r})"
        )

    _sync_integration_branch(repo_root)  # fetch + merge --ff-only; diverged -> error

    last_error = ""
    for _ in range(max_retries):
        path = create()  # allocates the next ID against disk state
        task_id, slug = _FILENAME_RE.match(path.stem).groups()
        _require(
            _git(repo_root, "add", str(path), str(repo_root / _COUNTER_RELATIVE)),
            "git add failed",
        )
        _require(
            _git(repo_root, "commit", "-m", f"chore(tasks): file {task_id} {slug}"),
            "git commit failed",
        )

        push = _git(repo_root, "push", "origin", INTEGRATION_BRANCH)
        if push.returncode == 0:
            return path

        # Another checkout published first: drop our unpushed commit, resync, reallocate.
        last_error = push.stderr.strip() or push.stdout.strip()
        _require(
            _git(repo_root, "reset", "--hard", "HEAD~1"),
            "git reset failed after rejected push",
        )
        _sync_integration_branch(repo_root)

    raise PublishError(
        f"could not publish task after {max_retries} attempt(s); last push error: {last_error}"
    )
```

`_git` drops `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`,
`GIT_ALTERNATE_OBJECT_DIRECTORIES` and `GIT_CEILING_DIRECTORIES` from the subprocess
environment. When `task.py new` runs from inside a git hook, these would otherwise point
the commands at another repository. The `reset --hard HEAD~1` only discards this
function's own unpushed commit; it never touches shared history.

### B.3 `report.validate_done_rules` (after A.2)

```python
def validate_done_rules(
    report: Report, task: Task, repo_root: Path = REPO_ROOT
) -> list[str]:
    if task.status != "done":
        return []
    problems: list[str] = []

    match = VERIFY_LINE_RE.search(report.section_text("Tests run"))
    if not match:
        problems.append(
            "done task has no 'Independent verify agent (fresh context) :: <status>' "
            "line in '## Tests run'"
        )
    elif not match.group("status").lower().startswith("passed"):
        problems.append(
            f"independent verify is recorded as {match.group('status')!r}; "
            "a done task needs a verify status that starts with 'passed'"
        )
    elif not VERIFY_COMMIT_RE.search(match.group("status")):
        problems.append(
            "independent verify line names no commit; record it as "
            "'passed (commit <hash>; ...)' with the commit the verify checked"
        )

    summary = report.section_text("Summary")
    if STALE_SUMMARY_RE.search(summary) or STALE_SUMMARY_PHRASE in summary.lower():
        problems.append(
            "'## Summary' calls the independent verify pending, not run or "
            "excepted; state the outcome only in the verify line"
        )

    if TOUCHES_TICKED_RE.search(report.section_text("Safety confirmations")):
        commit = merge_commit_for(
            task.id, repo_root
        )  # finds "chore(merge): merge task NNNN into <branch>"
        if commit is not None:
            changed = _git_diff_names(f"{commit}^1", commit, repo_root)
            outside = _outside_touches(
                changed, task
            )  # the task's own report and task file are allowed
            if outside:
                problems.append(
                    f"touches box is ticked but merge {commit[:12]} changed files "
                    "outside touches: " + ", ".join(outside)
                )
    return problems
```

### B.4 `backlog.parallel_batch`

```python
def parallel_batch(
    tasks: Sequence[Task], limit: int, active: Sequence[Task] = ()
) -> list[Task]:
    running = [task for task in active if task.status in ("in_progress", "review")]
    batch: list[Task] = []
    for task in tasks:  # already sorted by priority
        if len(batch) >= limit:
            break
        if any(tasks_conflict(task, other) for other in running):
            continue  # would conflict with unmerged work
        if all(not tasks_conflict(task, other) for other in batch):
            batch.append(task)
    return batch
```

Both callers pass every loaded task as `active`.

### B.5 `task.py validate`: duplicate IDs

```python
live: dict[str, str] = {}
for task in tasks:
    if task.status == "abandoned":
        continue
    first = live.setdefault(task.id, task.path.name)
    if first != task.path.name:
        problems.append(
            f"{task.path.name}: duplicate id {task.id} (also {first}); "
            "only abandoned tasks may share an id"
        )
```

### B.6 `housekeep.check_worktrees`

```python
for worktree in list_worktrees()[1:]:  # [0] is the primary checkout
    path, branch = worktree["path"], worktree["branch"]
    if not branch:
        continue  # detached HEAD
    if branch in (INTEGRATION_BRANCH, "main"):
        findings.append(
            f"WORKTREE {path}: checked out on {branch!r}, which must only live "
            "in the primary checkout"
        )
    elif is_branch_merged(branch):  # git merge-base --is-ancestor
        findings.append(
            f"WORKTREE {path}: branch {branch!r} is merged into "
            f"{INTEGRATION_BRANCH} but the worktree was never removed -- "
            f"run: git worktree remove {path}"
        )
```

### B.7 `report.md`: verify line (end of `## Tests run`, after A.2)

````markdown
End the list with the independent-verify line in exactly this form. The
orchestrator replaces `pending` with `passed (commit <hash>)`, naming the commit
verified, or with `failed` or `blocked`. Do not state the verify status in
`## Summary`; the verify line records it. A `done` task whose line says
`not run` or `pending` fails `report.py validate`.

```
Independent verify agent (fresh context) :: pending
```
````

## Appendix C. New template code for hooks and dev tooling (T-0004)

### C.1 `scripts/config/gate.sh`: new setting

```bash
# Pathspec for files the pre-commit hook checks (gate.sh --staged, autofix.sh --staged).
# LINT_CMD, FORMAT_CHECK_CMD and TYPECHECK_CMD (and the *_FIX_CMDs) must accept file paths
# as trailing arguments; with no arguments they check the whole repo.
STAGED_GLOB="*.py"
```

### C.2 `scripts/lib/common.sh`: helpers

```bash
# staged_files: staged paths (added, copied, modified, renamed) matching STAGED_GLOB.
staged_files() {
    git diff --cached --name-only --diff-filter=ACMR -- "${STAGED_GLOB:-*}"
}

# run_on_files <name> <command-string> [files...]: run_gate with the files appended as
# arguments to the command string; with no files the command runs unchanged.
run_on_files() {
    local name="$1" cmd="$2"; shift 2
    run_gate "$name" bash -c "$cmd \"\$@\"" gate ${1+"$@"}
}
```

### C.3 `scripts/gate.sh`

```bash
#!/usr/bin/env bash
# The single source of truth for "does this change pass?" -- run by agents during the
# verify/resolve loop, by .husky/pre-commit (--staged), by .husky/pre-push, and by CI.
#
# Usage: scripts/gate.sh [--fast | --staged]
#   --fast    skip TEST_CMD; for a quick loop while iterating, never as the final check.
#   --staged  lint, format check and typecheck only the staged files matching STAGED_GLOB;
#             no tests. Exits 0 when nothing matching is staged.

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPTS_DIR/lib/common.sh"
load_gate_config

fast=false
staged=false
for arg in "$@"; do
    case "$arg" in
        --fast) fast=true ;;
        --staged) staged=true; fast=true ;;
        *) die "unknown argument: $arg" ;;
    esac
done

cd "$(repo_root)"

# Bash 3.2 (macOS) has no mapfile, and expands an empty array under `set -u` only with the
# ${files[@]+...} guard used below.
files=()
if [[ "$staged" == true ]]; then
    while IFS= read -r f; do files+=("$f"); done < <(staged_files)
    if [[ ${#files[@]} -eq 0 ]]; then
        ok "no staged files match $STAGED_GLOB -- nothing to check"
        exit 0
    fi
fi

failures=0
run_on_files "lint" "$LINT_CMD" ${files[@]+"${files[@]}"} || failures=$((failures + 1))
run_on_files "format check" "$FORMAT_CHECK_CMD" ${files[@]+"${files[@]}"} || failures=$((failures + 1))
run_on_files "typecheck" "$TYPECHECK_CMD" ${files[@]+"${files[@]}"} || failures=$((failures + 1))

if [[ "$fast" == false ]]; then
    run_gate "tests" bash -c "$TEST_CMD" || failures=$((failures + 1))
else
    warn "tests: skipped -- do not treat this as a clean gate"
fi

echo
if [[ "$failures" -eq 0 ]]; then
    ok "gate clean"
else
    fail "$failures gate(s) failed"
    exit 1
fi
```

### C.4 `scripts/autofix.sh`: add `--staged`

```bash
staged=false
for arg in "$@"; do
    case "$arg" in
        --staged) staged=true ;;
        *) die "unknown argument: $arg" ;;
    esac
done

cd "$(repo_root)"

files=()
if [[ "$staged" == true ]]; then
    while IFS= read -r f; do files+=("$f"); done < <(staged_files)
    [[ ${#files[@]} -gt 0 ]] || { ok "no staged files match $STAGED_GLOB"; exit 0; }
fi

# Best effort: gate.sh is the real pass/fail check.
run_on_files "lint autofix" "$LINT_FIX_CMD" ${files[@]+"${files[@]}"} || true
run_on_files "format" "$FORMAT_FIX_CMD" ${files[@]+"${files[@]}"} || true
```

### C.5 `.husky/pre-commit`

```sh
#!/usr/bin/env sh
# Staged files only, no tests: .husky/pre-push runs the full gate. A commit that stages
# only .agents/ records (task filing, status changes, reports, BACKLOG.md) skips the hook,
# so `task.py new` and the orchestrator's state commits stay fast. The tooling code under
# .agents/tasks/scripts/ is never skipped.
staged=$(git diff --cached --name-only --diff-filter=ACMR)
[ -n "$staged" ] || exit 0

if ! printf '%s\n' "$staged" | grep -q -v '^\.agents/' \
    && ! printf '%s\n' "$staged" | grep -q '^\.agents/tasks/scripts/'; then
    echo "pre-commit: only .agents/ records staged; skipping gate."
    exit 0
fi

scripts/autofix.sh --staged

# Re-stage only what was already staged. `git add -u` would sweep in unrelated dirty files.
printf '%s\n' "$staged" | xargs git add --

exec scripts/gate.sh --staged
```

### C.6 `.husky/pre-push` (source-project's hook with two changes: the scripts exception and the gate call)

```sh
#!/usr/bin/env sh
# Skip the gate when every pushed commit changes only .agents/ records (task files,
# reports, BACKLOG.md, LESSONS.md), as `task.py new` does on each filing. Tooling code
# under .agents/tasks/scripts/ always runs the gate. Files are listed
# per commit, so a change that a later commit reverts still counts. Anything else runs the
# full gate: a file outside .agents/ (including one renamed into it, hence --no-renames), a
# new remote branch, or a range git cannot list. A merge commit lists its files against its
# first parent (--diff-merges=first-parent), so a change made only inside a merge counts.
tasks_only=1
while read -r local_ref local_sha remote_ref remote_sha; do
  # A deleted ref (all-zero local sha) pushes no commits.
  case "$local_sha" in *[!0]*) ;; *) continue ;; esac
  # A new remote branch (all-zero remote sha) has no base to diff against.
  case "$remote_sha" in *[!0]*) ;; *) tasks_only=0; break ;; esac
  if ! changed=$(git log --format= --name-only --no-renames --diff-merges=first-parent "$remote_sha..$local_sha" 2>/dev/null); then
    tasks_only=0
    break
  fi
  if printf '%s\n' "$changed" | grep -q -v -e '^\.agents/' -e '^$' \
      || printf '%s\n' "$changed" | grep -q '^\.agents/tasks/scripts/'; then
    tasks_only=0
    break
  fi
done

if [ "$tasks_only" = 1 ]; then
  echo "pre-push: only .agents/ records changed; skipping gate."
  exit 0
fi

exec scripts/gate.sh
```

### C.7 `scripts/commit_lint.py`: scissors cut-off and line-length rule

The `commit-msg` hook gets the message file before git cleans it up. With `git commit -v`,
the staged diff follows a scissors line, and its long lines would fail the new rule. Cut
there first:

```python
SCISSORS_RE = re.compile(r"^# -+ >8 -+$")


def strip_comments(message: str) -> str:
    kept: list[str] = []
    for line in message.splitlines():
        if SCISSORS_RE.match(line):
            break  # everything below is git's verbose diff
        if not line.startswith("#"):
            kept.append(line)
    return "\n".join(kept)
```

Then add next to `MAX_HEADER_LEN`, and run it in `lint()` right after the header-length
check (merge messages return earlier and stay exempt):

```python
MAX_LINE_LEN = 100

    for number, line in enumerate(lines[1:], start=2):
        if len(line) > MAX_LINE_LEN:
            errors.append(
                f"line {number} is {len(line)} chars, must be <= {MAX_LINE_LEN}: "
                f"{line[:40]!r}..."
            )
```

`chore(merge): merge task NNNN into develop` already matches `HEADER_RE` with type `chore`,
so it needs no special case. Update the module docstring: git's default merge messages
stay exempt for merges git writes itself, but this repo's own merges use the
`chore(merge)` form.

### C.8 `scripts/gitflow.sh`: merge messages

```bash
# merge_message <branch> <base>: the header CONTRIBUTING.md § Merge commits requires.
# Task branches (<type>/T-NNNN-<slug>) name the task; any other branch names itself.
merge_message() {
    local branch="$1" base="$2"
    if [[ "$branch" =~ ^[a-z]+/T-([0-9]{4,})- ]]; then
        printf 'chore(merge): merge task %s into %s' "${BASH_REMATCH[1]}" "$base"
    else
        printf 'chore(merge): merge %s into %s' "$branch" "$base"
    fi
}

# in finish():
git merge --no-ff "$branch" -m "$(merge_message "$branch" "$base")"
# hotfix back-merge:
git merge --no-ff "$MAIN_BRANCH" -m "$(merge_message "$MAIN_BRANCH" "$DEVELOP_BRANCH")"
```

`report.merge_commit_for` searches for `chore(merge): merge task NNNN into
<INTEGRATION_BRANCH>`. The two must stay in step; T-0004's acceptance test checks this.

## Appendix D. Devcontainer (T-0006)

### D.1 `.devcontainer/devcontainer.json`

```jsonc
{
  "name": "<repo_name>",
  "image": "mcr.microsoft.com/devcontainers/base:ubuntu",
  "features": {
    "ghcr.io/devcontainers/features/git:1": {},
    "ghcr.io/devcontainers/features/node:1": {},
    "ghcr.io/devcontainers/features/common-utils:2": {
      "installZsh": true,
      "configureZshAsDefaultShell": true,
      "upgradePackages": true
    },
    "ghcr.io/devcontainers-extra/features/tmux-apt-get:1": {},
    "ghcr.io/anthropics/devcontainer-features/claude-code:1": {}
  },
  // Optional: a dotfiles repo applied on first boot. Unset means no dotfiles.
  "containerEnv": { "DOTFILES_REPO": "${localEnv:DOTFILES_REPO}" },
  "postCreateCommand": "bash .devcontainer/postCreate.sh",
  "remoteUser": "vscode"
}
```

### D.2 `.devcontainer/spec-blind/devcontainer.json`

```jsonc
{
  // Same container as ../devcontainer.json, with src/ hidden so spec-first tests can be
  // written without reading the implementation (CLAUDE.md, "Spec-first test authoring").
  // For authoring only: the project is not installed and tests cannot run here.
  // Run them in the default container or on the host. The tmpfs only changes the
  // container's view; the host's src/ is untouched.
  "name": "<repo_name> (spec-blind)",
  "image": "mcr.microsoft.com/devcontainers/base:ubuntu",
  "features": { /* identical to ../devcontainer.json */ },
  "workspaceMount": "source=${localWorkspaceFolder},target=/workspace,type=bind,consistency=cached",
  "workspaceFolder": "/workspace",
  "mounts": ["type=tmpfs,target=/workspace/src"],
  "containerEnv": { "DOTFILES_REPO": "${localEnv:DOTFILES_REPO}" },
  "postCreateCommand": "bash .devcontainer/postCreate.sh --blind",
  "remoteUser": "vscode"
}
```

### D.3 `.devcontainer/postCreate.sh`

```bash
#!/usr/bin/env bash
# First-boot setup: uv, Python dependencies, git hooks, optional dotfiles.
# --blind: src/ is hidden (spec-blind container), so install dependencies only.
set -euo pipefail

blind=false
[[ "${1:-}" == "--blind" ]] && blind=true

if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

if [[ "$blind" == true ]]; then
    uv sync --no-install-project
else
    uv sync
fi

# Installs Husky; its prepare step sets core.hooksPath (Husky 9 uses .husky/_).
npm ci
hooks_path="$(git config --get core.hooksPath || true)"
if [[ "$hooks_path" != *".husky/_" ]]; then
    echo "postCreate.sh: core.hooksPath is '${hooks_path}', expected .husky/_; git hooks will not run." >&2
    exit 1
fi

# Optional dotfiles. A failure here never blocks the container.
if [[ -n "${DOTFILES_REPO:-}" ]]; then
    (
        set +e
        dir="${HOME}/.dotfiles"
        if [[ -d "$dir" ]]; then
            git -C "$dir" pull --ff-only
        elif ! git clone --depth 1 "$DOTFILES_REPO" "$dir"; then
            echo "postCreate.sh: could not clone $DOTFILES_REPO; skipping dotfiles." >&2
            exit 0
        fi
        cd "$dir" || exit 0
        for candidate in install.sh bootstrap.sh setup.sh; do
            if [[ -f "$candidate" ]]; then
                bash "$candidate"
                exit 0
            fi
        done
        for f in .tmux.conf .vimrc .gitconfig .zshrc; do
            [[ -f "$f" ]] && ln -sf "$dir/$f" "$HOME/$f"
        done
    ) || echo "postCreate.sh: dotfiles setup failed; continuing." >&2
fi
```

### D.4 Lock file

Generate `devcontainer-lock.json` with the devcontainer CLI after the first successful
build; do not copy source-project's. Record the CLI version in the report.

## Appendix E. Documentation snippets (T-0005)

### E.1 `AGENTS.md`

```markdown
# Agent Instructions

This router file has moved. See [`CLAUDE.md`](CLAUDE.md) for the full agent instructions.
```

### E.2 `CLAUDE.md`: new section "Batch runs: orchestrator merges"

```markdown
## Batch runs: orchestrator merges

By default an executor pushes its task branch and a human merges it. The owner may grant
the orchestrator merge authority for a named batch of tasks, in writing (a plan under
`.agents/plans/` or the dispatch instruction). The grant covers only that batch. Every
rule under "Ask first" still applies; a task that can only be finished by crossing one
is set `blocked`.

Under a grant, the orchestrator follows `.agents/README.md` § "The execution loop",
including the orchestrator-merge steps. It never merges without a passed independent
verify, never force-pushes, and never edits a task file except through `task.py
set-status`.
```

### E.3 `.agents/README.md`: orchestrator-merge steps in the execution loop

```markdown
When the owner has granted merge authority for the batch (`CLAUDE.md` § "Batch runs:
orchestrator merges"), step 7 becomes:

7. **Verify, resolve, merge.**
   - A separate fresh agent verifies the pushed branch: the full gate, every acceptance
     criterion checked against the files, `git diff --name-only` against `touches`, and,
     for test changes, that each expected value comes from spec text. It reports every
     failure and fixes nothing.
   - On a failure, a fresh executor fixes the findings on the same branch and a new
     verifier checks again. After three failed rounds the task is `blocked` and is not
     merged.
   - On a clean verify, the orchestrator records it in the report's verify line
     (`passed (commit <hash>; <counts>)`), commits that on the task branch, and merges
     with `chore(merge): merge task NNNN into develop`.
   - It reruns `scripts/gate.sh` on `develop`. Green: push. Red before pushing:
     `git reset --merge ORIG_HEAD` and block the task. Red after pushing:
     `git revert -m 1 <merge>` as a new commit, push, and block the task.
   - Before the next dispatch: `git pull --ff-only origin develop`.

Rules for every batch:

- An executor that meets an ambiguity its task file does not settle records it under the
  report's open questions and stops; the orchestrator blocks the task. Nobody guesses an
  owner decision.
- Executors never regenerate `BACKLOG.md` or `LESSONS.md` on a task branch; the
  orchestrator does it on `develop` when it changes a status.
- Only the orchestrator may widen a task's `touches`, and it records why in the report.
- Optionally, before dispatch, a fresh agent reviews the batch's task files against the
  repository. Its findings are amended into the task files on a `docs/` branch.
```
