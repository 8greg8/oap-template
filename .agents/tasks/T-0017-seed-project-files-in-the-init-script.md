---
id: T-0017
title: Seed project files in the init script
status: in_progress
type: feat
priority: medium
depends_on: [T-0016]
touches: [init_project.py, tests/test_init_project.py]
created: 2026-10-03
report: reports/T-0017.md
---

# T-0017 — Seed project files in the init script

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

`init_project.py` seeds the new project's files (plan step 5): a fresh short README, a `## Project` section in `CLAUDE.md`, `docs/spec/README.md`, and a smoke test replacing the sample code. The copy's gate passes with the new files.

## Context / current verified state

- Plan: `.agents/plans/2026-10-03-template-init.md`, accepted by the owner on 2026-10-03 (all eight decisions as recommended). Its § Design is the source of truth for this task's behavior; where this file and the plan differ, stop and report.
- The script lives at the repository root as `init_project.py` (Decision 7), outside `scripts/`, so it is not under "Ask first". It uses the standard library only.
- Depends on T-0016.
- The sample package is `src/proj_template/__init__.py` with `greet` and `farewell`, tested by `tests/test_greet.py` and `tests/test_farewell.py`. After T-0015's rename it is `src/<package>/`.
- The template README's "Getting started" asks the user to fill mission, architecture and domain in `CLAUDE.md`, which has no section for them. `CLAUDE.md` lines 172-174 point the spec-first rule at `docs/spec/`, which does not exist.
- Decision 5: the tooling tests stay, so `pytest` always collects tests; the smoke test proves the renamed package imports.
- Re-check against `develop` before starting and report any discrepancy.

## Scope

- README: write a fresh, short project README (title from `--name`, the description, a pointer to `CLAUDE.md` and `.agents/README.md`, and the gate command). Carry no template banner or text over.
- `CLAUDE.md`: insert a `## Project` section as the first `##` section, directly before `## Working unit: the task` (after the intro paragraphs), with `--name` and the description filled in and HTML comment prompts for mission, architecture and domain terms. Leave every other line unchanged.
- `docs/spec/README.md`: short text saying the specification lives here and the spec-first test rule in `CLAUDE.md` reads from it.
- Replace the sample code: `src/<package>/__init__.py` becomes a docstring-only module; remove `tests/test_greet.py` and `tests/test_farewell.py`; add `tests/test_smoke.py`, which imports `<package>`.
- Add every seeded, replaced and removed file to the dry run's change list.
- Run the new step inside T-0015's failure handler.

## Non-goals

- Do not change `scripts/`, `.husky/`, `.agents/tasks/scripts/`, `CLAUDE.md`, `pyproject.toml`, `package.json` or any lock file in this repository. The script edits those files only in the copy it runs against.
- Do not change the gate, hooks, release tooling, merge rules or the Ask-first list.
- Do not add a runtime or dev dependency.
- Do not change any `CLAUDE.md` rule text in the copy; only insert the `## Project` section.
- Do not fill in mission, architecture or domain content; leave prompts.
- Do not implement self-removal, the gate run, the commit or branch creation.

## Files to inspect

- `.agents/plans/2026-10-03-template-init.md` (step 5, Decision 5)
- `README.md`, `CLAUDE.md`, `src/proj_template/__init__.py`, `tests/test_greet.py`, `tests/test_farewell.py`
- `init_project.py`, `tests/test_init_project.py` as left by T-0016

## Required behavior

After `--yes --skip-install` on a copy: the README is the new short README with no template text; `CLAUDE.md` equals the template's `CLAUDE.md` plus one `## Project` section before `## Working unit: the task`; `docs/spec/README.md` exists; `tests/test_smoke.py` imports the package; the sample functions and their tests are gone. Nothing is staged.

## Tests required

Tests build a scratch copy from the files `git ls-files` lists plus the working-tree `init_project.py` and `tests/test_init_project.py` (uncommitted during development) committed in the copy, so the clean-tree precondition holds, give it a bare remote as `tests/test_gitflow.py` does, and run the script there with `--skip-install` and T-0015's `uv`/`npm` stubs on `PATH`, so no case needs the network. Expected values come from the plan, decided before running anything. Cover each item in Required behavior, including that removing the `## Project` section from the copy's `CLAUDE.md` gives back the template's file byte for byte. Do not run the copy's full gate here: the copy still holds `tests/test_init_project.py`, so its gate would build copies without end. Run `uv run pytest tests/test_smoke.py` in the copy instead; if `uv` cannot set up the copy's environment offline, report that case as not run with the reason. T-0018's end-to-end test runs the copy's full gate after step 6 removes the test file. Run `uv run pytest tests/test_init_project.py -v` and `scripts/gate.sh`.

## Documentation required

None in this task; the seeded files are the deliverable inside the copy.

## Acceptance criteria

- [ ] The copy's README has `--name` as its title and contains neither the template title `# OAP Template` nor the sentence "This is a **template**, not a working project".
- [ ] The copy's `CLAUDE.md` differs from the template's only by the `## Project` section before `## Working unit: the task`.
- [ ] `docs/spec/README.md` exists in the copy.
- [ ] `tests/test_smoke.py` imports the renamed package; `greet`, `farewell` and their tests are gone.
- [ ] The dry run lists every seeded, replaced and removed file.
- [ ] `uv run pytest tests/test_init_project.py -v` passes.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches` plus the report.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `feat/T-0017-seed-project-files-in-the-init-script`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0017.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0017.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0017
```
