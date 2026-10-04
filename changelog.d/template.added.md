- Task tooling under `.agents/`: task and report files, a generated backlog, and scripts to file,
  validate, start and close tasks.
- A single quality gate, `scripts/gate.sh`, run by the pre-commit and pre-push hooks, and a
  commit-msg hook that enforces Conventional Commits.
- Version computation from commit types and git tags in `scripts/next_version.py`.
- Git flow helpers in `scripts/gitflow.sh` for task, hotfix and docs branches and their worktrees.
- An init script, `init_project.py`, that turns a copy of the template into a new project.
- A devcontainer, including a variant that hides `src/` for spec-first test authoring.
- Contribution, code of conduct and security policies.
