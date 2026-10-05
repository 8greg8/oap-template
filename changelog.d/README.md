# Changelog fragments

Every change that is a `feat`, a `fix` or a breaking change adds one fragment file here. A release
folds the fragments into `CHANGELOG.md` and deletes them. Because each change owns its own file,
parallel branches never conflict on `CHANGELOG.md`.

## File name

`changelog.d/<id>.<category>.md`

- `<id>` is the task ID (`T-0023`) or the branch topic. Use letters, digits, `-` and `_` only.
- `<category>` is one of: `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`.

Examples: `T-0023.changed.md`, `login-timeout.fixed.md`.

Every file in this directory except this README must have that name; any other name fails the
check as a bad name. This README is never checked, folded or deleted. A change that needs two
categories adds two files.

## Content

One or more bullets, each a line starting with `- ` or `* `. Write what changed for a user or
maintainer of the project, in the past tense or as a plain statement, in one or two sentences.
Indent a continuation line.

```markdown
- Added the `--dry-run` flag to the export command. It prints what would be written.
  It is off by default.
```

A fragment may hold only three kinds of line, because the whole file is folded into `CHANGELOG.md`
as written:

- a bullet line, starting with `- ` or `* `;
- an indented continuation line, directly after a bullet or another continuation line;
- a blank line.

Any other line is rejected: an intro sentence, a heading, stray prose. An indented line after a
blank line, or before the first bullet, is rejected too.

A fragment is also rejected when it has no bullet, or when a bullet is a placeholder: empty text, a
whole-word to-do marker (`todo` or `to-do`), `TBD`, `FIXME` or the literal `<...>`, in any letter
case.

The file must be valid UTF-8. A file that is not is reported as an invalid fragment. One leading
byte order mark (BOM) is ignored.

## Before the first release

While no `vX.Y.Z` tag exists, nothing has been released, so there is no earlier behavior to change.
A fragment describes the project as it will first ship: plain "added" bullets that state what the
project does. Do not start a bullet with "Breaking:", and do not use "no longer", "used to" or
"now", because each of them describes a change to something that was never released.

Wrong, before the first release:

```markdown
- Breaking: `--push` no longer implies `--yes`. It used to release without asking.
```

Right, before the first release:

```markdown
- `--push` requires `--yes` and does not imply it. Without `--yes` it exits 2 and changes nothing.
```

After the first release a fragment describes a change to released behavior, and a breaking change
starts with "Breaking:". Before any release, the owner reads the release dry run's changelog
section and merges, rewords or deletes fragments that read wrong; a fix to something the same
release introduced belongs in one bullet or none.

## Check and release

- `python scripts/changelog.py check <base> <tip>` fails when a `feat`, `fix` or breaking commit in
  `<base>..<tip>` has no fragment added in that range, or when any fragment at `<tip>` is invalid.
  Renaming a fragment that exists at `<base>`, or deleting and adding it again, does not count as
  adding one. Exit status: 0 passes; 1 a failed check or an invalid fragment; 2 a usage error or a
  git failure; 3 an internal error.
- `python scripts/changelog.py preview [<version>]` prints the section `assemble` would write,
  headed with today's date when a version is given and `## [Unreleased]` otherwise. It changes
  nothing.
- `python scripts/changelog.py assemble <version>` writes the dated section under
  `## [Unreleased]`, in the order Added, Changed, Deprecated, Removed, Fixed, Security, then
  deletes the fragments. It refuses when `[Unreleased]` is not empty or any file here fails the
  rules above. It edits the working tree and does not stage. `--date` takes only `YYYY-MM-DD`.

Do not edit `CHANGELOG.md` by hand. It changes only at a release.
