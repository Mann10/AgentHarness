# Phase 13: Context Plumbing (Persist Fix) - Research

**Researched:** 2026-08-01
**Domain:** Session serialization / JSONL persistence plumbing for loaded skill bodies
**Confidence:** HIGH — all findings verified against the live codebase (Level 0/1 internal study, no external dependencies)

## Summary

Phase 13 closes the D-13 leak: loaded skill bodies must persist **in memory for the session** (system-role, summarization-exempt per D-12) but **never serialize to the JSONL session file**. The work is a paired change across `context/message.py` (add `Message.persist`), `session/models.py` (filter `to_events()`, fix `mark_saved()` index alignment), and `session/models.py` (non-serialized `Session.skill_state` field). No new external dependencies — the entire change is stdlib dataclasses.

The single most important finding: the current `mark_saved()`/`unpersisted_events()` pairing assumes `to_events()` is a 1:1 projection of `_context._messages`. Once `to_events()` filters out `persist=False` messages, the `_last_saved_count` index **must count persisted messages only** or repeated saves will produce missing/duplicated events (the index-drift bug the roadmap calls out). `restore_context()` already aligns (`_last_saved_count = len(self._stored_events)`) because stored events are all persisted.

**Primary recommendation:** Add `persist: bool = True` to `Message`, filter `to_events()`, and change `mark_saved()` to count `sum(1 for m in self._context._messages if m.persist)`. Skill bodies are added as `Message(role="system", content=body, persist=False)` — system role gives summarization exemption for free (`context/context.py:88`), `persist=False` keeps them out of JSONL by construction.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Persist flag on messages | Context layer (`context/message.py`) | — | `Message` is the unit of serialization; the flag belongs on the datum itself |
| Persistence filtering | Session layer (`session/models.py`) | — | `to_events()`/`unpersisted_events()`/`mark_saved()` own the JSONL projection |
| Session-scoped loaded-skill state | Session layer (`session/models.py`) | — | `skill_state` is session state, non-serialized by construction (same pattern as `skill_manifest`) |
| Summarization exemption | Context layer (`context/context.py`) | — | Already implemented at line 88 (`role != "system"`); document, don't reimplement |
| Store write path | Store layer (`session/store.py`) | — | Unchanged — consumes `to_events()`/`unpersisted_events()`, no edits needed |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `dataclasses` | 3.x (venv) | `Message.persist` field, `Session.skill_state` field | Existing pattern throughout `session/`, `context/`, `skills/` |
| Python stdlib `json` | 3.x | JSONL serialization in `session/store.py` | Existing store implementation — no changes needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` + `pytest-asyncio` | via pytest.ini (`asyncio_mode = auto`) | All tests async-native | Every new test file |
| `tempfile.mkdtemp()` | stdlib | Isolated session-store fixtures | `tests/test_store.py`, `tests/test_session_manager.py` pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `persist` flag on `Message` | Filter by `role == "system"` at serialization | Role-based filtering would also drop real system messages (summaries, meta); an explicit flag is precise and self-documenting |

**Installation:** None. No new dependencies. `requirements.txt` unchanged (PyYAML already added in Phase 12).

## Architecture Patterns

### System Architecture Data Flow

```
LLM turn
   │  Agent.core.run()
   ▼
ConversationContext.add_message(Message(...))
   │  _messages.append(); total_tokens +=
   ├── to_llm_messages()  ──►  LLM sees ALL messages (incl. skill bodies, system-role)
   └── _maybe_summarize() ──►  context.py:88: role=="system" excluded from to_summarize
                                   (skill bodies survive compaction)
Session.save (Scheduler on_turn_complete / Runtime.shutdown)
   │  store.save(session)
   ▼
Session.to_snapshot_meta()      ← explicit field copy — skill_state NEVER included
Session.to_events()             ← NEW: skips msg.persist == False (skill bodies filtered)
Session.unpersisted_events()    ← to_events()[_last_saved_count:] — index counts PERSISTED msgs
   ▼
