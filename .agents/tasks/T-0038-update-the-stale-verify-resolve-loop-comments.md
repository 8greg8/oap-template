---
id: T-0038
title: Update the stale verify-resolve loop comments in scripts
status: done
type: docs
priority: low
depends_on: []
touches: [scripts/gate.sh, scripts/autofix.sh, scripts/config/gate.sh]
created: 2026-10-06
report: reports/T-0038.md
---

# T-0038 — Update the stale verify-resolve loop comments in scripts

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

Three comments in `scripts/` describe the old per-commit "verify/resolve loop". Reword them to match
the current rules, with no change to what any script does.

## Context / current verified state

- `scripts/gate.sh:2-3` says the gate is "run by agents during the verify/resolve loop, by
  .husky/pre-commit (--staged), by .husky/pre-push, and by CI". Under the current rules the executor
  iterates with `--fast`, the one independent verifier runs the full gate, and `--if-needed` serves
  the later mechanical steps (`CONTRIBUTING.md` § "Agent verify/resolve workflow").
- `scripts/autofix.sh:2` calls the script "the 'resolve' half of the verify/resolve loop's
  mechanical part". There is no per-commit resolve loop now; the script is run by the pre-commit
  hook and by hand.
- `scripts/config/gate.sh:13` says "The four verify/resolve gates, in the order CONTRIBUTING.md's
  verify/resolve workflow runs them". The four commands and their order are unchanged.
- The heading "Agent verify/resolve workflow" still exists in `CONTRIBUTING.md`, so the comments are
  stale in their meaning, not broken references. Found by the independent verifier of T-0036.
- Re-check these lines against `develop` first, and `grep -rn "verify/resolve" scripts/ .husky/`
  for any other occurrence. Report a discrepancy before editing.

## Scope

- Reword those three comments (and any other `verify/resolve` comment the grep finds under
  `scripts/`) to describe who runs each script now. Comment lines only.
- Keep line lengths and style like the surrounding comments.

## Non-goals

- Do not change any executable line, variable, default command, flag or exit code.
- Do not change `STAGED_GLOB`, the gate commands or the `RECORD_PATHS` and slow-test settings.
- Do not change `.husky/`, `CONTRIBUTING.md`, `CLAUDE.md`, `scripts/README.md` or any test.
- No changelog fragment: this is a `docs` change with no behavior change.
- No new or edited tracked file contains `proj_template`, `proj-template`, `oap-template`, `8greg8`
  or the owner's email.

## Files to inspect

- `scripts/gate.sh`, `scripts/autofix.sh`, `scripts/config/gate.sh`
- `CONTRIBUTING.md` § "Agent verify/resolve workflow" and § Git hooks

## Required behavior

The comments say who runs each script under the current rules. Every script behaves exactly as
before: the diff has comment lines only.

## Tests required

- Show the diff is comment-only: every added and removed line, ignoring whitespace, starts with `#`
  (for example `git diff -U0 $(git merge-base origin/develop HEAD) HEAD -- scripts/ | grep -E
  '^[+-][^+-]' | grep -vE '^[+-]\s*#'` prints nothing).
- `scripts/gate.sh` (full; a change under `scripts/` is not on the slow-test safe list, so the slow
  tests run).

## Documentation required

None needed: the comments are the change. No changelog fragment (`docs` type).

## Acceptance criteria

- [ ] The three comments no longer describe a per-commit verify/resolve loop and match `CONTRIBUTING.md`.
- [ ] The diff contains comment lines only; the command from "Tests required" prints nothing.
- [ ] `grep -rn "verify/resolve" scripts/ .husky/` shows no stale meaning.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `docs/T-0038-update-the-stale-verify-resolve-loop-comments`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits. Iterate with
  `scripts/gate.sh --fast` and targeted tests and commit freely. Do not spawn a verifier: your own
  gate runs certify nothing.
- Write the report to `.agents/tasks/reports/T-0038.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after one
  independent verify of the pushed branch by a different agent, which runs the full gate itself.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0038.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0038
```
