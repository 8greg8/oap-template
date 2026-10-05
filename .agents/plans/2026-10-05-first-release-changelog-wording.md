# Plan: changelog wording before the first release, and the Ask-first tag wording

Status: accepted. Tasks T-0031 and T-0032.

**Owner decisions (2026-10-05, session instruction):** "go ahead with all of it", after the
orchestrator proposed the points below. This approves tasks T-0031 and T-0032 as described here, the
deletion of `changelog.d/T-0028.fixed.md`, `changelog.d/T-0029.fixed.md` and
`changelog.d/T-0030.changed.md` once their content is folded into `changelog.d/template.added.md`,
and the rewording of two `CLAUDE.md` "Ask first" items. It is the owner's written approval for the
"Ask first" and breaking-change items under § Approvals.

## Problem

1. **Fragments written as deltas before a first release.** `v0.1.0` is the first release. The
   fragments of T-0028, T-0029 and T-0030 say "no longer", "used to" and "Breaking:" about behavior
   that was never released, so a reader of the first changelog sees changes to nothing. T-0027
   already folded the earlier fragments into `changelog.d/template.added.md` for this reason
   (decision B of `2026-10-05-post-batch-review-fixes.md`).
2. **Overlapping "Ask first" items in `CLAUDE.md`.** "Cutting a release tag by hand (outside the
   tagging step defined in `CONTRIBUTING.md`)" and the item on `scripts/release.py` ("the tagging
   step named in the previous item is this script, so it is not exempt") read as contradicting each
   other.
3. **A stale reference in `DEV_TOOLING_SPEC.md`.** Line 8 cites "`README.md` step 3". A generated
   project's README has no numbered steps, and in the template step 3 runs the init script.

## Decisions

- **Keep changelog fragments.** They stop parallel branches conflicting on `CHANGELOG.md` and make
  a versioned push without an entry impossible. The wording problem exists only until a tag exists:
  after `v0.1.0`, "no longer implies `--yes`" describes released behavior.
- **A wording rule for the period before the first release.** While no `vX.Y.Z` tag exists, a
  fragment describes the project as it will first ship: plain "added" bullets, with no "Breaking:"
  and no "no longer", "used to" or "now". The rule is documentation and a verifier check, not code.
- **Curate fragments before every release.** The release dry run prints the exact section. Fragments
  are plain files, so the owner merges, rewords or deletes them before running `release.py --yes`.
  This also covers a bug that one unreleased task introduces and a later one fixes.
- **Split the tag items cleanly.** "Ask first" keeps one item for creating or moving a tag by hand
  (any tag not created by `scripts/release.py`) and one for running `release.py --yes` or
  `--yes --push`. The sentence "so it is not exempt" goes, because the first item no longer exempts
  anything.

## Tasks

1. **T-0031: Fold the post-batch fragments and document the pre-release wording rule** (docs).
   - Fold the content of `changelog.d/T-0028.fixed.md`, `changelog.d/T-0029.fixed.md` and
     `changelog.d/T-0030.changed.md` into `changelog.d/template.added.md` as plain feature bullets,
     then delete the three fragments.
   - `changelog.d/README.md`: the wording rule for the period before the first release.
   - `CONTRIBUTING.md` § Versioning: the curate-before-release step.
   - `.agents/README.md`: the verifier checks fragment wording against the rule.
2. **T-0032: Clarify the tag items in Ask first and drop the stale README reference** (docs,
   breaking). Depends on T-0031.
   - `CLAUDE.md`: reword the tag item; remove "so it is not exempt" from the release item.
   - `CONTRIBUTING.md` and `DEV_TOOLING_SPEC.md`: remove the references to the old wording; drop the
     "`README.md` step 3" sentence.
   - `changelog.d/T-0032.added.md`, worded by the rule above. The `CLAUDE.md` commit is
     `docs(claude)!:` with a `BREAKING CHANGE:` footer naming the reworded items.

T-0032 depends on T-0031 because both edit `CONTRIBUTING.md`, and T-0032's fragment follows the
rule T-0031 writes down. Run them one after the other: parallel test runs share a pytest temp
directory and produce spurious fixture errors.

## Approvals

- **Ask first:** T-0032 changes `CLAUDE.md`'s "Ask first" list (a rule change). T-0031 deletes three
  tracked fragments, which the owner approved above.
- **Breaking:** T-0032 changes the rule text agents follow; its `CLAUDE.md` commit is marked
  breaking. T-0031 is documentation and fragment folding only and carries no breaking marker.
- The owner decisions above are the written approval the orchestrator cites when merging.
