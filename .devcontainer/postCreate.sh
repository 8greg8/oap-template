#!/usr/bin/env bash
# First-boot setup: uv, Python dependencies, git hooks, optional dotfiles.
# --blind: src/ is hidden (spec-blind container), so install dependencies only.
set -euo pipefail

blind=false
[[ "${1:-}" == "--blind" ]] && blind=true

if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

if [[ "$blind" == true ]]; then
    uv sync --no-install-project
else
    uv sync
fi

# Installs Husky; its prepare step sets core.hooksPath (Husky 9 uses .husky/_).
npm ci
hooks_path="$(git config --get core.hooksPath || true)"
if [[ "$hooks_path" != *".husky/_" ]]; then
    echo "postCreate.sh: core.hooksPath is '${hooks_path}', expected .husky/_; git hooks will not run." >&2
    exit 1
fi

# Optional dotfiles. A failure here never blocks the container.
if [[ -n "${DOTFILES_REPO:-}" ]]; then
    (
        set +e
        dir="${HOME}/.dotfiles"
        if [[ -d "$dir" ]]; then
            git -C "$dir" pull --ff-only
        elif ! git clone --depth 1 "$DOTFILES_REPO" "$dir"; then
            echo "postCreate.sh: could not clone $DOTFILES_REPO; skipping dotfiles." >&2
            exit 0
        fi
        cd "$dir" || exit 0
        for candidate in install.sh bootstrap.sh setup.sh; do
            if [[ -f "$candidate" ]]; then
                bash "$candidate"
                exit 0
            fi
        done
        for f in .tmux.conf .vimrc .gitconfig .zshrc; do
            [[ -f "$f" ]] && ln -sf "$dir/$f" "$HOME/$f"
        done
    ) || echo "postCreate.sh: dotfiles setup failed; continuing." >&2
fi
