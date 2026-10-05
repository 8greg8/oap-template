---
id: T-0028
title: Harden the changelog check and the push hook
status: open
type: fix
priority: high
depends_on: [T-0027]
touches: [scripts/changelog.py, .husky/pre-push, scripts/gitflow.sh, scripts/config/gate.sh, tests/test_changelog.py, tests/test_hooks.py, tests/test_gitflow.py, changelog.d/T-0028.fixed.md]
created: 2026-10-05
report: reports/T-0028.md
---

# T-0028 — Harden the changelog check and the push hook

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

`changelog.py` rejects every fragment that would put unchecked or undecodable text into
`CHANGELOG.md`, reports its own failures distinctly from a missing fragment, and the push hook
and `gitflow.sh finish` check against the right, fresh base.

## Context / current verified state

- Plan: `.agents/plans/2026-10-05-post-batch-review-fixes.md`, accepted by the owner on 2026-10-05 (all tasks, decisions A and B). Its § Approvals
  is the owner's written approval for this task's "Ask first" and breaking items; cite it in the
  report. Where this file and the plan differ, stop and report.
- Re-check against `develop` before starting (`git pull --ff-only origin develop`) and report any
  discrepancy.
- `scripts/changelog.py`: `bullet_texts` checks only bullet lines but `build_section` folds the
  whole fragment (`:239-264`, `:314`); `check` reads blobs with `errors="replace"` while
  `read_working_fragments` decodes strictly (`:161-162`, `:309`); a leading BOM makes a valid
  fragment fail as "no bullet line" (`:71`, `:201`); `--date` uses `date.fromisoformat`, which
  accepts non-`YYYY-MM-DD` forms (`:384`); unexpected errors exit 1, which the hook reports as a
  missing fragment (`:110-126`, `:140`, `:686-695`, `.husky/pre-push:77-81`); `--no-renames` with
  `--diff-filter=A` counts a `git mv` of an existing fragment as added (`:506-523`).
- `.husky/pre-push:63,67` always uses `origin/<branch>` even when pushing to another remote
  (`$1`). `scripts/gitflow.sh:76-83` prefers `origin/$base` without fetching it.
- `.husky/pre-push:26` sources `scripts/config/gate.sh` under POSIX `sh`; that file has a bash
  shebang and invites adopters to edit it.
- `tests/test_hooks.py:392` (`test_tag_ref_is_not_checked`) and `:356`
  (`test_hotfix_branch_is_ranged_from_origin_main`) pass with the behavior they test removed.

## Scope

- Fragment content: a fragment may contain only bullet lines (`- ` or `* `), indented
  continuation lines and blank lines; anything else fails `check` and makes `assemble` refuse. An
  indented line is a continuation only directly after a bullet or another continuation line; an
  indented line after a blank line, or before the first bullet, is rejected. Move the
  intro-line case at `tests/test_changelog.py:390` from the valid to the rejected cases. Update the
  module docstring (`:32-40`) and `main`'s docstring (`:684`) for the content rule, strict UTF-8
  and exit 3.
- Decode fragments strictly as UTF-8 in every path; a non-UTF-8 fragment is a fragment problem
  (exit 1 with a clear message), never a traceback. Strip one leading BOM before parsing.
- `--date`: `re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value)`, then `date.fromisoformat`;
  otherwise exit 2 (unchanged).
- Exit codes: 0 pass, 1 missing or invalid fragment, 2 usage error or unlistable range (as
  today), 3 internal error (import or load failure, unexpected exception) with a one-line
  message. The hook: 0 passes; 1 prints the existing missing/invalid-fragment message and
  rejects; 2 skips; any other code (3, 127, a signal) prints
  "pre-push: changelog check failed (exit N) for <remote_ref>" and rejects, without the
  missing-fragment text.
- A fragment counts as added only if a non-merge commit in the range adds it with rename detection
  on (`git log --no-merges -M --diff-filter=A`, replacing `--no-renames`) and its path does not
  exist at `<base>`. A rename of an existing fragment (status R) and a delete-and-re-add of the
  same path do not satisfy `check`. A fragment added and later deleted inside the range (folded by
  a release) still counts.
