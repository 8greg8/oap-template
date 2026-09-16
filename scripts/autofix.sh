#!/usr/bin/env bash
# The "resolve" half of the verify/resolve loop's mechanical part: applies the safe,
# deterministic auto-corrections (lint autofix, formatting) so trivial issues never reach a
# human or a verifier as noise. Does NOT touch typecheck/test failures — those have no
# generic auto-fix and need a real code change.
#
# Usage: scripts/autofix.sh
# Typical loop: scripts/autofix.sh && scripts/gate.sh

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPTS_DIR/lib/common.sh"
load_gate_config

cd "$(repo_root)"

# `ruff check --fix` exits non-zero when unfixable violations remain even though it did apply
# every fix it could -- don't let that (via `set -e`) skip the format step below. gate.sh is
# the real pass/fail check; this script is best-effort cleanup.
run_gate "lint autofix (ruff check --fix)" bash -c "$LINT_FIX_CMD" || true
run_gate "format (ruff format)" bash -c "$FORMAT_FIX_CMD" || true

echo
ok "autofix complete -- run scripts/gate.sh to re-verify"
