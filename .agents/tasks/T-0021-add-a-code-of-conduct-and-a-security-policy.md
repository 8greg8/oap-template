---
id: T-0021
title: Add a code of conduct and a security policy
status: open
type: docs
priority: medium
depends_on: []
touches: [CODE_OF_CONDUCT.md, SECURITY.md, init_project.py, tests/test_init_project.py]
created: 2026-10-04
report: reports/T-0021.md
---

# T-0021 — Add a code of conduct and a security policy

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

The repository has a `CODE_OF_CONDUCT.md` and a `SECURITY.md` that fit this template, and
projects created with `init_project.py` do not inherit either file or the owner's contact
details.

## Context / current verified state

- The owner supplied both files in the session (2026-10-04). The code of conduct is the
  Contributor Covenant 3.0 with the maintainer contact already filled in; it is added as given.
  The security policy comes from another of the owner's repositories (a TypeScript MCP server)
  and must be adapted. The orchestrator gives the executor both texts.
- This repository is a Python and Node tooling template, not a service. It has no tagged
  releases; the version is dynamic (setuptools-scm, `pyproject.toml` line 6). No
  `.github/workflows/` exist.
- Security-relevant parts: `.agents/tasks/scripts/` (task, backlog, report, housekeep tooling),
  `scripts/` (gate, gitflow, commit lint, release tooling), `.husky/` hooks, `init_project.py`,
  `.devcontainer/` (including `postCreate.sh` and `spec-blind/`), `src/` and `tests/`, the
  agent instruction files (`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `.agents/README.md`),
  and the dependency pins (`uv.lock`, `package-lock.json`).
- `init_project.py` turns a template copy into a project. Its end-to-end test
  (`tests/test_init_project.py` lines 35 and 932) fails if the result contains `proj_template`,
  `proj-template`, `oap-template`, `oap-template-dev-tooling` or `8greg8`. Its dry-run change
  list is built near line 360; its checklist is `step_checklist` near line 770.
- Re-check against `develop` before starting and report any discrepancy.

## Scope

- Add `CODE_OF_CONDUCT.md` at the repository root with the owner's text unchanged, apart from
  removing the leading blank line.
- Add `SECURITY.md` at the repository root, adapted from the owner's text:
  - Supported versions: no tagged releases yet; only the latest `develop` and `main` receive
    fixes. Keep the owner's policy of supporting the latest minor release and the one before it
    once releases exist.
  - In scope: the parts listed under Context, described by path. Include unsafe behavior caused
    by the agent instruction files (for example, rules that would lead an agent to leak secrets
    or run destructive commands).
  - Out of scope: projects created from the template (report to their maintainers, unless the
    flaw comes from a file the template provides), AI coding agents and their vendors' products,
    third-party dependencies (report upstream, notify us), social engineering, physical access.
    Drop every reference to the other project (MCP server, SURS, PxWeb, `dist/`, `tsconfig.json`).
  - Reporting: keep GitHub private vulnerability reporting as preferred, but describe it from
    the reporter's side (the repository's Security tab, "Report a vulnerability"); keep the
    owner's fallback email exactly as given.
  - Keep the owner's severity table, response times, CVE, 90-day disclosure, supply-chain and
    safe-harbor sections. Adapt safe harbor to a repository with no running service: test only
    against your own clone or a project created from the template.
- `init_project.py`: remove `CODE_OF_CONDUCT.md` and `SECURITY.md` from the generated project,
  list both removals in the dry-run change list, and add a checklist line telling the new owner
  to add their own code of conduct and security policy.
- `tests/test_init_project.py`: extend the existing tests to check both files are absent after
  a run and that the dry run lists their removal.

## Non-goals

- Do not edit the code of conduct's wording, scope or enforcement ladder.
- Do not change the owner's response times, severity thresholds, disclosure period or contacts.
- Do not edit `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `NOTICE.md` or `LICENSE`.
- Do not change `scripts/`, `.husky/`, `.agents/tasks/scripts/`, `pyproject.toml` or any lock
  file.
- Do not add GitHub workflows, issue templates or repository settings.
- Do not change any other init step's behavior.

## Files to inspect

- `init_project.py` (change list near line 360, task-state removal, `step_checklist`)
- `tests/test_init_project.py`
- `pyproject.toml`, `scripts/README.md`, `.devcontainer/README.md`, `.agents/README.md`

## Required behavior

Both files exist at the root of this repository. `SECURITY.md` names only this repository's
paths and tooling. After `python init_project.py ...` on a template copy, neither file exists in
the result, the dry run lists both removals, and the checklist asks the owner to add their own.

## Tests required

- `uv run pytest tests/test_init_project.py -v` passes, including the new assertions.
- `scripts/gate.sh` passes.
- `grep -niE 'mcp|surs|pxweb|tsconfig|dist/' SECURITY.md` finds nothing.

## Documentation required

The two new files. No other documentation changes.

## Acceptance criteria

- [ ] `CODE_OF_CONDUCT.md` matches the owner's text, apart from the removed leading blank line.
- [ ] `SECURITY.md` lists only this repository's paths and tooling in scope, with no reference to the other project.
- [ ] `SECURITY.md` keeps the owner's fallback email, response times, severity table, CVE, disclosure, supply-chain and safe-harbor sections.
- [ ] `SECURITY.md` describes private vulnerability reporting from the reporter's side.
- [ ] A generated project contains neither file, the dry run lists both removals, and the checklist names them.
- [ ] `uv run pytest tests/test_init_project.py -v` passes.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `docs/T-0021-add-a-code-of-conduct-and-a-security-policy`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0021.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0021.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0021
```