- `.husky/pre-push`: use `remote=${1:-origin}` for `refs/remotes/$remote/develop` and
  `.../main`. When that ref is missing (including `$1` being a URL), skip the check with the
  existing message. Update the hook's header comment (`.husky/pre-push:12-22`).
- `scripts/gitflow.sh finish`: run `git fetch origin "$base"` (the remote `start()` already uses,
  `scripts/gitflow.sh:46`) before choosing `origin/$base`; on fetch failure warn and use the local
  `$base`. Print the add-a-fragment advice only for exit 1, and "changelog check failed (exit N)"
  otherwise.
- `scripts/config/gate.sh`: a comment that the file must stay POSIX-sourceable (plain
  assignments); a test sources it with `sh`.
- Tests: fix the two tests above so they fail when the behavior is removed; add tests for every
  item in this list.
- `changelog.d/T-0028.fixed.md`: this task's entry. The behavior commit is `fix(changelog)!:` with
  the footer: "BREAKING CHANGE: changelog.py exits 3 on an internal error (load failure or
  unexpected exception) instead of 1; fragments may contain only bullet, indented continuation
  and blank lines; --date accepts only YYYY-MM-DD."
- Hook tests: `_run_pre_push` (`tests/test_hooks.py:110-125`) passes `origin <url>` as the hook's
  arguments; add a test that pushes to a second remote name. Rework
  `test_finish_falls_back_to_local_base_without_origin_ref` (`tests/test_gitflow.py:236-245`) so
  the fetch fails (`git remote set-url origin <missing path>` after start) and assert the
  warning. Add a test that release-folded fragments in a `main` push range still pass.
- The task's fragment holds only bullet and indented continuation lines and no placeholder
  words, so it passes T-0028's content rule whichever task merges first.
- The report must not contain the upper-case placeholder word that `_schema.py:128` rejects;
  refer to those fixtures by test name only.

## Non-goals

- Do not change `scripts/release.py`, `scripts/next_version.py` or `init_project.py`.
- Do not change the gate commands or `STAGED_GLOB` in `scripts/config/gate.sh`; add the comment only.
- Do not change documentation files (T-0030).
- No new or edited tracked file contains `proj_template`, `proj-template`, `oap-template`, `8greg8` or the owner's email.

## Files to inspect

- `.agents/plans/2026-10-05-post-batch-review-fixes.md`
- Every file in `touches`; `.husky/commit-msg` (interpreter), `.agents/tasks/T-0022-*.md` and
  `T-0023-*.md` (the original contracts)

## Required behavior

Each case in Scope behaves as stated, and all existing behavior the T-0022 and T-0023 task files
specify is unchanged except the new exit status 3 and the stricter fragment content.

## Tests required

- `uv run pytest tests/test_changelog.py tests/test_hooks.py tests/test_gitflow.py -v` and
  `scripts/gate.sh`. A sh-sourcing test for `scripts/config/gate.sh`.
- Each new or fixed test is shown to fail with the behavior removed; record how in the report.

## Documentation required

None in this task; T-0030 documents exit status 3 and the content rule.

## Acceptance criteria

- [ ] A fragment with a non-bullet, non-continuation, non-blank line fails `check` and `assemble`.
- [ ] A non-UTF-8 fragment fails `check` and `assemble` with a clear message and no traceback.
- [ ] A fragment with a leading BOM is parsed normally.
- [ ] `--date` rejects anything but `YYYY-MM-DD`.
- [ ] Internal errors exit 3 and the hook reports "changelog check failed" for them.
- [ ] Renaming an existing fragment does not satisfy `check`.
- [ ] The hook uses the push's remote; `gitflow.sh finish` fetches the base first.
- [ ] `scripts/config/gate.sh` carries the POSIX comment and a test sources it with `sh`.
- [ ] `test_tag_ref_is_not_checked` and `test_hotfix_branch_is_ranged_from_origin_main` fail with their behavior removed.
- [ ] `changelog.d/T-0028.fixed.md` exists and `python3 scripts/changelog.py check $(git merge-base origin/develop HEAD) HEAD` exits 0 on the pushed branch.
- [ ] `uv run pytest tests/test_changelog.py tests/test_hooks.py tests/test_gitflow.py -v` passes.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `fix/T-0028-harden-the-changelog-check-and-the-push-hook`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0028.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0028.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0028
```
