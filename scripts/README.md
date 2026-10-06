# scripts/

Deterministic pipelines for the lint/typecheck/test gate, commit validation, SemVer versioning,
the changelog and release, and Gitflow branch operations. Full design: [`../DEV_TOOLING_SPEC.md`](../DEV_TOOLING_SPEC.md).

## Copying this into another repo

This folder moves together with `../.husky/` and `../package.json` — copy all three. To use the
changelog and release flow, also copy `../CHANGELOG.md` (reset to the empty header) and
`../changelog.d/README.md`:

```bash
cp -r scripts .husky package.json /path/to/target-repo/
cd /path/to/target-repo
```

Then adapt the one project-specific file, `scripts/config/gate.sh`, to that repo's actual
lint/format/typecheck/test commands and branch names. Everything else works unmodified.

Install the hooks:

```bash
npm install
npm run prepare      # husky sets core.hooksPath to .husky/_
chmod +x .husky/* scripts/*.sh scripts/*.py
```

Verify it landed correctly (this template's `.agents/tasks/scripts/housekeep.py setup` checks
this automatically if that tooling is also present):

```bash
git config --get core.hooksPath      # should print .husky/_ (Husky 9)
ls -l .husky                          # hook files should be executable
```

## Commands

```bash
scripts/gate.sh              # run all 4 verify gates (lint, format check, typecheck, test); the slow
                             # tests are skipped when every changed path is on SLOW_SAFE_PATHS
scripts/gate.sh --all        # run every test, the slow ones included
scripts/gate.sh --fast       # skip tests, for a quick iteration loop (not a substitute for the full gate)
scripts/gate.sh --staged     # lint/format/typecheck only staged files matching STAGED_GLOB; no tests
scripts/gate.sh --if-needed [<commit>...]   # skip the full gate for a commit that already has a gate
                             # record, run it otherwise (default HEAD); exit 0 only if all pass
scripts/gate.sh --if-needed --all [<commit>...]   # the same, but a record of a run without the
                             # slow tests does not count, and the gate that runs includes them
scripts/autofix.sh           # apply lint autofix + formatting, then re-run scripts/gate.sh
scripts/autofix.sh --staged  # same, but only on staged files matching STAGED_GLOB

scripts/commit_lint.py <msg-file>    # validate a commit message (used by .husky/commit-msg)
scripts/next_version.py              # print the next SemVer version from commits since last tag
                                     # (0.x rule: while the major is 0, a breaking change bumps minor)

scripts/changelog.py check <base> <tip>       # fail if a feat/fix/breaking commit in the range adds
                                              # no changelog.d/ fragment, or a fragment is invalid
                                              # (exit 1; 2 usage or git error; 3 internal error)
scripts/changelog.py preview [vX.Y.Z]         # print the section a release would write
scripts/changelog.py assemble vX.Y.Z [--date YYYY-MM-DD]   # fold fragments into CHANGELOG.md, delete them

scripts/release.py                   # dry run: version, commits, changelog section; changes nothing
scripts/release.py --yes             # merge develop into main, changelog, tag, update develop; local
scripts/release.py --yes --push      # same, then git push --atomic origin main develop vX.Y.Z
                                     # (--push without --yes is a usage error, exit 2)
scripts/release.py --yes --version v1.0.0   # override the version (canonical vX.Y.Z, SemVer-higher)
                                     # --yes and --push are "Ask first" items in CLAUDE.md

scripts/gitflow.sh feature start <topic>    # worktree + branch from develop
scripts/gitflow.sh feature finish <topic>   # changelog check, merge to develop, gate --if-needed HEAD (undo the
                                            # merge on red), clean up worktree
scripts/gitflow.sh bugfix  start|finish <topic>
scripts/gitflow.sh hotfix  start|finish <topic>   # from/into main, with back-merge to develop;
                                                  # then push both and run release.py --yes on main
scripts/gitflow.sh docs|chore|fix start|finish <T-NNNN-slug>   # task branches, from/into develop
```

## What each hook does

