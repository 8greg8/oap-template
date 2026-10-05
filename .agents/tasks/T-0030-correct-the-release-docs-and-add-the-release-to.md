---
id: T-0030
title: Correct the release docs and add the release to Ask first
status: review
type: docs
priority: medium
depends_on: [T-0028, T-0029]
touches: [CLAUDE.md, CONTRIBUTING.md, DEV_TOOLING_SPEC.md, README.md, scripts/README.md, changelog.d/README.md, .agents/README.md, changelog.d/T-0030.changed.md]
created: 2026-10-05
report: reports/T-0030.md
---

# T-0030 — Correct the release docs and add the release to Ask first

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

Running `scripts/release.py --yes` or `--push` is an "Ask first" item, and the process documents
match the code after T-0028 and T-0029.

## Context / current verified state

- Plan: `.agents/plans/2026-10-05-post-batch-review-fixes.md`, accepted by the owner on 2026-10-05 (all tasks, decisions A and B). Its § Approvals
  is the owner's written approval for this task's "Ask first" and breaking items; cite it in the
  report. Where this file and the plan differ, stop and report.
- Re-check against `develop` before starting (`git pull --ff-only origin develop`) and report any
  discrepancy.
- Depends on T-0028 and T-0029; document the merged code, and report any difference from the plan.
- `CLAUDE.md:111` lists only "Cutting a release tag by hand" under "Ask first"; `CONTRIBUTING.md`
  (`:208`) and the new `CLAUDE.md` fragment bullet already claim releases are a human step "as
  Ask first requires".
- `CONTRIBUTING.md:305-307` (verify/resolve step 6, hotfix) tells the agent to run
  `scripts/release.py --yes` on `main`; `:253` states the "not higher than the highest tag"
  refusal without "with `--version`"; the hooks bullet says `chore(merge)` commits pass through
  `pre-commit` (merges run `commit-msg` only; `.husky/` has no `pre-merge-commit`).
- `DEV_TOOLING_SPEC.md:6-7` cites `README.md` step 4 ("Wire up Husky-managed git hooks"), which no
  longer exists. `README.md:18` describes `DEV_TOOLING_SPEC.md` without the changelog.
- T-0022 was started from a stale local `develop`, which needed a fix round and left
  `3412c0d chore(merge): merge origin/develop into develop`.
- `scripts/README.md` and `changelog.d/README.md` are documentation added to the plan's T-0030
  scope by the pre-batch review: they describe `--push`, the hook exit codes
  (`scripts/README.md:56,79-86`) and the fragment rules (`changelog.d/README.md:21-33`).
  `changelog.d/README.md` is copied into generated projects.

## Scope

- `CLAUDE.md` "Ask first": add running `scripts/release.py --yes` or `--push` (a dry run stays
  free). Keep `## Working unit: the task` as the first `##` heading.
- `CONTRIBUTING.md`: step 6 hotfix bullet hands the release to a human; merges run `commit-msg`
  only; `--version` qualifier on the refusal; `--push` requires `--yes` (T-0029); changelog exit
  status 3 and the fragment content rule (T-0028).
- `DEV_TOOLING_SPEC.md`: drop or fix the stale README step reference; T-0028 and T-0029 behavior.
- `scripts/README.md`: `--push` requires `--yes`; exit status 3.
- `changelog.d/README.md`: the content rule (bullets, indented continuations, blank lines only),
  UTF-8 required, a leading BOM ignored. No template-name strings.
- Wherever the docs describe T-0028's behavior (`CONTRIBUTING.md:176-188`,
  `DEV_TOOLING_SPEC.md:164-175`, `scripts/README.md:79-86`): the hook uses the push's remote;
  `gitflow.sh finish` fetches the base first; a renamed fragment does not count as added; strict
  UTF-8 and BOM handling; strict `--date`.
- `README.md`: the `DEV_TOOLING_SPEC.md` table row mentions the changelog.
- `.agents/README.md`: before `set-status` or dispatch the orchestrator runs
  `git pull --ff-only origin develop`; if local `develop` has diverged, it rebases its unpushed
  status commits onto `origin/develop` instead of merging.
- `changelog.d/T-0030.changed.md`: this task's entry. The `CLAUDE.md` commit is
  `docs(claude)!:` with a `BREAKING CHANGE:` footer naming the new "Ask first" item.

## Non-goals

- Do not change any script, hook, test or `init_project.py`.
- Do not change § Merge authority or any other "Ask first" item.
- Do not change the task or report schema.
- No new or edited tracked file contains `proj_template`, `proj-template`, `oap-template`, `8greg8` or the owner's email. Do not name the source project of the practice.

## Files to inspect

- `.agents/plans/2026-10-05-post-batch-review-fixes.md`
- Every file in `touches`; the merged `scripts/changelog.py`, `scripts/release.py`, `.husky/pre-push`

## Required behavior

An agent following only the documents never runs `release.py --yes` or `--push` without the
owner asking, and every documented behavior matches the merged code.

## Tests required

- `scripts/gate.sh` passes (the init test checks the `CLAUDE.md` anchor).
- `python .agents/tasks/scripts/task.py validate` passes.

## Documentation required

The files in `touches`, as in Scope.

## Acceptance criteria

- [ ] `CLAUDE.md` "Ask first" names running `scripts/release.py --yes` or `--push`.
- [ ] `CONTRIBUTING.md` step 6 no longer tells an agent to run the release.
- [ ] `CONTRIBUTING.md` says merge commits run `commit-msg` only and qualifies the `--version` refusal.
- [ ] `--push` requiring `--yes` and changelog exit status 3 are documented wherever the old behavior was.
- [ ] `DEV_TOOLING_SPEC.md` has no stale README step reference; `README.md` mentions the changelog.
- [ ] `.agents/README.md` has the pull/rebase rule.
- [ ] `CLAUDE.md`'s first `##` heading is unchanged.
- [ ] `changelog.d/T-0030.changed.md` exists and `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 on the pushed branch.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `docs/T-0030-correct-the-release-docs-and-add-the-release-to`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0030.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0030.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0030
```
