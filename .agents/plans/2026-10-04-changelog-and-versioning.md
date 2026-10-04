# Plan: changelog and version bumping for the template

Status: D1 to D7 accepted as recommended. D8 added by the owner; its details D8a to D8c are
open. No tasks are filed yet.

**Owner decisions (2026-10-04, session instruction):** "accept the changelog plan as
recommended. What I would like to add is to bump version on every merge into develop branch,
since this is the main branch we are working on." D1 to D7 are accepted as recommended. D8
replaces D5's release-time bump with a bump at every merge into `develop`. Once D8a to D8c are
settled, this is the owner's written approval for the "Ask first" and breaking-change items
under § Approvals.

## Goal

Every project created from this template keeps a human-written changelog in the Keep a Changelog
format, and cannot push a versioned change without a changelog entry. Every merge into `develop`
that carries a versioned change produces a new version: a changelog section and a `vX.Y.Z` tag.
The source of the practice is `8greg8/sistat-mcp` (`develop` at `20ae53d`).

## What sistat-mcp does

| Part | Mechanism |
|---|---|
| `CHANGELOG.md` | Keep a Changelog 1.1.0 with an `## [Unreleased]` section; categories Added, Changed, Fixed |
| `scripts/bump.sh` (`pnpm run bump major\|minor\|patch`) | Bumps `version` in `package.json`, refreshes `pnpm-lock.yaml`, appends a placeholder bullet under `[Unreleased]` |
| `.husky/pre-commit` | Blocks a commit that stages any non-exempt file unless `package.json` and `CHANGELOG.md` are staged too; an exempt-path regex covers docs, config and CI files |
| `CLAUDE.md`, `AGENTS.md` | "Pre-commit Release Gate": agents bump and write the entry before every commit |
| Release | By hand: move `[Unreleased]` items to `## [X.Y.Z] - date`, tag `vX.Y.Z`; `publish.yml` on the tag publishes to npm and creates a GitHub Release |

What carries over:
- the Keep a Changelog file with `[Unreleased]`;
- hand-written entries;
- a hook that makes skipping a step impossible;
- agent rules that name the step;
- a frequent version bump.

What does not fit this template:

1. **Version in a file.** `package.json` is at 0.10.6 while the last released section is
   0.10.0, so the file drifts from releases. This template takes the version from git tags
   (`hatch-vcs`) and computes it from commit types (`scripts/next_version.py`). A second version
   source would compete with it.
2. **One shared file edited by every change.** Here several task branches run in parallel
   (`backlog.py ready --parallel N`, `touches`). Each would edit the same `[Unreleased]`
   heading, so merges into `develop` would conflict on `CHANGELOG.md`.
3. **Bump level by hand, and on every commit.** `docs:` and `chore:` bump patch, which disagrees
   with Conventional Commits and this template's `CONTRIBUTING.md` § Versioning.
4. **Presence check only.** The hook does not check that the placeholder was replaced.
5. **npm-only tooling.** `bump.sh` needs `node` and `pnpm`; `scripts/` here is stdlib Python.

## Design

### Changelog fragments (D1)

A change adds `changelog.d/<id>.<category>.md` with one or more bullet lines.
- `<id>` is the task ID (`T-0023`) or the branch topic.
- `<category>` is one of `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`.

Fragments never conflict, and a task's `touches` names only its own fragment. `CHANGELOG.md`
keeps the Keep a Changelog header, an empty `## [Unreleased]` heading and the version sections.
Nobody edits it by hand.

### `scripts/changelog.py` (stdlib only)

- `check <range>`: fails when the range holds a non-merge `feat`, `fix` or breaking commit
  (classified exactly as `next_version.py` does) and no commit in the range adds a fragment.
  It also fails on a fragment with a bad name or category, no bullet, or placeholder text.
  Fragments added and later folded into `CHANGELOG.md` inside the same range count as added.
- `preview`: prints the section the next bump would write.
- `assemble <version> [--date YYYY-MM-DD]`: writes `## [X.Y.Z] - date` under `[Unreleased]`,
  groups the fragments by category in Keep a Changelog order, then deletes the fragments.