| Hook | Runs |
|---|---|
| `pre-commit` | `autofix.sh --staged`, re-stages the files that were staged, then `gate.sh --staged` (no tests). Skipped when only `RECORD_PATHS` paths are staged |
| `commit-msg` | `commit_lint.py` against the message being committed (lines <= 100 chars) |
| `pre-push` | `changelog.py check` for each pushed branch, then the gate: one `gate.sh --if-needed --all <sha>...` call for `main` (always every test), one `gate.sh --if-needed <sha>...` call for `develop`, one `gate.sh --fast` call when the push has any other branch ref, no gate for tags. All are skipped when every pushed commit changes only `RECORD_PATHS` paths |

`RECORD_PATHS` in `config/gate.sh` lists the bookkeeping paths (task files, reports, `BACKLOG.md`, the
task counter, `LESSONS.md` and plans) as one space-separated string of git glob pathspecs. Both hooks
skip a change that touches only those, and `gate.sh` leaves them out of the key. All three exclude
each entry as a `:(exclude,glob)<entry>` pathspec. Task tooling under `.agents/tasks/scripts/`, the
templates and the process docs are code, never skipped. A new remote branch, or a range git cannot
list, never takes the skip.

### Slow tests

Tests marked `slow` (registered in `pyproject.toml` under `[tool.pytest.ini_options]`) are the
end-to-end cases of `tests/test_init_project.py`, about 250 to 300 s of a gate. `gate.sh` appends
`TEST_SKIP_SLOW_ARGS` (`-m "not slow"`) to `TEST_CMD` only when every path changed since the base
is on `SLOW_SAFE_PATHS` in `config/gate.sh`. Any other change, an empty change set, `--all` and a
push to `main` run them.

- `SLOW_SAFE_PATHS` uses the `RECORD_PATHS` pathspec syntax. It holds `RECORD_PATHS`, the changelog
  fragments `changelog.d/*.*.md` (the README is not one), and the prose docs `CONTRIBUTING.md`,
  `DEV_TOOLING_SPEC.md`, `PYTHON_CONVENTIONS.md` and `NOTICE.md`. A fast test greps those four docs
  for the template names, the one way they can break an end-to-end test. Adding a path to the list
  needs a human.
- The changed paths are `git diff --name-only --no-renames <base>` plus the untracked files for a
  run on the working tree, and `git diff --name-only --no-renames <base> <commit>` for a named
  commit. A rename counts both paths. No base found, or no change, runs the slow tests.
- The base is the merge base with `origin/develop`, or with `origin/main` when
  `git symbolic-ref -q --short HEAD` names a `hotfix/` branch (a detached HEAD uses `develop`). When
  the remote ref is missing the local branch is used. The names come from `DEVELOP_BRANCH` and
  `MAIN_BRANCH`.
- A skipped run prints `slow tests: skipped` and writes `slow=no` in its record.
  `--if-needed` accepts a `slow=no` record only for a commit whose change since the base is
  safe-list-only and only without `--all`; for any other commit it runs the gate with `--all`. A
  `slow=yes` record satisfies every check.

### Gate records

A full `gate.sh` run that passes on a tree that is clean before and after (`git status
--porcelain --untracked-files=all` empty) writes the file
`$(git rev-parse --git-common-dir)/gate-pass/<key>` and prints `gate record <key> (slow tests: yes)`
before `gate clean`. The file holds `key=`, `commit=`, `slow=yes|no` and `date=` lines. The key is a
hash of the commit's tree listing without the `RECORD_PATHS` entries, followed by one line each from
`uv --version`, `uv run python -VV`, `git --version` and `node -v`. A change to a record path keeps
the key; a change to any other tracked file or to a tool version changes it. `--fast`, `--staged`, a
failed run and a dirty run never write a record, and a dirty run says why. Only `gate.sh` writes
records; never create, copy or edit one by hand. Records are local files, never committed, and
every worktree of the repository shares them.

