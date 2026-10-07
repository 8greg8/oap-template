---
id: T-0015
title: Add init script CLI, preconditions, names and rename step
status: done
type: feat
priority: medium
depends_on: []
touches: [init_project.py, tests/test_init_project.py]
created: 2026-10-03
report: reports/T-0015.md
---

# T-0015 — Add init script CLI, preconditions, names and rename step

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

`init_project.py` exists at the repository root with the plan's CLI, preconditions, name derivation, dry run and rename step. Run with `--yes` on a fresh template copy, it renames every template name in § Names, sets the LICENSE, and regenerates or prints the lock-file commands. It does not yet reset tasks, seed files, commit or create branches.

## Context / current verified state

- Plan: `.agents/plans/2026-10-03-template-init.md`, accepted by the owner on 2026-10-03 (all eight decisions as recommended). Its § Design is the source of truth for this task's behavior; where this file and the plan differ, stop and report.
- The script lives at the repository root as `init_project.py` (Decision 7), outside `scripts/`, so it is not under "Ask first". It uses the standard library only.
- Template names today: `pyproject.toml` `[project] name = "proj-template"`, `description` (line 3), and `packages = ["src/proj_template"]` under `[tool.hatch.build.targets.wheel]`; `package.json` and `package-lock.json` name `oap-template-dev-tooling`; `.devcontainer/devcontainer.json` name `proj_template`; `.devcontainer/spec-blind/devcontainer.json` name `proj_template (spec-blind)`; `LICENSE` holder `8greg8`; `uv.lock` name `proj-template`; `tests/test_greet.py` and `tests/test_farewell.py` import `proj_template`.
- Re-check each against `develop` before starting and report any discrepancy.

## Scope

- CLI: `--name`, `--package`, `--owner`, `--description` (all required), `--dry-run`, `--yes`, `--skip-install`.
- Preconditions from the plan: clean working tree with no untracked files; on `develop` or `main`; `origin` set; `src/proj_template/` exists; `--package` is a valid lowercase Python identifier other than `proj_template`; the other branch (`main` or `develop`) does not exist locally or on `origin`. Each refusal names the failed check and exits non-zero.
- Name derivation per § Names; the dry run prints the three derived names and the full change list.
- With neither `--dry-run` nor `--yes`, print the change list, then refuse with a non-zero exit and a message saying to rerun with `--yes`. No interactive prompt. This refusal happens before any change, so it does not print the undo command.
- Step 2: `npm ci` and `uv sync` unless `--skip-install`.
- Step 3: rename per § Names, set `[project] description`, set the LICENSE holder to `--owner` and the year to the current year. Regenerate `uv.lock` with `uv lock` and `package-lock.json` with `npm install --package-lock-only`; never edit either by hand. `--skip-install` does not skip this; it covers step 2 only. If either command fails (for example offline), print both commands and continue.
- File operations are plain moves and writes; nothing is staged (plan § Safety).
- One failure handler wraps steps 1 to 8: on any error there it exits non-zero and prints the plan's undo command, `git restore --source=HEAD --staged --worktree . && git clean -fd && rm -rf src/<package>`. Later tasks add steps 4 to 8 inside it; T-0018 handles failures in steps 9 and 10, after the commit, separately.
- Structure the steps as functions so T-0016 to T-0018 add steps without rewriting this one.

## Non-goals

- Do not change `scripts/`, `.husky/`, `.agents/tasks/scripts/`, `CLAUDE.md`, `pyproject.toml`, `package.json` or any lock file in this repository. The script edits those files only in the copy it runs against.
- Do not change the gate, hooks, release tooling, merge rules or the Ask-first list.
- Do not add a runtime or dev dependency.
- Do not implement steps 4 to 10 of the plan (task reset, seeding, self-removal, gate run, commit, branch creation, checklist); later tasks own them.
- Do not touch `README.md` or the `<repo_name>` placeholders in docs.

## Files to inspect

- `.agents/plans/2026-10-03-template-init.md` (§ Design, § Names, § Safety)
- `pyproject.toml`, `package.json`, `.devcontainer/devcontainer.json`, `.devcontainer/spec-blind/devcontainer.json`, `LICENSE`, `src/proj_template/`, `tests/test_greet.py`, `tests/test_farewell.py`
- `tests/test_gitflow.py` (scratch-repo pattern)

## Required behavior

`python init_project.py --name "My Project" --package my_project --owner "Jane Doe" --description "One sentence." --dry-run` prints the names `my_project`, `my-project` and `my-project-dev-tooling` and the change list, and changes nothing. With `--yes --skip-install` the copy has `src/my_project/`, the new names in every file listed in Context, the new LICENSE holder and year, and no file staged. Every precondition failure exits non-zero with a message naming the check.

## Tests required

Tests build a scratch copy from the files `git ls-files` lists plus the working-tree `init_project.py` and `tests/test_init_project.py` (uncommitted during development) committed in the copy, so the clean-tree precondition holds, give it a bare remote as `tests/test_gitflow.py` does, and run the script there with `--skip-install`. Expected values come from the plan, decided before running anything. Unit tests put stub `uv` and `npm` executables first on `PATH` that record their arguments, so they run offline; one case makes the stub fail and checks that the commands are printed and the run continues. Cover: each precondition refusal (one case each); the refusal without `--dry-run` or `--yes`; a failure inside a step exits non-zero and prints the undo command; the dry run changes nothing (`git status --porcelain` empty) and prints the three names; the rename result for every file in Context except `uv.lock` and `package-lock.json`, and for those two that the stubs were called with `uv lock` and `npm install --package-lock-only`; nothing staged after the run. Run `uv run pytest tests/test_init_project.py -v` and `scripts/gate.sh`.

## Documentation required

None in this task. T-0018 rewrites the template README's getting-started section.

## Acceptance criteria

- [ ] `init_project.py` exists at the repository root and imports only the standard library.
- [ ] Every precondition in Scope refuses with a non-zero exit and a message naming the check, each covered by a test.
- [ ] `--dry-run` prints the three derived names and changes nothing.
- [ ] Without `--dry-run` or `--yes`, the script changes nothing and exits non-zero.
- [ ] `uv lock` and `npm install --package-lock-only` run even with `--skip-install`; when either fails, both commands are printed and the run continues.
- [ ] Any failure inside a step exits non-zero and prints the undo command.
- [ ] After `--yes --skip-install` with the lock stubs, a grep of the copy for `proj_template`, `proj-template` and `oap-template` hits only these files: `uv.lock`, `package-lock.json`, `init_project.py`, `tests/test_init_project.py`, and files under `.agents/`. The real lock commands and later steps handle them. The report lists the hits.
- [ ] The script names the template strings plainly; no string is split or encoded to avoid the grep.
- [ ] Nothing is staged after the run.
- [ ] `uv run pytest tests/test_init_project.py -v` passes.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches` plus the report.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `feat/T-0015-add-init-script-cli-preconditions-names-and`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0015.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0015.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0015
```
