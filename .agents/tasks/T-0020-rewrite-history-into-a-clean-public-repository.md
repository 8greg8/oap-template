---
id: T-0020
title: Rewrite history into a clean public repository copy
status: open
type: chore
priority: high
depends_on: [T-0015, T-0016, T-0017, T-0018, T-0019]
touches: [.agents/tasks, .agents/plans, .agents/LESSONS.md]
created: 2026-10-03
report: reports/T-0020.md
---

# T-0020 — Rewrite history into a clean public repository copy

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

`8greg8/oap-template` is a new private repository whose `main` and `develop` carry the full
history with the owner's commits under the private address, no private literal in any content
or message, and no `Claude-Session:` trailer. The cited commit hashes in task and report files
point to the new commits. The old repository survives untouched as `oap-template-archive`.

## Context / current verified state

- Plan: `.agents/plans/2026-10-03-public-release-cleanup.md`, accepted by the owner on
  2026-10-03. The plan's § Owner decisions is the owner's written approval for this rewrite (an
  "Ask first" item); cite it in the report. Its § Replacements and § Step 2 are the source of
  truth. Where this file and the plan differ, stop and report.
- Depends on T-0015 to T-0019. T-0019 makes the tree free of the literals, so the rewrite must
  leave the `develop` tree unchanged.
- The literals (P1, L2, L3, L3u, L3s, L3V, L3t) are defined in the plan and T-0019 without quoting them. After T-0019
  they exist only in history. Read them from `develop` before T-0019's merge commit
  (for example `git show <merge>^1:.agents/LESSONS.md`).
- The owner's work address is the committer address on 51 commits (`git log --format='%ae'`).
  The owner gives the private address at dispatch. It goes in the mailmap only, never in a
  tracked file.
- About 65 commit messages end with a `Claude-Session:` line; the number grows with each session commit.
- About 37 hashes of this repository's commits are cited in task, report and plan files under `.agents/`.
- A dry run of the plan's command on a mirror (2026-10-03) left no literal, no work email and no
  trailer. Tools: `uv tool run git-filter-repo`; gitleaks 8.21.2 from its GitHub release.
- Re-check against `develop` before starting and report any discrepancy.

## Scope

- Preconditions, checked and recorded in the report before anything else: T-0015 to T-0019 are
  `done`; no unmerged task branch exists on the remote; the owner has renamed this repository to
  `oap-template-archive` and created an empty private `8greg8/oap-template`. If any fails, set
  the task `blocked` and stop.
- In a scratch directory outside any checkout: mirror-clone `oap-template-archive` from GitHub
  and confirm `git rev-parse --is-shallow-repository` prints `false`, write
  `mailmap` and `replace.txt` next to the mirror (not inside it), run the plan's § Step 2
  command, and run its four checks.
- Push the rewritten `main` and `develop` to the new `8greg8/oap-template`. Push no other ref and
  no tags.
- In the new repository, on this task's branch: replace each cited old hash in
  tracked files with its new hash, from `filter-repo/commit-map`, keeping the cited length.
  Editing other tasks' files, reports and plans is allowed for this mapping only. This overrides
  the Workflow rule against editing another task's file. Then
  write the report, commit and push the branch.
- Re-run the gitleaks scan and the literal checks against a fresh clone of the new repository.

## Non-goals

- Do not push to, force-push, rename, delete or change settings on `oap-template-archive`.
- Do not change repository visibility, the default branch or the template flag. That is the
  owner's step 3.
- Do not push merged task branches or tags to the new repository.
- Do not edit file content during the rewrite beyond the plan's replacements. The tree check must
  stay empty.
- Do not commit `mailmap`, `replace.txt`, the private address, the work address or any literal.
- Do not change `scripts/`, `.husky/`, `CLAUDE.md`, `pyproject.toml` or any lock file.
- Do not merge the hash-update branch. The orchestrator merges after an independent verify.

## Files to inspect

- `.agents/plans/2026-10-03-public-release-cleanup.md`
- The T-0019 report and its merge commit
- Files under `.agents/` that cite commit hashes (`git grep -nE '\b[0-9a-f]{7,40}\b' -- .agents`)

## Required behavior

The new repository's `develop` tree equals the archive's `develop` tree, apart from the
hash-update commit. Every author and committer address is the private address or
`noreply@anthropic.com`. No content or message in any pushed commit contains a literal or the work-email
domain, and no message has a `Claude-Session:` line.

## Tests required

- The four checks from the plan's § Step 2, run on the rewritten mirror before pushing, each
  recorded as passed or failed.
- The same checks on a fresh clone of the new repository after pushing.
- After the hash update: every hash cited under `.agents/` resolves to a commit in the new
  repository (`git cat-file -e <hash>^{commit}`), apart from hashes of other repositories already
  cited as such.
- `scripts/gate.sh` passes on the hash-update branch.

## Documentation required

None needed. The plan already describes the result.

## Acceptance criteria

- [ ] Preconditions are recorded in the report; the task is blocked if any failed.
- [ ] `git diff <archive develop> <rewritten develop>` was empty before the hash-update commit.
- [ ] Author and committer addresses are only the private address and `noreply@anthropic.com`.
- [ ] No pushed commit's content or message contains P1, L2, L3, L3u or L3t, L3s or L3V as a whole word, or the work-email domain.
- [ ] No pushed commit message has a `Claude-Session:` line.
- [ ] gitleaks reports no leaks on a fresh clone of the new repository.
- [ ] Only `main`, `develop` and this task's branch exist on the new repository.
- [ ] The rewrite ran on a full (not shallow) mirror.
- [ ] Every cited hash under `.agents/` resolves in the new repository.
- [ ] `oap-template-archive` is unchanged.
- [ ] No tracked file or the report contains the private address, the work address or a literal.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff of the hash-update branch stays within `touches` plus the report.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `chore/T-0020-rewrite-history-into-a-clean-public-repository`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0020.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0020.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0020
```
