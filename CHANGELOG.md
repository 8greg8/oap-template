# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-07

### Added

- `scripts/changelog.py` with `check`, `preview` and `assemble` for changelog fragments in
  `changelog.d/`, and a `CHANGELOG.md` in Keep a Changelog form.
- `init_project.py` starts a generated project with an empty `CHANGELOG.md` (the Keep a
  Changelog header and an empty `[Unreleased]` section) and no changelog fragments, keeps
  `changelog.d/README.md`, and lists both changes in the dry run. Its checklist says branch
  protection must allow the release push.
- The agent rules in `CLAUDE.md` list creating a release tag by hand (any tag not created by
  `scripts/release.py`) and running `scripts/release.py --yes` or `--yes --push` as two separate
  "Ask first" items. No sentence makes one exempt from the other.
- Gate records. A full `scripts/gate.sh` run that passes on a clean tree writes a record keyed by
  the code and the tool versions, so the same code is not gated twice. The record lives in the git
  common directory and is never committed.
- `scripts/gate.sh --if-needed [<commit>...]` skips the full gate for a commit that has a record
  and runs it otherwise, in a temporary detached worktree when the commit is not checked out.
- `RECORD_PATHS` in `scripts/config/gate.sh` lists the bookkeeping paths (task files, reports,
  backlog, lessons, plans) as git glob pathspecs. `.husky/pre-commit` and `.husky/pre-push` skip a
  change that touches only those paths, and the key of a gate record ignores them.
- `.husky/pre-push` runs `scripts/gate.sh --if-needed` for every pushed commit of `develop` and
  `main`, and `scripts/gate.sh --fast` for any other branch. Tags trigger no gate.
- `scripts/gitflow.sh finish` runs `scripts/gate.sh --if-needed HEAD` after each merge it makes and
  undoes the merge when the gate is red. It runs no gate before the merge.
- Slow tests. The two end-to-end cases of `tests/test_init_project.py` carry a `slow` marker,
  registered in `pyproject.toml`. `scripts/gate.sh` appends `TEST_SKIP_SLOW_ARGS` (`-m "not slow"`)
  to `TEST_CMD` only when every path changed since the base is on `SLOW_SAFE_PATHS`. The list holds
  `RECORD_PATHS`, the changelog fragments and the prose docs `CONTRIBUTING.md`,
  `DEV_TOOLING_SPEC.md`, `PYTHON_CONVENTIONS.md` and `NOTICE.md`. Any other change, an empty change
  set and `--all` run every test.
- The base is the merge base with `origin/develop`, or with `origin/main` on a `hotfix/*` branch,
  and falls back to the local branch when the remote ref is missing.
- `scripts/gate.sh --all` runs every test. A gate record carries `slow=yes` or `slow=no`, and
  `--if-needed` accepts a `slow=no` record only for a change that is safe-list-only and only
  without `--all`.
- `.husky/pre-push` gates `main` with `scripts/gate.sh --if-needed --all` in its own call, so a
  push to `main` always runs the slow tests. `develop` keeps `--if-needed`.
- A fast test greps the safe-listed prose docs for the template names, so a doc that would break
  the end-to-end test is caught without it.
- `housekeep.py worktrees` and `housekeep.py all` report worktrees and local branches of tasks that
  are `done` or `abandoned`, merged or not, including branches that have no worktree. The check
  only reports and removes nothing. It exits 1 on any finding, so a leftover of a finished task
  makes both commands exit 1.
- The report verify line takes the form `passed (commit <hash>; gate <key>; <counts>)`, where
  `<key>` is the gate record key, cited with 12 to 64 lowercase hex characters. `report.py validate`
  rejects a malformed `gate` part and does not require one, so the form without it validates too.
  The report template documents the form.
- Verification rules. A change gets exactly one independent verifier, which checks the finished,
  pushed branch and runs the full gate itself. There is no verifier per commit: the executor
  iterates with `scripts/gate.sh --fast` and targeted tests and commits freely.
- The verifier works in a detached worktree of the orchestrator's checkout. Its full run writes the
  gate record that the post-merge `scripts/gate.sh --if-needed` check, `gitflow.sh finish` and the
  pushes to `develop` and `main` reuse. Only `scripts/gate.sh` writes records.
- A fix round gets a new verifier that checks the earlier findings and the diff since the verified
  commit, runs the full gate (or cites a record for the same code), and rechecks `touches` and "Ask
  first" for the whole branch. The orchestrator runs one verifier per task per round, in the
  foreground. Commits that change only bookkeeping records need no verification and no gate.