JSONL session file  ← never contains skill body content (D-13 closed)
```

### Pattern 1: Non-Serialized-By-Construction
**What:** A `Session` field that must not persist lives as a defaulted dataclass attribute that `to_snapshot_meta()` (explicit-field copy) never includes, guarded by a regression test naming the field.
**When to use:** Any session-scoped runtime state — proven in Phase 12 (`skill_manifest`) and now extended to `skill_state`.
**Example:**
```python
# session/models.py — already ships (Phase 12), replicate for skill_state
skill_manifest: str | None = None  # L46, never in to_snapshot_meta()
```
`to_snapshot_meta()` copies only `type/id/title/created_at/updated_at/system_prompt/metadata` — any field added to the dataclass without an explicit copy line is non-serialized by construction.

### Pattern 2: Persist Flag on the Datum
**What:** `Message.persist: bool = True` default; skill bodies constructed with `persist=False`. `to_events()` filters `not msg.persist`. `to_llm_messages()` does NOT filter (bodies stay live for the model).
**When to use:** Data that lives in context memory but must never hit disk.
**Example:**
```python
# context/message.py
@dataclass
class Message:
    role: str
    content: str
    token_count: int = 0
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    persist: bool = True  # NEW
```
`from_dict()` must NOT read `persist` from the dict (stored events are all persisted by definition; default True is correct).

### Anti-Patterns to Avoid
- **Index drift:** `mark_saved()` using `len(self._context._messages)` after adding the filter — must count persisted messages only, or `unpersisted_events()` mis-slices and repeated saves lose or duplicate events.
- **Filtering `to_llm_messages()`:** The model must keep seeing skill bodies every turn (ACT-03). Only the *serialization* path filters.
- **Serializing `persist` into the JSONL dict:** Stored events should never carry the key — `to_events()` skips non-persisted messages entirely, so the key never appears.
- **Adding a "loaded skills" field to `to_snapshot_meta()`:** `skill_state` must follow the explicit-copy omission pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Message serialization | Custom dict-builder per caller | Existing `to_events()` + persist filter | Single projection point; store/load both consume it |

**Key insight:** The serialization contract is already centralized in `Session.to_events()`/`unpersisted_events()`. The persist filter belongs there — one change point, both `save()` branches (append and full-rewrite) stay correct.

## Common Pitfalls

### Pitfall 1: mark_saved() Index Drift
**What goes wrong:** After filtering `to_events()`, `_last_saved_count` counts raw messages while `to_events()` returns fewer dicts → `unpersisted_events()[count:]` slices past the end (loses events) or re-slices already-saved events (duplicates).
**Why it happens:** `mark_saved()` currently does `self._last_saved_count = len(self._context._messages)` — a 1:1 assumption that breaks the moment filtering exists.
**How to avoid:** `mark_saved()` → `self._last_saved_count = sum(1 for m in self._context._messages if m.persist)`. `restore_context()` needs no change (`len(self._stored_events)` counts persisted events only).
**Warning signs:** Save/resume round-trip tests failing on message count after a `persist=False` message exists mid-conversation.

### Pitfall 2: Skill Bodies Summarized Away
**What goes wrong:** If a skill body were added as a non-system role, `_maybe_summarize()` would fold it into the summary (losing the exact body).
**Why it happens:** `context/context.py:88` exempts `role != "system"` from `to_summarize`.
**How to avoid:** Inject bodies as `role="system"` (D-12) — exemption is free. Document this contract at the injection helper (Phase 14 ships `add_skill_message()`; Phase 13 documents the exemption).
**Warning signs:** A test injecting a skill body as `role="user"` triggers summarization and loses the body.

## Code Examples

### Current `to_events()` (session/models.py:77-86) — must add filter
```python
def to_events(self) -> list[dict]:
    events = []
    for msg in self._context._messages:
        d = {"role": msg.role, "content": msg.content, "token_count": msg.token_count}
        if msg.tool_calls:
            d["tool_calls"] = [asdict(tc) for tc in msg.tool_calls]
        if msg.tool_call_id:
            d["tool_call_id"] = msg.tool_call_id
        events.append(d)
    return events
```
Add `if not msg.persist: continue` at loop top.

### Current `mark_saved()` (session/models.py:104-106) — must count persisted
```python
def mark_saved(self) -> None:
    if self._context is not None:
        self._last_saved_count = len(self._context._messages)
