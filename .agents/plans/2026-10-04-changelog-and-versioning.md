# Plan: changelog and version bumping for the template

Status: proposed. Owner decisions D1 to D7 below are open. No tasks are filed yet.

## Goal

Every project created from this template keeps a human-written changelog in the Keep a Changelog
format, is blocked from pushing a versioned change without a changelog entry, and gets its
release section and version from one command at release time. The source of the practice is
`8greg8/sistat-mcp` (`develop` at `20ae53d`).

## What sistat-mcp does

| Part | Mechanism |
|---|---|
| `CHANGELOG.md` | Keep a Changelog 1.1.0 with an `## [Unreleased]` section; categories Added, Changed, Fixed |
| `scripts/bump.sh` (`pnpm run bump major\|minor\|patch`) | Bumps `version` in `package.json`, refreshes `pnpm-lock.yaml`, appends a placeholder bullet under `[Unreleased]` |
| `.husky/pre-commit` | Blocks a commit that stages any non-exempt file unless `package.json` and `CHANGELOG.md` are staged too; an exempt-path regex covers docs, config and CI files |
| `CLAUDE.md`, `AGENTS.md` | "Pre-commit Release Gate": agents bump and write the entry before every commit |
| Release | By hand: move `[Unreleased]` items to `## [X.Y.Z] - date`, tag `vX.Y.Z`; `publish.yml` on the tag publishes to npm and creates a GitHub Release |

What works and should carry over: the Keep a Changelog file with `[Unreleased]`, hand-written
entries, a hook that makes skipping the entry impossible, agent rules that name the step, and a
release step that turns `[Unreleased]` into a dated section.

What does not fit this template:

1. **Per-commit version bump.** `package.json` is at 0.10.6 while the last released section is
   0.10.0. Every commit bumps, so the file version drifts from releases. This template already
   takes the version from git tags (`hatch-vcs`, `pyproject.toml`) and computes the next one
   from commit types (`scripts/next_version.py`). A second version source would compete with it.
2. **One shared file edited by every change.** Here several task branches run in parallel
   (`backlog.py ready --parallel N`, `touches`). Each would append under the same
   `[Unreleased]` heading, so merges into `develop` would conflict on `CHANGELOG.md`, and
   `touches` could never keep two feature tasks apart.
3. **Bump level by hand.** `pnpm run bump patch` for `docs:` and `chore:` disagrees with
   Conventional Commits, where only `feat`, `fix` and breaking changes move the version. This
   template's `CONTRIBUTING.md` § Versioning already follows the latter.
4. **Presence check only.** The hook checks that the files are staged, not that the placeholder
   ("update this line with a descriptive entry") was replaced.
5. **npm-only tooling.** `bump.sh` needs `node` and `pnpm`; `scripts/` here is stdlib Python.

## Proposed design

**Changelog fragments.** A change adds one small file, `changelog.d/<id>.<category>.md`, with
one or more bullet lines. `<id>` is the task ID (`T-0023`) or the branch topic; `<category>` is
one of Keep a Changelog's `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`.
Fragments never conflict, and each task's `touches` names only its own fragment.
`CHANGELOG.md` keeps the Keep a Changelog header, an `## [Unreleased]` heading and the released
sections. Nobody edits it by hand between releases.

**`scripts/changelog.py`** (stdlib only, like the rest of `scripts/`):
- `check <range>`: fails when the range holds a non-merge `feat`, `fix` or breaking commit
  (classified exactly as `next_version.py` does) but adds no fragment. Also fails on a fragment
  with a bad name or category, no bullet, or placeholder text.
- `preview`: prints the section the next release would write.
- `assemble <version> [--date YYYY-MM-DD]`: writes `## [X.Y.Z] - date` under `[Unreleased]`
  with the fragments grouped by category in Keep a Changelog order, then deletes the fragments.

**Enforcement in the pre-push hook**, not pre-commit. `.husky/pre-push` already sees the pushed
range per ref. It runs `changelog.py check` on that range before the gate, with the same skips
it has today (deleted refs, `.agents/`-only pushes). A task branch's commits are judged
together, so an entry is needed once per change, not once per commit. A new remote branch is
checked against its merge base with `develop`. `gitflow.sh finish` runs the same check before it
merges.

**Version bump at release, not per commit.** The version stays in git tags only.
`scripts/release.py` on `main`:
1. computes the version with `next_version.py`, as today;
2. runs `changelog.py assemble` and commits `chore(release): vX.Y.Z` on `main`;
3. creates the annotated tag.

