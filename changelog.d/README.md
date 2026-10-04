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
```

A fragment is rejected when it has no bullet or when a bullet is a placeholder: empty text, a
whole-word to-do marker (`todo` or `to-do`), `TBD`, `FIXME` or the literal `<...>`, in any letter
case.

## Check and release

- `python scripts/changelog.py check <base> <tip>` fails when a `feat`, `fix` or breaking commit in
  `<base>..<tip>` has no fragment added in that range, or when any fragment at `<tip>` is invalid.
- `python scripts/changelog.py preview [<version>]` prints the section `assemble` would write,
  headed with today's date when a version is given and `## [Unreleased]` otherwise. It changes
  nothing.
- `python scripts/changelog.py assemble <version>` writes the dated section under
  `## [Unreleased]`, in the order Added, Changed, Deprecated, Removed, Fixed, Security, then
  deletes the fragments. It refuses when `[Unreleased]` is not empty or any file here fails the
  rules above. It edits the working tree and does not stage.

Do not edit `CHANGELOG.md` by hand. It changes only at a release.
