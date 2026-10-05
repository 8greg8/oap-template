# Plan: cut the verification cost per task

Status: proposed. Owner decisions V1 to V8 are open. No tasks are filed yet.

## Goal

A task gets exactly one independent verification and, in the common case, one full gate run,
without weakening what is checked. Today a task costs 2 to 5 verify agents and 5 to 7 full gate
runs (40 to 60 minutes of gate time), and every fix round adds more.

## Findings (develop at `7dce84f`, 2026-10-05)

### Two verify procedures are stacked

1. `CONTRIBUTING.md` § "Agent verify/resolve workflow", step 2: "**Before any commit is
   written** … a separate, independent agent … runs the full gate", repeated after every resolve.
   It was written for a single agent making a standalone change.
2. `.agents/README.md` § "Verify, resolve, merge": a separate fresh agent verifies the pushed
   branch: the full gate plus acceptance criteria, `touches`, spec, fragment, breaking and
   "Ask first".
3. `CLAUDE.md` § "Verification is not optional" points to (1); § Merge authority points to (2).
   An executor that follows the rules spawns a verifier before each commit, and the orchestrator
   spawns another before the merge. Each finished verifier stays behind as a stale subagent.

### The same tree is gated again and again

Per task, with no failures:

| # | Trigger | Gate |
|---|---|---|
| 1 | per-commit verifier (`CONTRIBUTING.md` step 2), once per commit | full |
| 2 | `.husky/pre-commit` | staged lint, format, typecheck (seconds) |
| 3 | `.husky/pre-push` on the task branch (a new remote branch always runs it) | full |
| 4 | branch verifier (`.agents/README.md` step 7) | full |
| 5 | `scripts/gitflow.sh finish` (`:96`), when used | full |
| 6 | orchestrator after the merge ("reruns `scripts/gate.sh` on `develop`") | full |
| 7 | `.husky/pre-push` on `develop` | full |

When the task branch is up to date with `develop`, runs 3 to 7 gate the same tree. Nothing
records that a tree already passed, so nothing can be skipped.

### The full gate is slow, and one file dominates

`scripts/gate.sh` (ruff, ty, pytest): 551 tests in 505 s (8.5 min). `tests/test_init_project.py`
takes about 350 s of that: its end-to-end cases run real `uv lock`, `uv sync`, `npm ci` and the
generated project's own gate. The other 465 tests take 153 s. `pyproject.toml` has no
`[tool.pytest]` section and no markers; `TEST_CMD` is `uv run pytest`.

## Design

### One independent verification per change (V1, V2, V6)

- The executor runs `scripts/gate.sh` itself while working, as often as it likes. That is not
  self-certification; the gate is deterministic.
- Exactly one independent verifier checks the finished, pushed branch. Its job is judgment:
  acceptance criteria, `touches`, spec-first discipline, fragment and commit types, breaking and
  "Ask first". It does not re-run the full gate when a recorded pass exists for the branch head's
  tree (below); it cites that record. It runs the gate itself only when there is none.
- `CONTRIBUTING.md` § "Agent verify/resolve workflow" is rewritten to this shape for standalone
  changes too: implement, gate, commit freely; one independent verify of the finished branch;
  resolve; merge. No verifier per commit.
- A fix round's verifier checks the previous findings and the diff since the verified commit,
  not the whole task again. Three failed rounds still block the task.

### Record gate passes by tree (V3)

- After a full, clean run on a clean working tree, `scripts/gate.sh` writes a pass record named
  by the tree hash (`git rev-parse HEAD^{tree}`) and a hash of `scripts/config/gate.sh`, under
  `$(git rev-parse --git-common-dir)/gate-pass/`. Worktrees share it; nothing is committed.
- `scripts/gate.sh --if-needed` exits 0 at once when a record for the current tree and config
  exists, and otherwise runs the full gate.
- `.husky/pre-push`, `scripts/gitflow.sh finish` and the orchestrator's post-merge check use
  `--if-needed`. A merge whose tree equals the already-gated branch tree is not gated again; a
  merge that changes the tree is.
- `--staged`, `--fast` and a dirty tree never write a record. A different machine (another cloud
  container) has no record and simply runs the gate.

### Run the slow tests only when they matter (V4, V5)

- The real-install cases in `tests/test_init_project.py` get a `slow` marker, registered in
  `pyproject.toml` `[tool.pytest.ini_options]`.
- `scripts/gate.sh` runs `pytest -m "not slow"` unless the change touches a path the slow tests
  cover (`init_project.py`, `tests/test_init_project.py`, `pyproject.toml`, `package.json`, the
  lock files, `CLAUDE.md`, `README.md`, `changelog.d/README.md`, `CHANGELOG.md`, `src/`), listed
  in `scripts/config/gate.sh` as `SLOW_PATHS`. Then, and with `--all`, it runs everything.
