---
id: T-0019
title: Scrub private references and attribute the method text
status: open
type: docs
priority: high
depends_on: []
touches: [NOTICE.md, LICENSE, tests/test_report_scripts.py, .agents/LESSONS.md, .agents/plans/2026-10-03-workflow-sync.md, .agents/tasks/T-0001-enforce-report-writing-as-a-pipeline-gate-not.md, .agents/tasks/T-0002-port-git-atomic-task-filing-and-backlog-fixes.md, .agents/tasks/T-0003-port-report-validation-harvest-and-housekeep.md, .agents/tasks/T-0004-reconcile-hooks-and-dev-tooling-with-the-merge.md, .agents/tasks/T-0005-port-agent-rules-process-docs-and-orchestrator.md, .agents/tasks/T-0006-add-a-devcontainer.md, .agents/tasks/reports/T-0002.md, .agents/tasks/reports/T-0003.md, .agents/tasks/reports/T-0004.md, .agents/tasks/reports/T-0005.md]
created: 2026-10-03
report: reports/T-0019.md
---

# T-0019 — Scrub private references and attribute the method text

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(Non-goals, acceptance criteria) still stays complete.

## Goal

No tracked file on `develop` contains the local path, the downstream project name or the
workflow-sync source project name in any spelling or short form, and the method text is attributed in a new `NOTICE.md`. The
tree is exactly what T-0020's history rewrite will produce, so the rewritten `develop` tree
matches it byte for byte.

## Context / current verified state

- Plan: `.agents/plans/2026-10-03-public-release-cleanup.md`, accepted by the owner on
  2026-10-03. Its § Replacements is the source of truth for the replacements. Where this file and
  the plan differ, stop and report.
- This file does not quote the literals, because quoting them would put them back in the tree.
  Find them as follows:
  - L3, the source project name: the project named in the title of
    `.agents/plans/2026-10-03-workflow-sync.md`. 37 lines (45 occurrences) in 11 files: that plan,
    `.agents/LESSONS.md`, tasks T-0002 to T-0006 and reports T-0002 to T-0005.
  - L3u, L3 with the hyphen written as an underscore: `.agents/plans/2026-10-03-workflow-sync.md:129`.
  - L3s, the lowercase two-letter abbreviation of L3 as a whole word (for example `L3s:CLAUDE.md`,
    `L3s's`): about 74 occurrences in 8 of those 11 files. L3V, its uppercase form, is a shell
    variable at `.agents/plans/2026-10-03-workflow-sync.md` lines 315, 317 and 320.
  - L3t, the test function name at `tests/test_report_scripts.py:287`, which embeds L3s between
    underscores. Nothing else references it.
  - P1, the home-directory prefix: the text from `/home/` up to and including the `/` before L3
    inside the absolute path at `.agents/LESSONS.md:139` and `.agents/tasks/reports/T-0004.md:85`.
  - L2, the downstream project name: the backticked project name at
    `.agents/tasks/T-0001-enforce-report-writing-as-a-pipeline-gate-not.md` lines 25, 56 and 86.
- `strategic_model_init_material.md` is "Orchestrated Agentic Programming", version 1.0.1, by
  Janez Perš, from <https://edu.slaif.si/trainings/workshop-orchestrated-agentic-programming>.
  The owner treats it as MIT-licensed public SLAIF material.
