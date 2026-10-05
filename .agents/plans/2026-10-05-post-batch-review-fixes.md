# Plan: fixes from the post-merge review of T-0022 to T-0026

Status: accepted. Tasks T-0027 to T-0030.

**Owner decisions (2026-10-05, session instruction):** "approve all, A and B as recommended".
This approves tasks T-0027 to T-0030 as described here, decision A and decision B. It is the
owner's written approval for the "Ask first" and breaking-change items under § Approvals.

## Source

Three independent post-merge reviews of `develop` at `feaadf8` (2026-10-04/05), run in scratch
copies with a local bare remote:
- changelog tool and pre-push hook (`scripts/changelog.py`, `.husky/pre-push`, `gitflow.sh` finish);
- release flow end to end (`scripts/release.py`, `scripts/next_version.py`), including this
  repository's own first release, a feature release and a hotfix release;
- init script, docs and process (`init_project.py`, the T-0026 documents, the T-0022 to T-0026
  reports).

The gate is green on `feaadf8`. All three reviews found the planned behavior working; the items
below are what they found wrong.

## Decisions

- **A. Who may run `release.py`.** The docs say a release is a human step "as the 'Ask first'
  list requires", but that list only names cutting a release tag by hand. Decision: add running
  `scripts/release.py --yes` or `--push` to `CLAUDE.md`'s "Ask first" list (T-0030).
- **B. The first release's wording.** `v0.1.0` would list T-0023 and T-0024 as "Breaking:"
  changes to a template that was never released. Decision: fold their content into
  `changelog.d/template.added.md` as plain feature bullets and delete
  `changelog.d/T-0023.changed.md` and `changelog.d/T-0024.changed.md` before the first release
  (T-0027).

## Tasks

1. **T-0027: Make the init tests independent of the template's fragments, and fold the first
   release's entries** (chore). Blocks the first release.
   - `tests/test_init_project.py`: `test_dry_run_lists_the_changelog_reset_and_changes_nothing`
     and `test_generated_project_has_no_fragments_and_keeps_the_fragment_readme` assume the
     template still has fragments. After a release removes them, the pre-push gate fails and the
     release push is rejected (reproduced). They write their own fragment into the scratch copy.
   - Decision B.
2. **T-0028: Harden the changelog check and the push hook** (fix, breaking). Parallel with T-0029.
   - `changelog.py`: reject non-bullet, non-continuation, non-blank lines in a fragment (they are
     folded into `CHANGELOG.md` unchecked today); decode fragments strictly as UTF-8 in every path
     and report a non-UTF-8 fragment as a fragment problem; strip a leading BOM; accept `--date`
     only as `YYYY-MM-DD`; turn load and unexpected errors into a distinct exit status and
     message; do not count a rename of an existing fragment as an added fragment.
   - `.husky/pre-push`: report "changelog check failed" (not "missing fragment") for anything but
     a real finding; use the push's remote (`$1`) for the tracking refs.
   - `gitflow.sh finish`: fetch the base before checking against `origin/$base`.
   - `scripts/config/gate.sh`: state that it must stay POSIX-sourceable; a test sources it with `sh`.
   - Tests: make `test_tag_ref_is_not_checked` and `test_hotfix_branch_is_ranged_from_origin_main`
     prove their claims (both pass today with the behavior removed).
3. **T-0029: Fix `release.py` edge cases** (fix, breaking). Parallel with T-0028.
   - `--push` without `--yes` refuses instead of releasing. This reverses the documented
     "`--push` implies `--yes`" so that, as the 2026-10-04 plan says, nothing changes without
     `--yes`.
   - After a failed step, print both stdout and stderr.
   - A modify/delete conflict on a `changelog.d/` fragment during the `develop` update: say to
     resolve it as deleted (`git rm`), so it is not folded twice.
   - A rejected push names a local pre-push hook failure as a possible cause.
   - A repository with no commits gets a refusal, not a traceback.
   - Do not print `git checkout <start>` twice in the finish list.
4. **T-0030: Correct the release docs and add the release to "Ask first"** (docs, breaking).
   Depends on T-0028 and T-0029.
   - Decision A in `CLAUDE.md`.
   - `CONTRIBUTING.md`: the hotfix step hands the release to a human; merge commits run
     `commit-msg` only (no `pre-commit`); the "version not higher than the highest tag" refusal
     applies to `--version` only; behavior changed by T-0028 and T-0029.
   - `DEV_TOOLING_SPEC.md`: drop the stale "README step 4" reference; T-0028/T-0029 behavior.
   - `README.md`: the table row for `DEV_TOOLING_SPEC.md` mentions the changelog.
   - `.agents/README.md`: the orchestrator runs `git pull --ff-only origin develop` before
     `set-status` or dispatch, and rebases an unpushed status commit instead of merging (T-0022
     was started from a stale `develop`, which cost a fix round and left a
     `merge origin/develop into develop` commit).

## Approvals

- **Ask first:** T-0028 changes `scripts/` (including `scripts/config/gate.sh`); T-0029
  changes `scripts/release.py`; T-0030 changes `CLAUDE.md`'s "Ask first" list.
- **Breaking:**
  - T-0029: `--push` without `--yes` now refuses. Today it implies `--yes`, which is documented
    in `release.py --help`, `CONTRIBUTING.md` and `DEV_TOOLING_SPEC.md`, so this changes the CLI
    of a tool under `scripts/`.
  - T-0028: `changelog.py check` gains a distinct exit status for load and unexpected errors,
    which changes its documented exit codes.
  - T-0030: adds an item to "Ask first" (a rule change).
  Each marks its behavior commit breaking; T-0028 and T-0029 are typed `fix!`.
- The owner decisions above are the written approval the orchestrator cites when merging.

## Process corrections made with this plan

- The T-0022 to T-0026 reports gain a line citing the owner approval in
  `.agents/plans/2026-10-04-changelog-and-versioning.md` § Approvals, which `CLAUDE.md` § Merge
  authority requires and none of them had.
- Stale remote branches (`docs/changelog-and-versioning-plan`, `docs/pre-batch-review-T-0022-T-0026`,
  merged task branches) show T-0022 to T-0026 as open. The owner deletes them in GitHub; the
  session's git proxy refuses branch deletion.
