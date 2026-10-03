# Plan: make the repo usable as a template (init script)

Status: proposed. Nothing in this plan is built. It needs the owner's decisions in
§ Decisions for the owner before the tasks are filed. Amended 2026-10-03 after review;
§ Review changes lists what changed.

## Goal

A person who creates a new repository from this template runs one command and ends up with a clean,
renamed, working project: gate green, empty task history, `main` and `develop` sharing one history,
and the project-specific sections of `CLAUDE.md` waiting to be filled in. No manual find-and-replace.

## What was tested (2026-10-03)

A fresh copy of `develop` was set up in a scratch repo with its own remote, the way a template copy
would be.

Works as is:
- `npm ci`, `uv sync` and Husky hook install.
- `scripts/gate.sh`: 175 tests passed.
- `task.py new`, `housekeep.py all` and `gitflow.sh feature start`.

A second copy with task files, reports and plans removed and `.agents/tasks/.counter` set to `0`:
- `backlog.py reindex` and `report.py harvest` run with zero tasks.
- `task.py validate` passes.
- `scripts/gate.sh` still passes with 175 tests, so no test depends on this repo's task history.
- `task.py new` allocates `T-0001`.
- `housekeep.py all` reports only the "hooks not installed" setup finding, which is expected before
  `npm ci`.

Problems the script must solve:

| # | Problem | Evidence |
|---|---|---|
| 1 | Template copy gets the wrong branch content | Default branch is `main`, still the first scaffold commit; all work is on `develop` |
| 2 | Repository is not marked as a template | GitHub API: `is_template: false` |
| 3 | No `main` in a new project | `gitflow.sh hotfix start x` fails with `invalid reference: main` |
| 4 | Inherited task state | 14 done tasks, reports, `LESSONS.md`, three plans, `.counter` at 14 |
| 5 | Template names | Package `proj_template`, `package.json` name `oap-template-dev-tooling`, dev container names, LICENSE holder `8greg8`, sample `greet`/`farewell` code and tests |
| 6 | Missing project sections | README says to fill mission and architecture in `CLAUDE.md`, which has no such section; no `docs/spec/` |

GitHub's template rules (from its documentation): a new repository copies the default branch's files
and directory structure; "include all branches" is optional; branches created from a template have
unrelated histories, so pull requests and merges between them do not work. The plan relies on that
last rule: it does not use "include all branches". It copies one branch and has the script create
the other from it, so `main` and `develop` stay related and Gitflow works.

## Decisions for the owner

Recommended answer first. Reply with the numbers you accept or change.

1. **Template default branch.** Switch the default branch of this repository to `develop`. The copy
   then has the current files with no release step and no history change. The alternative is
   merging `develop` into `main`, which is a human release step.
2. **Mark the repository as a template.** Settings, Template repository. Only an admin can do this.
3. **Default branch of a new project.** `develop`, because `task.py` syncs `origin/develop`. The
   script creates `main` at the same commit for releases. Setting the default branch and branch
   protection on GitHub stays a human step, which the script prints as a checklist.
4. **Method text in new projects.** Keep `strategic_model_init_material.md`. It is reference
   material, and `CLAUDE.md` governs.
5. **Sample code.** Replace `greet` and `farewell` with one smoke test that imports the package.
   The tooling tests stay, so `pytest` always collects tests; the smoke test proves the renamed
   package imports.
6. **Self-removal.** The script deletes itself and its tests in the same commit, so a second run
   is impossible and no template residue stays.
7. **Where it lives.** `init_project.py` at the repository root. The script deletes itself, so it
   need not sit with the permanent tooling, and outside `scripts/` it is not under "Ask first".
   The alternative is `scripts/init_project.py`, which needs the owner's written approval for
   adding that one file; approving this plan by name would be that approval, cited in each task
   report.
8. **Lessons in new projects.** Clear `LESSONS.md`. It is generated from the reports by
   `report.py harvest`, so it cannot outlive the report reset. A lesson worth keeping in every
   project belongs in the template's docs, through a separate task, not in the init script.

## Design: `init_project.py`

Run once, from the primary checkout of a new repository made from the template.

```
python init_project.py --name "My Project" --package my_project \
    --owner "Jane Doe" --description "One sentence." [--dry-run] [--yes] [--skip-install]
```

Standard library only, like the task scripts, so it runs before any dependency is installed.