- `LICENSE` is MIT, "Copyright (c) 2026 8greg8" (the owner's GitHub account).
- T-0018 touches `README.md`. This task does not.
- Re-check against `develop` before starting and report any discrepancy.

## Scope

- Apply exactly the plan's § Replacements rules to every tracked file that contains a match,
  in two passes. First the plain-text rules: P1 to `/path/to/`, L2 to `downstream-project`, L3
  to `source-project`, L3u to `source_project`, `<L3V>=..` to `SRC=..`, `"$<L3V>"` to `"$SRC"`,
  L3t up to and including `_thresholds` to `test_no_source_project_thresholds`. Then the regex rule: L3s as a case-sensitive whole word (`\b<L3s>\b`) to `source-project`.
  The order matters: the regex pass must not see L3. Change nothing else on those lines.
- Editing other tasks' files and reports, and the workflow-sync plan, is allowed for these
  replacements only. This overrides the Workflow rule against editing another task's file.
- Add `NOTICE.md` with a "Third-party material" section for `strategic_model_init_material.md`:
  title, version, author, source URL, a statement that it is included under the MIT License as
  public SLAIF workshop material with copyright held by its author, and this acknowledgement
  verbatim: "We acknowledge the support of the EC/EuroHPC JU and the Slovenian Ministry of HESI
  via the project SLAIF (grant number 101254461)."
- Append one line to `LICENSE` after the MIT text: "Third-party material in this repository is
  listed in NOTICE.md."

## Non-goals

- Do not edit `strategic_model_init_material.md`, including its author and email front matter.
- Do not edit `README.md`; T-0018 owns it.
- Do not reword, reflow or otherwise edit lines beyond the replacements. T-0020's tree check
  depends on the edit being exactly the replacements.
- Do not rewrite history, change commit metadata or touch git config. That is T-0020.
- Do not change `scripts/`, `.husky/`, `.agents/tasks/scripts/`, `CLAUDE.md`, `pyproject.toml`
  or any lock file. In `tests/test_report_scripts.py`, change only the L3t function name.
- Do not write any of the literals (P1, L2, L3, L3u, L3s, L3V, L3t), or the owner's work email, into the report.

## Files to inspect

- `.agents/plans/2026-10-03-public-release-cleanup.md`
- Every file listed in `touches`
- `strategic_model_init_material.md` lines 1-10 and 64-72 (attribution facts)

## Required behavior

After the change, a case-insensitive `git grep` for P1, L2, L3 and L3u, and a case-insensitive
whole-word `git grep -w` for L3s, on the branch find nothing. Applying T-0020's `replace.txt` to the branch's tree with filter-repo's rules changes
no file.

## Tests required

- `git grep -n -i -e <P1> -e <L2> -e <L3> -e <L3u>` and `git grep -n -i -w <L3s>` on the
  branch: no output. Run it with the literals
  read from `develop` at the start of the task. Record the command shape in the report, not the
  literals.
- `git diff develop --stat` lists only files in `touches`, the report and `BACKLOG.md`.
- `git diff develop --word-diff=porcelain`: every changed word is one of the plan's replacements,
  apart from `NOTICE.md` and the `LICENSE` line.
- `scripts/gate.sh` passes.

## Documentation required

`NOTICE.md` (new) and the `LICENSE` pointer line, as in Scope.

## Acceptance criteria

- [ ] No tracked file contains P1, L2, L3, L3u or L3t, or L3s or L3V as a whole word in any case.
- [ ] The renamed test in `tests/test_report_scripts.py` still runs and passes.
- [ ] Every changed line outside `NOTICE.md` and `LICENSE` differs only by the plan's replacements.
- [ ] `NOTICE.md` names the title, version, author and source URL, states MIT with copyright held by the author, and quotes the SLAIF acknowledgement verbatim.
- [ ] `LICENSE` keeps the MIT text unchanged and adds the one pointer line.
- [ ] `strategic_model_init_material.md` and `README.md` are unchanged.
- [ ] The report contains none of the literals (P1, L2, L3, L3u, L3s, L3V, L3t) and no work email.
- [ ] `scripts/gate.sh` passes.
- [ ] Diff stays within `touches`, the report and `BACKLOG.md`.

## Workflow

- Read `CLAUDE.md` first — it is the primary router. (`AGENTS.md` is a redirect to it for
  models that look for that filename; reading it gains nothing.)
- Create a worktree and branch from `develop` as `docs/T-0019-scrub-private-references-and-attribute-the`, per
  `CONTRIBUTING.md`'s worktree conventions. Every task branch integrates into
  `develop`, whatever Conventional Commits `type` prefixes it — a genuine
  production hotfix is the separate, human-initiated `hotfix/` flow in
  `CONTRIBUTING.md`, not a task-driven branch.
- Commit only files related to this task, using Conventional Commits.
- Write the report to `.agents/tasks/reports/T-0019.md` and commit it on this branch.
- Push the branch. **Do not merge.** Do not open a pull request. The orchestrator merges after an
  independent verify by a different agent.
- Do not hand-edit `.agents/tasks/BACKLOG.md` or any other task's file — the
  orchestrator owns backlog state. Regenerating `BACKLOG.md` with `backlog.py
  reindex` to reflect this task's own status change is expected, and is not an
  edit in the sense meant here.

## Report

Fill in `.agents/tasks/reports/T-0019.md` from `.agents/tasks/templates/report.md`:

```bash
python .agents/tasks/scripts/report.py new T-0019
```
