---
task: {id}
outcome: {outcome}
branch: {branch}
commit: {commit}
tags: [{tags}]
---

# Report — {id}: {title}

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
