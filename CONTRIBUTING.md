# Contributing

This document defines the process for contributing to this repo — branching, commits, versioning,
and the agent-driven verify/commit/merge workflow. For environment setup, commands, and code style,
see [`PYTHON_CONVENTIONS.md`](PYTHON_CONVENTIONS.md).

## Branching

[Gitflow](https://nvie.com/posts/a-successful-git-branching-model/), with two permanent branches
and short-lived branches on top:

- `main` — always reflects the latest released state and is release-ready. No direct commits —
  it accepts only merges from `develop` (a release) or `hotfix/*`, and the `chore(release): vX.Y.Z`
  commit that `scripts/release.py` writes on it. The release tag `vX.Y.Z` sits on that
  `chore(release)` commit, not on the merge before it. A hotfix merged into `main` stays untagged
  until `release.py` runs on `main` (see Versioning).
- `develop` — integration branch for ongoing work. Always in a working, checks-passing state, but
  not necessarily released. No direct commits — only merges from `feat/*` or `bugfix/*`, from a
  task branch `<type>/T-NNNN-<slug>` (whatever its Conventional Commits `type` prefix), and the
  back-merge from `hotfix/*`. It also accepts what `release.py` does to it: a fast-forward to
  `main` after a normal release, or a `--no-ff` merge of `main` after a hotfix release. The one
  exception to "no direct commits" is task filing, which commits and pushes the new task file
  straight to `develop` (§ Worktrees for agents).
- `feat/<topic>` — new functionality, non-breaking, branched from and merged into `develop`.
- `bugfix/<topic>` — bug fixes against `develop`, non-breaking, branched from and merged into `develop`.
- `hotfix/<topic>` — urgent fixes branched from `main`, merged into both `main` and `develop`.

### Worktrees for agents

Agents work in an isolated `git worktree` per branch, never directly in the primary checkout, so
multiple agents (or multiple concurrent tasks) can operate on different branches at once without
stashing or clobbering each other's state. `scripts/gitflow.sh` creates and finishes them:

```bash
# From the primary checkout
scripts/gitflow.sh feature start <topic>    # ../<repo>-feat-<topic>, branch feat/<topic> from develop
scripts/gitflow.sh bugfix  start <topic>    # branch bugfix/<topic> from develop
scripts/gitflow.sh hotfix  start <topic>    # branch hotfix/<topic> from main
```

`gitflow.sh` also supports `docs`, `chore` and `fix` task branches (`docs/T-0005-<slug>`,
`chore/T-0007-<slug>`), from `develop`, with the same worktree, hook and finish behavior:

```bash
scripts/gitflow.sh docs  start  T-NNNN-<slug>   # ../<repo>-docs-T-NNNN-<slug>, branch docs/T-NNNN-<slug>
scripts/gitflow.sh chore finish T-NNNN-<slug>
```

A branch of any other kind needs a hand-written command:
`git worktree add ../<repo>-<type>-<topic> --no-track -b <type>/T-NNNN-<slug> origin/develop`
after `git fetch`. `--no-track` stops the branch from inheriting `origin/develop` as its upstream,
which would make a bare `git push` fail with a branch-name mismatch. Push such a branch the first
time with `git push -u origin <branch>`; a bare `git push` works after that.

- Name worktree directories `<repo>-<branch-type>-<topic>` so concurrent worktrees are identifiable
  (`gitflow.sh` does this).
- An agent does all work (edits, checks, commits) inside its own worktree.
- `gitflow.sh start` symlinks the primary checkout's `node_modules` into the new worktree and runs
  `husky` there, so hooks work immediately. A worktree made any other way needs `npm ci` (or
  `npm install`) before its first commit.
- Remove the worktree and delete its local branch once the branch is merged, in both flows this
  repo uses. In the single-agent flow, `scripts/gitflow.sh <kind> finish <topic>` does this after
  merging (see § Agent verify/resolve workflow, step 6). In the batched orchestrator flow
  (`.agents/README.md`'s execution loop), the subagent that created the worktree is gone by the
  time the orchestrator merges, so whoever performs that merge also runs
  `git worktree remove <path>` and `git branch -d <branch>` as part of the same step. `git branch
  -d` refuses on an unmerged branch, so this is safe by construction.
- `develop` and `main` are never checked out in a secondary worktree, only in the primary
  checkout. A worktree that needs to inspect or advance either branch does so via `git fetch` +
  `git log origin/<branch>` (read) or `git push origin <local-branch>:<develop|main>` (advance),
  never a local checkout of the branch itself.
- **Exception: filing a task.** `task.py new` (see `.agents/README.md` and `CLAUDE.md` §
  "Working unit: the task") deliberately runs in the primary checkout on `develop`, not a
  worktree. It is the one piece of work in this workflow that must land on `develop`
  immediately so every other worktree can see it, rather than the isolated, branch-scoped work
  everything else in this section describes.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), written by the agent that
made the change — never left to a human to write up after the fact.

The commit **type and footer must match the version impact of the change**, which depends on both
what changed and which branch it's on:

| Branch type          | Typical change             | Commit form                                  | Version impact |
|-----------------------|-----------------------------|-----------------------------------------------|-----------------|
| `feat/<topic>`         | new non-breaking feature    | `feat(scope): summary`                        | minor           |
| `bugfix/<topic>`       | non-breaking fix            | `fix(scope): summary`                          | patch           |
| `hotfix/<topic>`       | urgent patch on `main`      | `fix(scope): summary`                          | patch           |
| `hotfix/<topic>`       | urgent breaking fix on `main` | `fix(scope)!: summary` + `BREAKING CHANGE:` footer | major (minor while the major version is 0) |
| any branch             | breaking change              | `<type>(scope)!: summary` + `BREAKING CHANGE:` footer | major (minor while the major version is 0) |

The impact column is the bump `scripts/release.py` makes at the next release; nothing is bumped
when a change merges. The 0.x rule is in § Versioning.

A `feat`, `fix` or breaking commit also needs a changelog fragment (§ Versioning). Other types
(`docs`, `chore`, `test`, `refactor`, and so on) drive no version and need none, so pick the type
by what the change does for users: a `chore` that should be a `feat` gets no fragment and no
release.

Rules the agent follows:

- Never write `feat:`/`fix:` without a scope if the change is isolated to one module or subpackage
  under `src/<repo_name>/` (e.g. `feat(recipes): ...`) — omit scope only for changes spanning
  several.
- A breaking change is marked **both** with `!` after the type/scope and a `BREAKING CHANGE:` footer
  explaining the break — the footer is what `hatch-vcs`/semver tooling keys off, the `!` is for
  human skimmability.
- Squash incidental fixup commits made during the verify/resolve loop (see below) into a single
  clean commit before merge — the merged history should have one commit per logical change, not one
  per lint fix.

### Merge commits

A task branch merges into `develop` with a merge commit whose header is
`chore(merge): merge task NNNN into develop`, where `NNNN` is the task ID's four digits (for
example, `chore(merge): merge task 0154 into develop`). Any other branch uses
`chore(merge): merge <branch> into <base>`. `scripts/gitflow.sh finish` writes both forms. The
usual attribution footers follow. Do not use git's default `Merge branch '…'` message or a
`Merge <branch>: <summary>` form.

