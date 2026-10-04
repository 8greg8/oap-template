---
id: T-0022
title: Add the changelog tool, CHANGELOG.md and changelog fragments
status: open
type: feat
priority: high
depends_on: []
touches: [scripts/changelog.py, tests/test_changelog.py, CHANGELOG.md, changelog.d/README.md, changelog.d/template.added.md, changelog.d/T-0022.added.md]
created: 2026-10-04
report: reports/T-0022.md
---

# T-0022 — Add the changelog tool, CHANGELOG.md and changelog fragments

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

A stdlib-only `scripts/changelog.py` with `check`, `preview` and `assemble` exists and is tested,
`CHANGELOG.md` exists in Keep a Changelog form with an empty `[Unreleased]`, and `changelog.d/`
holds a README, the template summary fragment and this task's own fragment.

## Context / current verified state

- Plan: `.agents/plans/2026-10-04-changelog-and-versioning.md`, accepted by the owner on 2026-10-04 (D1 to D8). Its § Design is the source of
  truth for behavior; where this file and the plan differ, stop and report.
- The plan's § Approvals records the owner's written approval for the "Ask first" and
  breaking-change items this task touches; the orchestrator cites it at merge.
- Re-check against `develop` before starting and report any discrepancy.
- No `CHANGELOG.md` or `changelog.d/` exists. `scripts/next_version.py` classifies commits
  (breaking > feat > fix) with the regex at line 24 and `classify` near line 92; reuse that
  logic, do not duplicate it divergently.
- Everything under `scripts/` is stdlib-only Python with Google-style docstrings
  (`PYTHON_CONVENTIONS.md`).

## Scope

- `scripts/changelog.py` with the three subcommands exactly as the plan's § `scripts/changelog.py`
  and § Changelog fragments define them: fragment pattern `changelog.d/<id>.<category>.md`,
  the six categories, `check <base> <tip>` (non-merge commits, per-commit added fragments,
  tip validation), `preview`, `assemble <version> [--date]` (refuses a non-empty
  `[Unreleased]`, Keep a Changelog category order, deletes folded fragments, never touches
  `changelog.d/README.md`). Clear exit codes and messages.
- `CHANGELOG.md`: Keep a Changelog 1.1.0 header, link to SemVer, empty `## [Unreleased]`.
- `changelog.d/README.md`: how to write a fragment; must not name the template
  (`proj_template`, `proj-template`, `oap-template`, `8greg8`).
- `changelog.d/template.added.md`: the D6 summary of the template as it stands (task tooling,
  gate and hooks, gitflow, init script, devcontainer, policies), a few bullets.
- `changelog.d/T-0022.added.md`: this task's entry.
- `tests/test_changelog.py` with real temporary git repositories.

## Non-goals

- Do not change `.husky/`, `scripts/gitflow.sh`, `scripts/release.py` or `scripts/next_version.py`
  (T-0023, T-0024).
- Do not change `init_project.py` (T-0025) or any documentation file (T-0026).
- Do not add a dependency.

## Files to inspect

- `.agents/plans/2026-10-04-changelog-and-versioning.md`
- `scripts/next_version.py`, `scripts/commit_lint.py`, `tests/test_commit_lint.py`
- `PYTHON_CONVENTIONS.md`

## Required behavior

`check` fails on a `feat`, `fix` or breaking non-merge commit with no fragment added in the
range, and on any invalid fragment at the tip; passes otherwise, including when fragments were
added and later deleted in the range. `assemble` turns fragments into one dated section under
`[Unreleased]` and deletes them.

## Tests required

- `tests/test_changelog.py`: classification parity with `next_version.py`; merges ignored;
  per-commit fragment detection (added then deleted still counts); fragment name, category,
  empty and placeholder failures; README ignored; `assemble` output order, date, deletion,
  refusal on non-empty `[Unreleased]`; `preview` changes nothing.
- `uv run pytest tests/test_changelog.py -v` and `scripts/gate.sh`.

## Documentation required

`changelog.d/README.md` (new). Other docs are T-0026.

## Acceptance criteria

- [ ] `changelog.py check`, `preview` and `assemble` behave as the plan specifies.
- [ ] Only `changelog.d/<id>.<category>.md` files are fragments; `README.md` is never validated, folded or deleted.
- [ ] `CHANGELOG.md` has the Keep a Changelog header and an empty `[Unreleased]`.
- [ ] `changelog.d/template.added.md` and `changelog.d/T-0022.added.md` exist and pass `check`.
- [ ] `changelog.d/README.md` names no template string.
- [ ] `uv run pytest tests/test_changelog.py -v` passes.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `feat/T-0022-add-the-changelog-tool-changelog-md-and`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0022.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0022.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0022
```
