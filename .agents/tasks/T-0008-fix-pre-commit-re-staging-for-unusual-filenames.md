---
id: T-0008
title: Fix pre-commit re-staging for unusual filenames
status: done
type: fix
priority: medium
depends_on: []
touches: [.husky/pre-commit, tests/test_hooks.py]
created: 2026-10-03
report: reports/T-0008.md
---

# T-0008 — Fix pre-commit re-staging for unusual filenames

## Goal

`.husky/pre-commit` re-stages autofix changes correctly for every staged file, whatever its name (spaces, quotes, non-ASCII), and treats a pure rename into `.agents/` the same way `pre-push` does, so the gate is not silently skipped.

## Context / current verified state

- T-0004's independent verify (2026-10-03) staged `sp ace.py` and committed: `printf | xargs git add --` produced `fatal: pathspec 'sp' did not match any files`, the commit went through, and autofix changes to that file were dropped from the commit.
- `pre-commit` inspects `git diff --cached --diff-filter=ACMR`; a pure rename from outside `.agents/` into `.agents/` is seen only by its new path and skips the gate. `pre-push` uses `--no-renames` and does not have this gap.
- Re-check both against the current `.husky/pre-commit` and `tests/test_hooks.py` before changing anything and report any discrepancy.

## Scope

- Make the staged-file list NUL-delimited end to end (`git diff --cached -z --name-only` with `xargs -0`, or an equivalent) in `.husky/pre-commit`.
- Make the `.agents/`-only skip decision rename-aware, matching `pre-push`'s `--no-renames`.
- Add tests in `tests/test_hooks.py` for a staged filename with a space and one with a quote or non-ASCII character, and for a rename into `.agents/`. Each must fail before the fix.

## Non-goals

- Do not change `scripts/gate.sh`, `scripts/autofix.sh`, `.husky/pre-push` or `scripts/commit_lint.py`.
- Do not change which files the skip rule treats as tooling.
- Do not touch CI, `pyproject.toml` `[tool]` sections or any `.agents/` file other than the report.

## Files to inspect

- `.husky/pre-commit`, `.husky/pre-push`
- `tests/test_hooks.py`
- `scripts/lib/common.sh` (`staged_files`, `run_on_files`)

## Required behavior

Autofix changes to a file with whitespace, quotes or non-ASCII in its name are re-staged and included in the commit. A pure rename into `.agents/` runs the gate unless the renamed file is itself under `.agents/` after and before. Runs under bash 3.2.

## Tests required

New tests in `tests/test_hooks.py`, shown failing before the fix and passing after. Run `scripts/gate.sh`. If Docker is available, also run the staged paths under `docker run bash:3.2`.

## Documentation required

None needed unless `scripts/README.md` or `DEV_TOOLING_SPEC.md` describes the re-staging step; if so, update only that sentence. Note: this edits `.husky/`, which AGENTS.md puts under ask-first; the owner approved hook work for this series, but the executor must stop and ask if the change grows beyond `pre-commit`.

## Acceptance criteria

- [ ] A staged `sp ace.py` with autofix changes is re-staged and the commit contains the fixed content.
- [ ] Same for a name with a quote and for a non-ASCII name.
- [ ] A pure rename into `.agents/` does not skip the gate.
- [ ] The new tests failed before the fix and pass after.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches` plus the report.

## Workflow

- Read `AGENTS.md` (and `CLAUDE.md`, if present) first.
- Create a worktree and branch from `develop` as `fix/T-0008-fix-pre-commit-re-staging-for-unusual-filenames`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0008.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request.
- Do not edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state.

## Report

Fill in `.agents/tasks/reports/T-0008.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0008
```
