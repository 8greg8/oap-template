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
  not necessarily released. No direct commits — only merges from `feat/*` or `bugfix/*`.
- `feat/<topic>` — new functionality, non-breaking, branched from and merged into `develop`.
- `bugfix/<topic>` — bug fixes against `develop`, non-breaking, branched from and merged into `develop`.
- `hotfix/<topic>` — urgent fixes branched from `main`, merged into both `main` and `develop`.

### Worktrees for agents

Agents work in an isolated `git worktree` per branch, never directly in the primary checkout, so
multiple agents (or multiple concurrent tasks) can operate on different branches at once without
stashing or clobbering each other's state:

```bash
# From the primary checkout, for a new feature branch
git worktree add ../proj-template-feat-<topic> -b feat/<topic> develop

# For a hotfix, branched from main
git worktree add ../proj-template-hotfix-<topic> -b hotfix/<topic> main
```

- Name worktree directories `<repo>-<branch-type>-<topic>` so concurrent worktrees are identifiable.
- An agent does all work (edits, checks, commits) inside its own worktree.
- Remove the worktree once the branch is merged and deleted: `git worktree remove ../proj-template-feat-<topic>`.

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

- Never write `feat:`/`fix:` without a scope if the change is isolated to one package under `app/`
  (e.g. `feat(RecipeGenerator): ...`) — omit scope only for changes spanning multiple packages.
- A breaking change is marked **both** with `!` after the type/scope and a `BREAKING CHANGE:` footer
  explaining the break — the footer is what `hatch-vcs`/semver tooling keys off, the `!` is for
  human skimmability.
- Squash incidental fixup commits made during the verify/resolve loop (see below) into a single
  clean commit before merge — the merged history should have one commit per logical change, not one
  per lint fix.

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
   the full gate from the package directory under `app/<AgentName>/`:
   - `uv run ruff check`
   - `uv run ruff format --check`
   - `uv run ty check`
   - `uv run pytest`

   It produces a report listing every failure (lint violations, type errors, failing tests) — not
   just a pass/fail summary.
3. **Resolve** — the resolver agent (may be the original implementing agent) addresses every item in
   the report. Nothing is marked resolved without a corresponding fix or an explicit, justified
   waiver called out in the resolution.
4. **Repeat** steps 2–3 until the verifier reports a clean pass on all four gates. This is iterative
   by design — do not skip re-verification after fixes, and do not merge partial results.
5. **Commit** — only once verification is clean, the agent writes the commit message per the
   Commits section above and commits.
6. **Merge & push** — according to branch type:
   - `feat/<topic>` / `bugfix/<topic>` → merge into `develop`.
   - `hotfix/<topic>` → merge into `main`, then merge `main` back into `develop` to keep them in
     sync, then tag `main` per the version bump implied by the commit(s).
   - Push the target branch(es) and any new tag to `origin`.

Husky-managed git hooks (`pre-commit`, `pre-push`) re-run the same lint/type/test gate as a final
safety net — they should never actually catch anything the verify/resolve loop didn't already catch,
but a hook failure blocks the commit/push regardless of what step 4 concluded.

## Definition of done

A change is done when, and only when:

- [ ] The verify/resolve loop (above) has completed with a clean report.
- [ ] Husky hooks pass on commit and push.
- [ ] The commit message follows Conventional Commits and correctly reflects the version impact.
- [ ] The branch has been merged to its correct target(s) per branch type.
- [ ] For `hotfix/*`, `develop` has received the back-merge from `main`.
- [ ] Worktrees created for the task have been removed.