### Accepted history

`scripts/commit_lint.py` runs in the `commit-msg` hook, so it checks new commits as they are
written. It does not scan existing history. A commit already in `main` or `develop` that fails
the lint rules is listed here and accepted as it is: never rewrite, amend, rebase or force-push
shared history to fix it. Add an entry only with the owner's decision, naming the commit hash and
the rule it fails.

Accepted commits: none.

## Versioning

Semantic versioning via git tags (`vX.Y.Z`), extracted by `hatch-vcs` (see
[`PYTHON_CONVENTIONS.md`](PYTHON_CONVENTIONS.md) for how packages consume this). Git tags are the
only version source; no file holds a version. A version and a changelog section come into being
only when a human runs `scripts/release.py`. Merging into `develop` bumps nothing.

### Changelog fragments

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). It holds the
header, an empty `## [Unreleased]` heading and the released sections, and changes only at a
release. Never edit it by hand. Each change that needs an entry adds its own fragment file instead,
so parallel branches never conflict on `CHANGELOG.md`. A release folds the fragments into a dated
section and deletes them. `changelog.d/README.md` has the short version of these rules.

- **When.** A `feat`, `fix` or breaking commit (`!` or a `BREAKING CHANGE:` footer) needs a
  fragment in the same branch. Commits are classified by the same code `next_version.py` uses.
  Merge commits are ignored, and other types need none.
