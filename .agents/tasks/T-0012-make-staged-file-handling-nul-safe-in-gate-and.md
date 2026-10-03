---
id: T-0012
title: Make staged-file handling NUL-safe in gate and autofix scripts
status: in_progress
type: fix
priority: medium
depends_on: []
touches: [scripts/lib/common.sh, scripts/gate.sh, scripts/autofix.sh, scripts/README.md, tests/test_staged_files.py]
created: 2026-10-03
report: reports/T-0012.md
---

# T-0012 — Make staged-file handling NUL-safe in gate and autofix scripts

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

`scripts/gate.sh --staged` and `scripts/autofix.sh --staged` process staged files whose names contain a double quote, a single quote, a non-ASCII character or a newline, so the commit hook's re-staging fix (T-0008) works end to end.

## Context / current verified state

- T-0008's verify (2026-10-03) confirmed `staged_files` in `scripts/lib/common.sh` runs `git diff --cached --name-only --diff-filter=ACMR` without `-z`. Git then C-quotes names with a quote or non-ASCII character (`"qu\"ote.py"`, `"\304\215\305\241\305\276.py"`).
- `scripts/gate.sh` and `scripts/autofix.sh` read that output line by line into an array. ruff then fails with `E902 No such file or directory`, so the commit is blocked loudly. Names with spaces already work.
- `.husky/pre-commit` already handles all names (T-0008).
- Both scripts must run under bash 3.2: no `mapfile`; `read -r -d ''` is available.
- Re-check each point against the current files and report any discrepancy.

## Scope

- `staged_files`: emit NUL-delimited output (`git diff --cached -z ...`).
- `gate.sh` and `autofix.sh`: read it with `while IFS= read -r -d '' f`, keeping the bash 3.2 empty-array guard.
- Add `tests/test_staged_files.py`: run the real scripts in a scratch git repo with stub lint/format/typecheck commands (or ruff) against staged files named `sp ace.py`, `qu"ote.py`, `it's.py`, `čšž.py` and one with a newline. Each case must fail before the change and pass after.
- Update `scripts/README.md` only if it describes how staged files are listed.

## Non-goals

- Do not change `.husky/`, `scripts/gitflow.sh`, `scripts/commit_lint.py`, `scripts/release.py`, `scripts/config/gate.sh`, CI or `pyproject.toml`.
- Do not change which files are checked or any gate command.
- Do not touch `tests/test_hooks.py`; put new tests in the new module.
- Do not touch any `.agents/` file other than the report.
- This edits `scripts/`, which is human-gated; the owner approved it for this task under the batch grant in `.agents/plans/2026-10-03-batch-merge-grant.md`. Stop and ask if the change grows beyond staged-file listing and reading.

## Files to inspect

- `scripts/lib/common.sh`, `scripts/gate.sh`, `scripts/autofix.sh`, `scripts/config/gate.sh`, `scripts/README.md`
- `.husky/pre-commit`, `tests/test_hooks.py` (for how the existing hook tests build a scratch repo)

## Required behavior

With files named `sp ace.py`, `qu"ote.py`, `it's.py`, `čšž.py` and a name containing a newline staged, `gate.sh --staged` passes each file to the lint, format and typecheck commands as one intact argument, and `autofix.sh --staged` fixes each and the hook re-stages it. With no staged matching files both scripts behave as before. Runs under bash 3.2.

## Tests required

New `tests/test_staged_files.py`, shown failing before the change and passing after. Expected values come from the Required behavior above. Run `scripts/gate.sh`. If Docker is available, also run the changed scripts under `docker run bash:3.2`; if not, report `not run`.

## Documentation required

None needed unless `scripts/README.md` describes staged-file listing; if so, update only that sentence.

## Acceptance criteria

- [ ] `gate.sh --staged` and `autofix.sh --staged` handle a staged `sp ace.py`, `qu"ote.py`, `it's.py`, `čšž.py` and a newline-named file, each passed as one intact argument.
- [ ] Behavior with no staged matching files, and the files checked, are unchanged.
- [ ] The new tests failed before the change and pass after.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches` plus the report.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `fix/T-0012-make-staged-file-handling-nul-safe-in-gate-and`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0012.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0012.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0012
```
