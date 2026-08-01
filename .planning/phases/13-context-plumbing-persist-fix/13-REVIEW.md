---
phase: 13-context-plumbing-persist-fix
reviewed: 2026-08-01T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - context/message.py
  - session/models.py
  - context/context.py
  - tests/test_persist.py
findings:
  critical: 1
  warning: 2
  info: 4
  total: 7
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-08-01T00:00:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 13 adds a `Message.persist` field, a persist filter in `to_events()`/`mark_saved()`, a non-serialized `Session.skill_state` field, and 11 contract tests. The persist filter itself is internally consistent: `to_events()` and `mark_saved()` both count only `persist=True` messages, so persist=False skill bodies are correctly excluded from the JSONL file, and `skill_state` is safely omitted from every serialization path (the store uses only explicit copies in `to_snapshot_meta()`/`to_events()`).

However, one critical correctness defect was found and reproduced empirically: the index-based incremental-save mechanism (`unpersisted_events()` slicing by `_last_saved_count`) silently drops the newest messages from the session file when `_maybe_summarize()` removes already-saved messages between saves. This is a data-loss bug in exactly the functions this phase modified, and none of the 11 new tests cover it. All tests pass (11/11).

## Critical Issues

### CR-01: Incremental-save index drifts after summarization — newest messages silently lost from session file

**File:** `session/models.py:103-109` (interacts with `context/context.py:111-122` and `session/store.py:52-69`)
**Issue:** `unpersisted_events()` computes `self.to_events()[self._last_saved_count:]`, and `mark_saved()` stores a *count of persist messages*. This is only sound if the set of persist messages never shrinks. But `_maybe_summarize()` (context/context.py:117-121) *removes* saved messages and *inserts* a summary at index 0. After that, `len(to_events())` can be smaller than `_last_saved_count`, so the slice is `[]` and the next `store.save()` appends **nothing** — the newest user/assistant messages added since the last save are never written to the JSONL file. Reproduced:

```
save1: 4 events written, _last_saved_count=4
summarization fires (removes 2 saved messages, inserts summary)
save2: unpersisted_events() = to_events()[4:] = [] → nothing appended
       "question three" (new user msg) MISSING from file — confirmed
save3: index corrects to 5, "question four" written
```

The conversation history is silently corrupted: the user turn between the summarization and save2 is permanently missing, and the summary event itself is never persisted either. Phase 13 modified `mark_saved()` (line 109) and `to_events()` (line 81) — the exact code where this unsoundness lives — and its contract tests (e.g., `test_repeated_saves_with_persist_false_no_duplicate_events`) assert save-index correctness while never exercising summarization between saves.

**Fix:** Replace the count watermark with one that is immune to list shrinkage. Simplest robust approach — track saved message identities instead of a count:

```python
def mark_saved(self) -> None:
    if self._context is not None:
        # watermark by identity, not position: survives summarization removal
        self._saved_ids = {id(m) for m in self._context._messages}

def unpersisted_events(self) -> list[dict]:
    if self._context is None:
        return []
    saved = getattr(self, "_saved_ids", set())
    events = []
    for msg in self._context._messages:
        if msg.persist and id(msg) not in saved:
            d = {"role": msg.role, "content": msg.content, "token_count": msg.token_count}
            if msg.tool_calls:
                d["tool_calls"] = [asdict(tc) for tc in msg.tool_calls]
            if msg.tool_call_id:
                d["tool_call_id"] = msg.tool_call_id
            events.append(d)
    return events
```

`restore_context()` must seed the same watermark: `self._saved_ids = {id(m) for m in self._context._messages}` after replay. (Messages are kept alive in `_messages`, so `id()` reuse is not a concern.)

## Warnings

### WR-01: `Message.from_dict()` silently drops the `persist` key

**File:** `context/message.py:28-34`
**Issue:** `from_dict()` reconstructs the message without reading `"persist"`, so any event dict carrying that key silently loses the flag. This is asymmetric with `to_events()` (which now filters on `persist`) and is a latent trap: any future serialization path, hand-edited JSONL, or a different store implementation that writes `persist` will round-trip persist=False messages as persist=True — leaking skill bodies into the session file (the exact leak D-13/ACT-05 is meant to close). The new tests enshrine the omission (`test_from_dict_defaults_to_persist`) instead of fixing it.
**Fix:** `persist=d.get("persist", True),` in the `cls(...)` call at line 28-34.

### WR-02: No test covers summarization between saves — the data-loss scenario

**File:** `tests/test_persist.py:44-108`
**Issue:** All store-integration tests use `token_limit=1000` with short messages, so `_maybe_summarize()` never fires mid-sequence. The one test that exercises summarization (`test_system_skill_body_survives_summarization`, line 112) uses a bare `ConversationContext`, never a `Session` + `store.save()`. The phase's headline claim — "consecutive saves append each event exactly once" — is therefore unverified for the summarization path where CR-01 occurs.
**Fix:** Add a test that saves, drives token count past `token_limit * summarize_threshold` (e.g., `token_limit=60`, `count_tokens=len`), saves again, and asserts every new message content is present in the JSONL file exactly once. This test fails against the current implementation and passes after the CR-01 fix.

## Info

### IN-01: `print()` debug output in production summarization path

**File:** `context/context.py:95-101, 108, 124-132`
**Issue:** `_maybe_summarize()` writes multi-line progress banners with `print()` instead of the module's logging (`logging.getLogger`), including on the failure path. Inconsistent with `session/store.py` which uses `logger.warning`. Noise on every compaction event.
**Fix:** Replace with `logger.info(...)`/`logger.warning(...)`.

### IN-02: Tests reach into the store's private `_dir` attribute

**File:** `tests/test_persist.py:52, 87, 105, 156`
**Issue:** `(store._dir / f"{session.id}.jsonl")` couples tests to the store's private layout; a rename breaks five tests mechanically.
**Fix:** Expose a read helper on the store (e.g., `async def raw_text(session_id)`) or use a fixture that returns the file path via a public accessor.

### IN-03: Duplicated save-and-assert pattern across five tests

**File:** `tests/test_persist.py:44-108`
**Issue:** `test_persist_false_message_never_written_to_jsonl`, `test_resumed_session_has_no_skill_body`, `test_repeated_saves...`, and `test_persist_false_between_saves...` repeat the same seed/save/read-file choreography with minor variations, making the assertions' intent harder to diff.
**Fix:** Extract a `_seed_session(store)` helper and a `_file_text(store, session)` helper.

### IN-04: `to_events()`/`unpersisted_events()` still crash on store-loaded sessions; `skill_state` non-serialization is convention-only

**File:** `session/models.py:78-89, 103-105; 47`
**Issue:** (a) `unpersisted_events()`/`to_events()` raise `AttributeError` when `_context is None` (a session from `store.load()` that hasn't been `restore_context()`-ed) — `store.save()` on such a session crashes. The `get_messages()` docstring acknowledges this pattern, but `store.save()` still calls the unguarded path. (b) `skill_state` is documented as "non-serialized by construction", but that holds only by convention at each serialization site — there is no `dataclasses.asdict(session)` today (backend/rpc/server.py:129 applies only to domain events), yet any future generic serializer would leak `skill_state` and `_context`.
**Fix:** (a) Have `store.save()`/`unpersisted_events()` raise a clear `RuntimeError` (or return `[]`) instead of `AttributeError`. (b) Consider `skill_state: dict = field(default_factory=dict, repr=False, compare=False)` and add a `Session.to_dict()`-style audit so future serializers have one choke point.

---

_Reviewed: 2026-08-01T00:00:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
