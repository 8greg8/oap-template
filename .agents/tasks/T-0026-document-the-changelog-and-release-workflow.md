---
id: T-0026
title: Document the changelog and release workflow
status: done
type: docs
priority: medium
depends_on: [T-0024, T-0025]
touches: [CONTRIBUTING.md, CLAUDE.md, PYTHON_CONVENTIONS.md, DEV_TOOLING_SPEC.md, scripts/README.md, .agents/README.md, .agents/tasks/templates/task.md]
created: 2026-10-04
report: reports/T-0026.md
---

# T-0026 — Document the changelog and release workflow

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

The repository's process documents describe the changelog fragments, the push check, the release
flow, the 0.x rule and the agent rules exactly as T-0022 to T-0025 implemented them.

## Context / current verified state

- Plan: `.agents/plans/2026-10-04-changelog-and-versioning.md`, accepted by the owner on 2026-10-04 (D1 to D8). Its § Design is the source of
  truth for behavior; where this file and the plan differ, stop and report.
- The plan's § Approvals records the owner's written approval for the "Ask first" and
  breaking-change items this task touches; the orchestrator cites it at merge.
- Re-check against `develop` before starting and report any discrepancy.
- Depends on T-0024 and T-0025. Read the merged code, not only the plan; where they differ,
  document the code and report the difference.
- `DEV_TOOLING_SPEC.md` lists "No changelog generation" as a non-goal (line 48).
  `CONTRIBUTING.md` § Versioning (line 121) and the branching model (lines 12-22) predate the
  new flow. `PYTHON_CONVENTIONS.md` lines 56-57 say to publish with `git tag ... && git push --tags`.

## Scope

- Each item in the plan's § Agent rules: `CONTRIBUTING.md` (§ Versioning with the 0.x rule and
  `release.py --version`, branching model for `main` and `develop`, branch protection note),
  `PYTHON_CONVENTIONS.md`, `CLAUDE.md` (fragment rule for tasks; releases stay human; § Merge
  authority unchanged), `.agents/README.md` (verifier checks the fragment),
  `.agents/tasks/templates/task.md` (one guidance line; schema unchanged).
- `DEV_TOOLING_SPEC.md`: replace the changelog non-goal and describe `changelog.py`, the pre-push
  check and the release flow.
- `scripts/README.md`: commands and hook table.
- No edit adds `proj_template`, `proj-template`, `oap-template`, `8greg8` or the owner's email. Do not name the source project of the practice.
- Also update the sections that still describe the old flow: `CONTRIBUTING.md` § Commits table
  (a breaking change's version impact under the 0.x rule), § Agent
  verify/resolve workflow step 6 hotfix bullet, the hooks bullets ("pre-push runs the full gate",
  "release.py ... not wired into any hook") and "Every merge into `main` is tagged";
  `DEV_TOOLING_SPEC.md` § Version computation, § Release tagging, the hook description, the file
  tree and the hotfix line.
- Keep `## Working unit: the task` as the first `##` heading of `CLAUDE.md`
  (`init_project.py`'s `PROJECT_SECTION_ANCHOR` and its test depend on it).

## Non-goals

- Do not change any script, hook, test or `init_project.py`.
- Do not change the task or report schema or `task.py validate`.
- Do not change § Merge authority or the "Ask first" list beyond what the plan states.
- No fragment: this is a `docs` task.

## Files to inspect

- `.agents/plans/2026-10-04-changelog-and-versioning.md`
- The merged `scripts/changelog.py`, `scripts/release.py`, `scripts/next_version.py`,
  `.husky/pre-push`, `scripts/gitflow.sh`, `init_project.py`
- Every file in `touches`

## Required behavior

A contributor or agent following only the documents adds a correct fragment, passes the push
check, and can release and hotfix as the code does.

## Tests required

- `scripts/gate.sh` passes.
- `python .agents/tasks/scripts/task.py validate` passes for every task.

## Documentation required

The files in `touches`, as in Scope.

## Acceptance criteria

- [ ] Every item in the plan's § Agent rules is documented.
- [ ] `DEV_TOOLING_SPEC.md` no longer lists changelog generation as a non-goal.
- [ ] `PYTHON_CONVENTIONS.md` points to `release.py` for publishing.
- [ ] The 0.x rule and `release.py --version` are documented in `CONTRIBUTING.md`.
- [ ] Every statement matches the merged code; differences are reported.
- [ ] The task schema and `task.py validate` are unchanged.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `docs/T-0026-document-the-changelog-and-release-workflow`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0026.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0026.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0026
```
