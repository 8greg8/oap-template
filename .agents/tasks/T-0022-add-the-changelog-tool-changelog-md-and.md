---
id: T-0022
title: Add the changelog tool, CHANGELOG.md and changelog fragments
status: done
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
- No new tracked file (`CHANGELOG.md`, every `changelog.d/*` file, `tests/test_changelog.py`)
  contains `proj_template`, `proj-template`, `oap-template`, `8greg8` or the owner's email. `tests/test_init_project.py::test_template_strings_remain_only_in_allowed_files` scans every
  generated file for the three template strings, including `changelog.d/` and
  `tests/test_changelog.py` (which is not in its `ALLOWED_HITS`), so do not write any of the
  strings into `test_changelog.py`.
- Exit codes: `check` exits 0 on pass, 1 on a missing or invalid fragment, 2 on a usage error or
  when git cannot resolve `<base>` or `<tip>` or list the range.
- `check` lists and reads fragments at `<tip>` from git (`git ls-tree <tip> -- changelog.d/`,
  `git show <tip>:<path>`), never from the working tree. `assemble` and `preview` use the working
  tree.
- Fragment rules: `<id>` matches `[A-Za-z0-9][A-Za-z0-9_-]*` (no dots); a bullet is a line
  starting with `- ` or `* `, indented continuation lines allowed; a placeholder is a bullet whose
  text is empty, contains a match of the regex `\bto-?do\b`, or contains `TBD`, `FIXME` or the
  literal `<...>` (all case-insensitive); a bullet that names a pattern such as
  `changelog.d/<id>.<category>.md` is valid. Any file
  in `changelog.d/` other than `README.md` that does not match `<id>.<category>.md` fails as a bad
  name; `assemble` ignores `README.md` and refuses (exit 1, no changes) when any file fails these
  rules.
- The task and report validators reject the upper-case to-do word anywhere in a section; in the
  report, refer to that marker by the regex above.
- Versions: `assemble` accepts `X.Y.Z` or `vX.Y.Z` and writes `## [X.Y.Z] - YYYY-MM-DD`; `--date`
  defaults to today's local date. `preview [<version>]` prints the section `assemble` would
  write, headed `## [X.Y.Z] - <today>` when `<version>` is given or `## [Unreleased]` otherwise; it never calls
  `next_version.py` and changes nothing.
- `assemble` with zero fragments exits 1 and writes nothing. Within a category, fragments are
  ordered by file name and bullets keep file order. No compare-link footers. `assemble` edits and
  deletes working-tree files only and does not stage; the caller stages.

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
- Tests use only temporary repositories and fixtures; none reads this repository's `CHANGELOG.md`
  or `changelog.d/` contents. They pass in a project produced by `init_project.py`.

## Documentation required

`changelog.d/README.md` (new). Other docs are T-0026.

## Acceptance criteria

- [ ] `changelog.py check`, `preview` and `assemble` behave as the plan specifies.
- [ ] Only `changelog.d/<id>.<category>.md` files are fragments; `README.md` is never validated, folded or deleted.
- [ ] `CHANGELOG.md` has the Keep a Changelog header and an empty `[Unreleased]`.
- [ ] `changelog.d/template.added.md` and `changelog.d/T-0022.added.md` exist, and `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 on the pushed branch.
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
