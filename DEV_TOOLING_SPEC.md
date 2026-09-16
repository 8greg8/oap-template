# Dev Tooling Spec: Hooks, Gates, and Release Automation

This document specifies the copy-pasteable `scripts/` + `.husky/` + `package.json` bundle that
turns the process described in [`CONTRIBUTING.md`](CONTRIBUTING.md) (branching, commits,
versioning, verify/resolve) into deterministic, agent-runnable commands instead of prose an agent
has to interpret freshly each time. It is the implementation of `README.md` step 4 ("Wire up
Husky-managed git hooks") and of the tagging step `AGENTS.md` refers to ("outside the tagging step
defined in `CONTRIBUTING.md`").

It is written to be **copy-pasted as a unit** into an existing or new repository: the `scripts/`
folder, `.husky/`, and `package.json` move together, and the one file a target repo edits to adapt
them is `scripts/config/gate.sh`.

## Goals

1. **Deterministic pipelines an agent can call instead of reason about.** "Lint, typecheck, test,
   fix, stage, commit" becomes `scripts/gate.sh`, `scripts/autofix.sh`, and a commit helper — not a
   sequence of ad hoc commands re-derived from `PYTHON_CONVENTIONS.md` prose every time.
2. **The same gate everywhere.** The commands run by an agent before committing, by the
   verify/resolve loop's independent verifier, by the `pre-commit`/`pre-push` Husky hooks, and by
   CI (if present) must be *literally the same script* — never four hand-maintained copies of the
   same four commands that can drift apart.
3. **Conventional Commits and SemVer enforced programmatically, not by convention alone.** A
   malformed commit message is rejected at `commit-msg` time; the next release version is computed
   from commit history, not typed by hand.
4. **Gitflow branch operations as one-line commands**, matching the exact branch/merge/tag rules in
   `CONTRIBUTING.md` § Branching and § Versioning, so an agent (or human) doesn't hand-run
   multi-step git sequences that are easy to get subtly wrong (e.g. forgetting the hotfix
   back-merge to `develop`).
5. **Portable.** Only `scripts/config/gate.sh` is project-specific (the four gate commands and the
   default branch names). Everything else — hook wiring, commit-msg validation, version
   computation, gitflow helpers — is stack-agnostic shell/stdlib-Python and works unmodified in any
   git repo.

## Non-goals

- This does **not** replace `.agents/tasks/scripts/` (task/report/backlog tooling). That governs
  *what work is being done and its evidence trail*; this spec governs *the mechanical gate a change
  must pass and the git operations around it*. `housekeep.py setup` (existing) checks that this
  bundle is installed; nothing here duplicates task/backlog logic.
- No CI workflow files are defined here. `scripts/gate.sh` is written so a CI job is a one-line
  `scripts/gate.sh` call if/when one is added later, but authoring `.github/workflows/*` is out of
  scope.
- No auto-merge, auto-tag-push, or auto-release-on-push behavior. Tagging and pushing tags stay a
  deliberate, explicit invocation (`scripts/release.py`) — see `AGENTS.md`'s "Ask first" list
  (cutting a release tag by hand is a human-in-the-loop action; this spec gives the *tool*, not
  permission to run it unattended).
- No changelog generation. Out of scope for this pass; `scripts/next_version.py` prints the commits
  it used for its computation, which is enough to hand-write a changelog if one is wanted later.

## Layout

```
package.json                # minimal: husky devDependency + "prepare" script only
.husky/
  pre-commit                 # scripts/autofix.sh --check-only=false, then scripts/gate.sh
  commit-msg                 # scripts/commit_lint.py "$1"
  pre-push                   # scripts/gate.sh
scripts/
  README.md                  # how to install this bundle into a new/existing repo
  config/
    gate.sh                  # ONLY project-specific file: lint/format/typecheck/test commands
  lib/
    common.sh                # shared shell helpers: colors, fail(), section headers
  gate.sh                    # runs the 4 verify gates from config/gate.sh, fails fast, reports clearly
  autofix.sh                 # runs the *_FIX_CMD variants from config/gate.sh (safe auto-corrections)
  commit_lint.py              # stdlib-only: validates a commit message against Conventional Commits
  next_version.py             # stdlib-only: computes next SemVer from commits since last vX.Y.Z tag
  release.py                  # stdlib-only: tags main with the computed version (explicit, not automatic)
  gitflow.sh                  # feature/bugfix/hotfix start|finish, matching CONTRIBUTING.md exactly
```

Everything under `scripts/` besides `config/gate.sh` is committed as-is. `scripts/config/gate.sh`
is the adaptation point: it defines four shell variables the rest of the tooling sources and never
hardcodes elsewhere.

## `scripts/config/gate.sh` contract

```bash
# One line per gate, in the order they must run. Each is a full shell command string.
LINT_CMD="uv run ruff check"
LINT_FIX_CMD="uv run ruff check --fix"
FORMAT_CHECK_CMD="uv run ruff format --check"
FORMAT_FIX_CMD="uv run ruff format"
TYPECHECK_CMD="uv run ty check"
TEST_CMD="uv run pytest"

# Branch names, only needed by gitflow.sh / release.py.
MAIN_BRANCH="main"
DEVELOP_BRANCH="develop"
```

This repo's default values are the exact commands from `PYTHON_CONVENTIONS.md` § Commands, so the
gate a fresh clone of this template runs is identical to what that doc already tells a human/agent
to run by hand — the script is just the same commands with no chance of transcription drift.

A repo with a different stack (e.g. TypeScript) only edits this one file — e.g.
`LINT_CMD="pnpm eslint ."`, `TEST_CMD="pnpm vitest run"` — and every hook, the verify/resolve
loop, and `gitflow.sh`/`release.py` keep working unmodified.

## `scripts/gate.sh`

Runs, in order, with each gate's name and pass/fail printed as it completes (matching the four
gates named in `CONTRIBUTING.md` § Agent verify/resolve workflow so a report can quote this
output directly):