`gate.sh --if-needed [<commit>...]` looks for a record per commit (default `HEAD`) and skips the full
gate for each commit that has a sufficient one (see Slow tests). For a commit without one it runs the commit's own full gate
on the working tree when that commit is checked out and the tree is clean, and otherwise in a
temporary detached worktree of that commit, removed afterwards. It never refuses for want of a
checkout; it unsets the git environment variables a hook may have set and removes the worktree on
exit. An independent verifier does not rely on a record: it runs the plain `gate.sh` and so
writes the record that the later steps reuse. `release.py --yes --push` after a hotfix passes the
hook, which makes two calls: the release commit on the checked-out `main` is gated on the checkout
with `--all`, and the back-merge on `develop` in a temporary worktree. `gitflow.sh finish` runs `gate.sh --if-needed HEAD` after each
merge it makes and undoes the merge with `git reset --merge ORIG_HEAD` when the gate is red.

The fragment check in `pre-push` takes its range from the remote ref being updated: for `main` and
`develop`, `<remote sha>..<local sha>` (a first push of either is not checked); for `hotfix/*`, from
the merge base with `<remote>/main`; for any other branch, from the merge base with
`<remote>/develop`. `<remote>` is the remote git passes to the hook (`origin` when run by hand).
When git passes a URL there is no tracking ref, so the check is skipped for those ranges. Deleted
refs, tags and other non-branch refs are skipped. A range it cannot list (`changelog.py` exits 2, no
merge base, no tracking ref) skips the check for that ref with a message and the gate still runs.

`changelog.py` exit status 1 (a missing or invalid fragment) rejects the push with that explanation,
before the gate starts. Any other status, such as 3 for an internal error or 127 for a missing
`python3`, rejects it with `pre-push: changelog check failed (exit N) for <remote_ref>` and makes no
claim that a fragment is missing. `gitflow.sh finish` runs the same check first. It runs `git fetch
origin <base>`, then checks from the merge base with `origin/<base>`; when the fetch fails it warns
and uses the local base, as it does when there is no such ref. It stops on every failure and prints
the add-a-fragment advice only for exit status 1.

A fragment may hold only bullet lines, indented continuation lines and blank lines, must be valid
UTF-8 (one leading BOM is ignored), and a renamed fragment does not count as added (the path must
not exist at the base). `changelog.py assemble --date` takes only `YYYY-MM-DD`. A merge commit git
creates itself runs `commit-msg` only, because `.husky/` has no `pre-merge-commit` hook; of the
commits `release.py` makes, only the release commit runs `pre-commit`. `config/gate.sh` must stay
POSIX-sourceable, because `pre-push` runs under `sh`.

`release.py` is not run by any hook. Running it with `--yes` or `--push` is an "Ask first" item in
`../CLAUDE.md`; a dry run is free. `--push` requires `--yes`. It refuses a repository with no
commits, and needs a clean tree, local `main` and `develop` equal to `origin`, and neither branch
checked out in another worktree. On failure it prints the failed command's stdout and stderr,
labelled, then the exact commands to finish or undo by hand, and never runs a reset or force itself.
A rejected push names two likely causes: another push won the race, or a local `pre-push` hook
failed. A repository that protects `main` or `develop` must allow its push (`main`, `develop` and
the tag). Fragment rules, the 0.x rule and the hotfix flow are in `../CONTRIBUTING.md` § Versioning;
the full specification is in `../DEV_TOOLING_SPEC.md`. `gitflow.sh finish` merges with
`chore(merge): merge task NNNN into <base>` (task branches) or `chore(merge): merge <branch> into
<base>`. The `STAGED_GLOB` pathspec in `config/gate.sh` selects the files `--staged` checks.

An agent iterates with `scripts/gate.sh --fast` and targeted tests and commits freely. The one
independent verifier of a finished branch runs the full `scripts/gate.sh` itself, in a detached
worktree of the orchestrator's checkout (`git worktree add --detach <path> origin/<branch>`), and
its record is what the later steps reuse. The hooks check task-branch pushes with `--fast` and
guard `develop` and `main`; they are not the primary way this gate gets run.