**Preconditions (refuse with a clear message):**
- Working tree clean, with no untracked files (the undo's `git clean -fd` would delete them), on
  `develop` or `main`, and `origin` set.
- `src/proj_template/` still exists, so the script has not run before.
- `--package` is a valid lowercase Python identifier and differs from `proj_template`.
- The branch step 9 would create (`main` or `develop`) does not exist yet, locally or on `origin`.

**Names.** Three names are derived from `--package`, and the dry run prints each:
- Import package: `--package`, for example `my_project`. Renames `src/proj_template/`, the
  `packages` path in `[tool.hatch.build.targets.wheel]`, test imports and both dev container
  names (`<package>` and `<package> (spec-blind)`).
- Distribution name: `--package` with `_` replaced by `-`, for example `my-project`. Sets
  `[project] name` in `pyproject.toml` (now `proj-template`).
- npm name: `<distribution name>-dev-tooling`, for example `my-project-dev-tooling`. Sets the
  `package.json` name (now `oap-template-dev-tooling`).

`--name` is the display name, used in the README title and the `CLAUDE.md` project section.
`--description` sets `[project] description` in `pyproject.toml`.

**Steps, in order:**
1. Print the full change list. `--dry-run` stops here. Otherwise ask for `--yes`.
2. Install tooling unless `--skip-install`: `npm ci` and `uv sync`, so hooks work.
3. Rename, as in § Names. Set the LICENSE holder and year. Regenerate `uv.lock` with `uv lock`
   and `package-lock.json` with `npm install --package-lock-only`. Never hand-edit either. If
   offline, print the two commands and continue.
4. Reset task state. Remove `T-*.md` and `reports/*.md`. Remove every file in `.agents/plans/`
   and add `.agents/plans/README.md` saying owner plans and approvals go there (`CLAUDE.md` § Merge
   authority names that directory, and git does not keep an empty one). Write `0` to
   `.agents/tasks/.counter`. Regenerate `BACKLOG.md` and `LESSONS.md` with `backlog.py reindex` and
   `report.py harvest`. Keep `templates/` and `scripts/`.
5. Seed project files. Write a fresh, short project README in place of the template README; no
   template banner or text is carried over. Insert a `## Project` section at the top of
   `CLAUDE.md` with the description filled in and comment prompts for mission, architecture and
   domain terms. Add `docs/spec/README.md` explaining that the spec-first
   test rule reads from it. Replace the sample code with the smoke test.
6. Remove template residue: the script and `tests/test_init_project.py`.
7. Run `scripts/gate.sh`. Stop on red without committing.
8. Stage everything (`git add -A`) and commit once: `chore: initialize project from OAP template`.
9. Create the missing `main` or `develop` branch at the new commit, so both branches hold the
   initialized project. Local only. The preconditions already checked that it does not exist.
10. Print the human checklist: push both branches, set the default branch and protection on
    GitHub, fill the `CLAUDE.md` project section, write the first spec.

**Safety:**
- It never pushes, tags, or force-anything.
- Every file it removes is listed in the dry run first.
- Before the commit (step 8) it stages nothing: files are moved and written with plain file
  operations, not `git mv` or `git add`.
- On any failure before or during step 8, it exits non-zero and has created no branch or
  commit. The message prints the undo command:
  `git restore --source=HEAD --staged --worktree . && git clean -fd && rm -rf src/<package>`.
  The `rm` removes the new package directory, which can survive `git clean -fd` because the gate
  run leaves an ignored `__pycache__/` in it. Installed dependencies (`node_modules/`, `.venv/`)
  are ignored by git and left in place; `uv sync` refreshes `.venv/` on the next run.

## Task breakdown

Four sequential tasks. They share `init_project.py` and its test file, so `touches` overlap
and they cannot run in parallel. Each is PR-sized and ends with a report and an independent verify.

| Task | Scope | Touches | Depends on |
|---|---|---|---|
| I-1 | CLI, preconditions, dry run, name derivation, rename step, lock regeneration | `init_project.py`, `tests/test_init_project.py` | none |
| I-2 | Task state reset, `.counter`, `.agents/plans/README.md`, regenerate `BACKLOG.md` and `LESSONS.md` | same files | I-1 |
| I-3 | Seed README, `CLAUDE.md` project section, `docs/spec/`, smoke test | same files | I-2 |
| I-4 | Gate run, single commit, branch creation after the commit, self-removal, final checklist, template README "Getting started" rewrite, end-to-end dogfood test | same files, `README.md` | I-3 |

Task files are filed with `task.py new` once the decisions above are settled. Non-goals for all four:
no change to the gate, hooks, release tooling, `CLAUDE.md` rules or the Ask-first list, and no
change to the task scripts.

## Testing

- Unit tests build a scratch copy of the repo from `git ls-files`, with a bare remote, and run the
  script against it. Expected values come from this plan.
- I-4 adds one end-to-end test: copy, init, gate green, `task.py new` gives `T-0001`, `main` and
  `develop` both point at the init commit, `gitflow.sh hotfix start` works, the script is gone.
  A second case makes the gate fail and checks that no commit or branch was created.
- Dogfood, once I-4 is merged: create a real private repository from the template on GitHub and run
  the script there. The result goes in the I-4 report. This needs a human to create the repository.
- bash 3.2 does not apply: the script is Python.

## Risks

- **`uv lock` and `npm install` need network.** The script prints the commands when offline.
- **Names in docs.** The docs use `<repo_name>` as a generic placeholder. The script leaves those
  alone, because they describe the convention. Only real names are renamed.
- **Drift.** A new file with the template name added later is missed by the rename. The end-to-end
  test greps the result, `uv.lock` included, for `proj_template`, `proj-template` and
  `oap-template`, and fails on any hit.
- **Human gates the script cannot do.** Template setting, default branch and branch protection are
  GitHub settings. They are in the checklist, not automated.

## Out of scope

- Updating projects already created from the template.
- A `gh`-based repository creator.
- Changing the Gitflow model, the gate, or the merge rules.

## Review changes (2026-10-03)

A review of the first draft against `develop` `96a7bbf` changed:

1. Branch creation moved after the commit. Before, `main` would have pointed at the uninitialized
   template. A precondition refuses to start if that branch already exists.
2. § Names defines the import package, distribution and npm names, and sets
   `[project] description`.
3. Decision 5: corrected reason. The tooling tests stay, so `pytest` always collects tests.
4. `.agents/plans/` keeps a `README.md`, since `CLAUDE.md` names the directory.
5. Safety: nothing is staged and no branch or commit exists before step 8, and the undo command
   covers staged changes and the new package directory.
6. Step 5 writes a fresh README, so the separate banner removal is gone from step 6.
7. Decision 8 added: `LESSONS.md` is cleared, because it is generated from the reports.
8. The drift grep includes `proj-template` and `uv.lock`.
9. Decision 7 recommends `init_project.py` at the root, outside "Ask first"; `scripts/` stays
   the alternative.