- **Name.** `changelog.d/<id>.<category>.md`. `<id>` is the task ID (`T-0023`) or the branch topic:
  letters, digits, `-` and `_`, starting with a letter or digit, no dots. `<category>` is one of
  `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`, in lowercase. A change that
  needs two categories adds two files. Every file in `changelog.d/` except `README.md` must have
  this name; any other name fails the check.
- **Content.** Only bullet lines, indented continuation lines and blank lines. A bullet is a line
  starting with `- ` or `* `. An indented line continues a bullet only directly after that bullet
  or another continuation line; after a blank line, or before the first bullet, it fails. Any
  other line (an intro sentence, a heading, stray prose) fails too, because the whole file is
  folded into `CHANGELOG.md`. Write what changed for a user or maintainer, in one or two
  sentences. A fragment with no bullet fails. So does a placeholder bullet: empty text, a
  whole-word `todo` or `to-do`, `TBD`, `FIXME` or the literal `<...>`, in any letter case. The file
  must be valid UTF-8, and one leading byte order mark (BOM) is ignored; a file that is not UTF-8
  fails as a fragment problem.
- **Tasks.** A task whose change is `feat`, `fix` or breaking lists its fragment in `touches` and
  never lists `CHANGELOG.md`.
- **Preview.** `python scripts/changelog.py preview [vX.Y.Z]` prints the section a release would
  write and changes nothing.

`python scripts/changelog.py check <base> <tip>` is the check. It looks at the non-merge commits
in `<base>..<tip>` and fails when one is `feat`, `fix` or breaking and no commit in the range adds
a fragment. A commit adds a fragment when it adds the file, with rename detection on, and the
path does not exist at `<base>`, so renaming a fragment that exists at `<base>`, or deleting it and
adding it again under the same name, does not count. Each commit is inspected on its own, so a
fragment added and later folded in by a release inside the same range still counts. It also fails
on any invalid entry in `changelog.d/` at `<tip>`, which it reads from git, not from the working
tree. Exit status: 0 when the range passes; 1 when the check fails (a missing fragment, an invalid
fragment or one that is not UTF-8); 2 for a usage error, or when git cannot resolve the revisions
or list the range; 3 for an internal error (a sibling script cannot be loaded, or an unexpected
exception), reported as one line on stderr. `preview` and `assemble` use the same codes, and
`assemble --date` takes only `YYYY-MM-DD`.

The check runs in two places:

- **`pre-push`**, for each pushed branch, before the gate. The branch is taken from the remote ref
  being updated, never from the local ref name. The range is `<remote sha>..<local sha>` for `main`
  and `develop`; from the merge base with `<remote>/main` to the tip for `hotfix/*`; and from the
  merge base with `<remote>/develop` to the tip for any other branch, new or not. `<remote>` is the
  remote git passes to the hook (`origin` when the hook is run by hand), not always `origin`. A fix
  round that adds only `fix` commits to a branch that already has its fragment therefore passes. A
  rejected check rejects the push before the gate starts. The hook skips the check for a first
  push of `main` or `develop` (an all-zero remote sha, as in a new project's
  `git push -u origin main develop`), for deleted refs, for tags and other non-branch refs, and
  when every pushed commit changes only `.agents/` records. It also skips it, with a message, when
  the range cannot be listed: `changelog.py` exits 2, the merge base fails, or the remote-tracking
  ref is missing, as when git passes a URL instead of a remote name. The gate still runs in those
  cases. Exit 1 of `changelog.py` is a missing or invalid fragment and rejects the push with that
  explanation. Any other status (3 for an internal error, 127 for a missing `python3`, a signal)
  rejects the push with `pre-push: changelog check failed (exit N) for <remote_ref>`, with no claim
  that a fragment is missing.