### Fragment check on push (D2, D3)

`.husky/pre-push` runs `changelog.py check` on each pushed range before the gate. It keeps its
current skips (deleted refs, `.agents/`-only pushes). A new remote branch is checked against its
merge base with `develop`. `gitflow.sh finish` runs the same check before it merges. Only
`feat`, `fix` and breaking changes need an entry.

### Version bump on every merge into `develop` (D8)

`scripts/bump.py` (new, stdlib only) runs on `develop` right after a merge:

1. Computes the next version with `next_version.py`. If the merged commits hold no `feat`,
   `fix` or breaking change, it does nothing (see D8a).
2. Runs `changelog.py assemble <version>` and commits `chore(release): vX.Y.Z` on `develop`.
3. Creates the annotated tag `vX.Y.Z` on that commit.
4. With `--push`, runs `git push --atomic origin develop vX.Y.Z`, so the branch and tag land
   together or not at all. If the push is rejected because `develop` moved, it deletes the local
   tag and stops, and the merger pulls and repeats.

Who calls it:
- `gitflow.sh finish` calls it without `--push` after every merge into `develop`. `finish`
  does not push today; `bump.py` prints the atomic push command for the merger.
- The orchestrator's merge step in `.agents/README.md` calls `bump.py --push` in place of its
  plain push: merge, run the gate on `develop`, then bump and push.

A Husky `post-merge` hook is not used. It also fires on `git pull` into `develop`, which would
bump on every pull.

**Husky guard:** `.husky/pre-push` refuses a push of `develop` whose tip is not tagged when the
commits since the highest reachable `vX.Y.Z` tag include a `feat`, `fix` or breaking change. An
un-bumped merge therefore cannot reach `origin`. This is the template's version of sistat-mcp's
"commit blocked until bumped" hook.

**Version lookup.** `next_version.py` uses the highest `vX.Y.Z` tag reachable from `HEAD`, not
the nearest (`git describe`, today). A hotfix tag on `main` that is back-merged into `develop`
must not lower `develop`'s base version.

