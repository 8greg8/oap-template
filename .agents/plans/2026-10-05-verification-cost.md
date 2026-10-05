# Plan: cut the verification cost per task

Status: proposed. Owner decisions V1 to V9 are open. No tasks are filed yet.

## Goal

A task gets exactly one independent verification, and that verifier's full gate run is the one
full run the task needs in the common case, without weakening what is checked. Today a task costs
2 to 5 verify agents and 5 to 7 full gate runs (40 to 60 minutes of gate time), and every fix
round adds more.

## Findings (develop at `7dce84f`, 2026-10-05)

### Two verify procedures are stacked

1. `CONTRIBUTING.md` § "Agent verify/resolve workflow" opens "Before any commit is written,
   changes go through an iterative, independently-verified check loop"; its step 2 has a separate,
   independent agent run the full gate, repeated after every resolve. It was written for a single
   agent making a standalone change.
2. `.agents/README.md` § "Verify, resolve, merge": a separate fresh agent verifies the pushed
   branch: the full gate plus acceptance criteria, `touches`, spec, fragment, breaking and
   "Ask first".
3. `CLAUDE.md` § "Verification is not optional" points to (1); § Merge authority points to (2).
   An executor that follows the rules spawns a verifier before each commit, and the orchestrator
   spawns another before the merge. Each finished verifier stays behind as a stale subagent.

### The same code is gated again and again

Per task, with no failures:

| # | Trigger | Gate |
|---|---|---|
| 1 | per-commit verifier (`CONTRIBUTING.md` step 2), once per commit | full |
| 2 | `.husky/pre-commit` | staged lint, format, typecheck (seconds) |
| 3 | `.husky/pre-push` on the task branch (a new remote branch always runs it) | full |
| 4 | branch verifier (`.agents/README.md` step 7) | full |
| 5 | `scripts/gitflow.sh finish` (`:96`), when used | full |
| 6 | orchestrator after the merge ("reruns `scripts/gate.sh` on `develop`") | full |
| 7 | `.husky/pre-push` on `develop` (a merge lists its first-parent files) | full |

Runs 3 to 7 mostly gate the same code; the commits in between change only `.agents/` records
(the report, the verify line). Nothing records that code already passed.

### The full gate is slow, and two tests dominate

`scripts/gate.sh` (ruff, ty, pytest): 551 tests in 505 s (8.5 min). Two end-to-end cases in
`tests/test_init_project.py` take about 250 to 300 s: they copy every tracked file into a scratch
project, run `init_project.py --skip-install` (which runs `uv lock` and
`npm install --package-lock-only`), and run the generated project's full gate. The file's other
84 tests take about 40 s; the remaining 465 tests about 153 s. A gate without the two cases takes
about 3.3 min. `pyproject.toml` has no `[tool.pytest]` section; `TEST_CMD` is `uv run pytest`.

## Design

### The verifier's run is the canonical full gate (V1, V2)

- The executor iterates with `scripts/gate.sh --fast` and targeted tests, and may run the full
  gate whenever it wants. Its own runs certify nothing.
- Exactly one independent verifier checks the finished, pushed branch. It always runs the full
  gate itself (never `--if-needed`), which also writes the record below, and does the judgment work: acceptance criteria, `touches`,
  spec-first discipline, fragment and commit types, breaking and "Ask first". This keeps
  `CLAUDE.md`'s rule that the verify step is run by an independent agent.
