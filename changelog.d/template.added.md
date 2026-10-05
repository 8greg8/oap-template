- Task tooling under `.agents/`: task and report files, a generated backlog, and scripts to file,
  validate, start and close tasks.
- A single quality gate, `scripts/gate.sh`, run by the pre-commit and pre-push hooks, and a
  commit-msg hook that enforces Conventional Commits. The gate commands live in
  `scripts/config/gate.sh`, which stays POSIX-sourceable; a test sources it with `sh`.
- Version computation from commit types and git tags in `scripts/next_version.py`.
- Git flow helpers in `scripts/gitflow.sh` for task, hotfix and docs branches and their worktrees.
  `finish` fetches the base branch before it picks `origin/<base>`, warns and uses the local base
  when the fetch fails, and prints the add-a-fragment advice only when the changelog check found a
  problem.
- An init script, `init_project.py`, that turns a copy of the template into a new project.
- A devcontainer, including a variant that hides `src/` for spec-first test authoring.
- Contribution, code of conduct and security policies.
- A changelog fragment check. A push or a `scripts/gitflow.sh finish` that carries a `feat`, `fix`
  or breaking commit needs a fragment in `changelog.d/` and is rejected without one. The pre-push
  hook checks each pushed branch from its merge base with `origin/develop` (`origin/main` for
  `hotfix/*`), and `main` and `develop` from the remote commit to the pushed one. It checks against
  the remote the push goes to, not always `origin`. It reports "changelog check failed (exit N)"
  for any exit status other than a real finding, so a failed check is not mistaken for a missing
  fragment. Tags, deleted refs and `.agents/`-only pushes are not checked.
- A strict changelog fragment format. A fragment may hold only bullet lines, indented continuation
  lines directly after a bullet and blank lines, so unchecked text cannot reach `CHANGELOG.md`. A
  fragment with no bullet or with a placeholder bullet is rejected. Fragments are decoded strictly
  as UTF-8 on every path, a non-UTF-8 fragment is reported as a fragment problem, and one leading
  BOM is ignored. `scripts/changelog.py assemble --date` takes only `YYYY-MM-DD`. An internal
  error, a load failure or an unexpected exception, exits 3 with one line. Renaming a fragment
  that exists at the base, or deleting and adding it again, does not count as adding one.
- A release script, `scripts/release.py`, that releases `develop` into `main`. Without `--yes` it
  prints the version, the commits and the changelog section and changes nothing. With `--yes` it
  merges `develop` into `main`, folds the changelog fragments into `CHANGELOG.md`, commits
  `chore(release): vX.Y.Z`, tags that commit and brings `develop` up to `main`. After a hotfix it
  runs on `main` and merges `main` into `develop`. `--push`, which requires `--yes` and does not
  imply it, pushes `main`, `develop` and the tag atomically, and `--version vX.Y.Z` overrides the
  computed version. Without `--yes`, `--push` exits 2 with a usage message and changes nothing. It
  refuses a dirty tree, a branch that differs from `origin`, a branch checked out in another
  worktree, nothing to release, and a repository with no commits (exit status 1, with a clear
  message). When a step fails it prints the stdout and stderr of the failed command, each
  labelled, then the current state and the commands to finish by hand or undo. When bringing
  `develop` up to `main` conflicts on a changelog fragment, the finish commands say to resolve it
  as deleted with `git rm <path>`, because `main` already folded it. A rejected `--push` names both
  likely causes: another push won the race, or a local pre-push hook failed.
- A release is an "Ask first" item in `CLAUDE.md`. An agent runs `scripts/release.py --yes`, with or
  without `--push`, only when the owner asks for that release; a dry run stays free.
- A 0.x versioning rule. While the latest tag is `v0.x`, a breaking change bumps minor instead of
  major, so the first release is `v0.1.0`. From `v1.0.0` on a breaking change bumps major.
- A hotfix release step. `scripts/gitflow.sh hotfix finish` tells you to push `main` and
  `develop`, then run `scripts/release.py --yes` on `main`.
- Release, changelog and hook documentation in `CONTRIBUTING.md`, `DEV_TOOLING_SPEC.md`,
  `scripts/README.md` and `changelog.d/README.md` that matches the code: `--push` requires `--yes`,
  `changelog.py` exit status 3, the fragment content rule, strict UTF-8 and a leading BOM, the
  push's own remote, and merge commits running `commit-msg` only.
