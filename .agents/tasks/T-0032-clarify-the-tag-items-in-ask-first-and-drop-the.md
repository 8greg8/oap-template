---
id: T-0032
title: Clarify the tag items in Ask first and drop the stale README reference
status: review
type: docs
priority: medium
depends_on: [T-0031]
touches: [CLAUDE.md, CONTRIBUTING.md, DEV_TOOLING_SPEC.md, changelog.d/T-0032.added.md, changelog.d/T-0025.added.md]
created: 2026-10-05
report: reports/T-0032.md
---

# T-0032 — Clarify the tag items in Ask first and drop the stale README reference

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

`CLAUDE.md`'s "Ask first" list has two clear items: creating a release tag by hand, and running
`scripts/release.py --yes` or `--yes --push`. No text says `release.py` is "the tagging step", and
`CONTRIBUTING.md` and `DEV_TOOLING_SPEC.md` no longer quote the old wording or cite a README step
that a generated project lacks.

## Context / current verified state

- Plan: `.agents/plans/2026-10-05-first-release-changelog-wording.md`, accepted by the owner on 2026-10-05 ("go ahead with all of it"). Its § Approvals
  is the owner's written approval for this task's "Ask first" and breaking items; cite it in the
  report. Where this file and the plan differ, stop and report.
- Re-check against `develop` before starting (`git pull --ff-only origin develop`) and report any
  discrepancy. Depends on T-0031: both edit `CONTRIBUTING.md`, and T-0031 writes the fragment
  wording rule this task's fragment follows.
- `CLAUDE.md:111-112` reads "Cutting a release tag by hand (outside the tagging step defined in
  `CONTRIBUTING.md`) or editing an existing tag." The next item (`:113-118`) says "The tagging step
  named in the previous item is this script, so it is not exempt."
- `CONTRIBUTING.md:228` says "`scripts/release.py` is also the tagging step that `CLAUDE.md`
  mentions, so it is not exempt."
- `DEV_TOOLING_SPEC.md:6-9` says it implements "the tagging step `CLAUDE.md` refers to ("outside
  the tagging step defined in `CONTRIBUTING.md`")" and that "`README.md` step 3 installs the bundle
  in a generated project". A generated project's README has no numbered steps, and in the template
  step 3 runs the init script.

## Scope

- `CLAUDE.md` "Ask first", first tag item: "Creating a release tag by hand (any tag not created by
  `scripts/release.py`) or editing an existing tag."
- `CLAUDE.md` "Ask first", release item: remove the sentence "The tagging step named in the
  previous item is this script, so it is not exempt." Keep the rest of the item unchanged.
- `CONTRIBUTING.md:228`: replace the sentence about the tagging step with one saying tags are
  created only by `scripts/release.py` and creating one by hand is a separate "Ask first" item.
- `DEV_TOOLING_SPEC.md:6-9`: remove the clause about the tagging step `CLAUDE.md` refers to and the
  sentence "`README.md` step 3 installs the bundle in a generated project"; keep the surrounding
  sentences correct.
- Keep `## Working unit: the task` as `CLAUDE.md`'s first `##` heading. Change no other "Ask first"
  item and nothing in § Merge authority.
- `changelog.d/T-0032.added.md`: a plain bullet, worded by the rule in `changelog.d/README.md`
  (no "Breaking:", "no longer", "used to" or "now"), saying the agent rules list creating a release
  tag by hand and running `scripts/release.py --yes` or `--yes --push` as separate "Ask first"
  items.
- Commits: the `CLAUDE.md` commit is `docs(claude)!:` with a `BREAKING CHANGE:` footer naming the
  two reworded items and this plan, and it carries the fragment. The `CONTRIBUTING.md` and
  `DEV_TOOLING_SPEC.md` commits are `docs(...)` and not breaking.

## Non-goals

- Do not change any other "Ask first" item, § Merge authority or the first `##` heading of
  `CLAUDE.md`.
- Do not change any script, hook, test or `init_project.py`, and do not change the task or report
  schema.
- Do not change `CHANGELOG.md`, run a release or create a tag.
- Do not edit historical plans or task and report files that quote the old wording.
- No new or edited tracked file contains `proj_template`, `proj-template`, `oap-template`,
  `8greg8` or the owner's email. Do not name the source project of the practice.

## Files to inspect

- `.agents/plans/2026-10-05-first-release-changelog-wording.md`
- `CLAUDE.md` ("Ask first"), `CONTRIBUTING.md` § Releasing, `DEV_TOOLING_SPEC.md` (first
  paragraph), `changelog.d/README.md` (the wording rule from T-0031)

## Required behavior

An agent reading `CLAUDE.md` sees one item forbidding hand-made tags and one forbidding an
unrequested `release.py --yes` or `--push`, with no sentence that makes one exempt from the other.
`grep -rn "tagging step" CLAUDE.md CONTRIBUTING.md DEV_TOOLING_SPEC.md` finds nothing, and
`DEV_TOOLING_SPEC.md` no longer cites `README.md` step 3.

## Tests required

- `grep -rn "tagging step\|README.md. step 3" CLAUDE.md CONTRIBUTING.md DEV_TOOLING_SPEC.md`
  prints nothing.
- `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 (use
  local `develop` when the branch is not pushed, and say so).
- `python .agents/tasks/scripts/task.py validate` and `scripts/gate.sh` on the committed branch
  (the init test checks the `CLAUDE.md` anchor). Run one test or gate process at a time.

## Documentation required

The files in `touches`, as in Scope. The breaking `CLAUDE.md` commit carries
`changelog.d/T-0032.added.md`.

## Acceptance criteria

- [ ] `CLAUDE.md` "Ask first" has the reworded tag item and the release item without "so it is not exempt".
- [ ] No other "Ask first" item, no § Merge authority text and no first `##` heading changed in `CLAUDE.md`.
- [ ] `grep -rn "tagging step" CLAUDE.md CONTRIBUTING.md DEV_TOOLING_SPEC.md` prints nothing.
- [ ] `DEV_TOOLING_SPEC.md` has no "`README.md` step 3" reference.
- [ ] The `CLAUDE.md` commit is `docs(claude)!:` with a `BREAKING CHANGE:` footer naming the reworded items.
- [ ] `changelog.d/T-0032.added.md` exists, follows the wording rule, and `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 on the pushed branch.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `docs/T-0032-clarify-the-tag-items-in-ask-first-and-drop-the`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0032.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0032.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0032
```