- The report's verify line names the record: `passed (commit <hash>; gate <record-key>; <counts>)`.
- The process documents describe the gate records, `--if-needed`, `--all`, the `slow` marker and
  its safe list, the task-branch `--fast` push check, and the `housekeep.py worktrees` findings for
  finished tasks, which make it exit 1.
- The README that `init_project.py` writes advises `scripts/gate.sh --fast` while working. It names the
  full `scripts/gate.sh` as the check the independent verifier and the pushes to `develop` and `main`
  run.
- Task tooling under `.agents/`: task and report files, a generated backlog, and scripts to file,
  validate, start and close tasks.
- A single quality gate, `scripts/gate.sh`, run by the pre-commit and pre-push hooks, and a
  commit-msg hook that enforces Conventional Commits. The gate commands live in
  `scripts/config/gate.sh`, which stays POSIX-sourceable; a test sources it with `sh`.
- Version computation from commit types and git tags in `scripts/next_version.py`.
- Git flow helpers in `scripts/gitflow.sh` for task, hotfix and docs branches and their worktrees.
  `finish` fetches the base branch before it picks `origin/<base>`, warns and uses the local base
  when the fetch fails, and prints the add-a-fragment advice only when the changelog check found a
  problem.
- An init script, `init_project.py`, that turns a copy of the template into a new project.
- A devcontainer, including a variant that hides `src/` for spec-first test authoring.
- Contribution, code of conduct and security policies.
- A changelog fragment check. A push or a `scripts/gitflow.sh finish` that carries a `feat`, `fix`
  or breaking commit needs a fragment in `changelog.d/` and is rejected without one. The pre-push
  hook checks each pushed branch from its merge base with `origin/develop` (`origin/main` for
  `hotfix/*`), and `main` and `develop` from the remote commit to the pushed one. It checks against
  the remote the push goes to, not always `origin`. It reports "changelog check failed (exit N)"
  for any exit status other than a real finding, so a failed check is not mistaken for a missing
  fragment. Tags, deleted refs and `RECORD_PATHS`-only pushes are not checked.
- A strict changelog fragment format. A fragment may hold only bullet lines, indented continuation
  lines directly after a bullet and blank lines, so unchecked text cannot reach `CHANGELOG.md`. A
  fragment with no bullet or with a placeholder bullet is rejected. Fragments are decoded strictly
  as UTF-8 on every path, a non-UTF-8 fragment is reported as a fragment problem, and one leading
  BOM is ignored. `scripts/changelog.py assemble --date` takes only `YYYY-MM-DD`. An internal
  error, a load failure or an unexpected exception, exits 3 with one line. Renaming a fragment
  that exists at the base, or deleting and adding it again, does not count as adding one.
- A release script, `scripts/release.py`, that releases `develop` into `main`. Without `--yes` it
  prints the version, the commits and the changelog section and changes nothing. With `--yes` it
  merges `develop` into `main`, folds the changelog fragments into `CHANGELOG.md`, commits
  `chore(release): vX.Y.Z`, tags that commit and brings `develop` up to `main`. After a hotfix it
  runs on `main` and merges `main` into `develop`. `--push`, which requires `--yes` and does not
  imply it, pushes `main`, `develop` and the tag atomically, and `--version vX.Y.Z` overrides the
  computed version. Without `--yes`, `--push` exits 2 with a usage message and changes nothing. It
  refuses a dirty tree, a branch that differs from `origin`, a branch checked out in another
  worktree, nothing to release, and a repository with no commits (exit status 1, with a clear
  message). When a step fails it prints the stdout and stderr of the failed command, each
  labelled, then the current state and the commands to finish by hand or undo. When bringing
  `develop` up to `main` conflicts on a changelog fragment, the finish commands say to resolve it
  as deleted with `git rm <path>`, because `main` already folded it. A rejected `--push` names both
  likely causes: another push won the race, or a local pre-push hook failed.
- A release is an "Ask first" item in `CLAUDE.md`. An agent runs `scripts/release.py --yes`, with or
  without `--push`, only when the owner asks for that release; a dry run stays free.
- A 0.x versioning rule. While the latest tag is `v0.x`, a breaking change bumps minor instead of
  major, so the first release is `v0.1.0`. From `v1.0.0` on a breaking change bumps major.
- A hotfix release step. `scripts/gitflow.sh hotfix finish` tells you to push `main` and
  `develop`, then run `scripts/release.py --yes` on `main`.
- Release, changelog and hook documentation in `CONTRIBUTING.md`, `DEV_TOOLING_SPEC.md`,
  `scripts/README.md` and `changelog.d/README.md` that matches the code: `--push` requires `--yes`,
  `changelog.py` exit status 3, the fragment content rule, strict UTF-8 and a leading BOM, the
  push's own remote, and merge commits running `commit-msg` only.