- The pass record notes whether slow tests ran; a slow-path change needs a record that includes
  them.
- A push to `main` (a release) always runs the full suite, slow tests included.

### Subagent and worktree hygiene (V7)

- The orchestrator runs one verifier per task per round, in the foreground, and records its
  result in the report before starting anything else for that task.
- `housekeep.py` reports worktrees and local branches of tasks that are `done` or `abandoned`,
  so leftovers from finished tasks are visible.

### Bookkeeping commits (V8)

Commits that change only `.agents/` records (task status, reports, `BACKLOG.md`, `LESSONS.md`)
need no independent verification and no gate; the hooks already skip them. Plans and task files
written for the owner keep one independent review before they are merged, as now.

## Expected effect

| | Today | After |
|---|---|---|
| Verify agents per task | 2 to 5, plus one per fix round per commit | 1, plus one per fix round |
| Full gate runs per task | 5 to 7 | 1 (2 when the merge changes the tree) |
| One full gate | 8.5 min | about 2.5 min without slow tests; 8.5 min when they apply |
| Gate time per task | 40 to 60 min | about 3 to 10 min |

## Owner decisions

- **V1. One independent verifier per change, at branch level.** Recommended. Alternative: keep
  the per-commit verifier for standalone changes only.
- **V2. The verifier cites a recorded gate pass instead of re-running the gate.** Recommended.
  Alternatives: the verifier always re-runs the full gate (today), or runs only `--fast`.
- **V3. Gate-pass records by tree, used by pre-push, `gitflow.sh finish` and the post-merge
  check.** Recommended.
- **V4. Slow tests run only for `SLOW_PATHS` changes, `--all` and pushes to `main`.**
  Recommended. Alternatives: slow tests only at release, or always (today).
- **V5. Parallel tests (`pytest-xdist`).** Recommended: not now. Many tests create git
  repositories and run subprocesses; measure after V4 and decide then.
- **V6. A fix round's verifier checks the findings and the new diff only.** Recommended.
  Alternative: a full re-verification every round (today).
- **V7. Foreground verifiers and `housekeep.py` leftovers report.** Recommended.
- **V8. `.agents/`-only bookkeeping commits need no verification.** Recommended.

## Approvals this plan needs

- **Ask first:** `CLAUDE.md` § "Verification is not optional" and § Merge authority text;
  `scripts/gate.sh`, `scripts/config/gate.sh`, `scripts/gitflow.sh`; `pyproject.toml`
  `[tool.pytest]`; `.husky/pre-push`.
- **Breaking:** the verification rules (a rule change downstream projects rely on) and the hook
  behavior (pre-push may skip a gate).
- The owner's acceptance of this plan, recorded here, is the written approval the orchestrator
  cites when merging these tasks.

## Tasks (filed after acceptance)

1. **Record gate passes by tree** (feat, breaking). `scripts/gate.sh`, `scripts/config/gate.sh`,
   `.husky/pre-push`, `scripts/gitflow.sh`, `tests/test_gate.py` (new), `tests/test_hooks.py`,
   `tests/test_gitflow.py`, a fragment.
2. **Mark and gate the slow tests** (feat). Depends on 1. `pyproject.toml`,
   `tests/test_init_project.py`, `scripts/gate.sh`, `scripts/config/gate.sh`, `tests/test_gate.py`,
   a fragment.
3. **Report leftover worktrees and branches** (feat). `.agents/tasks/scripts/housekeep.py`, its
   tests, a fragment. Parallel with 1.
4. **Rewrite the verification rules** (docs, breaking). Depends on 1, 2 and 3. `CLAUDE.md`,
   `CONTRIBUTING.md`, `.agents/README.md`, `DEV_TOOLING_SPEC.md`, `scripts/README.md`, a fragment.

## Risks

- **A stale record lets a broken tree through.** The record is keyed by the exact tree and the
  gate config; any file change or config change misses it. Tool versions are pinned in `uv.lock`,
  which is part of the tree.
- **A slow-path list that is too narrow.** A change that breaks generated projects without
  touching a listed path skips the slow tests until the next `--all` run or release. The verifier
  checks the list against the diff, and the release push always runs everything.
- **A forged record.** A record is a local file an agent could create by hand. The verifier
  checks that the record's tree matches the branch head and that the report's gate line names the
  same tree; the rules forbid writing records outside `scripts/gate.sh`.
- **Less independent re-running.** The verifier no longer proves the gate on its own machine when
  a record exists. The record comes from the same deterministic gate, and the pre-push hook still
  enforces it.