- **`scripts/gitflow.sh <kind> finish`**, before the gate and the merge. The range is from the merge
  base with the base branch to the branch tip. `finish` first runs `git fetch origin <base>`, so
  the base is `origin/<base>` when that remote ref exists afterwards. When the fetch fails it
  prints a warning and uses the local base branch, as it does when there is no remote ref. Unlike
  the hook, `finish` stops on every failure, including a range it cannot list or a missing merge
  base. Only exit status 1 gets the advice to add `changelog.d/<id>.<category>.md`; any other
  status stops with `changelog check failed (exit N) on <branch>`.

### Version bump

`scripts/next_version.py` finds the last `vX.Y.Z` tag reachable from `HEAD` (`v0.0.0` when there is
none), classifies the commits since it, and bumps the highest level found:

- A breaking change bumps **major**, with the 0.x exception below.
- Else any `feat` bumps **minor**.
- Else only `fix` bumps **patch**.
- No such commit means nothing to release, and it exits 1.

**The 0.x rule.** While the last tag's major version is 0, a breaking change bumps **minor**, as
commitizen's `major_version_zero` does. A project stays on `0.y.z` until its owner moves to 1.0.0
on purpose. With no tag yet, a `feat` or a breaking change makes the first release `v0.1.0`, and
only `fix` commits make it `v0.0.1`. From major 1 on, a breaking change bumps major.

### Releasing

A release is a deliberate human step. Running `scripts/release.py --yes` or `--push` is an "Ask
first" item in `CLAUDE.md`: an agent runs it only when the owner asks for that release, and a dry
run stays free. `scripts/release.py` is also the tagging step that `CLAUDE.md` mentions, so it is
not exempt. It is never run from a hook. Run it in the primary checkout, on a clean `develop` (a
normal release) or on `main` (after a hotfix, see below).

```bash
scripts/release.py                         # dry run: version, commits, changelog section; changes nothing
scripts/release.py --yes                   # release locally; nothing is pushed
scripts/release.py --yes --push            # release, then push main, develop and the tag
scripts/release.py --yes --version v1.0.0  # override the computed version
```

`--push` requires `--yes` and does not imply it: `--push` alone is a usage error, exit 2, and
changes nothing. A dry run makes the same checks as a release and prints the section it would
write; the only thing it changes is the remote-tracking refs, through `git fetch origin`.

With `--yes`, from `develop`:

1. Check out `main` and merge `develop` with `--no-ff` (`chore(merge): merge develop into main`).
   Started on `main`, this step is skipped.
2. Run `changelog.py assemble vX.Y.Z` and commit `CHANGELOG.md` and the removed fragments as
   `chore(release): vX.Y.Z` on `main`.
3. Create the annotated tag `vX.Y.Z` on that commit.
4. Bring `develop` up to `main`. When `develop` is an ancestor of `main` (`git merge-base
   --is-ancestor`), as after a normal release, this is a fast-forward and both branches point at the
   same tagged commit. Otherwise, as after a hotfix, it is a `--no-ff` merge of `main` into
   `develop` (`chore(merge): merge main into develop`). Either way `develop` loses the folded
   fragments and can reach the new tag, so the next release does not fold them again.
5. Check out the branch the run started on. With `--push`, run
   `git push --atomic origin main develop vX.Y.Z`: all three refs land or none does. Without
   `--push`, it prints that command.

