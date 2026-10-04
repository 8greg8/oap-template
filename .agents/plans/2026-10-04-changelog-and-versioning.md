# Plan: changelog and release versioning for the template

Status: accepted except D8 (first release version), which is open. Tasks T-0022 to T-0026 are
filed once D8 is settled.

**Owner decisions (2026-10-04, session instructions):**
- "accept the changelog plan as recommended": D1 to D7 below.
- "lets make release and versioning only when we merge develop into main": versions and the
  changelog change only at a release, which merges `develop` into `main`. The earlier request for
  a bump at every merge into `develop` is withdrawn.

These are the owner's written approval for the "Ask first" and breaking-change items under
§ Approvals.

## Goal

Every project created from this template keeps a human-written changelog in the Keep a Changelog
format and cannot push a versioned change without a changelog entry. One release command merges
`develop` into `main`, writes the changelog section, tags `vX.Y.Z` and brings `develop` up to
date. The source of the practice is `8greg8/sistat-mcp` (`develop` at `20ae53d`).

## What sistat-mcp does

| Part | Mechanism |
|---|---|
| `CHANGELOG.md` | Keep a Changelog 1.1.0 with an `## [Unreleased]` section; categories Added, Changed, Fixed |
| `scripts/bump.sh` (`pnpm run bump major\|minor\|patch`) | Bumps `version` in `package.json`, refreshes `pnpm-lock.yaml`, appends a placeholder bullet under `[Unreleased]` |
| `.husky/pre-commit` | Blocks a commit that stages any non-exempt file unless `package.json` and `CHANGELOG.md` are staged too; an exempt-path regex covers top-level docs, config and CI files |
| `CLAUDE.md`, `AGENTS.md` | "Pre-commit Release Gate": agents bump and write the entry before every commit |
| Release | By hand: move `[Unreleased]` items to `## [X.Y.Z] - date`, tag `vX.Y.Z`; `publish.yml` on the tag publishes to npm and creates a GitHub Release |

What carries over:
- the Keep a Changelog file;
- hand-written entries;
- a hook that makes skipping the entry impossible;
- agent rules that name the step;
- a release that turns pending entries into a dated section and a tag.

What does not fit this template:

1. **Version in a file, bumped per commit.** `package.json` is at 0.10.6 while the last released
   section is 0.10.0, so the file drifts from releases. This template takes the version from git
   tags (`hatch-vcs`) and computes it from commit types (`scripts/next_version.py`).
2. **One shared file edited by every change.** Here task branches run in parallel
   (`backlog.py ready --parallel N`, `touches`). Each would edit the same `[Unreleased]`
   heading, so merges into `develop` would conflict on `CHANGELOG.md`.
3. **Bump level by hand.** `docs:` and `chore:` bump patch, which disagrees with Conventional
   Commits and this template's `CONTRIBUTING.md` § Versioning.
4. **Presence check only.** The hook does not check that the placeholder was replaced.
5. **npm-only tooling.** `bump.sh` needs `node` and `pnpm`; `scripts/` here is stdlib Python.

## Design

### Changelog fragments

A change adds `changelog.d/<id>.<category>.md` with one or more bullet lines.
- `<id>` is the task ID (`T-0023`) or the branch topic.
- `<category>` is one of `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`.

Fragments never conflict, and a task's `touches` names its own fragment, never `CHANGELOG.md`.
`CHANGELOG.md` keeps the Keep a Changelog header, an empty `## [Unreleased]` heading and the
released sections. It changes only at a release. `assemble` refuses to run when `[Unreleased]`
is not empty, so nothing is ever stranded there.

### `scripts/changelog.py` (stdlib only)

- `check <base> <tip>`: looks at the non-merge commits in `<base>..<tip>`, classified with the
  same regex and rules as `next_version.py` (merges excluded). It fails when one of them is
  `feat`, `fix` or breaking and no commit in the range adds a file under `changelog.d/`
  (per commit, `git log --diff-filter=A`, so fragments added and later folded in by a release in
  the same range still count). It also validates every fragment present at `<tip>`: name,
  category, at least one bullet, no placeholder text.
