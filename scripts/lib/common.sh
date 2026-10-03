#!/usr/bin/env bash
# Shared helpers for scripts/*.sh. Source this, don't execute it.
#
#   SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
#   . "$SCRIPTS_DIR/lib/common.sh"

set -euo pipefail

if [[ -t 1 ]]; then
    C_RED=$'\033[31m'
    C_GREEN=$'\033[32m'
    C_YELLOW=$'\033[33m'
    C_BOLD=$'\033[1m'
    C_RESET=$'\033[0m'
else
    C_RED=""; C_GREEN=""; C_YELLOW=""; C_BOLD=""; C_RESET=""
fi

# repo_root: absolute path to the git repo root, regardless of cwd.
repo_root() {
    git rev-parse --show-toplevel
}

# load_gate_config: sources scripts/config/gate.sh relative to the repo root.
load_gate_config() {
    local root
    root="$(repo_root)"
    # shellcheck disable=SC1091
    . "$root/scripts/config/gate.sh"
}

section() {
    printf '%s\n' "${C_BOLD}==> $*${C_RESET}"
}

ok() {
    printf '%s\n' "${C_GREEN}OK${C_RESET}  $*"
}

fail() {
    printf '%s\n' "${C_RED}FAIL${C_RESET}  $*" >&2
}

warn() {
    printf '%s\n' "${C_YELLOW}WARN${C_RESET}  $*" >&2
}

die() {
    fail "$*"
    exit 1
}

# run_gate <name> <command...>: runs a gate command, prints pass/fail, returns its exit code
# without exiting the shell (caller decides fail-fast behavior).
run_gate() {
    local name="$1"; shift
    section "$name: $*"
    if "$@"; then
        ok "$name"
        return 0
    else
        fail "$name"
        return 1
    fi
}

# staged_files: staged paths (added, copied, modified, renamed) matching STAGED_GLOB, each
# followed by a NUL. Without -z git C-quotes names holding a quote or non-ASCII character, and a
# newline in a name would split it. Read the output with `while IFS= read -r -d '' f`.
staged_files() {
    git diff --cached -z --name-only --diff-filter=ACMR -- "${STAGED_GLOB:-*}"
}

# run_on_files <name> <command-string> [files...]: run_gate with the files appended as
# arguments to the command string; with no files the command runs unchanged.
run_on_files() {
    local name="$1" cmd="$2"; shift 2
    run_gate "$name" bash -c "$cmd \"\$@\"" gate ${1+"$@"}
}

# merge_message <branch> <base>: the merge commit header, in the chore(merge) form.
# Task branches (<type>/T-NNNN-<slug>) name the task; any other branch names itself.
merge_message() {
    local branch="$1" base="$2"
    if [[ "$branch" =~ ^[a-z]+/T-([0-9]{4,})- ]]; then
        printf 'chore(merge): merge task %s into %s' "${BASH_REMATCH[1]}" "$base"
    else
        printf 'chore(merge): merge %s into %s' "$branch" "$base"
    fi
}
