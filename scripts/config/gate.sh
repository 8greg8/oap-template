#!/usr/bin/env bash
# Project-specific adaptation point. This is the ONLY file this bundle expects you to edit
# when copy-pasting scripts/ + .husky/ + package.json into another repo.
#
# Every other script sources this file for commands and branch names instead of hardcoding
# them, so changing a repo's stack means editing four command strings here, not chasing
# them through gate.sh, autofix.sh, gitflow.sh, and release.py.

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
