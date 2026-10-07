---
id: T-0018
title: Finish the init script with gate, commit, branch and self-removal
status: done
type: feat
priority: medium
depends_on: [T-0017]
touches: [init_project.py, tests/test_init_project.py, README.md]
created: 2026-10-03
report: reports/T-0018.md
---

# T-0018 — Finish the init script with gate, commit, branch and self-removal

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

`init_project.py` completes the plan: it removes itself and its tests, runs the gate, commits once, creates the missing branch at the new commit, and prints the human checklist. An end-to-end test proves a template copy becomes a working project, and the template README tells users to run the script.

## Context / current verified state

- Plan: `.agents/plans/2026-10-03-template-init.md`, accepted by the owner on 2026-10-03 (all eight decisions as recommended). Its § Design is the source of truth for this task's behavior; where this file and the plan differ, stop and report.
- The script lives at the repository root as `init_project.py` (Decision 7), outside `scripts/`, so it is not under "Ask first". It uses the standard library only.
- Depends on T-0017.
- Step order is fixed by the plan: 6 self-removal, 7 gate, 8 `git add -A` and one commit `chore: initialize project from OAP template`, 9 create the missing branch at the new commit (local only), 10 checklist. The precondition that the branch does not exist comes from T-0015.
- § Safety: on any failure before or during step 8 the script exits non-zero, has created no branch or commit, and prints `git restore --source=HEAD --staged --worktree . && git clean -fd && rm -rf src/<package>`.
- `gitflow.sh hotfix start` needs a local `main` (`scripts/gitflow.sh` line 47, `git worktree add ... "$base"`).
- `task.py new` syncs and pushes to `origin/develop`, so the end-to-end test pushes the copy's `develop` to its bare remote first.
- The template README's "Getting started with a new project" section (lines 24-39) describes manual renaming.
- Re-check against `develop` before starting and report any discrepancy.

## Scope

- Step 6: remove `init_project.py` and `tests/test_init_project.py` from the copy.
- Step 7: run `scripts/gate.sh`; on red, stop without committing and print the undo command.
- Step 8: `git add -A` and commit once with the plan's message; on a failed commit, print the undo command.
- Step 9: create the missing `main` or `develop` at the new commit. Never push, tag or force anything.
- Add the self-removed files and steps 7 to 10 (gate, commit, branch, checklist) to the dry run's change list.
- Run steps 6 to 8 inside T-0015's failure handler, so a failure anywhere before or during the commit prints the undo command.
- Steps 9 and 10 run after the commit, outside that handler. On a failure there, exit non-zero, never print the undo command, and print the init commit's hash. If step 9 did not complete, also print the `git branch <name>` command that creates the missing branch.
- Step 10: print the checklist: push both branches, set the default branch and branch protection on GitHub, fill the `CLAUDE.md` project section, write the first spec.
- End-to-end test: copy, init, gate green, `main` and `develop` both point at the init commit, `task.py new` gives `T-0001` after pushing `develop` to the bare remote, `gitflow.sh hotfix start` works, the script and its tests are gone, and a grep of the result (including `uv.lock`) for `proj_template`, `proj-template` and `oap-template` finds nothing. A second case commits a failing test in the copy before the run, so the gate fails, and checks that no commit or branch exists and the undo command restores a clean tree.
- `README.md` (template): rewrite "Getting started with a new project" to say: create a repository from the template, run `python init_project.py ...` (with `--dry-run` first), then follow the printed checklist. Keep the rest of the README unchanged.

## Non-goals

- Do not change `scripts/`, `.husky/`, `.agents/tasks/scripts/`, `CLAUDE.md`, `pyproject.toml`, `package.json` or any lock file in this repository. The script edits those files only in the copy it runs against.
- Do not change the gate, hooks, release tooling, merge rules or the Ask-first list.
- Do not add a runtime or dev dependency.
- Do not push, tag, or create anything on GitHub from the script or the tests (beyond the tests' local bare remote).
- Do not change README sections other than "Getting started with a new project".
- The dogfood run on a real GitHub repository needs a human to create it; do not attempt it. Report it as not run.

## Files to inspect

- `.agents/plans/2026-10-03-template-init.md` (steps 6 to 10, § Safety, § Testing)
- `README.md`, `scripts/gitflow.sh`, `.agents/tasks/scripts/task.py`
- `init_project.py`, `tests/test_init_project.py` as left by T-0017

## Required behavior

On a fresh template copy, `python init_project.py ... --yes` ends with one new commit `chore: initialize project from OAP template` on the current branch, the other branch at the same commit, a clean working tree, no `init_project.py` or `tests/test_init_project.py`, and the checklist printed. With a failing gate it exits non-zero with no new commit or branch and prints the undo command, which restores a clean tree.

## Tests required

Tests build a scratch copy from the files `git ls-files` lists plus the working-tree `init_project.py` and `tests/test_init_project.py` (uncommitted during development) committed in the copy, so the clean-tree precondition holds, give it a bare remote as `tests/test_gitflow.py` does, and run the script there with `--skip-install`. Expected values come from the plan, decided before running anything. Add the two end-to-end cases from Scope, and a unit case for a step-9 failure. They run the real `uv lock` and `npm install --package-lock-only` and the copy's real gate. Each case first checks that `uv lock` and `npm install --package-lock-only` succeed in the copy; if not (no network), it calls `pytest.skip` with that reason, so an offline gate is not red, and the report records the case as skipped, never as passed. The failing-gate case asserts that the planted test is the failure the gate reports. Run `uv run pytest tests/test_init_project.py -v` and `scripts/gate.sh`. The dogfood run on GitHub is not run in this task.

## Documentation required

`README.md` "Getting started with a new project", as in Scope.

## Acceptance criteria

- [ ] After a run, `main` and `develop` both point at the single init commit and the working tree is clean.
- [ ] `init_project.py` and `tests/test_init_project.py` are absent from the result.
- [ ] `task.py new` in the result allocates `T-0001`, and `gitflow.sh hotfix start` works.
- [ ] A grep of the result, including `uv.lock`, for `proj_template`, `proj-template` and `oap-template` finds nothing.
- [ ] With a failing gate, no commit or branch is created, and the printed undo command restores a clean tree.
- [ ] The script never pushes, tags or force-pushes.
- [ ] The dry run lists the self-removed files and steps 7 to 10.
- [ ] A failure in step 9 exits non-zero, prints the commit hash and the `git branch` command, and does not print the undo command.
- [ ] The template README's getting-started section describes the script and the checklist.
- [ ] `uv run pytest tests/test_init_project.py -v` passes.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches` plus the report.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `feat/T-0018-finish-the-init-script-with-gate-commit-branch`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0018.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0018.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0018
```