```
Change RHS to `sum(1 for m in self._context._messages if m.persist)`.

### Summarization exemption already present (context/context.py:88)
```python
to_summarize = [
    m for m in self._messages
    if m.role != "system" and id(m) not in recent_ids
]
```
Skill bodies as `role="system"` are excluded by construction — D-12 honored, documented in Phase 13, not reimplemented.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| All messages persist to JSONL | `persist=False` exempts skill bodies | Phase 13 | D-13 leak closed before any real body flows (roadmap ordering rationale) |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Skill bodies are injected as `role="system"` messages (D-12) | Common Pitfalls 2 | If a future phase injects as another role, bodies get summarized; Phase 14's `add_skill_message()` must honor system-role |
| A2 | `restore_context()` needs no index change | Common Pitfalls 1 | Verified against code: `_last_saved_count = len(self._stored_events)` counts stored (persisted) events — correct with the new filter |

## Open Questions

None — the change surface is fully mapped (verified: `Message` 33-line dataclass, `to_events`/`mark_saved` 10-line region, `Session` explicit-copy snapshot, store untouched).

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — pure stdlib dataclass/json change; pytest suite already green at 103 tests).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (`asyncio_mode = auto`) |
| Config file | `pytest.ini` (testpaths = tests) |
| Quick run command | `python -m pytest tests/test_persist.py -x` |
| Full suite command | `python -m pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ACT-03 | Loaded skill body persists in session memory as system-role message | unit | `python -m pytest tests/test_persist.py::test_persist_false_message_in_llm_messages -x` | ❌ Wave 0 |
| ACT-04 | Skill bodies survive summarization (system-role exemption) | unit | `python -m pytest tests/test_persist.py::test_system_role_message_exempt_from_summarization -x` | ❌ Wave 0 |
| ACT-05 | Loaded skill bodies never serialize to JSONL | unit | `python -m pytest tests/test_persist.py::test_persist_false_messages_never_written -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_persist.py -x`
- **Per wave merge:** `python -m pytest -q`
- **Phase gate:** Full suite green (103 existing + new persist tests) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_persist.py` — persist-filter + index-drift + JSONL-clean tests (covers ACT-03/04/05)

## Security Domain

> security_enforcement enabled (absent = enabled). ASVS L1.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | no | No external input surface — internal session serialization |
| V6 Cryptography | no | No secrets/crypto in scope |
| V9 Data Protection (confidentiality) | **yes** | D-13: skill content must never persist to the JSONL session file — the `persist=False` filter + guard tests enforce this |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Skill body content leaking to JSONL session file | Information Disclosure | `to_events()` skips `persist=False`; guard tests assert the JSONL file never contains skill body text |
| Index drift causing lost/duplicated session events | Tampering (integrity) | `mark_saved()` counts persisted messages only; save/resume round-trip tests |
| Summary containing skill body text | Information Disclosure | System-role exemption at `context/context.py:88`; document contract, regression-test it |

## Sources

### Primary (HIGH confidence)
- `context/message.py` (33 lines, full read) — Message dataclass, from_dict
- `context/context.py` (130 lines, full read) — line 88 system-role summarization exemption
- `session/models.py` (177 lines, full read) — to_events (L77-86), mark_saved (L104-106), to_snapshot_meta (L108-117), restore_context (L134-154), skill_manifest field (L46)
- `session/store.py` (142 lines, full read) — save append/rewrite branches (L42-73)
- `harness/session_manager.py`, `harness/runtime.py` (full read) — save triggers (Scheduler on_turn_complete, shutdown)
- `tests/test_store.py`, `tests/test_skills_integration.py` (full read) — existing round-trip + non-serialized guard patterns
- `.planning/phases/12-skills-discovery-manifest/12-04-SUMMARY.md` — Phase 12 seam + non-serialized-by-construction pattern

### Secondary (MEDIUM confidence)
- None needed — no external libraries or frameworks in scope

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against live codebase, zero new deps
- Architecture: HIGH — full read of all touched files
- Pitfalls: HIGH — index-drift mechanism traced line-by-line through `mark_saved`/`unpersisted_events`/store.save

**Research date:** 2026-08-01
**Valid until:** N/A (internal codebase study, not time-sensitive)