The dry run shows the version and the changelog section and changes nothing. Tagging stays a
deliberate, manual step, as `CLAUDE.md` "Ask first" requires.

**Agent rules.** `CONTRIBUTING.md` § Versioning and a short rule in `CLAUDE.md`'s task section
say: a task whose change is `feat`, `fix` or breaking adds its fragment and names it in
`touches`. The verifier in `.agents/README.md` § "Verify, resolve, merge" checks the fragment
exists and describes the change.

**Generated projects.** `init_project.py` replaces `CHANGELOG.md` with the empty header and
`[Unreleased]`, and removes every fragment, so a new project starts with no history.

## Owner decisions

- **D1. Changelog mechanism.** Fragments assembled at release (recommended). The alternatives
  are one `CHANGELOG.md` edited by every change, as in sistat-mcp, which conflicts under
  parallel tasks, or a changelog generated from commit subjects only, which needs no extra file
  but gives weaker text.
- **D2. Where it is enforced.** The pre-push range check plus `gitflow.sh finish`
  (recommended). The alternative is pre-commit per commit, as in sistat-mcp.
- **D3. Which changes need an entry.** `feat`, `fix` and breaking changes, matching the version
  impact (recommended). The alternative is every non-exempt change, as in sistat-mcp.
- **D4. Version source.** Git tags only, with no version written to a file (recommended).
  `package.json` stays private tooling metadata without a meaningful version.
- **D5. Release step.** `release.py` assembles the changelog, commits it on `main` and tags
  (recommended). Tags stay manual.
- **D6. The template's own changelog.** Start `CHANGELOG.md` with one hand-written
  `[Unreleased]` summary of the template as it stands (recommended), or backfill entries from
  the `feat` and `fix` commits so far. After this work lands, the owner cuts `v0.1.0`.
- **D7. GitHub Releases.** Out of scope: the template has no CI. A later task can add a workflow
  that creates a GitHub Release from the tag's changelog section, as sistat-mcp's
  `publish.yml` does.

## Approvals this plan needs

- **Ask first.** Tasks 1, 2 and 4 change `scripts/` (`changelog.py`, `release.py`,
  `gitflow.sh`), which `CLAUDE.md` puts under "Ask first".
- **Breaking change.** Task 2 changes hook behavior: a push without a fragment is now rejected.
  `CLAUDE.md` names hook behavior as a breaking contract for downstream projects, so that task's
  commit is marked breaking.
- An owner acceptance of this plan, recorded here, is the written approval the orchestrator
  cites when merging those tasks.

## Tasks (filed after acceptance)

1. **Add `scripts/changelog.py`, `CHANGELOG.md` and `changelog.d/`** (feat).
   - Touches: `scripts/changelog.py`, `tests/test_changelog.py`, `CHANGELOG.md`,
     `changelog.d/README.md`.
   - Scope: the three subcommands, Keep a Changelog output, and fragment validation.
   - Tests: classification parity with `next_version.py`, assembly order, fragment deletion,
     and the placeholder and bad-name failures.
2. **Enforce fragments on push and at release** (feat, breaking). Depends on 1.
   - Touches: `.husky/pre-push`, `scripts/gitflow.sh`, `scripts/release.py`,
     `tests/test_hooks.py`, `tests/test_gitflow.py`, `tests/test_release.py`.
   - Scope: the pre-push check with the current skips, the `gitflow.sh finish` check, the
     `release.py` assemble, commit and tag sequence, and a dry run that shows the section.
3. **Generated projects start with an empty changelog** (feat). Depends on 1.
   - Touches: `init_project.py`, `tests/test_init_project.py`.
4. **Document the changelog workflow** (docs). Depends on 2.
   - Touches: `CONTRIBUTING.md`, `CLAUDE.md`, `DEV_TOOLING_SPEC.md`, `scripts/README.md`,
     `.agents/README.md`, `.agents/tasks/templates/task.md`.
   - Scope: the rule, the verifier check, the spec's former "no changelog generation" non-goal,
     and a "changelog fragment" line under the task template's Documentation required.

Tasks 2 and 3 can run in parallel. Each task that is itself `feat` or breaking adds its own
fragment once task 1 has landed, so the template's first changelog describes this work.

## Risks

- **Fragment forgotten on direct commits.** The pre-push check covers every push, not only task
  branches, so this is caught.
- **Wrong commit type.** A change typed `chore` or `docs` that should be `feat` slips past the
  check. The verifier's existing commit-type check is the guard. It already flagged this case
  in T-0021.
- **Tag without a pushed release commit.** `release.py` keeps the tag push explicit with
  `--push`; the release commit on `main` is pushed by the same command.
