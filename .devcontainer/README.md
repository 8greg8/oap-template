# Devcontainer

Two configurations share one base image (Ubuntu) and the same features (`git`, `node`,
`common-utils` with zsh, `tmux`, `claude-code`). Feature versions are pinned by the
`devcontainer-lock.json` next to each `devcontainer.json`.

| Configuration | Open it when | What you get |
|---|---|---|
| `.devcontainer/devcontainer.json` (default) | Normal development: any task that edits, runs or tests code | Full repo at `/workspaces/<folder>`, `uv sync` done, `npm ci` done, Husky hooks active (`core.hooksPath` is `.husky/_`), so `scripts/gate.sh` passes |
| `.devcontainer/spec-blind/devcontainer.json` | Writing spec-first tests without being able to read the implementation | Repo at `/workspace` with `src/` replaced by an empty tmpfs; only dependencies are installed (`uv sync --no-install-project`) |

## Spec-blind notes

- It is for authoring only. The project itself is not installed and `src/` is empty, so tests
  cannot run there. Run them in the default container or on the host.
- The tmpfs only changes the container's view. The host's `src/` is untouched.
- Open it from the editor ("Reopen in Container", choose the spec-blind configuration) or with
  `devcontainer up --workspace-folder . --config .devcontainer/spec-blind/devcontainer.json`.

## First boot (`postCreate.sh`)

1. Installs `uv` with the official installer if it is missing.
2. `uv sync` (`--no-install-project` with `--blind`).
3. `npm ci`, which runs Husky's `prepare` step, then checks that `core.hooksPath` ends in
   `.husky/_` and fails loudly if it does not.
4. Optional dotfiles: set `DOTFILES_REPO` on the host (read through `containerEnv`) to a git URL.
   It is cloned to `~/.dotfiles` and its `install.sh`, `bootstrap.sh` or `setup.sh` is run,
   else common dotfiles are symlinked. With `DOTFILES_REPO` unset this step is skipped, and a
   failure in it never fails the script.

`UV_PYTHON_PREFERENCE=only-managed` is set in both configurations because the Ubuntu base image
ships only `python3-minimal` (no `tomllib`), which breaks the `hatchling` build backend; `uv`
downloads a complete CPython instead.

## Updating the lock files

After changing `features`, regenerate both lock files with the devcontainer CLI and commit them:

```bash
devcontainer up --workspace-folder . --experimental-lockfile
devcontainer up --workspace-folder . --config .devcontainer/spec-blind/devcontainer.json --experimental-lockfile
```
