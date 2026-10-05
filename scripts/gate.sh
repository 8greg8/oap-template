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
# the commit's tree without the RECORD_PATHS of scripts/config/gate.sh (each entry a
# `:(exclude,glob)` pathspec), plus `uv --version`, `uv run python -VV`, `git --version` and
# `node -v`, so code or a tool version that changed misses the record. --fast, --staged and a
# dirty run never write one. Records are local files and are never committed.

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
# A pathspec environment variable would change how the excludes below match.
unset GIT_LITERAL_PATHSPECS GIT_GLOB_PATHSPECS GIT_NOGLOB_PATHSPECS GIT_ICASE_PATHSPECS

# One `:(exclude,glob)<entry>` pathspec per RECORD_PATHS entry. `read -a` splits the string
# without expanding globs.
record_entries=()
read -r -a record_entries <<< "${RECORD_PATHS-}"
record_excludes=()
for entry in ${record_entries[@]+"${record_entries[@]}"}; do
    record_excludes+=(":(exclude,glob)$entry")
done
tool_versions=""

# load_tool_versions: sets tool_versions to one line each from `uv --version`,
# `uv run python -VV`, `git --version` and `node -v`, as seen from this checkout. A missing tool
# is recorded as absent. stderr is dropped, since uv prints progress there.
load_tool_versions() {
    tool_versions="$(
        uv --version 2>/dev/null || echo "uv: absent"
        uv run python -VV 2>/dev/null || echo "python: absent"
        git --version
        node -v 2>/dev/null || echo "node: absent"
    )"
}

# gate_key <commit>: the record key, a hash of the commit's tree listing without the
# RECORD_PATHS followed by the tool versions. `git ls-tree` takes no pathspec magic, so the
# listing comes from `git ls-files -s` over a temporary index of the commit. Needs
# load_tool_versions first.
gate_key() {
    local commit="$1" index key
    index="$(mktemp "${TMPDIR:-/tmp}/gate-index.XXXXXX")"
    git read-tree --index-output="$index" "$commit" || { rm -f "$index"; return 1; }
    key="$(
        {
            GIT_INDEX_FILE="$index" git ls-files -s -- . ${record_excludes[@]+"${record_excludes[@]}"}
            printf '%s\n' "$tool_versions"
        } | git hash-object --stdin
    )" || { rm -f "$index"; return 1; }
    rm -f "$index"
    printf '%s\n' "$key"
}

record_dir() {
    local common
    common="$(git rev-parse --git-common-dir)"
    printf '%s/gate-pass' "$(cd "$common" && pwd)"
}

tree_is_clean() {
    [[ -z "$(git status --porcelain --untracked-files=all)" ]]
}

# write_record <key> <commit> <slow>: the file holds no secrets, only what ran. slow says
# whether the slow end-to-end tests were part of the run (every full run includes them). A
# record with slow=yes is never overwritten by one with slow=no.
write_record() {
    local key="$1" commit="$2" slow="$3" dir tmp
    dir="$(record_dir)"
    mkdir -p "$dir"
    if [[ "$slow" == no ]] && grep -qx 'slow=yes' "$dir/$key" 2>/dev/null; then
        return 0
    fi
    tmp="$dir/.$key.$$"
    {
        printf 'key=%s\n' "$key"
        printf 'commit=%s\n' "$commit"
        printf 'slow=%s\n' "$slow"
        printf 'date=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    } > "$tmp"
    mv "$tmp" "$dir/$key"
}

gate_tmp=""
cleanup_gate_worktree() {
    if [[ -n "$gate_tmp" ]]; then
        git worktree remove --force "$gate_tmp/wt" >/dev/null 2>&1 || true
        rm -rf "$gate_tmp"
        git worktree prune >/dev/null 2>&1 || true
        gate_tmp=""
    fi
}

# gate_in_worktree <commit>: run the commit's own full gate in a temporary detached worktree
# and remove the worktree on exit, whatever the result. The inner run writes the record. The
# git environment variables that a hook or another worktree may have set are dropped first, so
# git works on the new worktree.
gate_in_worktree() {
    local commit="$1" rc=0
    unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY \
        GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_PREFIX
    trap cleanup_gate_worktree EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    gate_tmp="$(mktemp -d)"
    git worktree add --detach --quiet "$gate_tmp/wt" "$commit" || return 1
    (cd "$gate_tmp/wt" && bash scripts/gate.sh) || rc=$?
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
            ok "gate record $key exists for ${sha:0:12}; the full gate is skipped"
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
        warn "dirty tree before the run: no gate record will be written"
    elif ! git rev-parse --verify --quiet 'HEAD^{commit}' >/dev/null; then
        warn "no commit yet: no gate record will be written"
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
            write_record "$key" "$head" yes
            ok "gate record $key (slow tests: yes)"
        else
            warn "dirty tree after the run: no gate record written"
        fi
    fi
    ok "gate clean"
    exit 0
else
    fail "$failures gate(s) failed"
    exit 1
fi