- The verifier works in a detached worktree of the orchestrator's checkout
  (`git worktree add --detach <path> origin/<branch>`; a plain checkout of the branch is refused
  while the executor's worktree holds it), so its record is in the shared git directory where the
  orchestrator's later steps find it.
- `CONTRIBUTING.md` § "Agent verify/resolve workflow" takes the same shape for standalone changes:
  implement, iterate, commit freely; one independent verify of the finished branch; resolve; merge.
  No verifier per commit.

### Gate records keyed by code, not by bookkeeping (V3)

- After a full, clean run, `scripts/gate.sh` writes a record under
  `$(git rev-parse --git-common-dir)/gate-pass/`. The key hashes:
  - the tree with the bookkeeping records filtered out: the paths in a new `RECORD_PATHS` list in
    `scripts/config/gate.sh` (`.agents/tasks/T-*.md`, `.agents/tasks/reports/`,
    `.agents/tasks/BACKLOG.md`, `.agents/tasks/.counter`, `.agents/LESSONS.md`, `.agents/plans/`).
    Everything else, including `.agents/tasks/scripts/`, `.agents/tasks/templates/` and
    `.agents/README.md`, is code for the key. `.husky/pre-commit` and `.husky/pre-push` switch their
    skip rule to the same `RECORD_PATHS` list, so the hooks and the key agree (today the hooks skip
    every `.agents/` path except `.agents/tasks/scripts/`);
  - `uv --version`, `uv run python -VV`, `node -v` and `git --version`.
  The record also says whether the slow tests ran. A record without slow tests does not satisfy a
  check that needs them: always for `main`, and for any other commit when the change since the base
  is not safe-list-only (below).
- "Clean" means `git status --porcelain --untracked-files=all` is empty before and after the run.
  `--staged`, `--fast` and a dirty run never write a record.
- `scripts/gate.sh --if-needed [<commit>...]` checks a record for each named commit (default
  `HEAD`) and exits 0 only if all have a sufficient one. For each commit without one it runs the
  full gate: on the working tree when that commit is checked out and the tree is clean, otherwise
  in a temporary detached worktree of that commit, which it removes afterwards. It never refuses a
  push for want of a checkout. (This is what lets `release.py --push` after a hotfix pass: the
  release commit on `main` is checked out and the back-merge on `develop` is gated in a temporary
  worktree.)
- Users: `.husky/pre-push` for `develop` and `main` passes each pushed non-deleted `local_sha`;
  `gitflow.sh finish` and the orchestrator's post-merge check use `--if-needed` on the merge. A
  merge whose filtered tree equals the verified branch tree is not gated again.
- Records written inside scratch repositories by tests and by `init_project.py` stay in those
  repositories and are harmless.

### Pre-push on task branches (V4)

A push of any branch other than `develop` and `main` runs `gate.sh --fast` (lint, format,
typecheck) instead of the full gate; the verifier's full run follows before any merge. Pushes to
`develop` and `main` keep requiring a record or a full run.

### Slow tests run unless the change is provably safe (V5, V6)

- The two end-to-end cases get a `slow` marker, registered in `pyproject.toml`
  `[tool.pytest.ini_options]`.
- `scripts/gate.sh` skips them (`-m "not slow"`) only when every path changed since the base is on
  a safe list in `scripts/config/gate.sh` (`SLOW_SAFE_PATHS`): `RECORD_PATHS`, `changelog.d/`
  fragments (not its `README.md`), and the prose docs `CONTRIBUTING.md`, `DEV_TOOLING_SPEC.md`,
  `PYTHON_CONVENTIONS.md` and `NOTICE.md`. Any other change runs them, and so does `--all`.
- The end-to-end test fails if any generated file contains a template name, and `init_project.py`
  copies those four docs unchanged. A new fast test (not `slow`) greps exactly the safe-listed docs
  for the template-name strings, so the one way they can break the end-to-end test is caught
  without it.
- The base is the merge base with `origin/$DEVELOP_BRANCH` (`origin/$MAIN_BRANCH` for `hotfix/*`),
  falling back to the local branch when the remote ref is missing; pre-push and the post-merge
  check use the same definition.
- A push to `main` (a release) always runs everything.

### Fix rounds (V7)

A fix round's verifier checks the previous findings and the diff since the verified commit, runs
the full gate (or cites a record) for the new head, and rechecks `touches` and "Ask first" for the
whole branch, since a fix can break a criterion that already passed.

### Subagent and worktree hygiene (V8)

- The orchestrator runs one verifier per task per round, in the foreground, and records its result
  before starting anything else for that task.
- `housekeep.py worktrees` (which already flags merged worktrees, `housekeep.py:396`) also reports
  worktrees and local branches of `done` or `abandoned` tasks, including unmerged ones and branches
  with no worktree. Its exit status rules stay as documented, or the change is called out.

### Bookkeeping commits (V9)

Commits that change only `RECORD_PATHS` need no independent verification and no gate; the hooks
skip them. Plans and task files written for the owner keep one independent review
before they are merged.

### The verify line

The report's verify line becomes
`passed (commit <hash>; gate <record-key>; <counts>)`, naming the record the verifier wrote.
`.agents/tasks/templates/report.md` documents it and `report.py validate` accepts it.

## Expected effect

| | Today | After |
|---|---|---|
| Verify agents per task | 2 to 5, plus one per commit per fix round | 1, plus one per fix round |
| Full gate runs per task | 5 to 7 | 1; 2 when the merge changes the code, the usual case in a parallel batch |
| One full gate | 8.5 min | 8.5 min when slow tests apply; about 3.3 min for safe-list-only changes |
| Gate time per task | 40 to 60 min | about 8.5 to 17 min for code tasks; 3 to 7 min for docs and plans |

## Owner decisions

- **V1. One independent verifier per change, at branch level; no verifier per commit.**
  Recommended.
- **V2. The verifier's own full gate run is the canonical one; later steps reuse its record.**
  Recommended. Alternative: every step re-runs the gate (today).
- **V3. Records keyed by the code tree without `.agents/` records, plus tool versions.**
  Recommended.
- **V4. Pre-push on task branches runs `--fast`; `develop` and `main` need a record or a full
  run.** Recommended. Alternative: full gate on every push (today).
- **V5. Slow tests skipped only for safe-list-only changes; always on `main` and with `--all`.**
  Recommended. Alternative: always run them (today).
- **V6. Parallel tests (`pytest-xdist`).** Recommended: not now; measure after V5.
- **V7. Fix rounds: findings, new diff, full gate or record, whole-branch `touches` and
  "Ask first".** Recommended.
- **V8. Foreground verifiers and a `housekeep.py` leftovers report.** Recommended.
- **V9. `.agents/`-only bookkeeping commits need no verification.** Recommended.

## Approvals this plan needs

- **Ask first:** `CLAUDE.md` § "Verification is not optional" and § Merge authority text;
  `scripts/gate.sh`, `scripts/config/gate.sh`, `scripts/gitflow.sh`; `pyproject.toml`
  `[tool.pytest]`.
- **Breaking:** the verification rules; the pre-push behavior (task 1: records; task 2: slow-test
  skipping; both change what the hook checks by default); the report verify-line format.
- The owner's acceptance of this plan, recorded here, is the written approval the orchestrator
  cites when merging these tasks.

## Tasks (filed after acceptance)

1. **Gate records and `--if-needed`** (feat, breaking). `scripts/gate.sh`,
   `scripts/config/gate.sh`, `.husky/pre-push`, `.husky/pre-commit`, `scripts/gitflow.sh`,
   `tests/test_release.py` (a hotfix `release.py --push` passes the new hook),
   `tests/test_gate.py` (new),
   `tests/test_hooks.py`, `tests/test_gitflow.py`, `scripts/README.md`, `DEV_TOOLING_SPEC.md`, a
   fragment.
2. **Slow marker and safe-list skipping** (feat, breaking). Depends on 1. `pyproject.toml`,
   `tests/test_init_project.py` (the marker and the fast template-name test for safe-listed docs), `scripts/gate.sh`, `scripts/config/gate.sh`, `.husky/pre-push`
   (`main` always runs everything), `tests/test_gate.py`, `tests/test_hooks.py`,
   `scripts/README.md`, `DEV_TOOLING_SPEC.md`, a fragment.
3. **Process tooling: leftovers report and verify line** (feat, breaking). Parallel with 1.
   `.agents/tasks/scripts/housekeep.py`, `.agents/tasks/scripts/report.py`,
   `.agents/tasks/templates/report.md`, `tests/test_task_scripts.py`,
   `tests/test_report_scripts.py`, a fragment.
4. **Rewrite the verification rules** (docs, breaking). Depends on 1, 2 and 3. `CLAUDE.md`,
   `CONTRIBUTING.md`, `.agents/README.md`, `.agents/tasks/templates/task.md`,
   `PYTHON_CONVENTIONS.md`, `README.md`, `DEV_TOOLING_SPEC.md`, `scripts/README.md`, a fragment.

## Risks

- **A stale record lets a broken tree through.** The key covers the code tree and the tool
  versions; any code, lock-file or tool change misses it.
- **A forged or self-written record.** A record is a local file, and any clean full run writes
  one, the executor's included. That is why the verifier never relies on a record: it always runs
  the full gate itself. Records only let the later mechanical steps (post-merge check, `develop`
  and `main` pushes, `gitflow.sh finish`) skip re-running the same code. The rules forbid writing
  records outside `scripts/gate.sh`.
- **A safe list that is too wide.** Its docs can break the end-to-end test only through a template
  name, which the fast grep test catches. Adding to the list is a change to
  `scripts/config/gate.sh` and needs a human.
- **Task-branch pushes are no longer fully gated.** A broken branch is caught by the verifier's
  full run before any merge, and `develop` and `main` stay fully protected.
