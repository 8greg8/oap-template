---
id: T-0031
title: Fold the post-batch fragments and document the pre-release wording rule
status: done
type: docs
priority: medium
depends_on: []
touches: [changelog.d/template.added.md, changelog.d/T-0028.fixed.md, changelog.d/T-0029.fixed.md, changelog.d/T-0030.changed.md, changelog.d/README.md, CONTRIBUTING.md, .agents/README.md]
created: 2026-10-05
report: reports/T-0031.md
---

# T-0031 — Fold the post-batch fragments and document the pre-release wording rule

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

The first release's changelog describes the template as it will first ship. The fragments of T-0028,
T-0029 and T-0030 are folded into `changelog.d/template.added.md` as plain feature bullets and
deleted, `changelog.d/README.md` states the wording rule for the period before the first release,
`CONTRIBUTING.md` has a curate-before-release step, and `.agents/README.md` has the verifier check
fragment wording. `python3 scripts/changelog.py preview v0.1.0` then shows one `### Added` section
with no "Breaking:", "no longer" or "used to" text.

## Context / current verified state

- Plan: `.agents/plans/2026-10-05-first-release-changelog-wording.md`, accepted by the owner on 2026-10-05 ("go ahead with all of it"). Its § Approvals
  is the owner's written approval for this task's fragment deletions; cite it in the report. Where
  this file and the plan differ, stop and report.
- Re-check against `develop` before starting (`git pull --ff-only origin develop`) and report any
  discrepancy.
- `changelog.d/` holds `README.md`, `template.added.md`, `T-0022.added.md`, `T-0025.added.md`,
  `T-0028.fixed.md`, `T-0029.fixed.md` and `T-0030.changed.md`. `python3 scripts/changelog.py
  preview v0.1.0` prints a `### Changed` and a `### Fixed` section whose bullets say "Breaking:",
  "no longer" and "used to" about behavior that was never released.
- T-0027 already folded the fragments of T-0023 and T-0024 into `changelog.d/template.added.md`
  for the same reason; `.agents/tasks/reports/T-0027.md` shows how.
- `changelog.d/README.md` is copied into generated projects.
- `.agents/README.md` (about line 148) describes what the verifier checks, including the fragment.
- `CONTRIBUTING.md` § Releasing describes the release dry run and the `--yes` sequence.

## Scope

- Rewrite the content of `changelog.d/T-0028.fixed.md`, `changelog.d/T-0029.fixed.md` and
  `changelog.d/T-0030.changed.md` as plain bullets in `changelog.d/template.added.md`, each a
  statement of what the template does. Cover: the `changelog.py` content rule, strict UTF-8, the
  ignored BOM, `--date` as `YYYY-MM-DD`, exit status 3, and renames not counting as added; the
  pre-push hook using the push's own remote and reporting a failed check distinctly from a missing
  fragment; `gitflow.sh finish` fetching the base first; `scripts/config/gate.sh` staying
  POSIX-sourceable; `release.py` requiring `--yes` with `--push`, printing labelled stdout and
  stderr, the `git rm` advice for a fragment conflict, the two causes of a rejected push, and
  refusing a repository with no commits; running `release.py --yes` or `--push` being an "Ask
  first" item; and the corrected documentation. Merge a new bullet into an existing one where they
  overlap, and keep the bullets consistent with each other (for example `--push` requires
  `--yes`). Use no "Breaking:", "no longer", "used to" or "now".
- Delete `changelog.d/T-0028.fixed.md`, `changelog.d/T-0029.fixed.md` and
  `changelog.d/T-0030.changed.md` with `git rm`. The owner approved these deletions in the plan.
- `changelog.d/README.md`: add a section "Before the first release". While no `vX.Y.Z` tag exists,
  a fragment describes the project as it will first ship: plain "added" bullets, with no
  "Breaking:" and no "no longer", "used to" or "now", because nothing has been released to change.
  Give one wrong and one right example. After the first release a fragment describes a change to
  released behavior, and a breaking change starts with "Breaking:". No template-name strings.
- `CONTRIBUTING.md` § Releasing: add a step before `release.py --yes`: read the dry run's changelog
  section, then merge, reword or delete fragments that read wrong (a fix to something this release
  introduced belongs in one bullet or none), and commit those edits as a `docs(changelog)` change
  through the usual branch flow, which needs no fragment. Link the wording rule.
- `.agents/README.md`: in the verifier's checks, add that it reads each new fragment against the
  wording rule and reports "Breaking:", "no longer", "used to" or "now" before the first tag.
- Commits: `docs(changelog): ...` for the fragments and the README, `docs(contributing): ...` and
  `docs(agents): ...` for the others. None is breaking and none needs a fragment.

## Non-goals

- Do not change any script, hook, test or `init_project.py`, and add no code that enforces the
  wording rule. It is documentation and a verifier check.
- Do not change `CLAUDE.md` or `DEV_TOOLING_SPEC.md` (T-0032).
- Do not change `CHANGELOG.md`, run a release or create a tag.
- Do not change `changelog.d/T-0022.added.md` or `changelog.d/T-0025.added.md`, and reword the
  existing bullets of `changelog.d/template.added.md` only as far as consistency needs.
- No new or edited tracked file contains `proj_template`, `proj-template`, `oap-template`,
  `8greg8` or the owner's email. Do not name the source project of the practice.

## Files to inspect

- `.agents/plans/2026-10-05-first-release-changelog-wording.md`
- `changelog.d/*`, `.agents/tasks/reports/T-0027.md` (the earlier fold)
- `CONTRIBUTING.md` § Releasing and § Versioning, `.agents/README.md` (verifier section)

## Required behavior

`python3 scripts/changelog.py preview v0.1.0` prints a single `### Added` section. The text of the
preview contains none of "Breaking:", "no longer" and "used to". `changelog.py check` passes, and
every remaining fragment passes the content rule.

## Tests required

- `python3 scripts/changelog.py preview v0.1.0`: one `### Added` section, no "Breaking:", "no
  longer" or "used to". Record the output summary.
- `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 (use
  local `develop` when the branch is not pushed, and say so).
- `python .agents/tasks/scripts/task.py validate` and `scripts/gate.sh` on the committed branch.
  Run one test or gate process at a time: parallel runs share a pytest temp directory and cause
  spurious fixture errors.

## Documentation required

The files in `touches`, as in Scope. No fragment: this is a `docs` task.

## Acceptance criteria

- [ ] `changelog.d/T-0028.fixed.md`, `changelog.d/T-0029.fixed.md` and `changelog.d/T-0030.changed.md` are deleted and their content is in `changelog.d/template.added.md`.
- [ ] `python3 scripts/changelog.py preview v0.1.0` shows one `### Added` section and none of "Breaking:", "no longer", "used to".
- [ ] `changelog.d/template.added.md` states `--push` requires `--yes` and is consistent with `CONTRIBUTING.md`.
- [ ] `changelog.d/README.md` has the "Before the first release" section with a wrong and a right example and names no template string.
- [ ] `CONTRIBUTING.md` § Releasing has the curate-before-release step and links the rule.
- [ ] `.agents/README.md` has the verifier checking fragment wording.
- [ ] `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 on the pushed branch.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `docs/T-0031-fold-the-post-batch-fragments-and-document-the`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0031.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0031.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0031
```
