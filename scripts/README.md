# scripts/

Deterministic pipelines for the lint/typecheck/test gate, commit validation, SemVer/release
tagging, and Gitflow branch operations. Full design: [`../DEV_TOOLING_SPEC.md`](../DEV_TOOLING_SPEC.md).

## Copying this into another repo

This folder moves together with `../.husky/` and `../package.json` — copy all three:

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
scripts/release.py                   # dry-run preview of the next release tag
scripts/release.py --yes             # create the tag locally
scripts/release.py --yes --push      # create and push the tag

scripts/gitflow.sh feature start <topic>    # worktree + branch from develop
scripts/gitflow.sh feature finish <topic>   # gate, merge to develop, clean up worktree
scripts/gitflow.sh bugfix  start|finish <topic>
scripts/gitflow.sh hotfix  start|finish <topic>   # from/into main, with back-merge to develop
```

## What each hook does

| Hook | Runs |
|---|---|
| `pre-commit` | `autofix.sh --staged`, re-stages the files that were staged, then `gate.sh --staged` (no tests). Skipped when only `.agents/` records are staged |
| `commit-msg` | `commit_lint.py` against the message being committed (lines <= 100 chars) |
| `pre-push` | the full `gate.sh`. Skipped when every pushed commit changes only `.agents/` records |

Code under `.agents/tasks/scripts/` is never skipped by either hook. A new remote branch, or a
range git cannot list, always runs the full gate. `gitflow.sh finish` merges with
`chore(merge): merge task NNNN into <base>` (task branches) or
`chore(merge): merge <branch> into <base>`. The `STAGED_GLOB` pathspec in
`config/gate.sh` selects the files `--staged` checks.

These are the same scripts an agent (or you) should run by hand during the verify/resolve loop
— the hooks are a safety net, not the primary way this gate gets run.
