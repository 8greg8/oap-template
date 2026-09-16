#!/usr/bin/env bash
# The single source of truth for "does this change pass?" — run by agents during the
# verify/resolve loop, by `.husky/pre-push`, and (if wired up later) by CI. Never duplicate
# these four commands anywhere else; edit scripts/config/gate.sh instead.
#
# Usage: scripts/gate.sh [--fast]
#   --fast   skip TEST_CMD (lint/format/typecheck only) — for a quick loop while iterating;
#            never use --fast as the final check before commit/push.

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPTS_DIR/lib/common.sh"
load_gate_config

fast=false
for arg in "$@"; do
    case "$arg" in
        --fast) fast=true ;;
        *) die "unknown argument: $arg" ;;
    esac
done

cd "$(repo_root)"

failures=0

run_gate "lint (ruff check)" bash -c "$LINT_CMD" || failures=$((failures + 1))
run_gate "format check (ruff format --check)" bash -c "$FORMAT_CHECK_CMD" || failures=$((failures + 1))
run_gate "typecheck (ty check)" bash -c "$TYPECHECK_CMD" || failures=$((failures + 1))

if [[ "$fast" == false ]]; then
    run_gate "tests (pytest)" bash -c "$TEST_CMD" || failures=$((failures + 1))
else
    warn "tests: skipped (--fast) — do not treat this as a clean gate"
fi

echo
if [[ "$failures" -eq 0 ]]; then
    ok "gate clean"
    exit 0
else
    fail "$failures gate(s) failed"
    exit 1
fi
