# Changelog fragments

Every change that is a `feat`, a `fix` or a breaking change adds one fragment file here. A release
folds the fragments into `CHANGELOG.md` and deletes them. Because each change owns its own file,
parallel branches never conflict on `CHANGELOG.md`.

## File name

`changelog.d/<id>.<category>.md`

- `<id>` is the task ID (`T-0023`) or the branch topic. Use letters, digits, `-` and `_` only.
- `<category>` is one of: `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`.

Examples: `T-0023.changed.md`, `login-timeout.fixed.md`.

Only files with this name shape are fragments. This README is not one. A change that needs two
categories adds two files.

## Content

One or more bullet lines, each starting with `- `. Write what changed for a user or maintainer of
the project, in the past tense or as a plain statement, in one or two sentences. Indent a
continuation line.

```markdown
- Added the `--dry-run` flag to the export command. It prints what would be written.
```

A fragment is rejected when it has no bullet line or contains placeholder text such as `TODO`,
`TBD`, `FIXME`, `XXX`, "describe the change" or "lorem ipsum".

## Check and release

- `python scripts/changelog.py check <base> <tip>` fails when a `feat`, `fix` or breaking commit in
  `<base>..<tip>` has no fragment added in that range, or when any fragment at `<tip>` is invalid.
- `python scripts/changelog.py preview` prints the section the next release would write and
  changes nothing.
- `python scripts/changelog.py assemble <version>` writes the dated section under
  `## [Unreleased]`, in the order Added, Changed, Deprecated, Removed, Fixed, Security, then
  deletes the fragments. It refuses when `[Unreleased]` is not empty.

Do not edit `CHANGELOG.md` by hand. It changes only at a release.
