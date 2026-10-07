#!/usr/bin/env bash
# The single source of truth for "does this change pass?" -- run by an executor agent while
# iterating (--fast), by the one independent verifier (the full gate), by later mechanical steps
# (--if-needed), by .husky/pre-commit (--staged), by .husky/pre-push, and by CI.
# Never duplicate these commands anywhere else; edit scripts/config/gate.sh instead.
#
# Usage: scripts/gate.sh [--fast | --staged | [--all] [--if-needed [<commit>...]]]
#   --fast       skip TEST_CMD; for a quick loop while iterating, never as the final check.
#   --staged     lint, format check and typecheck only the staged files matching STAGED_GLOB;
#                no tests. Exits 0 when nothing matching is staged.
#   --if-needed  for each named commit (default HEAD), skip the full gate when a gate record
#                for that exact code exists, and run it otherwise. Exits 0 only when every
#                commit has passed.
#   --all        run every test, the slow ones included. Without it the slow tests are skipped
#                when every path changed since the base is on SLOW_SAFE_PATHS. With
#                --if-needed, a record of a run that skipped them does not count.
#
# Slow tests. TEST_SKIP_SLOW_ARGS is appended to TEST_CMD only when SLOW_SAFE_PATHS (see
# scripts/config/gate.sh) lists every path changed since the base, and `--all` is absent. The
# base is the merge base of the checked-out commit with origin/$DEVELOP_BRANCH
# (origin/$MAIN_BRANCH on a hotfix/* branch), or with the local branch when the remote ref is
# missing. The changed paths are `git diff --name-only --no-renames <base>` plus the untracked
# files for a run on the working tree, and `git diff --name-only --no-renames <base> <commit>`
# for a named commit. An empty set, or a base that cannot be found, runs the slow tests.
#
# Gate records. A full run on a tree that is clean before and after, and that passes, writes
# a record named by a key under "$(git rev-parse --git-common-dir)/gate-pass/". The key hashes
# the commit's tree without the RECORD_PATHS of scripts/config/gate.sh (each entry a
# `:(exclude,glob)` pathspec), plus `uv --version`, `uv run python -VV`, `git --version` and
# `node -v`, so code or a tool version that changed misses the record. --fast, --staged and a
# dirty run never write one. A record says whether the slow tests ran (slow=yes|no). Records
# are local files and are never committed.

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPTS_DIR/lib/common.sh"
load_gate_config