1. `LINT_CMD`
2. `FORMAT_CHECK_CMD`
3. `TYPECHECK_CMD`
4. `TEST_CMD`

Stops at the first failing gate (fail-fast) and exits non-zero. Exit 0 only when all four pass.
This is what `pre-push` runs, what the verify/resolve loop's independent verifier runs, and what a
CI job would run — one script, one source of truth.

## `scripts/autofix.sh`

Runs `LINT_FIX_CMD` then `FORMAT_FIX_CMD` — the safe, deterministic auto-corrections (not
`TYPECHECK_CMD`/`TEST_CMD`, which have no generic "fix" form). Intended use: an agent runs
`autofix.sh` then `gate.sh` in a loop (the "resolve" half of verify/resolve) until `gate.sh` is
clean, instead of hand-fixing lint nits. `pre-commit` runs it automatically so trivial formatting
issues never block a commit or reach the verifier as noise.

## Commit message validation: `scripts/commit_lint.py`

Invoked by `.husky/commit-msg` as `commit_lint.py "$1"` (husky passes the path to the commit
message file). Stdlib-only Python, no `npm` commit-lint dependency needed. Enforces:

- Header matches `^(?P<type>\w+)(\((?P<scope>[^)]+)\))?(?P<bang>!)?: (?P<subject>.+)$`.
- `type` is one of: `feat fix docs style refactor perf test build ci chore revert`.
- `subject` is non-empty, does not end with a period, and the header is ≤100 chars.
- If `bang` (`!`) is present, the message body must contain a `BREAKING CHANGE:` footer — enforces
  `CONTRIBUTING.md`'s rule that breaking changes are marked both ways, not just one.
- If the body contains a `BREAKING CHANGE:` footer, `bang` must also be present (same rule, other
  direction).
- Git's own auto-generated merge commit messages (`Merge branch 'x' into y`, `Merge pull request
  #N ...`) are exempt — they don't follow Conventional Commits and aren't meant to (same
  convention `commitlint` uses by default). Without this exemption, `gitflow.sh`'s `finish`
  subcommands couldn't complete a merge.

Exits non-zero with a specific, actionable message (which rule failed, what was found) on any
violation — Husky then blocks the commit.

## Version computation: `scripts/next_version.py`

Stdlib-only. Algorithm:

1. `git describe --tags --match 'v[0-9]*.[0-9]*.[0-9]*' --abbrev=0` for the last release tag;
   default `v0.0.0` if none exists yet.
