# Contributing

This document defines the process for contributing to this repo — branching, commits, versioning,
and the agent-driven verify/commit/merge workflow. For environment setup, commands, and code style,
see [`PYTHON_CONVENTIONS.md`](PYTHON_CONVENTIONS.md).

## Branching

[Gitflow](https://nvie.com/posts/a-successful-git-branching-model/), with two permanent branches
and short-lived branches on top:

- `main` — always reflects the latest released state. Every merge into `main` is tagged
  (`vX.Y.Z`, see Versioning) and is release-ready. No direct commits — only merges from `develop`
  (release) or `hotfix/*`.
- `develop` — integration branch for ongoing work. Always in a working, checks-passing state, but
  not necessarily released. No direct commits — only merges from `feat/*` or `bugfix/*`, from a
  task branch `<type>/T-NNNN-<slug>` (whatever its Conventional Commits `type` prefix), and the
  back-merge from `hotfix/*`. The one exception to "no direct commits" is task filing, which
  commits and pushes the new task file straight to `develop` (§ Worktrees for agents).
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
| `hotfix/<topic>`       | urgent breaking fix on `main` | `fix(scope)!: summary` + `BREAKING CHANGE:` footer | major     |
| any branch             | breaking change              | `<type>(scope)!: summary` + `BREAKING CHANGE:` footer | major    |

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
[`PYTHON_CONVENTIONS.md`](PYTHON_CONVENTIONS.md) for how packages consume this). Tags are cut from
`main` after a merge lands there. Commit types accumulated since the last tag determine the next
version:

- Any `BREAKING CHANGE` footer since the last tag → next tag bumps **major**.
- Else any `feat:` → bumps **minor**.
- Else only `fix:` → bumps **patch**.

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
     (`scripts/gitflow.sh <feature|bugfix> finish <topic>`).
   - `hotfix/<topic>` → merge into `main`, then merge `main` back into `develop` to keep them in
     sync, then tag `main` per the version bump implied by the commit(s)
     (`scripts/gitflow.sh hotfix finish <topic>`, then `scripts/release.py`).
   - Push the target branch(es) and any new tag to `origin`.

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
- `pre-push` runs the full `scripts/gate.sh`, tests included.
- `pre-commit` and `pre-push` skip the gate when every changed file is under `.agents/` (task
  files, reports, `BACKLOG.md`, `LESSONS.md`, as `task.py new` pushes). Code under
  `.agents/tasks/scripts/` never counts as skippable. A new remote branch, a range git cannot
  list, or any file outside `.agents/` (including one renamed into it) always runs the full gate.
- `scripts/release.py` (see Versioning) is a separate, deliberately manual step; it is not wired
  into any hook.

## Definition of done

A change is done when, and only when:

- [ ] The verify/resolve loop (above) has completed with a clean report.
- [ ] Husky hooks pass on commit and push.
- [ ] The commit message follows Conventional Commits and correctly reflects the version impact.
- [ ] The branch has been merged to its correct target(s) per branch type.
- [ ] For `hotfix/*`, `develop` has received the back-merge from `main`.
- [ ] Worktrees created for the task have been removed.
