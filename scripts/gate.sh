#!/usr/bin/env bash
# The single source of truth for "does this change pass?" -- run by agents during the
# verify/resolve loop, by .husky/pre-commit (--staged), by .husky/pre-push, and by CI.
# Never duplicate these commands anywhere else; edit scripts/config/gate.sh instead.
#
# Usage: scripts/gate.sh [--fast | --staged]
#   --fast    skip TEST_CMD; for a quick loop while iterating, never as the final check.
#   --staged  lint, format check and typecheck only the staged files matching STAGED_GLOB;
#             no tests. Exits 0 when nothing matching is staged.

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPTS_DIR/lib/common.sh"
load_gate_config

fast=false
staged=false
for arg in "$@"; do
    case "$arg" in
        --fast) fast=true ;;
        --staged) staged=true; fast=true ;;
        *) die "unknown argument: $arg" ;;
    esac
done

cd "$(repo_root)"

# Bash 3.2 (macOS) has no mapfile, and expands an empty array under `set -u` only with the
# ${files[@]+...} guard used below.
files=()
if [[ "$staged" == true ]]; then
    while IFS= read -r f; do files+=("$f"); done < <(staged_files)
    if [[ ${#files[@]} -eq 0 ]]; then
        ok "no staged files match $STAGED_GLOB -- nothing to check"
        exit 0
    fi
fi

failures=0

run_on_files "lint" "$LINT_CMD" ${files[@]+"${files[@]}"} || failures=$((failures + 1))
run_on_files "format check" "$FORMAT_CHECK_CMD" ${files[@]+"${files[@]}"} || failures=$((failures + 1))
run_on_files "typecheck" "$TYPECHECK_CMD" ${files[@]+"${files[@]}"} || failures=$((failures + 1))

if [[ "$staged" == true ]]; then
    : # pre-commit mode: tests belong to pre-push
elif [[ "$fast" == false ]]; then
    run_gate "tests" bash -c "$TEST_CMD" || failures=$((failures + 1))
else
    warn "tests: skipped (--fast) -- do not treat this as a clean gate"
fi

echo
if [[ "$failures" -eq 0 ]]; then
    ok "gate clean"
    exit 0
else
    fail "$failures gate(s) failed"
    exit 1
fi
