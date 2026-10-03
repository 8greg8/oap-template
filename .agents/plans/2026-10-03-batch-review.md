# Review plan: batch T-0001, T-0008 to T-0012

For the human reviewer. The orchestrator merged this batch into `develop` under the grant in
`2026-10-03-batch-merge-grant.md`. Every branch passed an independent fresh-context verify and
`scripts/gate.sh` before merging. This plan says what to look at, what the known gaps mean in plain
terms, and how to close each one.

## What merged

| Task | Merge commit | Verified commit | Gate at verify |
|---|---|---|---|
| T-0008 pre-commit re-staging | `d36a259` | `13b69b6` | 116 tests passed |
| T-0012 NUL-safe gate and autofix | `3d253b0` | `b88a3a6` | 130 tests passed |
| T-0001 report gate in `set-status` | `1562dc6` | `81e1c20` | 146 tests passed |
| T-0009 helper shebangs | `87ebf73` | `fd3c9a2` | 169 tests passed |
| T-0010 agent-doc wording | `af98144` | `c3eaf0c` | 169 tests passed |
| T-0011 gitflow task branches, housekeep | `f237af3` | `122728d` | 175 tests passed |

See one task's change with `git diff <merge>^1 <merge>`. Each report is
`.agents/tasks/reports/T-00XX.md`.

## Review first: files that need a human

`CLAUDE.md` says changes to `scripts/` and `.husky/` need a human. The owner approved each of these
in writing for this batch. Read them before anything else:

- `.husky/pre-commit` (T-0008): NUL-delimited file list, literal pathspecs, rename-aware skip.
- `scripts/lib/common.sh`, `scripts/gate.sh`, `scripts/autofix.sh` (T-0012): `git diff -z` and
  `read -r -d ''`. The files checked and the gate commands are unchanged.
- `scripts/gitflow.sh` (T-0011): one added `case` arm, `docs|chore|fix`, plus usage text.
- `scripts/release.py` (T-0011): docstring line 4 only, `AGENTS.md` to `CLAUDE.md`.

Not changed: `pyproject.toml`, CI, `scripts/config/gate.sh`, `scripts/commit_lint.py`.

## The gaps, in plain terms

None of these blocks the merge. None has a task filed. Each is either accepted or closed by a
check you can run.

1. **Real bash 3.2 was never run.** macOS ships bash 3.2, and the script comments and task files require the
   scripts to work there. The sandbox had no Docker daemon and no `shellcheck`, so the changed
   scripts (T-0008 hook, T-0011 `gitflow.sh`, T-0012 `gate.sh`, `autofix.sh`, `common.sh`) were only
   read through for bash 4 constructs, and the repo's existing test that bans them passes. The
   changes use `read -r -d ''`, which bash 3.2 supports, and a `case` arm.
   - Close it: on a Mac, confirm `bash --version` prints 3.2.x (a Homebrew bash can shadow it), then
     run `uv run pytest tests/test_staged_files.py tests/test_gitflow.py tests/test_hooks.py -q`.
     The tests call plain `bash`.
   - Or, where Docker works, syntax-check in 3.2:
     `docker run --rm -v "$PWD":/repo -w /repo bash:3.2 bash -c 'for f in scripts/*.sh scripts/lib/common.sh; do bash -n "$f" || exit 1; done'`.
     This checks syntax only, because the image has no `git`.

2. **`housekeep.py worktrees` can still call an empty branch merged (T-0011).** The check cannot
   tell "a branch with no commits of its own" from "a branch already merged", because both are
   ancestors of `develop`. T-0011 fixes the case where the branch tip equals the `develop` tip,
   which is a worktree just cut from current `develop`. Two cases remain:
   - An empty branch cut from an older `develop`, after `develop` has moved on, still looks merged.
     The effect is a harmless cleanup reminder for a worktree that has not started.
   - A branch merged by fast-forward, whose tip equals the `develop` tip, is no longer reported.
     The repo always merges with `--no-ff`, so this does not occur in the normal flow.
   - Close it: accept it, or ask for a stricter test, such as "the tip is the second parent of a
     merge commit on `develop`". That is a change to `housekeep.py` and is not required for this
     batch.

3. **The `set-status` branch lookup never fetches (T-0001).** When the report is not in the working
   tree, the gate looks at local branches, then `origin/` branches, matching `*/T-00XX-*`.
   - It does not run `git fetch`, so an `origin/` branch must already be fetched.
   - A stale local branch wins over a newer `origin/` one.
   - A branch name without a slash, such as `T-0001-foo`, does not match.
   - Close it: accept it. The task branch names always have a type prefix, and the orchestrator
     works from a checkout that already holds the branch.