`--version vX.Y.Z` replaces the computed version, for a deliberate jump such as `v1.0.0`. It takes
only the canonical form: a leading `v`, three numbers and no leading zeros. It must be SemVer-higher
than the highest `vX.Y.Z` tag in the repository, whatever branch that tag is on. It does not skip
the other checks: there must still be releasable commits and fragments.

`release.py` runs `git fetch origin` first and refuses, changing nothing and exiting 1, when:

- the repository has no commits, the starting branch is neither `main` nor `develop`, or the run
  is outside a git repository;
- the fetch fails, or the working tree is dirty;
- local `main` or `develop` is missing, has no `origin` counterpart, or differs from it (behind,
  ahead or diverged), so an unpushed hotfix cannot be released by mistake;
- `main` or `develop` is checked out in another worktree, because the release checks out both;
- there is nothing to release: no `feat`, `fix` or breaking commit since the last tag, or no
  fragment in `changelog.d/`;
- a fragment is invalid, `--version` is not higher than the highest tag, or the tag already
  exists. Only `--version` is compared with the highest tag; the computed version always follows
  the last tag reachable from `HEAD`.

If a step fails after the first change (a merge conflict, a hook rejecting the release commit, a
rejected push), `release.py` stops and prints the failed command's stdout and stderr, each
labelled, then the current state, then two lists of exact commands: one to finish by hand after
fixing the problem, one to undo what the run changed. When bringing `develop` up to `main`
conflicts on a changelog fragment, the finish list says to resolve it as deleted with
`git rm <path>`: `main` already folded it, and keeping it would fold it twice at the next release.
It never runs `git reset`, forces or retries anything itself. The undo list can contain
`git reset --hard` and `git branch -f`; an agent does not run those without the human's go-ahead
(`CLAUDE.md` § "Ask first"), and hands the printed output to the human instead. A rejected atomic
push leaves the release complete locally. The message names both likely causes, another push
winning the race and a local `pre-push` hook failing, and the command to retry.

**Hotfix release.** `scripts/gitflow.sh hotfix finish <topic>` merges the hotfix into `main` and
back into `develop`. It pushes and tags nothing. The hotfix adds its fragment (a `fix` needs
`changelog.d/<topic>.fixed.md`), and `finish` checks it. Then:

1. Push both branches: `git push origin main develop`. The push check finds the hotfix fragment in
   the `main` range.
