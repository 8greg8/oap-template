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
scripts/gate.sh              # run all 4 verify gates (lint, format check, typecheck, test)
scripts/gate.sh --fast       # skip tests, for a quick iteration loop (not a substitute for the full gate)
scripts/gate.sh --staged     # lint/format/typecheck only staged files matching STAGED_GLOB; no tests
scripts/autofix.sh           # apply lint autofix + formatting, then re-run scripts/gate.sh
scripts/autofix.sh --staged  # same, but only on staged files matching STAGED_GLOB

scripts/commit_lint.py <msg-file>    # validate a commit message (used by .husky/commit-msg)
scripts/next_version.py              # print the next SemVer version from commits since last tag
                                     # (0.x rule: while the major is 0, a breaking change bumps minor)

scripts/changelog.py check <base> <tip>       # fail if a feat/fix/breaking commit in the range adds
                                              # no changelog.d/ fragment, or a fragment is invalid
scripts/changelog.py preview [vX.Y.Z]         # print the section a release would write
scripts/changelog.py assemble vX.Y.Z [--date YYYY-MM-DD]   # fold fragments into CHANGELOG.md, delete them

scripts/release.py                   # dry run: version, commits, changelog section; changes nothing
scripts/release.py --yes             # merge develop into main, changelog, tag, update develop; local
scripts/release.py --yes --push      # same, then git push --atomic origin main develop vX.Y.Z
scripts/release.py --yes --version v1.0.0   # override the version (canonical vX.Y.Z, SemVer-higher)

scripts/gitflow.sh feature start <topic>    # worktree + branch from develop
scripts/gitflow.sh feature finish <topic>   # changelog check, gate, merge to develop, clean up worktree
scripts/gitflow.sh bugfix  start|finish <topic>
scripts/gitflow.sh hotfix  start|finish <topic>   # from/into main, with back-merge to develop;
                                                  # then push both and run release.py --yes on main
scripts/gitflow.sh docs|chore|fix start|finish <T-NNNN-slug>   # task branches, from/into develop
```

## What each hook does

| Hook | Runs |
|---|---|
| `pre-commit` | `autofix.sh --staged`, re-stages the files that were staged, then `gate.sh --staged` (no tests). Skipped when only `.agents/` records are staged |
| `commit-msg` | `commit_lint.py` against the message being committed (lines <= 100 chars) |
| `pre-push` | `changelog.py check` for each pushed branch, then the full `gate.sh`. Both are skipped when every pushed commit changes only `.agents/` records |

Code under `.agents/tasks/scripts/` is never skipped by either hook. A new remote branch, or a
range git cannot list, always runs the full gate.

The fragment check in `pre-push` takes its range from the remote ref being updated: for `main` and
`develop`, `<remote sha>..<local sha>` (a first push of either is not checked); for `hotfix/*`, from
the merge base with `origin/main`; for any other branch, from the merge base with `origin/develop`.
Deleted refs, tags and other non-branch refs are skipped. A range it cannot list (`changelog.py`
exits 2, no merge base, no `origin` ref) skips the check for that ref with a message and the gate
still runs. Any other failure, including a failed check or a missing `python3`, rejects the push
before the gate starts. `gitflow.sh finish` runs the same check first, from the merge base with
`origin/<base>` (the local base when there is no such ref), and stops on every failure.

`release.py` is not run by any hook. It needs a clean tree, local `main` and `develop` equal to
`origin`, and neither branch checked out in another worktree; on failure it prints the exact
commands to finish or undo by hand and never runs a reset or force itself. A repository that
protects `main` or `develop` must allow its push (`main`, `develop` and the tag). Fragment rules,
the 0.x rule and the hotfix flow are in `../CONTRIBUTING.md` § Versioning; the full specification is
in `../DEV_TOOLING_SPEC.md`. `gitflow.sh finish` merges with
`chore(merge): merge task NNNN into <base>` (task branches) or
`chore(merge): merge <branch> into <base>`. The `STAGED_GLOB` pathspec in
`config/gate.sh` selects the files `--staged` checks.

These are the same scripts an agent (or you) should run by hand during the verify/resolve loop
— the hooks are a safety net, not the primary way this gate gets run.
