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
# Appended to TEST_CMD when scripts/gate.sh skips the slow tests (see SLOW_SAFE_PATHS). The
# string is passed to `bash -c` together with TEST_CMD, so its quoting is shell quoting. Empty
# or unset: the slow tests are never skipped.
TEST_SKIP_SLOW_ARGS='-m "not slow"'

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

# Paths whose change cannot break a slow test: same syntax as RECORD_PATHS. scripts/gate.sh
# appends TEST_SKIP_SLOW_ARGS to TEST_CMD only when every path changed since the base is on this
# list. Any other change, an empty change set, `--all` and a push to MAIN_BRANCH run the slow
# tests. The list is RECORD_PATHS, the changelog fragments (`*.*.md` leaves out the README), and
# the prose docs that init_project.py copies unchanged; a fast test greps those docs for the
# template names. Empty or unset: the slow tests always run. Adding a path is a change that
# needs a human.
SLOW_SAFE_PATHS="${RECORD_PATHS-} changelog.d/*.*.md CONTRIBUTING.md DEV_TOOLING_SPEC.md PYTHON_CONVENTIONS.md NOTICE.md"
