- Task tooling under `.agents/`: task and report files, a generated backlog, and scripts to file,
  validate, start and close tasks.
- A single quality gate, `scripts/gate.sh`, run by the pre-commit and pre-push hooks, and a
  commit-msg hook that enforces Conventional Commits.
- Version computation from commit types and git tags in `scripts/next_version.py`.
- Git flow helpers in `scripts/gitflow.sh` for task, hotfix and docs branches and their worktrees.
- An init script, `init_project.py`, that turns a copy of the template into a new project.
- A devcontainer, including a variant that hides `src/` for spec-first test authoring.
- Contribution, code of conduct and security policies.
- A changelog fragment check. A push or a `scripts/gitflow.sh finish` that carries a `feat`, `fix`
  or breaking commit needs a fragment in `changelog.d/` and is rejected without one. The pre-push
  hook checks each pushed branch from its merge base with `origin/develop` (`origin/main` for
  `hotfix/*`), and `main` and `develop` from the remote commit to the pushed one. Tags, deleted
  refs and `.agents/`-only pushes are not checked.
- A release script, `scripts/release.py`, that releases `develop` into `main`. Without `--yes` it
  prints the version, the commits and the changelog section and changes nothing. With `--yes` it
  merges `develop` into `main`, folds the changelog fragments into `CHANGELOG.md`, commits
  `chore(release): vX.Y.Z`, tags that commit and brings `develop` up to `main`. After a hotfix it
  runs on `main` and merges `main` into `develop`. `--push` pushes `main`, `develop` and the tag
  atomically, and `--version vX.Y.Z` overrides the computed version. It refuses a dirty tree, a
  branch that differs from `origin`, a branch checked out in another worktree, and nothing to
  release.
- A 0.x versioning rule. While the latest tag is `v0.x`, a breaking change bumps minor instead of
  major, so the first release is `v0.1.0`. From `v1.0.0` on a breaking change bumps major.
- A hotfix release step. `scripts/gitflow.sh hotfix finish` tells you to push `main` and
  `develop`, then run `scripts/release.py --yes` on `main`.
