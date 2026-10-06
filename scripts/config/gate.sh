#!/usr/bin/env bash
# Project-specific adaptation point. This is the ONLY file this bundle expects you to edit
# when copy-pasting scripts/ + .husky/ + package.json into another repo.
#
# Every other script sources this file for commands and branch names instead of hardcoding
# them, so changing a repo's stack means editing four command strings here, not chasing
# them through gate.sh, autofix.sh, gitflow.sh, and release.py.
#
# This file must stay POSIX-sourceable: plain NAME="value" assignments only, no bash arrays or
# other bash-only syntax. The bash scripts source it, and so does .husky/pre-push, which runs
# under POSIX sh (dash on many systems) and would fail on bash-only syntax.

# The four verify/resolve gates, in the order CONTRIBUTING.md's verify/resolve workflow runs
# them. Defaults below match PYTHON_CONVENTIONS.md exactly for this template.
LINT_CMD="uv run ruff check"
LINT_FIX_CMD="uv run ruff check --fix"
FORMAT_CHECK_CMD="uv run ruff format --check"
FORMAT_FIX_CMD="uv run ruff format"
TYPECHECK_CMD="uv run ty check"
TEST_CMD="uv run pytest"

# Branch names used by gitflow.sh and release.py, per CONTRIBUTING.md § Branching.
MAIN_BRANCH="main"
DEVELOP_BRANCH="develop"

# Pathspec for files the pre-commit hook checks (gate.sh --staged, autofix.sh --staged).
# LINT_CMD, FORMAT_CHECK_CMD and TYPECHECK_CMD (and the *_FIX_CMDs) must accept file paths
# as trailing arguments; with no arguments they check the whole repo.
STAGED_GLOB="*.py"

# Paths that only record bookkeeping: one space-separated string of git glob pathspecs, so no
# entry holds a space. scripts/gate.sh leaves them out of the key of a gate record, and
# .husky/pre-commit and .husky/pre-push skip a change that touches only these paths. All three
# exclude each entry as a `:(exclude,glob)<entry>` pathspec, so git is the only matcher: `*`
# does not cross `/` and `**` does. Everything else, including the task tooling under
# .agents/tasks/scripts/ and the process docs, is code for both. Shell code expands the string
# with globbing off (`set -f`).
RECORD_PATHS=".agents/tasks/T-*.md .agents/tasks/reports/** .agents/tasks/BACKLOG.md .agents/tasks/.counter .agents/LESSONS.md .agents/plans/**"
