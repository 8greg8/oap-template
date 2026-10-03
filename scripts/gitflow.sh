#!/usr/bin/env bash
# One-line wrappers around the exact worktree/branch/merge operations CONTRIBUTING.md §
# Branching documents by hand -- so they're one command instead of a multi-step sequence to
# get right every time. Does not replace CONTRIBUTING.md as the source of truth; it's a
# mechanical implementation of it.
#
# Usage:
#   scripts/gitflow.sh feature start  <topic>
#   scripts/gitflow.sh feature finish <topic>
#   scripts/gitflow.sh bugfix  start  <topic>
#   scripts/gitflow.sh bugfix  finish <topic>
#   scripts/gitflow.sh hotfix  start  <topic>
#   scripts/gitflow.sh hotfix  finish <topic>

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPTS_DIR/lib/common.sh"
load_gate_config

cd "$(repo_root)"

REPO_NAME="$(basename "$(repo_root)")"

usage() {
    die "usage: gitflow.sh <feature|bugfix|hotfix> <start|finish> <topic>"
}

[[ $# -eq 3 ]] || usage
kind="$1"; action="$2"; topic="$3"

case "$kind" in
    feature) prefix="feat"; base="$DEVELOP_BRANCH" ;;
    bugfix)  prefix="bugfix"; base="$DEVELOP_BRANCH" ;;
    hotfix)  prefix="hotfix"; base="$MAIN_BRANCH" ;;
    *) usage ;;
esac

branch="$prefix/$topic"
worktree_dir="../${REPO_NAME}-$([[ "$kind" == "feature" ]] && echo feat || echo "$kind")-${topic}"

start() {
    section "starting $branch from $base"
    git fetch origin "$base" 2>/dev/null || true
    git worktree add "$worktree_dir" -b "$branch" "$base"
    ok "worktree created at $worktree_dir on branch $branch"

    # node_modules/ and .husky/_ are gitignored (husky-managed shim state), so a fresh
    # worktree has no working hooks until they exist there too. Reuse the root checkout's
    # node_modules via symlink (cheap, no reinstall) and regenerate the shim.
    if [[ -f package.json && -d node_modules ]]; then
        ln -s "$(repo_root)/node_modules" "$worktree_dir/node_modules"
        ( cd "$worktree_dir" && npx --no-install husky ) \
            && ok "hooks activated in $worktree_dir" \
            || warn "could not activate hooks in $worktree_dir -- run 'npm run prepare' there by hand"
    fi

    echo "cd $worktree_dir to begin work."
}

finish() {
    if ! git show-ref --verify --quiet "refs/heads/$branch"; then
        die "branch $branch does not exist locally"
    fi

    section "verifying $branch before merge"
    if ! git -C "$worktree_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        die "worktree $worktree_dir not found -- run gate.sh and merge manually if it was already removed"
    fi
    ( cd "$worktree_dir" && "$SCRIPTS_DIR/gate.sh" ) || die "gate failed on $branch -- fix before finishing"

    section "merging $branch into $base"
    git checkout "$base"
    git merge --no-ff "$branch" -m "$(merge_message "$branch" "$base")"

    if [[ "$kind" == "hotfix" ]]; then
        section "back-merging $MAIN_BRANCH into $DEVELOP_BRANCH"
        git checkout "$DEVELOP_BRANCH"
        git merge --no-ff "$MAIN_BRANCH" -m "$(merge_message "$MAIN_BRANCH" "$DEVELOP_BRANCH")"
        warn "remember: scripts/release.py to tag $MAIN_BRANCH per CONTRIBUTING.md § Versioning"
    fi

    git worktree remove "$worktree_dir" --force 2>/dev/null || warn "could not remove worktree $worktree_dir (may already be gone)"
    git branch -d "$branch"
    ok "$branch merged and cleaned up"
}

case "$action" in
    start) start ;;
    finish) finish ;;
    *) usage ;;
esac