- `preview`: prints the section the next release would write.
- `assemble <version> [--date YYYY-MM-DD]`: writes `## [X.Y.Z] - date` under `[Unreleased]`,
  groups the fragments by category in Keep a Changelog order, then deletes the fragments.

### Fragment check on push

`.husky/pre-push` runs `changelog.py check` for each pushed ref before the gate:
- `main` and `develop`: `<remote_sha>..<local_sha>`.
- Any other branch, new or not: from its merge base with `origin/develop` (`origin/main` for
  `hotfix/*`) to the tip. A fix round that adds only `fix` commits to a branch that already has
  its fragment therefore passes.
- `refs/tags/*` and deleted refs are skipped, as are `.agents/`-only pushes (the current skip).

A release push needs no special case: the range on `main` contains the released commits and the
commits that added their fragments, and the range on `develop` holds only the merge and the
release commit. `gitflow.sh finish` runs the same branch check before it merges. Only `feat`, `fix` and breaking changes need an entry.

### Release: `scripts/release.py`

Run by a human on a clean `develop` (or on `main` after `gitflow.sh hotfix finish`).

- Without `--yes`, it changes nothing and prints:
  - the version (`next_version.py`);
  - the commits behind it;
  - the changelog section.
- With `--yes`:
  1. From `develop`: check out `main` and merge `develop` with `--no-ff`
     (`chore(merge): merge develop into main`). From `main` after a hotfix this step is
     skipped.
  2. Run `changelog.py assemble <version>` and commit `chore(release): vX.Y.Z` on `main`.
  3. Create the annotated tag `vX.Y.Z` on that commit.
  4. Bring `develop` up to `main`. After a normal release `develop` is an ancestor of `main`,
     so this is a fast-forward and the two branches point at the same tagged commit. After a
     hotfix, `develop` has diverged, so it is a `--no-ff` back-merge
     (`chore(merge): merge main into develop`). Either way `develop` loses the folded fragments
     and can reach the new tag, so the next release does not fold them again.
- `--version vX.Y.Z` overrides the computed version, for a deliberate jump such as `v1.0.0`;
  it refuses a version that is not higher than the latest tag.
- With `--push`: `git push --atomic origin main develop vX.Y.Z`. All three refs land together or
  none does.
- It runs `git fetch origin` first and refuses to run when:
  - the working tree is dirty;
  - local `main` or `develop` differs from `origin` (behind, ahead or diverged);
  - `main` is checked out in another worktree;
  - `next_version.py` finds nothing to release.

`gitflow.sh hotfix finish` keeps merging into `main` and back into `develop`. Its closing
message changes to: check out `main` and run `scripts/release.py --yes`.

A repository with branch protection on `main` or `develop` must allow the release push, or the
owner runs the release through pull requests instead. The documentation says so.

Tagging stays a deliberate human step, as `CLAUDE.md` "Ask first" requires. `release.py` is the
"tagging step defined in `CONTRIBUTING.md`" that rule refers to.

### Agent rules

- `CONTRIBUTING.md`:
  - § Versioning: fragments, the release command and what it does to both branches; tags sit on
    the `chore(release)` commit on `main`, not on the merge;
  - § branching model: `main` accepts the `chore(release)` commit from `release.py`; `develop`
    accepts the release fast-forward or back-merge from `main`.
- `PYTHON_CONVENTIONS.md`: the "build and publish via git tags" lines point to `release.py`.
- `CLAUDE.md`: a task whose change is `feat`, `fix` or breaking adds its fragment and lists it
  in `touches`. Releases stay a human step; § Merge authority is unchanged.
- `.agents/README.md`: the verifier checks the fragment exists and describes the change.

### Generated projects

`init_project.py` replaces `CHANGELOG.md` with the empty header and `[Unreleased]` and removes
every fragment. `changelog.d/README.md` stays and must not name the template. A repository
created with GitHub's "Use this template" has no tags; `init_project.py` does not delete tags in
a clone that has them.

## Owner decisions

Accepted 2026-10-04:
- **D1:** changelog fragments assembled at release.
- **D2:** enforcement in the pre-push range check and `gitflow.sh finish`.
- **D3:** only `feat`, `fix` and breaking changes need an entry.
- **D4:** git tags are the only version source.
- **D5:** the release, a merge of `develop` into `main`, assembles the changelog, commits it on
  `main` and tags it. Releases stay manual.
