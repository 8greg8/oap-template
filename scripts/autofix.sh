#!/usr/bin/env bash
# Applies the safe, deterministic auto-corrections (lint autofix, formatting) so trivial issues
# never reach a human or a verifier as noise. Run by .husky/pre-commit (--staged) and by hand.
# Does NOT touch typecheck/test failures -- those have no generic auto-fix and need a real code
# change.
#
# Usage: scripts/autofix.sh [--staged]
#   --staged  fix only the staged files matching STAGED_GLOB (used by .husky/pre-commit).
# Typical loop: scripts/autofix.sh && scripts/gate.sh

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPTS_DIR/lib/common.sh"
load_gate_config

staged=false
for arg in "$@"; do
    case "$arg" in
        --staged) staged=true ;;
        *) die "unknown argument: $arg" ;;
    esac
done

cd "$(repo_root)"

# Bash 3.2: no mapfile; empty arrays are expanded with the ${files[@]+...} guard.
files=()
if [[ "$staged" == true ]]; then
    while IFS= read -r -d '' f; do files+=("$f"); done < <(staged_files)
    [[ ${#files[@]} -gt 0 ]] || { ok "no staged files match $STAGED_GLOB"; exit 0; }
fi

# `ruff check --fix` exits non-zero when unfixable violations remain even though it did apply
# every fix it could -- don't let that (via `set -e`) skip the format step below. gate.sh is
# the real pass/fail check; this script is best-effort cleanup.
run_on_files "lint autofix" "$LINT_FIX_CMD" ${files[@]+"${files[@]}"} || true
run_on_files "format" "$FORMAT_FIX_CMD" ${files[@]+"${files[@]}"} || true

echo
ok "autofix complete -- run scripts/gate.sh to re-verify"
