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
#   scripts/gitflow.sh <docs|chore|fix> start  <T-NNNN-slug>   # task branches, from develop
#   scripts/gitflow.sh <docs|chore|fix> finish <T-NNNN-slug>

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPTS_DIR/lib/common.sh"
load_gate_config

cd "$(repo_root)"

REPO_NAME="$(basename "$(repo_root)")"

usage() {
    die "usage: gitflow.sh <feature|bugfix|hotfix|docs|chore|fix> <start|finish> <topic>"
}

[[ $# -eq 3 ]] || usage
kind="$1"; action="$2"; topic="$3"

case "$kind" in
    feature) prefix="feat"; base="$DEVELOP_BRANCH" ;;
    bugfix)  prefix="bugfix"; base="$DEVELOP_BRANCH" ;;
    hotfix)  prefix="hotfix"; base="$MAIN_BRANCH" ;;
    docs|chore|fix) prefix="$kind"; base="$DEVELOP_BRANCH" ;;
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

# undo_merge <commit before the merge>: `git reset --merge ORIG_HEAD` for the merge just made.
# When the merge made no commit (the branch was already merged), HEAD is still that commit and
# ORIG_HEAD may be stale, so nothing is reset.
undo_merge() {
    if [[ "$(git rev-parse HEAD)" != "$1" ]]; then
        git reset --merge ORIG_HEAD
    fi
}

finish() {
    if ! git show-ref --verify --quiet "refs/heads/$branch"; then
        die "branch $branch does not exist locally"
    fi

    section "verifying $branch before merge"
    if ! git -C "$worktree_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        die "worktree $worktree_dir not found -- run gate.sh and merge manually if it was already removed"
    fi

    # The same fragment check .husky/pre-push runs on a branch: from the merge base with the
    # base branch to the tip. The remote-tracking ref is preferred (it is what a push is
    # checked against), so it is fetched first, from the same remote start() uses; a stale ref
    # would check against the wrong range. When the fetch fails, or there is no such ref, the
    # local base is the fallback.
    base_ref="$base"
    if git fetch origin "$base" 2>/dev/null; then
        if git show-ref --verify --quiet "refs/remotes/origin/$base"; then
            base_ref="origin/$base"
        fi
    else
        warn "could not fetch origin $base; checking the changelog against the local $base"
    fi
    merge_base="$(git merge-base "$base_ref" "refs/heads/$branch")" \
        || die "no merge base between $base_ref and $branch -- cannot check the changelog"
    check_rc=0
    python3 "$SCRIPTS_DIR/changelog.py" check "$merge_base" "refs/heads/$branch" || check_rc=$?
    if [[ "$check_rc" -eq 1 ]]; then
        die "changelog check failed on $branch -- add changelog.d/<id>.<category>.md and commit it before finishing"
    elif [[ "$check_rc" -ne 0 ]]; then
        die "changelog check failed (exit $check_rc) on $branch"
    fi

    # The gate runs after each merge, on the merge commit: --if-needed skips it when that code
    # already has a gate record (the verifier's run on the branch, when the merge changed no
    # code) and runs it otherwise. On red the merge is undone, so nothing bad is left on the
    # base branch, and nothing has been pushed.
    section "merging $branch into $base"
    git checkout "$base"
    base_before="$(git rev-parse HEAD)"
    git merge --no-ff "$branch" -m "$(merge_message "$branch" "$base")"
    if ! "$SCRIPTS_DIR/gate.sh" --if-needed HEAD; then
        undo_merge "$base_before"
        die "gate failed on $base after merging $branch; the merge is undone and nothing was pushed"
    fi

    if [[ "$kind" == "hotfix" ]]; then
        section "back-merging $MAIN_BRANCH into $DEVELOP_BRANCH"
        git checkout "$DEVELOP_BRANCH"
        develop_before="$(git rev-parse HEAD)"
        git merge --no-ff "$MAIN_BRANCH" -m "$(merge_message "$MAIN_BRANCH" "$DEVELOP_BRANCH")"
        if ! "$SCRIPTS_DIR/gate.sh" --if-needed HEAD; then
            # Undo both merges: the back-merge first, while ORIG_HEAD still names its parent,
            # then the merge into the base branch, from the commit saved before it.
            undo_merge "$develop_before"
            git checkout "$base"
            git reset --merge "$base_before"
            die "gate failed on $DEVELOP_BRANCH after the back-merge; both merges are undone and nothing was pushed"
        fi
        warn "hotfix merged into $MAIN_BRANCH and back into $DEVELOP_BRANCH; nothing is pushed or tagged yet."
        warn "next: git push origin $MAIN_BRANCH $DEVELOP_BRANCH"
        warn "then: git checkout $MAIN_BRANCH && scripts/release.py --yes   (release.py refuses an unpushed branch)"
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
