---
id: T-0027
title: Make init tests independent of template fragments and fold the first release entries
status: open
type: chore
priority: high
depends_on: []
touches: [tests/test_init_project.py, changelog.d/template.added.md, changelog.d/T-0023.changed.md, changelog.d/T-0024.changed.md]
created: 2026-10-05
report: reports/T-0027.md
---

# T-0027 — Make init tests independent of template fragments and fold the first release entries

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

The test suite passes whether or not the template has changelog fragments, so the first release
can be pushed, and the first release's changelog describes the template without "Breaking:"
entries against a version that was never released.

## Context / current verified state

- Plan: `.agents/plans/2026-10-05-post-batch-review-fixes.md`, accepted by the owner on 2026-10-05 (all tasks, decisions A and B). Its § Approvals
  is the owner's written approval for this task's "Ask first" and breaking items; cite it in the
  report. Where this file and the plan differ, stop and report.
- Re-check against `develop` before starting (`git pull --ff-only origin develop`) and report any
  discrepancy.
- `tests/test_init_project.py:965` (`test_dry_run_lists_the_changelog_reset_and_changes_nothing`)
  and `:1002` (`test_generated_project_has_no_fragments_and_keeps_the_fragment_readme`) assert the
  scratch template copy has fragments. A release deletes every fragment, so after
  `release.py --yes --push` the pre-push gate fails these two tests and rejects the push
  (reproduced in the post-merge review).
- `changelog.d/T-0023.changed.md` and `changelog.d/T-0024.changed.md` start their bullets with
  "Breaking:". `changelog.d/template.added.md` holds the template summary (decision B).

## Scope

- In those two tests (or the fixture they share), write a test-owned fragment into the scratch
  copy and commit it there before running init, and assert on that fragment, never on the
  repository's own `changelog.d/` contents.
- Decision B: rewrite the content of `changelog.d/T-0023.changed.md` and
  `changelog.d/T-0024.changed.md` as plain feature bullets in `changelog.d/template.added.md`
  (fragment check on push and at finish; release from `develop` into `main` with the changelog;
  the 0.x rule; the hotfix release step), then delete those two fragments. Keep
  `T-0022.added.md` and `T-0025.added.md`.
- Commit types: `test(init): ...` for the tests and `docs(changelog): ...` for the fragments; no
  fragment for this task (neither type needs one).

## Non-goals

- Do not change `init_project.py`, any file under `scripts/` or `.husky/`, or any other test.
- Do not change `CHANGELOG.md` or run a release.
- Do not reword `T-0022.added.md` or `T-0025.added.md`.
- No new or edited tracked file contains `proj_template`, `proj-template`, `oap-template`, `8greg8` or the owner's email.

## Files to inspect

- `.agents/plans/2026-10-05-post-batch-review-fixes.md`
- `tests/test_init_project.py` (the two tests and their fixture), `changelog.d/*`

## Required behavior

With every fragment except `changelog.d/README.md` removed from a copy of the repository, the full
test suite passes. `python3 scripts/changelog.py preview v0.1.0` shows one `### Added` section and
no "Breaking:" text.

## Tests required

- In a scratch copy: delete all fragments except `README.md`, commit, run
  `uv run pytest tests/test_init_project.py -q`; it passes. Record the command and result.
- `uv run pytest tests/test_init_project.py -v` and `scripts/gate.sh` on the branch.
- `python3 scripts/changelog.py preview v0.1.0` and `python3 scripts/next_version.py` (still
  `v0.1.0`).

## Documentation required

None.

## Acceptance criteria

- [ ] The two tests no longer depend on the repository's own fragments.
- [ ] With all fragments removed in a scratch copy, `uv run pytest tests/test_init_project.py -q` passes.
- [ ] `changelog.d/T-0023.changed.md` and `changelog.d/T-0024.changed.md` are deleted and their content is in `changelog.d/template.added.md` without "Breaking:".
- [ ] `python3 scripts/changelog.py preview v0.1.0` shows no "Breaking:" text, and `python3 scripts/next_version.py` prints `v0.1.0`.
- [ ] `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 on the pushed branch.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `chore/T-0027-make-init-tests-independent-of-template`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0027.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0027.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0027
```
