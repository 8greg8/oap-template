#!/usr/bin/env bash
# The single source of truth for "does this change pass?" -- run by agents during the
# verify/resolve loop, by .husky/pre-commit (--staged), by .husky/pre-push, and by CI.
# Never duplicate these commands anywhere else; edit scripts/config/gate.sh instead.
#
# Usage: scripts/gate.sh [--fast | --staged | --if-needed [<commit>...]]
#   --fast       skip TEST_CMD; for a quick loop while iterating, never as the final check.
#   --staged     lint, format check and typecheck only the staged files matching STAGED_GLOB;
#                no tests. Exits 0 when nothing matching is staged.
#   --if-needed  for each named commit (default HEAD), skip the full gate when a gate record
#                for that exact code exists, and run it otherwise. Exits 0 only when every
#                commit has passed.
#
# Gate records. A full run on a tree that is clean before and after, and that passes, writes
# a record named by a key under "$(git rev-parse --git-common-dir)/gate-pass/". The key hashes
# the commit's tree without the RECORD_PATHS of scripts/config/gate.sh, plus `uv --version`,
# `uv run python -VV`, `node -v` and `git --version`, so code or a tool version that changed
# misses the record. --fast, --staged and a dirty run never write one. Records are local files
# and are never committed.

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPTS_DIR/lib/common.sh"
load_gate_config

fast=false
staged=false
if_needed=false
commits=()
for arg in "$@"; do
    case "$arg" in
        --fast) fast=true ;;
        --staged) staged=true; fast=true ;;
        --if-needed) if_needed=true ;;
        -*) die "unknown argument: $arg" ;;
        *) commits+=("$arg") ;;
    esac
done
if [[ "$if_needed" == false && ${#commits[@]} -gt 0 ]]; then
    die "unknown argument: ${commits[0]} (commits are accepted only with --if-needed)"
fi
if [[ "$if_needed" == true && "$fast" == true ]]; then
    die "--if-needed cannot be combined with --fast or --staged"
fi

cd "$(repo_root)"

# Bash 3.2 (macOS) has no mapfile, and expands an empty array under `set -u` only with the
# ${files[@]+...} guard used below.
record_patterns=()
read -r -a record_patterns <<< "${RECORD_PATHS-}"
tool_versions=""

# is_record_path <path>: true when the path matches a RECORD_PATHS pattern. A pattern ending
# in "/" is a directory prefix; any other is an exact path or a glob in which "*" matches "/".
is_record_path() {
    local path="$1" pattern
    for pattern in ${record_patterns[@]+"${record_patterns[@]}"}; do
        case "$pattern" in
            */) [[ "$path" == "$pattern"* ]] && return 0 ;;
            *) [[ "$path" == $pattern ]] && return 0 ;;
        esac
    done
    return 1
}

# load_tool_versions: sets tool_versions to the versions seen from this checkout. A missing
# tool is recorded as such. stderr is dropped, since uv prints progress there.
load_tool_versions() {
    tool_versions="$(
        echo "gate-pass-v1"
        uv --version 2>/dev/null || echo "uv: unavailable"
        uv run python -VV 2>/dev/null || echo "python: unavailable"
        node -v 2>/dev/null || echo "node: unavailable"
        git --version
    )"
}

# gate_key <commit>: the record key. Needs load_tool_versions first.
gate_key() {
    local commit="$1" entry path
    {
        while IFS= read -r -d '' entry; do
            path="${entry#*$'\t'}"
            is_record_path "$path" || printf '%s\0' "$entry"
        done < <(git ls-tree -r -z "$commit")
        printf '%s\n' "$tool_versions"
    } | git hash-object --stdin
}

record_dir() {
    local common
    common="$(git rev-parse --git-common-dir)"
    printf '%s/gate-pass' "$(cd "$common" && pwd)"
}

tree_is_clean() {
    [[ -z "$(git status --porcelain --untracked-files=all)" ]]
}

# write_record <key> <commit>: the file holds no secrets, only what ran. slow_tests says
# whether the slow end-to-end tests were part of the run; every full run includes them.
write_record() {
    local key="$1" commit="$2" dir tmp
    dir="$(record_dir)"
    mkdir -p "$dir"
    tmp="$dir/.$key.$$"
    {
        printf 'commit=%s\n' "$commit"
        printf 'slow_tests=yes\n'
        printf 'written=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    } > "$tmp"
    mv "$tmp" "$dir/$key"
}

gate_tmp=""
cleanup_gate_worktree() {
    if [[ -n "$gate_tmp" ]]; then
        git worktree remove --force "$gate_tmp/tree" >/dev/null 2>&1 || true
        rm -rf "$gate_tmp"
        git worktree prune >/dev/null 2>&1 || true
        gate_tmp=""
    fi
}

# gate_in_worktree <commit>: run the commit's own full gate in a temporary detached worktree
# and remove the worktree afterwards, whatever the result.
gate_in_worktree() {
    local commit="$1" rc=0
    trap cleanup_gate_worktree EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    gate_tmp="$(mktemp -d "${TMPDIR:-/tmp}/gate-worktree.XXXXXX")"
    git worktree add --detach --quiet "$gate_tmp/tree" "$commit" || return 1
    (
        unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
        cd "$gate_tmp/tree" && bash scripts/gate.sh
    ) || rc=$?
    cleanup_gate_worktree
    return "$rc"
}

if [[ "$if_needed" == true ]]; then
    [[ ${#commits[@]} -gt 0 ]] || commits=(HEAD)
    load_tool_versions
    for ref in "${commits[@]}"; do
        sha="$(git rev-parse --verify --quiet "$ref^{commit}")" || die "not a commit: $ref"
        key="$(gate_key "$sha")"
        if [[ -f "$(record_dir)/$key" ]]; then
            ok "gate record ${key:0:12} exists for ${sha:0:12}; the full gate is skipped"
            continue
        fi
        if [[ "$(git rev-parse HEAD)" == "$sha" ]] && tree_is_clean; then
            section "no gate record for ${sha:0:12}; running the full gate on this checkout"
            bash "$SCRIPTS_DIR/gate.sh" || die "gate failed for ${sha:0:12}"
        else
            section "no gate record for ${sha:0:12}; running the full gate in a temporary worktree"
            gate_in_worktree "$sha" || die "gate failed for ${sha:0:12}"
        fi
    done
    ok "every commit has passed the gate"
    exit 0
fi

# A record is written only after a full run on a tree that is clean before and after.
want_record=false
if [[ "$fast" == false ]]; then
    if ! tree_is_clean; then
        warn "the working tree is not clean: this run will not write a gate record"
    elif ! git rev-parse --verify --quiet 'HEAD^{commit}' >/dev/null; then
        warn "there is no commit yet: this run will not write a gate record"
    else
        want_record=true
        load_tool_versions
    fi
fi

files=()
if [[ "$staged" == true ]]; then
    while IFS= read -r -d '' f; do files+=("$f"); done < <(staged_files)
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
    if [[ "$want_record" == true ]]; then
        if tree_is_clean; then
            head="$(git rev-parse HEAD)"
            key="$(gate_key "$head")"
            write_record "$key" "$head"
            ok "gate record ${key:0:12} written for ${head:0:12}"
        else
            warn "the run changed the working tree: no gate record written"
        fi
    fi
    ok "gate clean"
    exit 0
else
    fail "$failures gate(s) failed"
    exit 1
fi