fast=false
staged=false
if_needed=false
run_all=false
commits=()
for arg in "$@"; do
    case "$arg" in
        --fast) fast=true ;;
        --staged) staged=true; fast=true ;;
        --if-needed) if_needed=true ;;
        --all) run_all=true ;;
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
if [[ "$run_all" == true && "$fast" == true ]]; then
    die "--all cannot be combined with --fast or --staged"
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
# One `:(exclude,glob)<entry>` pathspec per SLOW_SAFE_PATHS entry, built the same way.
slow_entries=()
read -r -a slow_entries <<< "${SLOW_SAFE_PATHS-}"
slow_excludes=()
for entry in ${slow_entries[@]+"${slow_entries[@]}"}; do
    slow_excludes+=(":(exclude,glob)$entry")
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
# whether the slow end-to-end tests were part of the run (yes or no). A record with slow=yes is
# never overwritten by one with slow=no. Sets record_slow to what the record now says.
record_slow=""
write_record() {
    local key="$1" commit="$2" slow="$3" dir tmp
    dir="$(record_dir)"
    mkdir -p "$dir"
    record_slow="$slow"
    if [[ "$slow" == no ]] && grep -qx 'slow=yes' "$dir/$key" 2>/dev/null; then
        record_slow=yes
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

# slow_base <commit>: prints the base for the slow-test decision, the merge base of <commit>
# with origin/$DEVELOP_BRANCH (origin/$MAIN_BRANCH when a hotfix/* branch is checked out; a
# detached HEAD uses the develop base), falling back to the local branch when the remote ref is
# missing. Fails, printing nothing, when no base can be found.
slow_base() {
    local target="$1" branch current ref
    current="$(git symbolic-ref -q --short HEAD 2>/dev/null || true)"
    case "$current" in
        hotfix/*) branch="$MAIN_BRANCH" ;;
        *) branch="$DEVELOP_BRANCH" ;;
    esac
    for ref in "refs/remotes/origin/$branch" "refs/heads/$branch"; do
        if git rev-parse --verify --quiet "$ref^{commit}" >/dev/null; then
            git merge-base "$ref" "$target" 2>/dev/null
            return
        fi
    done
    return 1
}

# slow_can_skip [<commit>]: succeeds when the slow tests may be skipped, that is when the
# change since the base is not empty and every path of it is on SLOW_SAFE_PATHS. With a commit
# the change is the commit's diff against the base; without one it is the working tree's. Any
# doubt (no skip arguments, no safe list, no base, a git failure) fails, so the slow tests run.
slow_can_skip() {
    local commit="${1-}" base changed unsafe
    [[ -n "${TEST_SKIP_SLOW_ARGS-}" && ${#slow_excludes[@]} -gt 0 ]] || return 1
    base="$(slow_base "${commit:-HEAD}")" || return 1
    [[ -n "$base" ]] || return 1
    if [[ -n "$commit" ]]; then
        changed="$(git diff --name-only --no-renames "$base" "$commit" --)" || return 1
        unsafe="$(git diff --name-only --no-renames "$base" "$commit" -- . "${slow_excludes[@]}")" || return 1
    else
        changed="$(git diff --name-only --no-renames "$base" -- &&
            git ls-files --others --exclude-standard)" || return 1
        unsafe="$(git diff --name-only --no-renames "$base" -- . "${slow_excludes[@]}" &&
            git ls-files --others --exclude-standard -- . "${slow_excludes[@]}")" || return 1
    fi
    [[ -n "$changed" && -z "$unsafe" ]]
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

# gate_in_worktree <commit> [<gate.sh argument>...]: run the commit's own full gate in a
# temporary detached worktree and remove the worktree on exit, whatever the result. The inner
# run writes the record. The
# git environment variables that a hook or another worktree may have set are dropped first, so
# git works on the new worktree.
gate_in_worktree() {
    local commit="$1" rc=0
    shift
    unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY \
        GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_PREFIX
    trap cleanup_gate_worktree EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    gate_tmp="$(mktemp -d)"
    git worktree add --detach --quiet "$gate_tmp/wt" "$commit" || return 1
    (cd "$gate_tmp/wt" && bash scripts/gate.sh ${1+"$@"}) || rc=$?
    cleanup_gate_worktree
    return "$rc"
}

if [[ "$if_needed" == true ]]; then
    [[ ${#commits[@]} -gt 0 ]] || commits=(HEAD)
    load_tool_versions
    for ref in "${commits[@]}"; do
        sha="$(git rev-parse --verify --quiet "$ref^{commit}")" || die "not a commit: $ref"
        key="$(gate_key "$sha")"
        # A record whose run skipped the slow tests counts only when the change since the base
        # is safe-list-only and --all is absent. A run that has to include them gets --all, so
        # the inner gate cannot decide differently (a hotfix checkout and a detached worktree
        # take different bases).
        skippable=false
        if [[ "$run_all" == false ]] && slow_can_skip "$sha"; then
            skippable=true
        fi
        why="no gate record for ${sha:0:12}"
        if [[ -f "$(record_dir)/$key" ]]; then
            if grep -qx 'slow=yes' "$(record_dir)/$key" || [[ "$skippable" == true ]]; then
                ok "gate record $key exists for ${sha:0:12}; the full gate is skipped"
                continue
            fi
            why="the gate record for ${sha:0:12} is of a run without the slow tests, which this commit needs"
        fi
        gate_args=()
        if [[ "$skippable" == false ]]; then
            gate_args=(--all)
        fi
        if [[ "$(git rev-parse HEAD)" == "$sha" ]] && tree_is_clean; then
            section "$why; running the full gate on this checkout"
            bash "$SCRIPTS_DIR/gate.sh" ${gate_args[@]+"${gate_args[@]}"} || die "gate failed for ${sha:0:12}"
        else
            section "$why; running the full gate in a temporary worktree"
            gate_in_worktree "$sha" ${gate_args[@]+"${gate_args[@]}"} || die "gate failed for ${sha:0:12}"
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
slow=yes

run_on_files "lint" "$LINT_CMD" ${files[@]+"${files[@]}"} || failures=$((failures + 1))
run_on_files "format check" "$FORMAT_CHECK_CMD" ${files[@]+"${files[@]}"} || failures=$((failures + 1))
run_on_files "typecheck" "$TYPECHECK_CMD" ${files[@]+"${files[@]}"} || failures=$((failures + 1))

if [[ "$staged" == true ]]; then
    : # pre-commit mode: tests belong to pre-push
elif [[ "$fast" == false ]]; then
    test_cmd="$TEST_CMD"
    if [[ "$run_all" == false ]] && slow_can_skip; then
        test_cmd="$TEST_CMD $TEST_SKIP_SLOW_ARGS"
        slow=no
        warn "slow tests: skipped (every path changed since the base is on SLOW_SAFE_PATHS); --all runs them"
    fi
    run_gate "tests" bash -c "$test_cmd" || failures=$((failures + 1))
else
    warn "tests: skipped (--fast) -- do not treat this as a clean gate"
fi

echo
if [[ "$failures" -eq 0 ]]; then
    if [[ "$want_record" == true ]]; then
        if tree_is_clean; then
            head="$(git rev-parse HEAD)"
            key="$(gate_key "$head")"
            write_record "$key" "$head" "$slow"
            ok "gate record $key (slow tests: $record_slow)"
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
