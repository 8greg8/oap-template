# Python Development Conventions

These conventions apply to all Python code in this repo (and any tests/tooling around it).

## Project Layout

Standard `src` layout, managed as a single `uv` workspace with one root `pyproject.toml`:

```
<repo-name>/
├── pyproject.toml     # workspace root: project metadata, deps, tool config
├── uv.lock
├── src/
│   └── <repo_name>/   # importable package (snake_case), main source tree
│       ├── __init__.py
│       └── ...
└── tests/
    └── test_*.py
```

- `<repo-name>` is the repo directory name (may contain hyphens); `<repo_name>` is the importable
  package name under `src/` (snake_case, matches `[project].name` in `pyproject.toml` with hyphens
  converted to underscores).
- Run all commands from the repo root — there is no per-subdirectory `pyproject.toml`/`uv sync` step.
- If the repo grows into multiple installable packages, add them as `uv` workspace members (see
  [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/)) under a `packages/`
  directory, each with its own `pyproject.toml`, listed in the root `[tool.uv.workspace].members` —
  don't restructure `src/<repo_name>` for this until it's actually needed.
- `[tool.hatch.version]` uses `source = "vcs"`, so the package version is derived directly from
  `vX.Y.Z` git tags at the repo root (see [`CONTRIBUTING.md`](CONTRIBUTING.md)) — no extra
  `raw-options.root` needed since the workspace root and the version-controlled root are the same.
  Tags are created only by `scripts/release.py`, never by hand, and a change that is a `feat`, `fix`
  or breaking change adds a changelog fragment under `changelog.d/` (see `CONTRIBUTING.md` §
  Versioning).

## Commands

Run from the repo root:

```bash
# Install dependencies (including dev tools: pytest, ruff, ty)
uv sync

# Run tests
uv run pytest

# Run the package's entry point
uv run python -m <repo_name>

# Lint
uv run ruff check
uv run ruff check --fix       # fix what's auto-fixable
uv run ruff check --select I --fix   # sort imports
uv run ruff format            # format code

# Type check
uv run ty check

# Release: tag, changelog and push (a human runs this; see CONTRIBUTING.md § Versioning)
scripts/release.py              # dry run: next version, commits, changelog section
scripts/release.py --yes --push
```

`pytest`, `ruff`, and `ty` are declared as `dev` dependency-group entries in the root
`pyproject.toml` — `uv sync` installs them automatically, no global/tool install needed.

These are the exact commands behind `scripts/gate.sh`, which the one independent verifier runs in
full on a finished branch (see [`CONTRIBUTING.md`](CONTRIBUTING.md) § Agent verify/resolve
workflow). While iterating, use `scripts/gate.sh --fast` (everything except the tests) and targeted
`uv run pytest` runs, and run the full `scripts/gate.sh` yourself before handing work off, so the
verifier's report is a confirmation, not a first discovery of problems. Your own runs certify
nothing.

## Dependency Management

Run from the repo root, never by hand-editing `pyproject.toml`:

```bash
# Add a runtime dependency
uv add <package>

# Add a dev-only dependency (linting, testing, etc.)
uv add --group dev <package>

# Remove a dependency
uv remove <package>

# Upgrade a dependency to the latest allowed version
uv lock --upgrade-package <package>
```

- Always commit `uv.lock` together with the `pyproject.toml` change that caused it — never commit
  one without the other.
- Never hand-edit `uv.lock` — it's a generated file; let `uv` regenerate it.
- Prefer the narrowest dependency that solves the problem — check whether an existing dependency
  (including transitive ones already in the lockfile) already covers the need before adding a new one.

## Testing

- Tests live under `tests/`, mirroring the module under test: `src/<repo_name>/foo.py` →
  `tests/test_foo.py`.
- Any new public function/class and any bug fix ships with a test that would have failed before the
  change — this is what "done" means for the test gate, not a numeric coverage target.
- Prefer real objects over mocks where practical; mock only external boundaries (network calls,
  third-party APIs, filesystem/clock where determinism matters).

## Conventions

- **Python**: 3.10+, managed with `uv`.
- **Docstrings**: Google style (`Args:`, `Returns:`, `Raises:` sections) for all public classes and
  functions.
- **String formatting**: Prefer f-strings over `%`-formatting or `str.format()`.
- **Design**: Follow SOLID principles — single responsibility per module/class, open for extension via
  hooks, depend on abstractions not concretions.