- **D6:** the template's first changelog gets one hand-written summary of the template as it
  stands, shipped as the fragment `changelog.d/template.added.md` (so `[Unreleased]` stays
  empty).
- **D7:** a GitHub Release workflow stays out of scope.

Open:
- **D8. First release version.** The repository has no tags, so `next_version.py` starts from
  `v0.0.0`. T-0023 and T-0024 are breaking, which bumps major, so the first release would be
  `v1.0.0`. Recommended: adopt the SemVer 0.x convention. While the major version is 0, a
  breaking change bumps minor and a `feat` or `fix` bumps patch, so the first release is
  `v0.1.0` and the template stays pre-1.0 until the owner deliberately cuts `v1.0.0` with
  `release.py --version`. The alternatives are to accept `v1.0.0`, or to keep today's rules and
  add only the `--version` override.

## Approvals

- **Ask first:** T-0022, T-0023 and T-0024 change `scripts/`; T-0026 changes
  `scripts/README.md`.
- **Breaking change:**
  - T-0023 makes the pre-push hook reject a versioned push without a fragment;
  - T-0024 changes `release.py`'s behavior (it now runs from `develop` and merges, commits and
    moves `develop`) and the branching rules.
  - `CLAUDE.md` names hook behavior, script behavior and the branching rules as breaking
    contracts.
  - T-0026 writes down the branching and versioning rules T-0024 implements. It is covered by
    the same approval; its own commits are `docs` and carry no breaking marker.
- The owner decisions above are the written approval the orchestrator cites when merging these
  tasks.

## Tasks

Each `feat` or breaking task adds its own fragment and lists it in `touches`.

1. **T-0022: Add `scripts/changelog.py`, `CHANGELOG.md` and `changelog.d/`** (feat).
   - Touches: `scripts/changelog.py`, `tests/test_changelog.py`, `CHANGELOG.md`,
     `changelog.d/README.md`, `changelog.d/template.added.md`, `changelog.d/T-0022.added.md`.
2. **T-0023: Require a changelog fragment on push and at finish** (feat, breaking). Depends on
   T-0022.
   - Touches: `.husky/pre-push`, `scripts/gitflow.sh`, `tests/test_hooks.py`,
     `tests/test_gitflow.py`, `changelog.d/T-0023.changed.md`.
3. **T-0024: Release from `develop` into `main` with the changelog** (feat, breaking). Depends on
   T-0023.
   - Touches: `scripts/release.py`, `scripts/next_version.py` (D8), `scripts/gitflow.sh` (hotfix
     message), `tests/test_release.py`, `tests/test_next_version.py`, `tests/test_gitflow.py`,
     `changelog.d/T-0024.changed.md`.
   - Scope includes the refusals listed under § Release and their tests.
4. **T-0025: Generated projects start with an empty changelog** (feat). Depends on T-0022.
   - Touches: `init_project.py`, `tests/test_init_project.py`, `changelog.d/T-0025.added.md`.
   - Scope: the new lines in the dry-run change list; the generated project names no template.
5. **T-0026: Document the changelog and release workflow** (docs). Depends on T-0024.
   - Touches: `CONTRIBUTING.md`, `CLAUDE.md`, `PYTHON_CONVENTIONS.md`, `DEV_TOOLING_SPEC.md`,
     `scripts/README.md`, `.agents/README.md`, `.agents/tasks/templates/task.md`.

T-0025 can run in parallel with T-0023 and T-0024; their `touches` do not overlap.

## Risks

- **Wrong commit type.** A change typed `chore` that should be `feat` gets no fragment and no
  version bump. The verifier's commit-type check is the guard; it flagged this case in T-0021.
- **Release from a stale clone.** `release.py` refuses when `main` or `develop` is behind
  `origin`, and the atomic push rejects a release that raced another push.
- **A forgotten hotfix release.** Until `release.py` runs on `main`, the hotfix sits on `main`
  without a tag or changelog section. `gitflow.sh hotfix finish` reminds the user, as today.
