---
phase: 13-context-plumbing-persist-fix
fixed_at: 2026-08-01T20:45:13Z
review_path: .planning/phases/13-context-plumbing-persist-fix/13-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 13: Code Review Fix Report

**Fixed at:** 2026-08-01T20:45:13Z
**Source review:** .planning/phases/13-context-plumbing-persist-fix/13-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### CR-01: Incremental-save index drifts after summarization — newest messages silently lost from session file

**Files modified:** `session/models.py`
**Commit:** `dc33600`
**Applied fix:** Replaced the positional `_last_saved_count` watermark (an index into `to_events()`) with an identity watermark `_saved_messages = {id(msg): msg}` built in `mark_saved()` and seeded identically in `restore_context()`. `unpersisted_events()` now iterates live messages and returns only those whose identity is not in the watermark, so removing already-saved messages via `_maybe_summarize()` can no longer shift the write pointer and drop the newest messages.

**Important deviation from the review suggestion:** The reviewer's suggested `_saved_ids = {id(m) for m in ...}` (a set of bare `id()` integers) was **empirically shown to be broken during testing**. When summarization removes messages from `_messages`, those objects are garbage-collected and Python can reuse their `id()` for a newly-created message — so a brand-new message could be wrongly classified as "already saved" and dropped, reproducing the same data-loss symptom. The fix therefore stores `{id(msg): msg}` (a dict whose values hold strong references), guaranteeing an `id()` is never recycled while the watermark is live. The regression test (WR-02) fails against both the original code and the bare-`{id(m)}` variant, and passes deterministically (10/10 repeated runs) with the strong-reference dict.

### WR-01: `Message.from_dict()` silently drops the `persist` key

**Files modified:** `context/message.py`
**Commit:** `cd8039a`
**Applied fix:** Added `persist=d.get("persist", True),` to the `cls(...)` call in `from_dict()`, so event dicts carrying the `persist` key round-trip the flag instead of defaulting every reconstruction to `persist=True`. Prevents skill bodies from leaking into the JSONL file through any future serialization path (D-13/ACT-05).

### WR-02: No test covers summarization between saves — the data-loss scenario

**Files modified:** `tests/test_persist.py`
**Commit:** `10757be`
**Applied fix:** Added `test_summarization_between_saves_does_not_lose_new_messages`, which saves a 4-message session, drives the token count past `token_limit * summarize_threshold` (`token_limit=60`, `count_tokens=len`) so `_maybe_summarize()` removes the already-saved messages and inserts a summary, then saves again and asserts every new message content (plus the summary event) is present in the JSONL file exactly once. Verified to **fail against the original positional-index implementation** (`assert 0 == 1` — "question four" missing from file) and pass after the CR-01 fix.

## Skipped Issues

None — all in-scope findings were fixed.

---

_Fixed: 2026-08-01T20:45:13Z_
_Fixer: OpenCode (gsd-code-fixer)_
_Iteration: 1_