4. **New `gitflow.sh` kinds do not check the topic format (T-0011).** `gitflow.sh docs start foo`
   works even though task branches should be `T-NNNN-<slug>`. The old kinds never checked either.
   Close it: accept it, or add a format check in a later change.

5. **A quirk of the new report gate (T-0001).** It refuses `done` if the report's Summary still says
   the verify is pending. This caught one slip: T-0009's Summary said so after verification. It
   was fixed on `develop` in commit `24e0e9d`. Nothing is open.

## Optional ideas written in reports

Two reports have a "Follow-up recommended" section. They are ideas, not tasks, and nothing depends
on them:

- T-0011: record branch creation, for example by reflog, to close gap 2 fully.
- T-0012: run the changed scripts under `docker run bash:3.2` where a daemon exists, which is
  gap 1.

## Per-task checks

- **T-0008:** stage a file named `sp ace.py`, one with a quote, and one with a non-ASCII name, then
  commit. The autofix changes should be in the commit. `git mv` a file from `src/` into `.agents/`
  and confirm the gate runs.
- **T-0012:** the same three names now also work through the real ruff, because `gate.sh` and
  `autofix.sh` read the list NUL-delimited. A name with a newline works too.
- **T-0001:** run `task.py set-status T-00XX review` for a task with no report. It must exit
  non-zero and leave the status alone. Then with a report only on its branch, it must succeed.
  `done` must refuse a `pending` verify line.
- **T-0009:** `git ls-files -s .agents/tasks/scripts` shows the four `_*.py` helpers as 100644 and
  the four CLI scripts as 100755.
- **T-0010:** `CLAUDE.md` and `.agents/README.md` list the same three orchestrator edits to task
  files. `CONTRIBUTING.md` shows `--no-track` and a first `git push -u origin <branch>`.
- **T-0011:** `scripts/gitflow.sh docs start T-0099-x`, then `finish`, in a scratch clone. The merge
  header should read `chore(merge): merge task 0099 into develop`.

## Decisions the orchestrator made under the grant

Read these as judgment calls you may overrule:

- **T-0001 gate versus loop order:** the gate reads the report from the working tree, then from the
  task's branch, so the loop's order (`set-status review` before the merge) is unchanged.
- **T-0001 `done`:** moving to `done` is checked as `report.py validate` checks a done task. No
  existing validation rule changed.
- **Task-file edits:** `touches` was widened for T-0001 (its test module) and T-0011
  (`scripts/README.md`, `scripts/release.py`, `CONTRIBUTING.md`, `tests/test_gitflow.py`). T-0011's
  scope and non-goals were also amended before dispatch so its two doc fixes did not need new
  tasks. T-0010 reconciled `CLAUDE.md` to allow these edits.
- **T-0012 was filed by the orchestrator** after T-0008's verify found that quote and non-ASCII
  names still failed in the real scripts. It was completed in this batch.

## Process changes after the batch (T-0013)

After the batch, the owner changed the merge rules. Review these as a rule change, not as code.

- **Owner instruction:** "Merge into develop must be by default granted to agents. The independent
  verification must be done by another agent. Human is involved only if breaking changes."
- **What changes:** the orchestrator merges a verified task branch into `develop` by default, with
  no per-batch grant. An executor never merges or verifies its own work. A human decides only for
  breaking changes and for the existing Ask-first items. Merges into `main`, tags and releases
  stay human. T-0013 writes this into `CLAUDE.md`, `.agents/README.md`, `CONTRIBUTING.md` and the
  task template, and defines "breaking change" once in `CLAUDE.md`.
- **Dropped clauses:** the owner agreed to drop per-task "must not start without approval" clauses.
  New task files omit them, because `CLAUDE.md` governs. Two closed task files still carry one:
  T-0008 (a note about `.husky/`) and T-0011 (a non-goal about `scripts/gitflow.sh`). They are done
  records and were left unedited, since editing them is outside the orchestrator's permitted
  task-file edits.
- **Conflict to decide:** `strategic_model_init_material.md`, the OAP method text, lists "merge to
  protected branches" as a human approval gate and says "treat every merge as a human decision".
  The new rule departs from it for `develop`. T-0013 does not edit that file. Decide whether to
  amend the method text or to keep it as the general doctrine, with `CLAUDE.md` as the
  project-specific override.
- **Check:** after T-0013 merges, `grep -n -i "opt-in\|never the default" CLAUDE.md .agents/README.md`
  should find nothing that still makes a grant the precondition.

## Sign-off

- [ ] Human-gated files read.
- [ ] Gap 1 closed or accepted, with the bash 3.2 result noted.
- [ ] Gaps 2 to 4 accepted or turned into tasks.
- [ ] Merge-by-default rule change (T-0013) accepted, including the conflict with the method text.
- [ ] `scripts/gate.sh` run on `develop` at the review commit.
