---
id: T-0029
title: Fix release.py edge cases
status: in_progress
type: fix
priority: high
depends_on: [T-0027]
touches: [scripts/release.py, tests/test_release.py, changelog.d/T-0029.fixed.md]
created: 2026-10-05
report: reports/T-0029.md
---

# T-0029 — Fix release.py edge cases

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

`release.py` never releases without `--yes`, shows the full output of a failed step, gives
correct recovery advice for fragment conflicts and rejected pushes, and refuses cleanly in a
repository with no commits.

## Context / current verified state

- Plan: `.agents/plans/2026-10-05-post-batch-review-fixes.md`, accepted by the owner on 2026-10-05 (all tasks, decisions A and B). Its § Approvals
  is the owner's written approval for this task's "Ask first" and breaking items; cite it in the
  report. Where this file and the plan differ, stop and report.
- Re-check against `develop` before starting (`git pull --ff-only origin develop`) and report any
  discrepancy.
- `scripts/release.py:689-701`: `--push` sets `args.yes = True`, documented in its help text,
  `CONTRIBUTING.md:220` and `DEV_TOOLING_SPEC.md:305`.
- `:495` prints `result.stderr or result.stdout` after a failed step, so a hook's stdout (for
  example ruff diagnostics) is lost.
- `:449`, `:466`: a modify/delete conflict on a `changelog.d/` fragment while updating `develop`
  after a hotfix release is resolved by the generic advice, which can keep the fragment and fold
  it twice at the next release.
- `:593-596`: a rejected push only suggests `git fetch origin`, not a local pre-push hook failure.
- `:111`: `current_branch()` raises in a repository with no commits.
- `:469`: when the run starts on `develop`, the finish list prints `git checkout develop` twice.

## Scope

- `--push` without `--yes` exits 2 with a usage message and changes nothing.
- After a failed step, print stdout and stderr (both, labelled).
- When the `develop` update conflicts on a path under `changelog.d/` (other than `README.md`),
  the printed advice says to resolve it as deleted (`git rm <path>`) because `main` already
  folded it.
- A rejected push's message names both causes: another push won the race (fetch and retry) or a
  local pre-push hook failed (fix and rerun the printed push command).
- A repository with no commits: refuse with a clear message (exit 1).
- Do not print the same `git checkout <start>` twice in the finish list.
- Tests in `tests/test_release.py`; at least one test runs the real `.husky` hooks on the commits
  `release.py` makes (the fixture sets `core.hooksPath=/dev/null` today).
- `changelog.d/T-0029.fixed.md`: this task's entry. The behavior commit is `fix(release)!:` with a
  `BREAKING CHANGE:` footer: `--push` no longer implies `--yes`.
- The real-hooks test copies `.husky/{commit-msg,pre-commit,pre-push}`, `scripts/commit_lint.py`,
  `scripts/autofix.sh`, `scripts/lib/common.sh` and a stub `scripts/gate.sh` (`exit 0`) into the
  fixture, sets `core.hooksPath=.husky`, runs `release.py --yes --push`, and asserts that the
  merge and release commits pass `commit-msg` and `pre-commit` and the push passes pre-push's
  changelog check.
- The task's fragment holds only bullet and indented continuation lines and no placeholder
  words, so it passes T-0028's content rule whichever task merges first.

## Non-goals

- Do not change the release sequence, refusals, version rules or `--version` behavior beyond the
  items above.
- Do not change `scripts/changelog.py`, `scripts/next_version.py`, `scripts/gitflow.sh` or hooks.
- Do not change documentation files (T-0030).
- No new or edited tracked file contains `proj_template`, `proj-template`, `oap-template`, `8greg8` or the owner's email.

## Files to inspect

- `.agents/plans/2026-10-05-post-batch-review-fixes.md`
- `scripts/release.py`, `tests/test_release.py`, `.agents/tasks/T-0024-*.md` (the original contract)

## Required behavior

Each item in Scope behaves as stated; every other behavior in the T-0024 task file is unchanged.

## Tests required

- One test per Scope item, plus the real-hooks test.
- `uv run pytest tests/test_release.py -v` and `scripts/gate.sh`.

## Documentation required

`release.py --help` text for `--push`. Other docs are T-0030.

## Acceptance criteria

- [ ] `release.py --push` without `--yes` exits 2 and changes nothing.
- [ ] A failed step prints both stdout and stderr.
- [ ] A fragment conflict during the `develop` update prints `git rm` advice for that path.
- [ ] A rejected push names the local hook failure as a possible cause.
- [ ] A repository with no commits is refused with exit 1 and no traceback.
- [ ] The finish list never repeats the same checkout.
- [ ] A test runs the real `.husky` hooks on `release.py`'s commits.
- [ ] `changelog.d/T-0029.fixed.md` exists and `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 on the pushed branch.
- [ ] `uv run pytest tests/test_release.py -v` passes.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `fix/T-0029-fix-release-py-edge-cases`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0029.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0029.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0029
```