**`main` (D8b).** `main` catches up to a tagged `develop` commit by fast-forward
(`scripts/release.py`, reworked from "tag `main`" to "fast-forward `main` to the latest
`develop` tag"). `main` then carries the same commit and version as `develop`. A fast-forward
is always possible, because every hotfix is back-merged into `develop`, so `main` stays an
ancestor of `develop`.

**Hotfixes (D8c).** A hotfix merges into `main`, gets a patch tag there with `bump.py`, and is
back-merged into `develop`. That back-merge brings a `fix` commit not reachable from
`develop`'s tag, so `bump.py` bumps `develop` too.

### Agent rules

- `CONTRIBUTING.md` § Versioning: fragments, the bump at each merge into `develop`, promotion of
  `main`, hotfixes.
- `CLAUDE.md`:
  - a task whose change is `feat`, `fix` or breaking adds its fragment and lists it in `touches`;
  - the "Ask first" item on release tags and § Merge authority's "does not extend to release
    tags" now exclude the version tag `bump.py` creates in the defined merge step;
  - promoting `main` stays a human step.
- `.agents/README.md`:
  - the merge step runs `bump.py --push`;
  - the verifier checks that the fragment exists and describes the change.

### Generated projects

`init_project.py` replaces `CHANGELOG.md` with the empty header and `[Unreleased]`, and removes
every fragment. A new project starts with no versions and no tags.

## Owner decisions

Accepted (2026-10-04):
- **D1:** changelog fragments assembled at bump time.
- **D2:** enforcement in the pre-push range check and `gitflow.sh finish`.
- **D3:** only `feat`, `fix` and breaking changes need an entry.
- **D4:** git tags are the only version source.
- **D5:** superseded by D8. The release step no longer writes the changelog; `bump.py` does it
  at each merge into `develop`.
- **D6:** `CHANGELOG.md` starts with one hand-written `[Unreleased]` summary of the template as
  it stands. The first bump after this work lands produces `v0.1.0`.
- **D7:** a GitHub Release workflow stays out of scope.

Added by the owner:
- **D8:** bump the version on every merge into `develop`.

Open:
- **D8a. Merges without a versioned change.** Recommended: a merge with only `docs`, `chore`,
  `test`, `refactor`, `style`, `ci` or `build` commits gets no new version, matching D3 and
  Conventional Commits. The alternative is a patch bump on every merge, as sistat-mcp does for
  every commit.
- **D8b. Promoting `main`.** Recommended: a fast-forward to the latest `develop` tag, run by a
  human with `release.py`. The alternative is to drop `main` from the flow.
- **D8c. Hotfixes.** Recommended: keep the hotfix flow, with a patch tag on `main` and a bump on
  `develop` at the back-merge. The alternative is to fix on `develop` and promote `main`, which
  also ships everything else that is on `develop`.

## Approvals this plan needs

- **Ask first:**
  - tasks 1, 2, 3 and 4 change `scripts/`;
  - task 3 makes merges create tags, which `CLAUDE.md` keeps for a human today.
- **Breaking change:**
  - task 2 rejects pushes without a fragment;
  - task 3 changes the merge rules (a bump at every merge into `develop`, a push guard on
    `develop`);
  - task 4 changes how `main` is released.
  `CLAUDE.md` names hook behavior and the branching and merge rules as breaking contracts.
- The owner decisions recorded above are the written approval the orchestrator cites when
  merging these tasks, once D8a to D8c are settled.

## Tasks (filed after D8a to D8c are settled)

1. **Add `scripts/changelog.py`, `CHANGELOG.md` and `changelog.d/`** (feat).
   - Touches: `scripts/changelog.py`, `tests/test_changelog.py`, `CHANGELOG.md`,
     `changelog.d/README.md`.
2. **Require a fragment on push and at finish** (feat, breaking). Depends on 1.
   - Touches: `.husky/pre-push`, `scripts/gitflow.sh`, `tests/test_hooks.py`,
     `tests/test_gitflow.py`.
3. **Bump the version at every merge into `develop`** (feat, breaking). Depends on 2.
   - Touches: `scripts/bump.py`, `scripts/next_version.py`, `scripts/gitflow.sh`,
     `.husky/pre-push`, `tests/test_bump.py`, `tests/test_next_version.py`,
     `tests/test_hooks.py`, `tests/test_gitflow.py`.
   - Scope: `bump.py` with the atomic push; the highest-tag lookup; the `develop` push guard;
     `gitflow.sh finish` calling `bump.py` for merges into `develop`, including hotfix
     back-merges.
4. **Promote `main` by fast-forward** (feat, breaking). Depends on 3.
   - Touches: `scripts/release.py`, `tests/test_release.py`.
5. **Generated projects start with an empty changelog** (feat). Depends on 1.
   - Touches: `init_project.py`, `tests/test_init_project.py`.
6. **Document the changelog and versioning workflow** (docs). Depends on 3 and 4.
   - Touches: `CONTRIBUTING.md`, `CLAUDE.md`, `DEV_TOOLING_SPEC.md`, `scripts/README.md`,
     `.agents/README.md`, `.agents/tasks/templates/task.md`.

Task 5 can run in parallel with tasks 2 to 4. Tasks 2 and 3 both touch `.husky/pre-push` and
`scripts/gitflow.sh`, so they run in sequence. Once task 1 has landed, each `feat` or breaking
task adds its own fragment.

Until task 6 lands, the orchestrator runs `bump.py --push` after each merge by hand, as soon as
task 3 has landed.

## Risks

- **Two mergers at once.** Both compute the same next version. The atomic push lets only one
  land; the other deletes its local tag, pulls and bumps again.
- **Wrong commit type.** A change typed `chore` that should be `feat` gets no fragment and no
  bump. The verifier's commit-type check is the guard; it flagged this case in T-0021.
- **A tag pushed without its branch, or the reverse.** Prevented by `--atomic`. A red gate after
  the push is handled as today: revert the merge as a new commit, which `bump.py` then versions
  as needed.
- **History of many tags.** Every versioned merge creates a tag. That is the intended effect of
  D8.