2. The owner runs `git checkout main && scripts/release.py --yes`, or asks the agent to (an "Ask
   first" item). From `main` it skips the merge of `develop`, assembles the changelog, commits and
   tags, and merges `main` back into `develop`.

Run it on `main` only for this case. A branch that is ahead of `origin` is refused, so push first.

**Branch protection.** A repository with protection on `main` or `develop` must allow the release
push (`main`, `develop` and the tag together), or the owner runs the release through pull requests
instead. A repository created with GitHub's "Use this template" has no tags, so its first release
starts from `v0.0.0`.

## Agent verify/resolve workflow

Before any commit is written, changes go through an iterative, independently-verified check loop —
an agent never certifies its own work as passing:

1. **Implement** — the working agent makes the change in its worktree.
2. **Verify** — a separate, independent agent (fresh context, no stake in the implementation) runs
   the full gate from the repo root: `scripts/gate.sh`. It runs, in order, `ruff check`,
   `ruff format --check`, `ty check` and `pytest` (the exact commands live in
   `scripts/config/gate.sh`, the one place to change them).

   It produces a report listing every failure (lint violations, type errors, failing tests) — not
   just a pass/fail summary. The verify agent's ephemeral status/progress chatter while it works
   (not anything it writes to disk) may be terse, caveman-style, if that mode is available; see
   `CLAUDE.md` § "Chatter vs. persisted output" for what stays full prose regardless.
3. **Resolve** — the resolver agent (may be the original implementing agent) addresses every item in
   the report. Nothing is marked resolved without a corresponding fix or an explicit, justified
   waiver called out in the resolution.
4. **Repeat** steps 2–3 until the verifier reports a clean pass on all four gates. This is iterative
   by design — do not skip re-verification after fixes, and do not merge partial results.
5. **Commit** — only once verification is clean, the agent writes the commit message per the
   Commits section above and commits.
6. **Merge & push** — according to branch type:
   - `feat/<topic>` / `bugfix/<topic>` → merge into `develop`
     (`scripts/gitflow.sh <feature|bugfix> finish <topic>`). A `feat`, `fix` or breaking change
     has its changelog fragment committed on the branch first; `finish` refuses without it.
   - `hotfix/<topic>` → merge into `main`, then merge `main` back into `develop` to keep them in
     sync (`scripts/gitflow.sh hotfix finish <topic>`). Nothing is pushed or tagged yet. Push
     `main` and `develop`, then hand the release to the owner: `scripts/release.py --yes` on `main`
     tags the hotfix, writes its changelog section and brings `develop` up to date (§ Versioning).
     The agent does not run it unless the owner asks (`CLAUDE.md` § "Ask first").
   - Push the target branch(es) to `origin`. Tags are pushed only by `release.py --yes --push`, or
     by the atomic push command it prints.

Husky-managed git hooks re-run the same gate as a final safety net — they should never actually
catch anything the verify/resolve loop didn't already catch, but a hook failure blocks the
commit/push regardless of what step 4 concluded.

**Installing the hooks**: run `npm install` once per checkout (or worktree). It also runs Husky's
`prepare` step, which sets `core.hooksPath` to `.husky/_`. A worktree created by
`scripts/gitflow.sh` already has this (see § Worktrees for agents); any other worktree needs its
own `npm ci` before its first commit. `.agents/tasks/scripts/housekeep.py setup` checks the
install.

- `pre-commit` runs `scripts/autofix.sh --staged`, re-stages the files that were staged, then
  `scripts/gate.sh --staged`: lint, format check and typecheck on staged files only (so
  pre-existing, unrelated repo debt cannot block an unrelated commit), and no tests.
- `commit-msg` runs `scripts/commit_lint.py` against the Conventional Commits rules above.
- `pre-push` runs `scripts/changelog.py check` for each pushed branch (§ Versioning), against the
  remote the push goes to, then the full `scripts/gate.sh`, tests included. A failed fragment check,
  or any exit status of `changelog.py` other than 0 and 2, rejects the push before the gate starts.
- `pre-commit` and `pre-push` skip the gate when every changed file is under `.agents/` (task
  files, reports, `BACKLOG.md`, `LESSONS.md`, as `task.py new` pushes). `pre-push` then skips the
  fragment check too. Code under `.agents/tasks/scripts/` never counts as skippable. A new remote
  branch, a range git cannot list, or any file outside `.agents/` (including one renamed into it)
  always runs the full gate.
- A merge commit that git creates itself runs `commit-msg` only. Git runs no `pre-commit` for it,
  and `.husky/` has no `pre-merge-commit` hook, so the `chore(merge)` commits that
  `scripts/gitflow.sh finish` and `scripts/release.py` write are linted but not gated. A merge
  that stopped on a conflict and is finished by hand with `git commit` runs `pre-commit` too.
- `scripts/release.py` (see Versioning) is a separate, deliberately manual step; no hook runs it.
  Only its `chore(release)` commit passes through `commit-msg` and `pre-commit`; its merges run
  `commit-msg` only, as above (unless finished by hand after a conflict), and its push passes
  through `pre-push`.

## Definition of done

A change is done when, and only when:

- [ ] The verify/resolve loop (above) has completed with a clean report.
- [ ] Husky hooks pass on commit and push.
- [ ] The commit message follows Conventional Commits and correctly reflects the version impact.
- [ ] A `feat`, `fix` or breaking change has its changelog fragment in `changelog.d/`.
- [ ] The branch has been merged to its correct target(s) per branch type.
- [ ] For `hotfix/*`, `develop` has received the back-merge from `main`, and the human has been
      told that `scripts/release.py --yes` on `main` is what tags it.
- [ ] Worktrees created for the task have been removed.
