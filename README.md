# OAP Template

A starting point for Python repositories built to be worked on by AI coding agents, following
[Orchestrated Agentic Programming](strategic_model_init_material.md) (OAP): a human-governed method
that separates strategic reasoning (specification, architecture, task decomposition) from bounded,
evidence-producing execution.

This is a **template**, not a working project — clone or use it as a GitHub template, then fill in
the placeholders (`<repo_name>`, mission, architecture) for your actual repository.

## What's in here

| File / folder | Purpose |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | The entry point for any coding agent working in this repo — autonomy boundaries, what needs asking first, spec-first test rules, batch-run authority, and how the task workflow below fits together. [`AGENTS.md`](AGENTS.md) is a one-line redirect to it. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Branching (Gitflow), commit conventions, semantic versioning, and the verify/resolve/merge workflow every change follows. |
| [`PYTHON_CONVENTIONS.md`](PYTHON_CONVENTIONS.md) | Project layout (`uv` workspace, `src/` layout), commands, dependency management, testing, and code style. |
| [`DEV_TOOLING_SPEC.md`](DEV_TOOLING_SPEC.md) | Spec for the `scripts/` + `.husky/` + `package.json` bundle: deterministic lint/typecheck/test gates, commit-message validation, SemVer release tagging, and Gitflow helpers — copy-pasteable into any repo. |
| [`.agents/`](.agents/README.md) | Tooling for running work as discrete, PR-sized **tasks**: task files as work orders, reports as evidence, a generated backlog, and harvested lessons-learned memory. See `.agents/README.md`. |
| [`.agents/plans/`](.agents/plans/) | Dated plans: the owner's written decisions and approvals for a body of work, and other task-independent notes. |
| [`.devcontainer/`](.devcontainer/README.md) | Dev container with `uv`, Node and Claude Code, hooks installed on first boot. `.devcontainer/spec-blind/` is a second configuration that hides `src/` for authoring spec-first tests (authoring only; tests cannot run there). |
| [`strategic_model_init_material.md`](strategic_model_init_material.md) | The full OAP reference manual this template's workflow is derived from. |

## Getting started with a new project

1. Rename the package: replace `<repo_name>` throughout `PYTHON_CONVENTIONS.md` with your actual
   package name, and lay out `src/<repo_name>/` accordingly.
2. Fill in the project-specific parts of `CLAUDE.md` (mission, architecture, domain) — the process
   sections (autonomy, task workflow, file boundaries) are already ready to use as-is. Put the
   specification under `docs/spec/`; the spec-first test rule in `CLAUDE.md` refers to it.
3. Set up the `uv` workspace (`uv init` / `pyproject.toml`) per `PYTHON_CONVENTIONS.md`.
4. Wire up Husky-managed git hooks per `CONTRIBUTING.md`'s verify/resolve workflow: edit
   `scripts/config/gate.sh` for your stack's lint/typecheck/test commands, then `npm install`
   (its `prepare` step installs the hooks; see [`DEV_TOOLING_SPEC.md`](DEV_TOOLING_SPEC.md) and
   [`scripts/README.md`](scripts/README.md)). Run `scripts/gate.sh` to check the result. Or open
   the repo in the dev container, whose first-boot script runs `uv sync` and `npm ci` for you.
5. Start working via tasks: file them with `task.py new` from the primary checkout on `develop`;
   see `.agents/README.md` for the full command reference (`task.py new`, `backlog.py ready`,
   `report.py new`, `housekeep.py all`).

## Design principles

- **Process lives in files agents can read**, not in tribal knowledge — `CLAUDE.md`,
  `CONTRIBUTING.md`, and `PYTHON_CONVENTIONS.md` are the machine-readable contract.
- **Work is PR-sized and evidence-based.** A task names its goal, scope, and explicit non-goals; a
  report states exactly what ran and what passed, failed, or wasn't run — never "looks good."
- **Verification is never self-certified.** An independent check (verify/resolve loop, or a
  separate reviewing agent) confirms a change before it's committed.
- **Non-goals are guardrails, not decoration.** Naming what a task must *not* touch is treated as
  seriously as naming what it must do.

## License

[MIT](LICENSE)