2. `git log <last_tag>..HEAD --pretty=format:%H%x1f%B%x1e` to walk commits since that tag (on the
   current branch — normally run against `main` right after a merge lands).
3. Parse each commit's header the same way `commit_lint.py` does. Classify:
   - Any commit with `!` in the header or a `BREAKING CHANGE:` footer → **major**.
   - Else any `feat` commit → **minor**.
   - Else any `fix` commit → **patch**.
   - No qualifying commits → no bump (exits non-zero, "nothing to release").
4. Bump the *highest* qualifying level off the last tag (major resets minor+patch to 0, minor
   resets patch to 0), per `CONTRIBUTING.md` § Versioning.
5. Print the next version (`vX.Y.Z`) to stdout, and on stderr the list of commits that drove the
   decision (hash + header), so the output is auditable, not a black box.

`--dry-run` (default) only prints; nothing here creates a tag.

## Release tagging: `scripts/release.py`

Explicit, human/agent-invoked, never triggered by a hook:

1. Refuses to run unless the current branch is `MAIN_BRANCH` (from `gate.sh` config) and the
   working tree is clean.
2. Calls `next_version.py` for the version to cut.
3. Prints the version and the commits behind it, and requires `--yes` to actually create the tag
   (otherwise it's a dry-run preview) — matching `AGENTS.md`'s rule that cutting a release tag is
   not something to do silently.
4. With `--yes`: creates an annotated tag `git tag -a vX.Y.Z -m "..."`. Does **not** push by
   default; `--push` additionally runs `git push origin vX.Y.Z`, since pushing a tag is the
   irreversible, shared-state part of this operation.

Note: `hatch-vcs`'s derived version is computed at build time and `uv sync` will not rebuild it
just because a new tag now exists — after cutting a release, run
`uv sync --reinstall-package <package>` (or any change that forces a rebuild) if you need the
installed package's `__version__`/metadata to reflect the new tag immediately.

## Gitflow helper: `scripts/gitflow.sh`

Thin wrapper around exactly the branch/worktree operations `CONTRIBUTING.md` § Branching already
documents by hand, so they're one command instead of a multi-line sequence to get right every time:

```bash
scripts/gitflow.sh feature start <topic>   # worktree ../<repo>-feat-<topic>, branch feat/<topic> from develop
scripts/gitflow.sh feature finish <topic>  # merge feat/<topic> into develop, remove the worktree
scripts/gitflow.sh bugfix start|finish <topic>   # same, bugfix/<topic>
scripts/gitflow.sh hotfix start <topic>    # worktree ../<repo>-hotfix-<topic>, branch hotfix/<topic> from main
scripts/gitflow.sh hotfix finish <topic>   # merge into main, back-merge main into develop, remove worktree
                                            # (prints a reminder to run release.py; does not tag itself)
```

`finish` subcommands refuse to run if `scripts/gate.sh` fails on the branch being merged — the gate
is not bypassable through the gitflow helper.

## How this composes with the existing verify/resolve loop

`CONTRIBUTING.md` § Agent verify/resolve workflow is unchanged by this spec — it's the same five
steps. What changes is that steps 2 ("Verify") and 4 ("repeat") are now literally
`scripts/gate.sh` and `scripts/autofix.sh` + `scripts/gate.sh`, not a re-derivation of "run ruff,
ty, pytest" from `PYTHON_CONVENTIONS.md` each time. `AGENTS.md`'s rule that verification must come
from "an independent agent invocation (fresh context)" is unaffected — the script makes that
invocation's job mechanical, it doesn't replace the independence requirement.

## Installation into a target repo

See `scripts/README.md` for the copy-paste + `npm install` + `npm run prepare` steps. In short:
copy `package.json`, `.husky/`, `scripts/` into the target repo root, edit
`scripts/config/gate.sh` for that repo's actual lint/typecheck/test commands, then:

```bash
npm install
npm run prepare        # sets core.hooksPath, per Husky's install step
chmod +x .husky/* scripts/*.sh
```

`housekeep.py setup` (in repos that have `.agents/tasks/`) verifies this landed correctly:
`.husky/` exists with executable hooks and `core.hooksPath` is configured.
