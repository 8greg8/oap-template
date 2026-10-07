---
id: T-0006
title: Add a devcontainer
status: done
type: feat
priority: medium
depends_on: []
touches: [.devcontainer]
created: 2026-10-03
report: reports/T-0006.md
---

# T-0006 — Add a devcontainer

## Goal

A devcontainer in which `uv`, the Python dependencies and the git hooks work after first
boot, plus an opt-in spec-blind variant that hides `src/` for writing spec-first tests.

## Context / current verified state

- Plan: `.agents/plans/2026-10-03-workflow-sync.md` §1.6, §3.3, Appendix D (code). Owner decision D5 (2026-10-03).
- This repo has no `.devcontainer/`.
- `source-project:.devcontainer/` has the base image and features to reuse, a personal dotfiles URL,
  and a tmpfs over `src/`. It lacks `uv`, `uv sync` and `npm ci`.
- Husky 9 sets `core.hooksPath` to `.husky/_`.

## Scope

- `.devcontainer/devcontainer.json` (D.1), named `<repo_name>`.
- `.devcontainer/spec-blind/devcontainer.json` (D.2).
- `.devcontainer/postCreate.sh` (D.3): `uv` from the official installer (a pinned feature
  is acceptable if the report says why), `uv sync` (`--no-install-project` with
  `--blind`), `npm ci`, a `core.hooksPath` check, and optional dotfiles from
  `DOTFILES_REPO`.
- `devcontainer-lock.json`, generated with the devcontainer CLI (D.4).
- `.devcontainer/README.md`: when to use each configuration.

## Non-goals

- No CI, no Codespaces prebuilds.
- No personal dotfiles URL.
- Do not edit `README.md` or `CLAUDE.md`; T-0005 links the devcontainer.

## Files to inspect

- `../source-project/.devcontainer/*`
- `package.json`, `pyproject.toml`

## Required behavior

- The default container ends first boot with `uv sync` done and the hooks active.
- In the blind container, `src/` is an empty tmpfs and only dependencies are installed.
- With `DOTFILES_REPO` unset, dotfiles are skipped; a dotfiles failure never fails
  `postCreate.sh`.

## Tests required

Build both configurations (devcontainer CLI or editor) and run `scripts/gate.sh` in the
default one. If no container runtime is available, report it as not run. Run
`bash -n .devcontainer/postCreate.sh`.

## Documentation required

`.devcontainer/README.md`.

## Acceptance criteria

- [ ] Both configurations build, and `gate.sh` passes in the default one. If no container runtime is available, report this as not run.
- [ ] In the blind configuration `src/` is empty while the host's `src/` is unchanged.
- [ ] With `DOTFILES_REPO` unset, `postCreate.sh` exits 0.
- [ ] `git config core.hooksPath` ends in `.husky/_` after first boot of the default configuration.

## Workflow

- Read `AGENTS.md` (and `CLAUDE.md`, if present) first.
- Create a worktree and branch from `develop` as `feat/T-0006-add-a-devcontainer`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0006.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request.
- Do not edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state.

## Report

Fill in `.agents/tasks/reports/T-0006.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0006
```
