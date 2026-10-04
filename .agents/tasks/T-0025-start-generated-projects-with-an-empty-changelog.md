---
id: T-0025
title: Start generated projects with an empty changelog
status: done
type: feat
priority: medium
depends_on: [T-0022]
touches: [init_project.py, tests/test_init_project.py, changelog.d/T-0025.added.md]
created: 2026-10-04
report: reports/T-0025.md
---

# T-0025 — Start generated projects with an empty changelog

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

A project created with `init_project.py` starts with an empty `CHANGELOG.md` and no fragments,
names no template string, and its checklist says branch protection must allow the release push.

## Context / current verified state

- Plan: `.agents/plans/2026-10-04-changelog-and-versioning.md`, accepted by the owner on 2026-10-04 (D1 to D8). Its § Design is the source of
  truth for behavior; where this file and the plan differ, stop and report.
- The plan's § Approvals records the owner's written approval for the "Ask first" and
  breaking-change items this task touches; the orchestrator cites it at merge.
- Re-check against `develop` before starting and report any discrepancy.
- Depends on T-0022 (the files it resets).
- `init_project.py` builds a dry-run change list (`plan_changes`), removes task state, seeds
  files (`step_seed_files`) and prints a checklist (`step_checklist`, branch-protection item near
  line 789). `tests/test_init_project.py` greps generated projects for template strings.

## Scope

- Replace `CHANGELOG.md` with the Keep a Changelog header and an empty `[Unreleased]`.
- Remove every fragment matching `changelog.d/<id>.<category>.md`; keep `changelog.d/README.md`.
- List both in the dry-run change list.
- Reword the checklist's branch-protection item so protection allows the release push or the
  owner releases through pull requests.
- Tests in `tests/test_init_project.py`.
- `changelog.d/T-0025.added.md`: this task's entry.
- Do the reset inside `step_seed_files` (update its docstring) and add both lines to
  `plan_changes` next to the other `replace`/`remove` seed lines; no new step (the test harness's
  `_THROUGH_SEEDING` filter would drop one).
- The generated `CHANGELOG.md` is byte-identical to the header and `## [Unreleased]` part of
  T-0022's `CHANGELOG.md`; a test runs `scripts/changelog.py assemble` on it with one fragment to
  prove it parses.
- Reword the branch-protection mention in `plan_changes`' closing checklist line as well as the
  `step_checklist` item.

## Non-goals

- Do not change any other init step.
- Do not change `scripts/`, `.husky/` or documentation files.
- Do not delete git tags.

## Files to inspect

- `.agents/plans/2026-10-04-changelog-and-versioning.md`
- `init_project.py`, `tests/test_init_project.py`, `changelog.d/README.md`, `CHANGELOG.md`

## Required behavior

After `python init_project.py ...`, `CHANGELOG.md` holds only the header and `[Unreleased]`,
`changelog.d/` holds only `README.md`, the dry run lists both changes, and the end-to-end
template-string grep still finds nothing.

## Tests required

- Dry-run list, generated `CHANGELOG.md` content, fragments removed, README kept, checklist
  wording, end-to-end grep.
- `uv run pytest tests/test_init_project.py -v` and `scripts/gate.sh`.

## Documentation required

None in this task; T-0026 documents generated-project behavior.

## Acceptance criteria

- [ ] A generated project's `CHANGELOG.md` has only the header and an empty `[Unreleased]`.
- [ ] A generated project has no fragments and keeps `changelog.d/README.md`.
- [ ] The dry run lists both changes.
- [ ] The checklist's branch-protection item mentions the release push.
- [ ] `changelog.d/T-0025.added.md` exists and `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 on the pushed branch.
- [ ] `uv run pytest tests/test_init_project.py -v` passes.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `feat/T-0025-start-generated-projects-with-an-empty-changelog`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0025.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0025.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0025
```
