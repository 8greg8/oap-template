---
task: {id}
outcome: {outcome}
branch: {branch}
commit: {commit}
tags: [{tags}]
---

# Report — {id}: {title}

Write every section below in concise prose (see `CLAUDE.md`'s "Concise
prose in task and report files" section) — required literal content
(status words, safety confirmations) still stays complete.

## Summary

TODO: two or three sentences. What was asked, what happened, and whether the
acceptance criteria are met. State the outcome plainly; do not soften a failure.

## What was done

TODO: the actual changes, in order.

## Files changed

TODO: one path per line, with a short note on why each changed. Anything here
that is not covered by the task's `touches` list is scope creep — say so.

## Tests run

TODO: exact command, exact result. One per line. Use this vocabulary and no
other: passed / failed / skipped / not run / blocked.

```
uv run pytest tests/test_x.py :: 12 passed
uv run ruff check src tests :: passed
uv run pytest tests/integration :: not run (no test data mount)
```

End the list with the independent-verify line in exactly this form. The
orchestrator replaces `pending` with `passed (commit <hash>; gate <record-key>;
<counts>)`, or with `failed` or `blocked`. `<hash>` is the commit verified.
`<record-key>` is the key of the gate record the verifier's full gate run wrote
(7 to 64 hex digits). `<counts>` is the verifier's own result, such as the number
of tests passed. The `gate <record-key>` part is optional: reports written before
it existed use `passed (commit <hash>; <counts>)` and still validate, but a part
that starts with `gate ` must hold a well-formed key. Do not state the verify
status in `## Summary`; the verify line records it. A `done` task whose line says
`not run` or `pending` fails `report.py validate`.

```
Independent verify agent (fresh context) :: pending
```

Do not write "all tests passed" unless the full relevant suite was actually run.

## Documentation impact

TODO: docs changed, or "none needed" with a reason.

## Safety confirmations

- [ ] No secrets, credentials, or production paths committed.
- [ ] No files changed outside the task's declared `touches` scope.
- [ ] No skipped or unrun test reported as passing.
- [ ] `.agents/tasks/BACKLOG.md` and other tasks' files were not modified.
- [ ] Branch pushed; nothing merged.

## Known limitations

TODO: what this change does not cover, and what remains unproven.

## Follow-up recommended

TODO: concrete next tasks, if any. Describe them well enough that the
orchestrator can turn each into a work order with `task.py new`.

## Lessons learned

TODO: what a future agent hitting a similar problem should know — a wrong
assumption that cost time, a non-obvious repo constraint, a command that does
not work here and what does instead. Omit generic advice; write only what is
specific to this repo. Entries are harvested into `.agents/LESSONS.md` and
grouped by the `tags` in this report's frontmatter, so choose those tags to
match how a future task would search.
