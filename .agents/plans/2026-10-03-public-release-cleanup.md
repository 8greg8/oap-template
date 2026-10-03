# Plan: clean the repository before making it public

Status: proposed. Owner decisions D1 to D4 below are open.

## Goal

The repository can be made public without exposing the owner's work email, a local filesystem
path or the name of a private downstream project. The third-party method text is
clearly attributed and is not covered by this repository's MIT license. This holds for every
commit and branch, not only the current tree.

## Findings (scan of 2026-10-03)

- Secrets: none. gitleaks over all 102 commits on all branches and detect-secrets over the working
  tree reported no findings.
- Work email: all 50 owner-authored commits carry the owner's work address as author and committer.
  The owner's private Gmail address is the intended one. The other 71 commits are authored by
  `Claude <noreply@anthropic.com>` and stay as they are.
- Local path: an absolute home-directory path to the `source-project` checkout appears in
  `.agents/LESSONS.md` and `.agents/tasks/reports/T-0004.md`, and in 11 diff lines in history.
- Downstream project name: named three times in `.agents/tasks/T-0001-*.md`, eight times in
  history, and once in the body of commit `0b32945`.
- Method text: `strategic_model_init_material.md` is the workshop material "Orchestrated Agentic
  Programming" by Janez Perš, from
  <https://edu.slaif.si/trainings/workshop-orchestrated-agentic-programming>. The file has no
  license notice. The repository `LICENSE` (MIT, "8greg8", the owner's GitHub account) does not
  say that it excludes this file.
- Commit hash citations: 36 hashes of this repository's own commits are cited in task and report
  files. Any history rewrite changes every hash, so these citations go stale.

Out of scope here, unless the owner says otherwise (see D3): `source-project` as a name (98 mentions,
mostly in the workflow-sync plan and T-0002 to T-0006), `Claude-Session:` trailers on 60
commits, and the plan files that quote owner instructions.

## Approach

Content fixes land first on `develop` as one ordinary task. Then a history rewrite produces a
clean copy that carries the same fixes back through every commit. The rewrite is pushed to a
new repository. The existing private repository is never force-pushed, and it stays as an
archive.

### Step 1: content fixes on `develop` (one `docs` task)

1. Replace the absolute path in `.agents/LESSONS.md` and `.agents/tasks/reports/T-0004.md`
   with a generic one: "use the absolute path of the sibling checkout".
2. Replace the downstream project name in T-0001 with "a downstream project". Keep the meaning
   of all three sentences. The Non-goals item stays a Non-goal and is reworded only.
3. Attribute the method text and keep it out of the MIT grant:
   - Add a "Third-party material" section to `README.md`. It names the file, its author,
     title, version and source URL, and states that the MIT license does not cover it.
   - Add one line under the MIT text in `LICENSE`: "`strategic_model_init_material.md` is
     third-party material, copyright its author, and is not covered by this license. See
     README.md."
   - Leave the file itself unchanged, including the author's name and email in its front
     matter. They are the author's own attribution.
4. Gate passes. Independent verify, then merge per `.agents/README.md`.

This task touches `LICENSE`, `README.md`, `.agents/LESSONS.md`, one task file and one report.
No `scripts/` or `[tool]` changes, so nothing is in "Ask first".

### Step 2: rewrite history into a clean copy

Run only once nothing is in flight: every task branch is merged or abandoned, and T-0015 to
T-0018 are done or parked. A branch made before the rewrite cannot be merged into the new
history.

In a fresh mirror clone in a scratch directory, outside this repository:

```bash
git clone --mirror git@github.com:8greg8/oap-template.git oap-clean.git
cd oap-clean.git
# mailmap: maps the work address to the private address. Kept outside the repo.
# replace.txt: maps the local path and the downstream name to their Step 1 wording.
# Kept outside the repo, so the literals are not committed again.
git filter-repo --mailmap ../mailmap --replace-text ../replace.txt \
  --replace-message ../replace.txt
```

filter-repo updates abbreviated hashes cited in commit messages on its own, but not hashes in
file contents. Step 3 handles those. A dry run of this command on a scratch mirror (2026-10-03,
placeholder address) rewrote all 50 owner commits, left no match for either literal or the
work-email domain, and gitleaks reported no leaks.

Check before pushing:
- `git log --all --format='%ae %ce' | sort -u` lists only the private address and
  `noreply@anthropic.com`.
- `git log --all -p` and `git log --all --format=%B` contain neither literal from
  `replace.txt`, and neither does the work-email domain.
- gitleaks over the rewritten history reports no leaks.
- The final tree of `develop` is identical to the Step 1 merge result:
  `git diff <old develop> <new develop>` is empty.

### Step 3: publish

1. Rename the current repository to `oap-template-archive` (stays private).
2. Create a new, empty, private `8greg8/oap-template` and push `main` and `develop` from the
   rewritten mirror. Do not push merged task branches.
3. Add one commit on `develop` that rewrites the 36 cited hashes in task and report files from
   old to new, using `filter-repo/commit-map` from Step 2. Merge `develop` into `main`, or point
   `main` at it, per the template-init plan's decision 1.
4. Apply the GitHub settings from the template-init plan: default branch, template flag.
5. Re-run the scan from this plan on the new repository. Only then switch it to public.

### Step 4: stop it recurring

- The owner sets `git config --global user.email` to the private address on every machine
  that commits here. Sessions that commit as Claude are unaffected.
- Optional: enable GitHub's "Block command line pushes that expose my email" and use the
  GitHub noreply address.

## Alternative: single-commit copy

Push one squashed commit of the Step 1 `develop` tree to the new repository instead of the
rewritten history. It is simpler, and Step 3.3 is not needed. But the task and report files
then cite commits that do not exist anywhere public, and the record of how the template was
built is lost. Use this only if D2 is "no history".

## Owner decisions

- **D1. Method text.** Republishing it publicly needs the author's permission or a license that
  allows it. This could not be checked from here, because the workshop site was unreachable. If
  neither exists, drop the file from the clean copy (add `--path
  strategic_model_init_material.md --invert-paths` to Step 2) and link to the workshop page
  instead. Recommended: ask the author, and hold Step 3.5 until it is settled.
- **D2. History.** Rewritten history (recommended, Steps 2 and 3) or a single commit
  (Alternative).
- **D3. Further scrubbing.** Keep `source-project` mentions and `Claude-Session:` trailers as they
  are (recommended), or add them to `replace.txt`. Stripping trailers needs a message callback,
  not `--replace-message`.
- **D4. Repository name.** The new repository keeps the name `oap-template` and the old one
  becomes `oap-template-archive` (recommended), or the new one gets a new name.

## Risks

- A history rewrite cannot be undone once the new repository is public. Forks and caches keep
  whatever was public. Step 3.5 is the last point where it can be fixed cheaply.
- Every hash changes. Local clones of the old repository must be re-cloned from the new one, not
  pulled.
