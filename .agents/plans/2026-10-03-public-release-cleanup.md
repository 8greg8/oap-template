# Plan: clean the repository before making it public

Status: accepted. Tasks T-0019 and T-0020.

**Owner decisions (2026-10-03, session instruction):** the method text is treated as MIT-licensed
public material of the SLAIF project, with its funding acknowledgement. History is kept and
rewritten (D2). The workflow-sync source project's name, including its two-letter short form, and
the `Claude-Session:` commit trailers are removed as well (D3). No rule is added to stop future
sessions from adding `Claude-Session:` trailers. The new repository keeps the name `oap-template` and the current one
becomes `oap-template-archive` (D4). This is the owner's written approval for the history
rewrite in T-0020.

## Goal

The repository can be made public without exposing the owner's work email, a local filesystem
path, the name of a private downstream project, the name of the workflow-sync source project or
session links. The third-party method text is attributed to its author. This holds for every
commit, not only the current tree.

This plan does not quote the literals it removes. A file that quoted them would have to be
rewritten itself. They are found in the repository as described below.

## Findings (scan of 2026-10-03)

- Secrets: none. gitleaks over all commits on all branches and detect-secrets over the working
  tree reported no findings.
- Work email: all 51 owner-authored commits carry the owner's work address as author and committer.
  It should be the owner's private Gmail address. The other commits are authored by
  `Claude <noreply@anthropic.com>` and stay as they are.
- Local path (L1): the absolute home-directory path in `.agents/LESSONS.md:139` and
  `.agents/tasks/reports/T-0004.md:85`.
- Downstream project name (L2): the backticked project name in
  `.agents/tasks/T-0001-*.md` lines 25, 56 and 86, and in the body of commit `b973ccf`.
- Source project name (L3): the project named in the title of
  `.agents/plans/2026-10-03-workflow-sync.md`. On `develop` it is on 37 lines (45 occurrences)
  in 11 files, and it appears in commit messages such as `0b32945`. L1 contains L3. L3u, the same
  name with the hyphen written as an underscore, is at `.agents/plans/2026-10-03-workflow-sync.md:129`.
- Short form of L3 (L3s): the lowercase two-letter abbreviation of L3, used as a whole word in
  prose and path prefixes (for example `L3s:CLAUDE.md`, `L3s's`). About 70 occurrences in the
  same 11 files on `develop`, and some in history. L3V, its uppercase form, is a shell variable at
  `.agents/plans/2026-10-03-workflow-sync.md` lines 315, 317 and 320. A search of all history
  found the short form only in prose and in that variable, never in lock files or hashes.
- Session trailers: about 65 commit messages end with a `Claude-Session:` line. The number grows
  with each session commit.
- Method text: `strategic_model_init_material.md` is "Orchestrated Agentic Programming", version
  1.0.1, by Janez Perš, published as SLAIF workshop material at
  <https://edu.slaif.si/trainings/workshop-orchestrated-agentic-programming>. Neither the file
  nor the page shows a license. The page renders client-side and could not be read from the
  session container.
- Commit hash citations: about 37 hashes of this repository's own commits are cited in task,
  report and plan files. The rewrite changes every hash.

## Replacements

The same replacements apply to the tree (T-0019) and to all history (T-0020). Because
they match, the rewritten `develop` tree must be identical to the `develop` tree after T-0019.

| Literal | Replacement |
|---|---|
| P1: the home-directory prefix in front of L3 inside L1, ending in `/` | `/path/to/` |
| L2 | `downstream-project` |
| L3 | `source-project` |
| L3u | `source_project` |
| L3V followed by `=..` | `SRC=..` |
| `"$` L3V `"` | `"$SRC"` |
| L3s as a whole word, lowercase only (regex `\b<L3s>\b`, case-sensitive) | `source-project` |

L1 therefore becomes `/path/to/source-project`. All rules but the last are plain text.
filter-repo applies every plain-text rule before any regex rule. The last rule depends on that
order: it must run after L3 is replaced, or it would turn L3 into `source-project-system`.
T-0019 applies the rules to the tree in the same order. No plain-text rule depends on another;
a dry run showed that a regex rule for all of L1 never matched once L3 had been replaced, which
is why P1 is a prefix rule.

## Step 1 (T-0019): fix the tree on `develop`

- Apply the replacements to every tracked file that contains a literal.
- Add `NOTICE.md`. It names the method text's file, title, version, author and source URL,
  states that the file is included under the MIT License as public SLAIF workshop material and
  that its copyright stays with the author, and quotes the acknowledgement: "We acknowledge the
  support of the EC/EuroHPC JU and the Slovenian Ministry of HESI via the project SLAIF (grant
  number 101254461)."
- Add one line to `LICENSE` that points to `NOTICE.md` for third-party material.
- `README.md` is not touched, because T-0018 owns it.

## Step 2 (T-0020): rewrite history into the new repository

The mirror must be a full clone from GitHub; `git rev-parse --is-shallow-repository` must print
`false`. Preconditions: T-0015 to T-0019 are merged, no other task branch is open, and the owner has
renamed this repository to `oap-template-archive` and created an empty private
`8greg8/oap-template`.

In a mirror clone in a scratch directory, with a mailmap and a replacements file kept outside
the repository:

```bash
git filter-repo --mailmap ../mailmap \
  --replace-text ../replace.txt --replace-message ../replace.txt \
  --message-callback 'import re; return re.sub(rb"\n*Claude-Session: [^\n]*", b"", message)'
```

filter-repo updates abbreviated hashes cited in commit messages on its own. A dry run of this
exact command with all seven rules, on a full mirror of all branches (2026-10-03, placeholder
address), rewrote all 51 owner commits and left no match for any literal or the work-email domain
in contents or messages, and no `Claude-Session:` line in messages. The rewritten plan's shell
lines read `SRC=../source-project` and `"$SRC"`. An independent verify reproduced the four-rule
version.

Before pushing, check:
- Author and committer addresses are only the private address and `noreply@anthropic.com`.
- `git log --all -p` and `git log --all --format=%B` contain no literal and no work-email
  domain, and no message line starts with `Claude-Session:`. Plan text that names the trailer is
  expected.
- gitleaks over the rewritten history reports no leaks.
- `git diff <old develop> <new develop>` is empty.

Then push `main` and `develop` only. Then one commit on `develop` maps the cited hashes from
old to new using `filter-repo/commit-map`, and the scan above is re-run on the new repository.

## Step 3 (owner): publish

1. Apply the GitHub settings from the template-init plan (default branch, template flag).
2. Switch `oap-template` to public. `oap-template-archive` stays private.
3. Set `git config --global user.email` to the private address on every machine that commits
   here. Optionally enable "Block command line pushes that expose my email".
4. Re-clone. Local clones of the old repository cannot be pulled into the new one.

## Risks

- After the switch to public, forks and caches keep whatever was public. The scan before the
  switch is the last cheap fix point.
- A task branch made before the rewrite cannot be merged into the new history.
- Sessions add `Claude-Session:` trailers to new commits by default. Unless a rule says
  otherwise, commits made after the rewrite carry them again.
