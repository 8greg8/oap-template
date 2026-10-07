# Dev Tooling Spec: Hooks, Gates, and Release Automation

This document specifies the copy-pasteable `scripts/` + `.husky/` + `package.json` bundle that
turns the process described in [`CONTRIBUTING.md`](CONTRIBUTING.md) (branching, commits,
versioning, verify/resolve) into deterministic, agent-runnable commands instead of prose an agent
has to interpret freshly each time. It implements the gate, the Husky-managed hooks, the changelog
and the release flow that `CONTRIBUTING.md` describes.

It is written to be **copy-pasted as a unit** into an existing or new repository: the `scripts/`
folder, `.husky/`, and `package.json` move together, and the one file a target repo edits to adapt
them is `scripts/config/gate.sh`.

## Goals

1. **Deterministic pipelines an agent can call instead of reason about.** "Lint, typecheck, test,
   fix, stage, commit" becomes `scripts/gate.sh`, `scripts/autofix.sh`, and a commit helper — not a
   sequence of ad hoc commands re-derived from `PYTHON_CONVENTIONS.md` prose every time.
2. **The same gate everywhere.** The commands run by an agent while iterating, by the one
   independent verifier of a finished branch, by the `pre-commit`/`pre-push` Husky hooks, and by
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
- No auto-merge, auto-tag-push, or auto-release-on-push behavior. Releasing, tagging and pushing
  tags stay a deliberate, explicit invocation (`scripts/release.py`). `CLAUDE.md`'s "Ask first"
  list covers it: running `release.py --yes` or `--push` needs the owner's request, and only a
  dry run is free. This spec gives the *tool*, not permission to run it unattended.
- No changelog text is generated from commit messages. Entries are written by hand as fragments
  (`changelog.d/`), and `scripts/changelog.py` only checks, previews and assembles them.
- No GitHub Release or publishing workflow. `release.py` creates the tag; what happens on a tag is
  out of scope.

## Layout

```
package.json                # minimal: husky devDependency + "prepare" script only
.husky/
  pre-commit                 # staged files only, no tests: autofix.sh --staged, re-stage, gate.sh --staged
  commit-msg                 # scripts/commit_lint.py "$1"
  pre-push                   # changelog fragment check per pushed branch, then the gate: develop needs a
                             # gate record (gate.sh --if-needed), main one with the slow tests
                             # (--if-needed --all), any other ref gets gate.sh --fast; all skipped when
                             # every pushed commit is RECORD_PATHS only
scripts/
  README.md                  # how to install this bundle into a new/existing repo
  config/
    gate.sh                  # ONLY project-specific file: gate commands, branch names, RECORD_PATHS,
                             # SLOW_SAFE_PATHS
  lib/
    common.sh                # shared shell helpers: colors, fail(), section headers
  gate.sh                    # runs the 4 verify gates from config/gate.sh, counts failures, reports clearly; writes and
                             # checks gate records (--if-needed)
  autofix.sh                 # runs the *_FIX_CMD variants from config/gate.sh (safe auto-corrections)
  commit_lint.py              # stdlib-only: validates a commit message against Conventional Commits
  next_version.py             # stdlib-only: computes next SemVer from commits since last vX.Y.Z tag
  changelog.py                # stdlib-only: check, preview and assemble changelog fragments
  release.py                  # stdlib-only: merges develop into main, writes the changelog, tags,
                              # updates develop (explicit, not automatic)
  gitflow.sh                  # feature/bugfix/hotfix start|finish, matching CONTRIBUTING.md exactly
CHANGELOG.md                  # Keep a Changelog; empty [Unreleased], changes only at a release
changelog.d/
  README.md                   # the fragment rules; never checked, folded or deleted
  <id>.<category>.md          # one fragment per change; deleted when a release folds it in
```

Everything under `scripts/` besides `config/gate.sh` is committed as-is. `scripts/config/gate.sh`
is the adaptation point: it defines the shell variables the rest of the tooling sources and never
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
# Appended to TEST_CMD when the slow tests are skipped (see SLOW_SAFE_PATHS).
TEST_SKIP_SLOW_ARGS='-m "not slow"'

