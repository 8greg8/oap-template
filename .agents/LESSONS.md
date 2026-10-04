<!-- GENERATED FILE — do not edit by hand.
     Regenerate with: python .agents/tasks/scripts/report.py harvest
     The reports in .agents/tasks/reports/ are the source of truth. -->

# Lessons Learned

Harvested from task reports. Read the tags relevant to your task before
starting — these are repo-specific traps that already cost someone time.

20 lesson(s) across 11 section(s). Generated 2026-10-04.

## Tag index

Each lesson appears once, under its first tag; the index links every tag
to all lessons that carry it.

- `agent-rules` — [T-0005](#t-0005-success)
- `agent-workflow` — [T-0010](#t-0010-success)
- `backlog` — [T-0002](#t-0002-success)
- `bash` — [T-0012](#t-0012-success)
- `bash-3.2` — [T-0011](#t-0011-success)
- `chore` — [T-0020](#t-0020-success)
- `commit` — [T-0018](#t-0018-success)
- `commit-lint` — [T-0004](#t-0004-success)
- `devcontainer` — [T-0006](#t-0006-success), [T-0007](#t-0007-success)
- `docker` — [T-0006](#t-0006-success)
- `docs` — [T-0005](#t-0005-success), [T-0010](#t-0010-success), [T-0013](#t-0013-success), [T-0014](#t-0014-success), [T-0019](#t-0019-success)
- `end-to-end` — [T-0018](#t-0018-success)
- `execution-loop` — [T-0001](#t-0001-success)
- `file-mode` — [T-0009](#t-0009-success)
- `file-modes` — [T-0007](#t-0007-success)
- `filter-repo` — [T-0020](#t-0020-success)
- `gate` — [T-0004](#t-0004-success), [T-0018](#t-0018-success)
- `git` — [T-0007](#t-0007-success), [T-0012](#t-0012-success)
- `git-pathspec` — [T-0008](#t-0008-success)
- `git-publish` — [T-0002](#t-0002-success)
- `git-worktree` — [T-0010](#t-0010-success), [T-0011](#t-0011-success)
- `gitflow` — [T-0004](#t-0004-success), [T-0011](#t-0011-success)
- `history-rewrite` — [T-0020](#t-0020-success)
- `hooks` — [T-0004](#t-0004-success), [T-0008](#t-0008-success)
- `housekeep` — [T-0003](#t-0003-success), [T-0011](#t-0011-success)
- `husky` — [T-0004](#t-0004-success), [T-0006](#t-0006-success), [T-0008](#t-0008-success)
- `init-script` — [T-0015](#t-0015-success), [T-0016](#t-0016-success), [T-0017](#t-0017-success), [T-0018](#t-0018-success)
- `merge-authority` — [T-0013](#t-0013-success), [T-0014](#t-0014-success)
- `method-text` — [T-0014](#t-0014-success)
- `notice` — [T-0019](#t-0019-success)
- `nul-safe` — [T-0012](#t-0012-success)
- `orchestrator` — [T-0005](#t-0005-success), [T-0013](#t-0013-success)
- `port` — [T-0003](#t-0003-success)
- `pre-commit` — [T-0008](#t-0008-success)
- `process` — [T-0005](#t-0005-success)
- `public-release` — [T-0019](#t-0019-success), [T-0020](#t-0020-success)
- `rename` — [T-0015](#t-0015-success)
- `report-gate` — [T-0001](#t-0001-success)
- `report-validation` — [T-0003](#t-0003-success)
- `ruff` — [T-0007](#t-0007-success)
- `scripts` — [T-0012](#t-0012-success)
- `scrub` — [T-0019](#t-0019-success)
- `seeding` — [T-0017](#t-0017-success)
- `set-status` — [T-0001](#t-0001-success)
- `shebang` — [T-0009](#t-0009-success)
- `staged-files` — [T-0012](#t-0012-success)
- `task-scripts` — [T-0009](#t-0009-success)
- `task-state` — [T-0016](#t-0016-success)
- `task-tooling` — [T-0001](#t-0001-success), [T-0002](#t-0002-success)
- `template` — [T-0015](#t-0015-success), [T-0016](#t-0016-success), [T-0017](#t-0017-success), [T-0018](#t-0018-success)
- `tests` — [T-0015](#t-0015-success), [T-0016](#t-0016-success), [T-0017](#t-0017-success), [T-0018](#t-0018-success)
- `upstream-tracking` — [T-0010](#t-0010-success)
- `uv` — [T-0006](#t-0006-success)
- `workflow` — [T-0013](#t-0013-success)
- `worktree` — [T-0002](#t-0002-success)

## devcontainer

### T-0006 (success)

- The `mcr.microsoft.com/devcontainers/base:ubuntu` image (Ubuntu 26.04) has only
  `python3-minimal`; `uv` selects it and builds fail on missing `tomllib`. Set
  `UV_PYTHON_PREFERENCE=only-managed`.
- A git worktree's `.git` file points to a host path, so git does not work in a container opened
  on a worktree; test devcontainers from a normal clone.
- `devcontainer up --experimental-lockfile` writes the lock file next to the config used, so run
  it once per configuration.

Tags: `devcontainer`, `uv`, `husky`, `docker`

Source: [`reports/T-0006.md`](tasks/reports/T-0006.md)

## docs

### T-0005 (success)

`scripts/gitflow.sh` cannot create `docs/` or `chore/` task branches, so a task branch of those
types needs a hand-written `git worktree add ... origin/develop`, and `node_modules` is not
symlinked into it. `npm ci` is needed before its first commit if the hooks are to run.

Tags: `docs`, `agent-rules`, `process`, `orchestrator`

Source: [`reports/T-0005.md`](tasks/reports/T-0005.md)

### T-0010 (success)

- `git worktree add -b <branch> origin/develop` sets the new branch to track `origin/develop`. A bare `git push` then fails under `push.default=simple` because the names differ. `--no-track` leaves no upstream, so the first push still needs `git push -u origin <branch>`.
- Line numbers quoted in a task's context can drift as other tasks merge. The `AGENTS.md` citations had moved by two lines.

Tags: `docs`, `agent-workflow`, `git-worktree`, `upstream-tracking`

Source: [`reports/T-0010.md`](tasks/reports/T-0010.md)

### T-0013 (success)

The merge-authority wording lives in `CLAUDE.md`, `.agents/README.md`, `CONTRIBUTING.md` and the task template. A later change to merge rules should grep all four, plus `.agents/plans/`, for the section names it renames.

Tags: `docs`, `merge-authority`, `orchestrator`, `workflow`

Source: [`reports/T-0013.md`](tasks/reports/T-0013.md)

### T-0014 (success)

The method text is one long-line-per-paragraph file, and its cited line numbers shift after any insertion. Re-grep by phrase rather than trusting a line number from an earlier report.

Tags: `docs`, `merge-authority`, `method-text`

Source: [`reports/T-0014.md`](tasks/reports/T-0014.md)

### T-0019 (success)

- Do not guess a short form by taking initials of a project name. Derive it from an existing embedded occurrence, then check the rule counts against the counts the task states. A wrong guess matched nothing and the count mismatch exposed it.
- A script run by a worktree-isolated agent must write its scratch data to the scratchpad directory by absolute path, so private literals never land in the tree.

Tags: `docs`, `public-release`, `scrub`, `notice`

Source: [`reports/T-0019.md`](tasks/reports/T-0019.md)

## git

### T-0007 (success)

- A fresh clone takes file modes from the git index, so a host checkout can pass ruff `EXE001` while a clone fails; verify mode-sensitive lint in a fresh clone.
- In this harness, a Bash call that combines git with a loop or `&&` chain can be refused for worktree-isolation checks; run git commands as plain separate calls.

Tags: `git`, `ruff`, `file-modes`, `devcontainer`

Source: [`reports/T-0007.md`](tasks/reports/T-0007.md)

## gitflow

### T-0011 (success)

- `housekeep.py`'s old merged check was ancestry-only, so any test that wanted a "merged" worktree could pass with an empty branch. Such tests must commit on the branch and merge it.
- `ruff format` wraps lines at 88 columns here; the gate's format check fails on a single over-long condition, so run `uv run ruff format <files>` before the gate.

Tags: `gitflow`, `housekeep`, `git-worktree`, `bash-3.2`

Source: [`reports/T-0011.md`](tasks/reports/T-0011.md)

## hooks

### T-0004 (success)

- A worktree shares `core.hooksPath` with the primary checkout, so hooks run from the primary checkout's `.husky/_` (files from the checked-out branch there), not the worktree's edited hooks.
- The sibling `../source-project` path does not resolve from inside `.claude/worktrees/<id>/`; use the absolute path `/path/to/source-project`.

Tags: `hooks`, `husky`, `gate`, `commit-lint`, `gitflow`

Source: [`reports/T-0004.md`](tasks/reports/T-0004.md)

### T-0008 (success)

- A rename is invisible to a `--diff-filter=ACMR` listing as anything but its new path. Use `--no-renames` and no filter when deciding on "what did this commit touch", as `pre-push` does.
- `git add -- <name>` treats `[`, `*` and `?` in a name as pathspec globs, so a test that stages `a[1].py` must use `:(literal)a[1].py`, and the hook must set `GIT_LITERAL_PATHSPECS=1`.
- Hook tests with stub `autofix.sh`/`gate.sh` cannot show problems inside the real scripts. Check unusual names against the real `staged_files` too.

Tags: `hooks`, `husky`, `pre-commit`, `git-pathspec`

Source: [`reports/T-0008.md`](tasks/reports/T-0008.md)

## init-script

### T-0015 (success)

- `npm install --package-lock-only` still runs the project's `prepare` script. In this repo that is `husky`, so the command exits 127 in a tree without `node_modules`, though the lock file is written.
- `git status --porcelain` output passed through a `.strip()` helper loses the leading space of the first line, so ` M file` reads as a staged `M file`. Use `git diff --cached --name-only` to test for staged files.
- The ruff configuration in this repo flags `datetime.date.today()` (DTZ011) and a bare `except Exception` (BLE001), and flags a shebang file that is not executable (EXE001). Use `datetime.now().astimezone()`, add a reasoned `noqa`, and `chmod +x`.
- A worktree-isolated agent's shell refuses commands that mention git in a compound or inline-script form. Put such helper code in a file under the scratchpad and run that.

Tags: `init-script`, `template`, `rename`, `tests`

Source: [`reports/T-0015.md`](tasks/reports/T-0015.md)

### T-0016 (success)

- The pre-commit hook runs lint, format and type checks on the staged files, not the test suite. A tests-first commit is therefore possible; this task recorded the failing run in the report instead.
- `git ls-files` does not keep an empty directory, and `.agents/tasks/reports/` survives only through `.gitkeep`. Any reset that removes `reports/*.md` must leave that file.
- The task scripts resolve paths from their own file location, so running them as subprocesses with `cwd` in the copy is enough to regenerate the copy's files. Set `PYTHONDONTWRITEBYTECODE=1`, or `__pycache__/` appears inside the directory that must stay unchanged.
- A worktree-isolated agent's shell refuses an inline heredoc script that mentions git. Use the edit tools for such changes.

Tags: `init-script`, `template`, `task-state`, `tests`

Source: [`reports/T-0016.md`](tasks/reports/T-0016.md)

### T-0017 (success)

- A new text block inserted before an anchor heading round-trips byte for byte only if it ends with a blank line and the edit helper replaces the heading line itself; test the round trip by cutting from the section start to the anchor.
- When a later step deletes files an earlier step edits, the earlier step's observable assertions move to the later step's replacement files. Check the existing tests for this before adding a deleting step.

Tags: `init-script`, `template`, `seeding`, `tests`

Source: [`reports/T-0017.md`](tasks/reports/T-0017.md)

### T-0018 (success)

- `npm install --package-lock-only` still runs the root `prepare` script. In a copy without `node_modules/`, that is `husky: not found` and exit 127, which looks like a network failure. Pass `--ignore-scripts`.
- `husky` sets `core.hooksPath` in the repo where it runs, so a test copy that ran `npm ci` or `npm install` without `--ignore-scripts` has live hooks from then on, whatever the test set earlier.
- A commit body line over 100 characters fails `scripts/commit_lint.py`; wrap bodies.
- When a later step makes an earlier step's test assumptions false (the script removes itself), keep the earlier cases by truncating `STEPS` in a small driver rather than editing their assertions.

Tags: `init-script`, `template`, `gate`, `commit`, `end-to-end`, `tests`

Source: [`reports/T-0018.md`](tasks/reports/T-0018.md)

## public-release

### T-0020 (success)

- After a repository rename, a cloud session's git access still follows the old name; attach the
  renamed and the new repository explicitly before cloning or pushing.
- A newly created repository needs the Claude GitHub App granted to it before any push; the
  symptom is a 403 from `git ls-remote`.
- Pushing a rewritten history to a fresh repository, and writing files that describe it, can be
  blocked by the session's permission classifier; the owner's explicit approval in the session
  is what unblocks it.
- filter-repo applies plain-text rules before regex rules, so a regex rule must not depend on a
  plain-text rule's output, and a rule that does must be ordered accordingly.

Tags: `public-release`, `history-rewrite`, `filter-repo`, `chore`

Source: [`reports/T-0020.md`](tasks/reports/T-0020.md)

## report-validation

### T-0003 (success)

`housekeep.py` reads module-level `REPO_ROOT` and `_schema.REPORTS_DIR` (via `Task.report_path`); tests must patch both to point at a tmp repo.

Tags: `report-validation`, `housekeep`, `port`

Source: [`reports/T-0003.md`](tasks/reports/T-0003.md)

## scripts

### T-0012 (success)

- `git diff --cached --name-only` without `-z` C-quotes only names with a double quote, backslash, control character or non-ASCII byte. Spaces and single quotes pass through, so a test with only those names proves nothing about quoting.

Tags: `scripts`, `bash`, `git`, `nul-safe`, `staged-files`

Source: [`reports/T-0012.md`](tasks/reports/T-0012.md)

## task-scripts

### T-0009 (success)

`git update-index --chmod=-x` also stages the file's current content, so a later `git add` is not needed for edits made before it.

Tags: `task-scripts`, `shebang`, `file-mode`

Source: [`reports/T-0009.md`](tasks/reports/T-0009.md)

## task-tooling

### T-0001 (success)

`Task.report_path` resolves from `_schema.REPORTS_DIR`, which derives from the script's own location. Tests can therefore exercise `task.py` safely by copying `scripts/` and `templates/` into `tmp_path` and running the copy, with no monkeypatching. `task.py new --no-publish` seeds a valid task file there without git. For branch tests, `git init` the same `tmp_path`, commit the report on a task branch, and strip `GIT_*` variables from the test's git calls. A `validate_report` rule that keys on `task.status` can be judged for a target status by passing a copy of the task with that status; no rule change is needed.

Tags: `task-tooling`, `report-gate`, `set-status`, `execution-loop`

Source: [`reports/T-0001.md`](tasks/reports/T-0001.md)

### T-0002 (success)

- The agent worktree started on the initial scaffold commit, not `develop`; fast-forward the new branch to `develop` before reading task files.
- Worktree-isolated Bash refuses commands whose text mentions git alongside other constructs; run git commands as separate plain calls and put multi-line Python in a scratchpad file.

Tags: `task-tooling`, `git-publish`, `backlog`, `worktree`

Source: [`reports/T-0002.md`](tasks/reports/T-0002.md)