# Branch names, only needed by gitflow.sh / release.py.
MAIN_BRANCH="main"
DEVELOP_BRANCH="develop"

# Bookkeeping paths: one space-separated string of git glob pathspecs, left out of a gate
# record's key and skipped by the hooks.
RECORD_PATHS=".agents/tasks/T-*.md .agents/tasks/reports/** .agents/tasks/BACKLOG.md .agents/tasks/.counter .agents/LESSONS.md .agents/plans/**"

# Paths whose change cannot break a slow test: same syntax as RECORD_PATHS.
SLOW_SAFE_PATHS="${RECORD_PATHS-} changelog.d/*.*.md CONTRIBUTING.md DEV_TOOLING_SPEC.md PYTHON_CONVENTIONS.md NOTICE.md"
```

This repo's default values are the exact commands from `PYTHON_CONVENTIONS.md` § Commands, so the
gate a fresh clone of this template runs is identical to what that doc already tells a human/agent
to run by hand — the script is just the same commands with no chance of transcription drift.

A repo with a different stack (e.g. TypeScript) only edits this one file — e.g.
`LINT_CMD="pnpm eslint ."`, `TEST_CMD="pnpm vitest run"` — and every hook, the verify/resolve
loop, and `gitflow.sh`/`release.py` keep working unmodified.

`RECORD_PATHS` lists the paths that only record bookkeeping: task files, reports, `BACKLOG.md`, the
task counter, `LESSONS.md` and plans. It is one space-separated string of git glob pathspecs, so no
entry holds a space: `*` does not cross `/` and `**` does. `gate.sh` and both hooks exclude each entry
as a `:(exclude,glob)<entry>` pathspec, so git is the one matcher, and shell code expands the string
with globbing off (`set -f`). Everything else counts as code, including `.agents/tasks/scripts/`,
`.agents/tasks/templates/` and `.agents/README.md`. Both hooks use the list for their skip rule, and
`gate.sh` uses it to build the key of a gate record, so the hooks and the key always agree.

The file must stay POSIX-sourceable: plain `NAME="value"` assignments, no bash arrays or other
bash-only syntax. The bash scripts source it, and so does `.husky/pre-push`, which runs under
POSIX `sh` (`dash` on many systems). A test sources it with `sh`. `gate.sh` reads `RECORD_PATHS` as `${RECORD_PATHS-}`, so a copy of the config without it still
works: no path is then a record path, so the hooks gate every change and the key covers every
tracked file.

`SLOW_SAFE_PATHS` lists the paths whose change cannot break a slow test: `RECORD_PATHS`, the
changelog fragments `changelog.d/*.*.md` (`*.*.md` leaves out `changelog.d/README.md`), and the
prose docs `CONTRIBUTING.md`, `DEV_TOOLING_SPEC.md`, `PYTHON_CONVENTIONS.md` and `NOTICE.md`, which
`init_project.py` copies unchanged. It uses the same pathspec syntax as `RECORD_PATHS`.
`TEST_SKIP_SLOW_ARGS` is shell-quoted text appended to `TEST_CMD` when the slow tests are skipped.
`gate.sh` reads both as `${VAR-}`; with either empty or unset the slow tests always run. Adding a
path to the list changes what the gate checks and needs a human.

## `scripts/gate.sh`

Runs, in order, with each gate's name and pass/fail printed as it completes (matching the four
gates named in `CONTRIBUTING.md` § Agent verify/resolve workflow so a report can quote this
output directly):

1. `LINT_CMD`
2. `FORMAT_CHECK_CMD`
3. `TYPECHECK_CMD`
4. `TEST_CMD`

Runs every gate even after one fails, counts the failures, and exits 1 when any failed
(`N gate(s) failed`). Exit 0 only when all four pass. This is what the independent verifier of a
finished branch runs in full, what `pre-push` runs (through `--if-needed` for `develop` and `main`,
and `--fast` for any other branch), and what a CI job would run — one script, one source of truth.
An executor iterates with `--fast` and targeted tests; its own runs certify nothing.

Flags:

- `--fast` skips `TEST_CMD`. Never the final check.
- `--staged` runs lint, format check and typecheck on the staged files that match
  `STAGED_GLOB` (a pathspec in `scripts/config/gate.sh`, default `*.py`), and never runs tests.
  It exits 0 when no staged file matches. `LINT_CMD`, `FORMAT_CHECK_CMD`, `TYPECHECK_CMD` and
  the `*_FIX_CMD`s therefore must accept file paths as trailing arguments; with no arguments
  they check the whole repo. `pre-commit` uses this mode.
- `--if-needed [<commit>...]` checks a gate record for each named commit (default `HEAD`) and
  exits 0 only when every commit has a sufficient record or passes a full gate run. See § Gate
  records. It cannot be combined with `--fast` or `--staged`, and a commit argument is accepted
  only with it.
- `--all` runs every test, the slow ones included. Without it the slow tests are skipped when the
  change since the base is safe-list-only (§ Slow tests). It cannot be combined with `--fast` or
  `--staged`. With `--if-needed`, a record of a run without the slow tests does not count.

`gate.sh` and `autofix.sh` run under bash 3.2 (macOS default): no `mapfile`, and empty arrays
are expanded with the `${files[@]+"${files[@]}"}` guard so `set -u` does not abort.

### Slow tests

The end-to-end cases of `tests/test_init_project.py` carry `@pytest.mark.slow`, registered in
`pyproject.toml` under `[tool.pytest.ini_options]`; they take about 250 to 300 s of a full gate.
`gate.sh` runs `TEST_CMD` followed by `TEST_SKIP_SLOW_ARGS` only when all of these hold: `--all` is
absent, the two settings are non-empty, a base is found, the change since the base is not empty,
and every changed path matches `SLOW_SAFE_PATHS`. In every other case it runs `TEST_CMD` alone.

- **Changed paths.** For a run on the working tree: `git diff --name-only --no-renames <base>` plus
  `git ls-files --others --exclude-standard`. For a named commit under `--if-needed`:
  `git diff --name-only --no-renames <base> <commit>`. `--no-renames` makes a rename count both
  paths. Both are filtered with the `:(exclude,glob)` pathspecs of `SLOW_SAFE_PATHS`; any path left
  over forbids the skip.
- **Base.** The merge base of the commit with `origin/$DEVELOP_BRANCH`, or with
  `origin/$MAIN_BRANCH` when `git symbolic-ref -q --short HEAD` names a `hotfix/` branch. A detached
  HEAD uses the develop base. When that remote ref does not exist the local branch of the same name
  is used. When neither exists, or git finds no merge base, the slow tests run.
- **Always run.** `--all`; a push to `main` (the hook passes `--all` in its own call for `main`'s
  shas); a change set that is empty.
- **Safety net.** `init_project.py` copies the four prose docs of the list unchanged, and the
  end-to-end test fails when a generated file holds a template name. A fast test in
  `tests/test_init_project.py` greps exactly those four docs for the template names, so the one
  way they can break the end-to-end test is caught without running it.

### Gate records

A full `gate.sh` run that passes writes a record, so later steps do not gate the same code again.

- **Key.** A hash (`git hash-object --stdin`, 40 or 64 lowercase hex characters) over the listing
  of the commit's tree without the `RECORD_PATHS` entries, followed by one line each from
  `uv --version`, `uv run python -VV`, `git --version` and `node -v` (`node: absent` when node is
  missing). The listing is `git ls-files -s` over a temporary index of the commit, because
  `git ls-tree` accepts no pathspec magic. The tool versions are those seen from the checkout where
  `gate.sh` runs. Changing a record path keeps the key. Changing any other tracked file, or a tool
  version, changes it.
- **Where.** The file `$(git rev-parse --git-common-dir)/gate-pass/<key>`, in the git directory
  shared by every worktree of the repository, never committed and never part of the tree. It holds
  four lines: `key=`, `commit=`, `slow=yes|no` (whether the slow tests ran) and `date=`. A
  `slow=yes` record is never overwritten by a `slow=no` one.
- **When it is written.** Only after a full run in which every gate passed on a tree that is
  clean before and after: `git status --porcelain --untracked-files=all` prints nothing both
  times. The run prints `gate record <key> (slow tests: yes|no)` before `gate clean`.
  `--fast`, `--staged`, a failed run and a dirty run never write one; a dirty run prints why
  (`dirty tree before the run` or `dirty tree after the run`).
- **`--if-needed [<commit>...]`.** For each commit (default `HEAD`) it computes the key and looks
  for the record. A record is sufficient when it says `slow=yes`, or when it says `slow=no` and
  the commit's change since the base is safe-list-only and `--all` is absent. A commit with a
  sufficient record is skipped. For each other commit it runs the
  commit's own full gate: on the working tree when that commit is checked out and the tree is
  clean, otherwise in a temporary detached worktree, which is the commit's `scripts/gate.sh` run
  from `git worktree add --detach "$(mktemp -d)/wt" <commit>`. Before it uses the worktree it
  unsets `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`,
  `GIT_ALTERNATE_OBJECT_DIRECTORIES` and `GIT_PREFIX`, which a hook may have set. A trap on exit
  removes the worktree (`git worktree remove --force`, then `git worktree prune`) whether the
  gate passed or not. No `npm ci` is needed; `uv run` creates the `.venv`. When the commit needs
  the slow tests (its change is not safe-list-only, or `--all` was given) the inner `gate.sh`
  gets `--all`, so it cannot decide otherwise from a different base. The inner run writes the
  record. It never refuses for want of a checkout, and it exits 1 at the first commit whose gate
  fails.

Records are local files, and any clean full run writes one, an executor's included. The
independent verifier therefore never relies on a record: it runs the full gate itself, in a
detached worktree of the orchestrator's checkout (`git worktree add --detach <path>
origin/<branch>`), which writes the record into the shared git directory. Only `gate.sh` writes
records; nobody creates, copies or edits one by hand. Records only let the later mechanical steps
skip the same code: the `develop` and `main` pushes, `gitflow.sh finish` and the orchestrator's
post-merge `gate.sh --if-needed`. A fix round's verifier may cite a record an earlier independent
verifier's run wrote for the same code. Records written inside scratch repositories by tests and by
`init_project.py` stay in those repositories.

## Hooks

- `pre-commit`: exits 0 when nothing is staged. Exits 0 with a message when every staged path
  (listed with `--no-renames`, so a rename into a record path also counts its old path) matches
  a `RECORD_PATHS` entry (task filing, status changes, reports, `BACKLOG.md`, `LESSONS.md`, plans).
  Otherwise runs `autofix.sh --staged`, re-stages only the files that were
  already staged (NUL-delimited, as literal paths, so any filename works), then
  `gate.sh --staged`. Tests are left to `pre-push`.
- `pre-push`: reads git's `<local ref> <local sha> <remote ref> <remote sha>` lines and lists
  the files of each pushed commit (`git log --name-only --no-renames
  --diff-merges=first-parent`). It skips everything, the fragment check and the gate, only when
  every pushed commit touches nothing but `RECORD_PATHS` paths. A deleted ref pushes no commits. A
  new remote branch, or a range git cannot list, never takes the skip. Otherwise it runs the
  fragment check (below) for each pushed ref, then the gate, which depends on the ref:
  - `main`: one `gate.sh --if-needed --all` call with the local sha of every non-deleted `main`
    ref, made first. The slow tests always run for `main`: a record of a run without them does not
    satisfy it.
  - `develop`: one `gate.sh --if-needed` call with the local sha of every non-deleted `develop`
    ref. The full gate runs only for a commit that has no sufficient gate record, and skips the
    slow tests for a change that is safe-list-only (§ Slow tests).
  - any other branch: one `gate.sh --fast` call when the push has such a ref. The independent
    verifier's full run follows before a merge, and `develop` and `main` stay fully protected.
  - tags and other non-branch refs trigger no gate.
  A hotfix release push passes: `release.py --yes --push` leaves `main` checked out, so the hook
  makes two calls. The release commit is gated on the checkout with `--all`, and the back-merge on
  `develop` in a temporary worktree.
- `commit-msg`: `commit_lint.py`, below.
- Merge commits: a merge commit that git creates itself runs `commit-msg` only. Git runs no
  `pre-commit` for it, and `.husky/` has no `pre-merge-commit` hook, so the `chore(merge)` commits
  of `gitflow.sh finish` and `release.py` are linted but not gated. A merge that stopped on a
  conflict and is finished by hand with `git commit` runs `pre-commit` too. Of the commits
  `release.py` makes, only `chore(release)` runs `pre-commit`.

Code under `.agents/tasks/scripts/`, the templates and the process docs are not in `RECORD_PATHS`,
so they never take the skip.

### Fragment check on push

For each pushed ref, `pre-push` runs `python3 scripts/changelog.py check <base> <local sha>`. The
branch comes from `<remote ref>`, never from `<local ref>`, which can be `HEAD`. `<remote>` is the
remote git passes to the hook as `$1` (`origin` when the hook is run by hand), so a push to another
remote is checked against that remote's tracking refs. The base is:

| Pushed ref | Base |
|---|---|
| `MAIN_BRANCH`, `DEVELOP_BRANCH` | the remote sha; a first push (all-zero remote sha) is not checked |
| `hotfix/*` | merge base of `<remote>/MAIN_BRANCH` and the tip |
| any other branch, new or not | merge base of `<remote>/DEVELOP_BRANCH` and the tip |
| a deleted ref, a tag, any non-branch ref | not checked |

The branch names come from `scripts/config/gate.sh`. Exit codes decide what happens next:

- 0: the ref passes.
- 2, or no merge base because the remote-tracking ref is missing (a range git cannot list; `$1` is
  a URL, for example, so there is no such ref): the check is skipped for that ref with a message,
  and the gate still runs. This fails open, as the hook already does for a range it cannot list.
- 1: a missing or invalid fragment. The push is rejected before the gate starts, with that
  explanation. This fails closed.
- Any other code (3 for an internal error of `changelog.py`, 127 for a missing `python3`, a
  signal): the push is rejected before the gate starts with
  `pre-push: changelog check failed (exit N) for <remote ref>`. It makes no claim that a fragment
  is missing. This fails closed.

A release push needs no special case. The `main` range holds the released commits and the commits
that added their fragments. The `develop` range holds merge commits and the `chore(release)`
commit, which drive no version.

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
- `subject` is non-empty, does not end with a period, and every line (header, body, footer) is
  ≤100 chars. Everything below git's scissors line (`# ------ >8 ------`, written by
  `git commit -v`) is ignored, because the hook sees the file before git strips it.
- If `bang` (`!`) is present, the message body must contain a `BREAKING CHANGE:` footer — enforces
  `CONTRIBUTING.md`'s rule that breaking changes are marked both ways, not just one.
- If the body contains a `BREAKING CHANGE:` footer, `bang` must also be present (same rule, other
  direction).
- Git's own auto-generated merge commit messages (`Merge branch 'x' into y`, `Merge pull request
  #N ...`) stay exempt for merges git writes itself (same convention `commitlint` uses by
  default). This repo's own merges, made by `gitflow.sh finish`, use the Conventional form
  `chore(merge): merge task NNNN into develop` (for a `<type>/T-NNNN-<slug>` branch) or
  `chore(merge): merge <branch> into <base>`; they are linted like any other commit.

Exits non-zero with a specific, actionable message (which rule failed, what was found) on any
violation — Husky then blocks the commit.

## Version computation: `scripts/next_version.py`

Stdlib-only. Algorithm:

1. `git describe --tags --match 'v[0-9]*.[0-9]*.[0-9]*' --abbrev=0` for the last release tag
   reachable from `HEAD`; default `v0.0.0` if none exists yet.
2. `git log <last_tag>..HEAD --pretty=format:%H%x1f%B%x1e` to walk commits since that tag (on the
   current branch).
3. Parse each commit's header the same way `commit_lint.py` does. Classify:
   - Any commit with `!` in the header or a `BREAKING CHANGE:` footer → **breaking**.
   - Else any `feat` commit → **feat**.
   - Else any `fix` commit → **fix**.
   - No qualifying commits → no bump (exits 1, "nothing to release").
4. Bump the *highest* qualifying level off the last tag, per `CONTRIBUTING.md` § Versioning:
   - `feat` bumps minor and resets patch; `fix` bumps patch.
   - **SemVer 0.x rule:** while the last tag's major version is 0, a breaking change bumps
     **minor** (`v0.y.z` → `v0.(y+1).0`), as commitizen's `major_version_zero` does. From major 1
     on, a breaking change bumps major and resets minor and patch.
   - With no tag, the base is `v0.0.0`, so a `feat` or breaking change gives `v0.1.0` and a `fix`
     gives `v0.0.1`. The owner moves to `v1.0.0` on purpose with `release.py --version v1.0.0`.
5. Print the next version (`vX.Y.Z`) to stdout, and on stderr the list of commits that drove the
   decision (hash + header), so the output is auditable, not a black box. `--quiet` leaves the
   list out.

It only computes and prints; nothing here creates a tag.

## Changelog: `scripts/changelog.py`, `CHANGELOG.md` and `changelog.d/`

`CHANGELOG.md` follows Keep a Changelog 1.1.0: a header, an empty `## [Unreleased]` heading and the
released sections. It changes only when a release folds fragments in. A change that needs an entry
adds one fragment file instead, so parallel task branches never conflict on `CHANGELOG.md`.

**Fragments.** `changelog.d/<id>.<category>.md`. `<id>` matches `[A-Za-z0-9][A-Za-z0-9_-]*` (a task
ID or a branch topic, no dots). `<category>` is one of `added`, `changed`, `deprecated`, `removed`,
`fixed`, `security`. The body holds only bullet lines (`- ` or `* `), indented continuation lines
and blank lines, because the whole file is folded into `CHANGELOG.md`. An indented line continues a
bullet only directly after that bullet or another continuation line; after a blank line, or before
the first bullet, it is invalid. So is any other line (an intro sentence, a heading, stray prose).
A fragment with no bullet is invalid, and so is a bullet that is empty or holds a case-insensitive
whole-word `todo` or `to-do`, `TBD`, `FIXME` or `<...>`. Fragments are decoded strictly as UTF-8 on
every path; a file that is not UTF-8 is a fragment problem, and one leading BOM is ignored. Every
file in `changelog.d/` except `README.md` must be a valid fragment; `README.md` is never checked,
folded or deleted. `changelog.py` is stdlib-only and loads `next_version.py` to classify commits,
so the check and the version bump use one definition of `feat`, `fix` and breaking.

**Subcommands.**

- `check <base> <tip>`: takes the non-merge commits in `<base>..<tip>`. Fails when one is `feat`,
  `fix` or breaking and no commit in the range adds a fragment (found per commit with
  `git log -M --diff-filter=A`, so a fragment added and later folded in by a release inside the
  range still counts). A path that exists at `<base>` never counts as added, and rename detection
  is on, so renaming a fragment, or deleting and re-adding it under the same name, does not count.
  Also fails on any invalid entry in `changelog.d/` at `<tip>`, read with
  `git ls-tree` and `git show`, never from the working tree.
- `preview [version]`: prints the section `assemble` would write, headed `## [X.Y.Z] - <today>`
  when a version is given and `## [Unreleased]` otherwise. Reads the working tree and changes
  nothing. With no fragments it prints a note to stderr and exits 0.
- `assemble <version> [--date YYYY-MM-DD]`: `--date` takes exactly `YYYY-MM-DD` and a real date.
  Writes `## [X.Y.Z] - date` under `## [Unreleased]`,
  grouped by category in Keep a Changelog order (Added, Changed, Deprecated, Removed, Fixed,
  Security), then deletes the folded fragments. It edits the working tree and stages nothing. It
  refuses when `[Unreleased]` is not empty (so nothing is stranded there), when the version already
  has a section, when a fragment is invalid, and when there are no fragments.

**Exit codes.** 0 success; 1 the check failed, a fragment is invalid (including one that is not
UTF-8), or the command refused to run, with the reason on stderr; 2 usage error (including a
malformed version or date), or git cannot resolve a revision, list the range or run at all; 3
internal error (a sibling script cannot be loaded, or an unexpected exception), reported as one
line on stderr. `version` accepts `X.Y.Z` or `vX.Y.Z`.

## Release: `scripts/release.py`

Explicit, human-invoked, never triggered by a hook. A release is a merge of `develop` into
`main`; it is the only thing that changes versions or `CHANGELOG.md`. `CONTRIBUTING.md` §
Versioning has the contributor-facing summary.

```
scripts/release.py                         # dry run
scripts/release.py --yes                   # release locally
scripts/release.py --yes --push            # release and push main, develop and the tag
scripts/release.py --yes --version v1.0.0  # override the computed version
```

**Refusals.** Nothing is changed and the exit code is 1 when any of these hold, checked in this
order. `git fetch origin` runs after the first check, and a failed fetch is itself a refusal:

1. the directory is not a git repository, the repository has no commits, or the starting branch
   is not `MAIN_BRANCH` or `DEVELOP_BRANCH`;
2. the working tree is dirty;
3. local `MAIN_BRANCH` or `DEVELOP_BRANCH` does not exist, has no `origin` counterpart, or is
   behind, ahead of or diverged from it;
4. `MAIN_BRANCH` or `DEVELOP_BRANCH` is checked out in another worktree;
5. `next_version.py` finds nothing to release;
6. with `--version`, the value is not higher than the highest `vX.Y.Z` tag in the repository;
7. the tag already exists;
8. `changelog.py preview` fails (an invalid fragment) or finds no fragment.

A `--version` value that is not canonical `vX.Y.Z` (a leading `v`, three numbers, no leading
zeros) is a usage error, exit 2, before any check. So is `--push` without `--yes`: exit 2 with a
usage message, nothing changed. `--push` does not imply `--yes`.

**Dry run.** Without `--yes` it makes the same checks, prints the version, the commits behind it
and the changelog section, and changes only the remote-tracking refs, through the fetch. It exits
0.

**With `--yes`:**

1. Started on `DEVELOP_BRANCH`: check out `MAIN_BRANCH` and merge `DEVELOP_BRANCH` with `--no-ff`
   (`chore(merge): merge develop into main`). Started on `MAIN_BRANCH` the step is skipped.
2. `changelog.py assemble <version>`, then stage `CHANGELOG.md` and `changelog.d` and commit
   `chore(release): vX.Y.Z` on `MAIN_BRANCH`.
3. Create the annotated tag `vX.Y.Z` (`Release vX.Y.Z`) on that commit, not on the merge.
4. Bring `DEVELOP_BRANCH` up to `MAIN_BRANCH`, chosen by `git merge-base --is-ancestor develop
   main`, not by the starting branch. An ancestor, as after a normal release, is a fast-forward
   (`--ff-only`), so both branches point at the same tagged commit. Otherwise, as after a hotfix,
   it is a `--no-ff` merge (`chore(merge): merge main into develop`). Either way `develop` loses
   the folded fragments and reaches the new tag.
5. Check out the starting branch again. With `--push`, run
   `git push --atomic origin main develop vX.Y.Z`: all three refs or none. Without it, print that
   command. A rejected push leaves the release complete locally, prints the retry command and
   exits 1. The message names both likely causes: another push won the race, or a local
   `pre-push` hook failed.

**Failure.** If a step fails after the first change (a merge conflict, a hook rejecting a commit),
the script stops, prints the failed command's stdout and stderr, each under its own label, then
the current state (branch, `HEAD`, both branch tips against their values before the run, whether
the tag exists, whether a merge is in progress, `git status --short`), then the exact commands to
finish by hand and the exact commands to undo the run, in order, and exits 1. When the step that
brings `develop` up to `main` stops on a conflicted changelog fragment, the finish list says to
resolve it as deleted with `git rm <path>`, because `main` already folded it and keeping it would
fold it twice at the next release.
It never runs `git reset`, a force push or a retry. The undo list may contain `git reset --hard`
and `git branch -f`, which are for a human to run (`CLAUDE.md` § "Ask first").

**Hotfix.** `gitflow.sh hotfix finish` merges into `MAIN_BRANCH` and back into `DEVELOP_BRANCH`
without pushing. Push both branches, then check out `MAIN_BRANCH` and run `release.py --yes`. The
local branch must equal `origin`, so an unpushed hotfix is refused. Step 1 is skipped, and step 4
is a back-merge because `develop` has diverged. The release is an "Ask first" item, so the
owner runs it or asks for it.

**Branch protection.** A repository with protection on `main` or `develop` must allow the release
push, or the owner releases through pull requests. `init_project.py`'s checklist says so.

`hatch-vcs`'s derived version is computed at build time and `uv sync` will not rebuild it just
because a new tag now exists — after cutting a release, run
`uv sync --reinstall-package <package>` (or any change that forces a rebuild) if you need the
installed package's `__version__`/metadata to reflect the new tag immediately.

**Generated projects.** `init_project.py` replaces `CHANGELOG.md` with the empty header and
`[Unreleased]` and removes every fragment, keeping `changelog.d/README.md`. It does not delete tags.
A repository created with GitHub's "Use this template" has none.

## Gitflow helper: `scripts/gitflow.sh`

Thin wrapper around exactly the branch/worktree operations `CONTRIBUTING.md` § Branching already
documents by hand, so they're one command instead of a multi-line sequence to get right every time:

```bash
scripts/gitflow.sh feature start <topic>   # worktree ../<repo>-feat-<topic>, branch feat/<topic> from develop
scripts/gitflow.sh feature finish <topic>  # merge feat/<topic> into develop, remove the worktree
scripts/gitflow.sh bugfix start|finish <topic>   # same, bugfix/<topic>
scripts/gitflow.sh hotfix start <topic>    # worktree ../<repo>-hotfix-<topic>, branch hotfix/<topic> from main
scripts/gitflow.sh hotfix finish <topic>   # merge into main, back-merge main into develop, remove worktree
                                            # (pushes and tags nothing; prints the next steps)
```

`finish` subcommands refuse to finish if the changelog check fails on the branch or the gate fails
after a merge. The gate is `scripts/gate.sh --if-needed HEAD` and runs after each merge `finish`
makes: the merge into the base branch and, for a hotfix, the back-merge into `develop`. It skips the
full gate when that code already has a gate record (the verifier's run, when the merge changed no
code) and runs it otherwise. On red, `finish` runs `git reset --merge ORIG_HEAD` for each merge it
made in this run (a hotfix back-merge first, then the merge into `main` from the commit saved before
it, since the back-merge replaced `ORIG_HEAD`) and stops. Nothing has been pushed, and the branch
and its worktree are kept. There is no gate before the merge. Neither check is bypassable through
the gitflow helper. The changelog check is
`changelog.py check <merge base> <branch>`, where the merge base is with `origin/<base>` when that
ref exists and with the local base branch otherwise. `finish` runs `git fetch origin <base>` first
so that ref is current; when the fetch fails it prints a warning and uses the local base branch.
The check runs first, and it stops on every failure, including a range it cannot list. Only exit
status 1 prints the advice to add a fragment; any other status stops with
`changelog check failed (exit N) on <branch>`. `finish` for a hotfix ends by printing: push `main`
and `develop`, then check out `main` and run `scripts/release.py --yes`, which is the owner's
step.

`finish` writes the merge commit with `merge_message` (in `scripts/lib/common.sh`):
`chore(merge): merge task NNNN into <base>` for a `<type>/T-NNNN-<slug>` branch, otherwise
`chore(merge): merge <branch> into <base>`; the hotfix back-merge uses the second form. The
task form is what `.agents/tasks/scripts/report.py` looks up to find a task's merge commit.

## How this composes with the verify/resolve workflow

`CONTRIBUTING.md` § Agent verify/resolve workflow has one independent verification per change, of
the finished branch, and none per commit. The executor iterates with `scripts/gate.sh --fast`,
`scripts/autofix.sh` and targeted tests, and commits freely. The verifier runs `scripts/gate.sh`
in full, so its run is the canonical one and writes the gate record that the post-merge check,
`gitflow.sh finish` and the pushes to `develop` and `main` reuse. A task's report names the record
in its verify line, `passed (commit <hash>; gate <record-key>; <counts>)`. `CLAUDE.md`'s rule that
verification must come from "an independent agent invocation (fresh context)" is unaffected: the
script makes that invocation's job mechanical, it doesn't replace the independence requirement.

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
