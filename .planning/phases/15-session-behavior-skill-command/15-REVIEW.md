---
phase: 15-session-behavior-skill-command
reviewed: 2026-08-02T00:00:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - tests/test_skills_load_rpc.py
  - backend/rpc/protocol.py
  - backend/rpc/__init__.py
  - backend/rpc/dispatcher.py
  - backend/rpc/adapter.py
  - harness/runtime.py
  - tui-ink/src/types.ts
  - tui-ink/src/bridge/rpc-client.ts
  - tests/test_skill_command.py
  - main.py
  - skills/limits.py
  - docs/skills-allowed-tools.md
  - tests/test_skills_filter.py
  - skills/filter.py
  - skills/__init__.py
  - tests/test_load_skill.py
findings:
  critical: 0
  warning: 5
  info: 9
  total: 14
status: issues_found
---

# Phase 15: Code Review Report

**Reviewed:** 2026-08-02T00:00:00Z
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

Reviewed the Phase 15 skills-system changes: the `skills.load` RPC method (protocol → dispatcher → adapter → `RuntimeAPI.load_skill_status`), the REPL `/skill` command, the loaded-skill token cap (`skills/limits.py`, enforced in `load_skill`), and the CAP-04 filter contract (`skills/filter.py` + tests + docs).

The core mechanics are sound and well-tested: the `load_skill` check→mark→inject sequence is atomic under asyncio (no `await` between the dedup check, cap check, and record append — verified that `client.count_tokens` is synchronous), so the H-03 TOCTOU defense and the cap accounting hold even under `asyncio.gather`'d parallel `read_skill` calls in `agent/core.py:171`. The dispatcher's `RPCError` passthrough, the adapter's error mapping, and the REPL branch handling all behave as documented and match their tests.

The significant findings are in the **locked contracts**, not the executing code: the CAP-04 enforcement plan documented for Phase 17 is inconsistent with the `skill_state["loaded"]` record shape and with the empty-set semantics of `intersect_allowed_tools` (two semantically opposite outcomes — "nothing allowed" vs "no restriction" — return the same `set()`, and the documented Phase 17 filter step would drop *all* non-skill tools in the common no-restriction case). These will produce incorrect behavior at enforcement time if not corrected. No BLOCKERs found in the currently-executing paths.

## Warnings

### WR-01: CAP-04 enforcement plan reads `allowed_tools` off records that don't carry it

**File:** `docs/skills-allowed-tools.md:52-53`
**Issue:** The locked enforcement plan says: "Collect `allowed_tools` from every skill in `skill_state['loaded']`" then `combined = intersect_allowed_tools([set(s.allowed_tools) for s in loaded])`. But the records written by `RuntimeAPI.load_skill` (`harness/runtime.py:210`) are plain dicts `{"name", "dir", "tokens"}` — they have no `allowed_tools` key. At Phase 17 enforcement, `s.allowed_tools` on a dict raises `AttributeError`, and even conceptually the record shape cannot satisfy the plan. The record shape and the contract doc have drifted.
**Fix:** Either (a) extend the loaded record to include the allowed-tools at load time: `loaded.append({"name": info.name, "dir": str(info.path), "tokens": body_tokens, "allowed_tools": list(info.allowed_tools)})` and document it, or (b) rewrite the enforcement step to re-resolve `SkillStore.lookup(rec["name"]).allowed_tools` instead of reading off the record. Update the doc's snippet to match the chosen shape.

### WR-02: Duplicated security-relevant `RESERVED_SKILL_TOOLS` constant

**File:** `skills/filter.py:5` (and `skills/provider.py:11`)
**Issue:** `RESERVED_SKILL_TOOLS` is defined as two independent `frozenset`s in `skills/filter.py` and `skills/provider.py`. This is an allowlist that must never drift (CAP-03 guarantees `read_skill`/`read_skill_path` survive any filter). `skills/__init__.py` already re-exports the provider's copy, so the filter's private copy is gratuitous.
**Fix:** Delete the local definition and import the canonical one:
```python
from skills.provider import RESERVED_SKILL_TOOLS
```

### WR-03: `intersect_allowed_tools` conflates "nothing allowed" with "no restriction"

**File:** `skills/filter.py:27` (tests lock it in at `tests/test_skills_filter.py:46-48`)
**Issue:** The function returns `set()` for two semantically opposite inputs: (a) disjoint restricted sets (D-13: nothing is allowed) and (b) no restricted skills at all (D-14: no restriction applies). The docs (`docs/skills-allowed-tools.md:30-31,53-55`) say "no restriction to apply" for case (b), yet the documented Phase 17 step filters the tool list by `combined` and re-applies `retain_read_skills(tools, combined)` — which with `combined == set()` drops **every** tool except `read_skill`/`read_skill_path`. The all-unrestricted case — the most common case — would silently disable all real tools. The return value alone cannot distinguish the two cases.
**Fix:** Return a tri-state or expose a separate signal. E.g., return `None` (or a `(has_restriction, allowed)` pair) when no skill restricts, so Phase 17 can skip filtering entirely; keep `set()` only for the disjoint-restriction case. Update `tests/test_skills_filter.py:45-48` to assert the new contract. Escalates to BLOCKER when Phase 17 enforcement lands.

### WR-04: Mark-before-inject leaves a phantom record if injection fails

**File:** `harness/runtime.py:210-212`
**Issue:** The record is appended to `skill_state["loaded"]` *before* `await session.context.add_skill_message(...)`. The D-11 "no partial state" guarantee (tested at `tests/test_load_skill.py:177-191`) holds only for the cap-refusal path, which is before the mark. If `add_skill_message`/`add_message` raises for any reason (e.g., `count_tokens` failure, `total_tokens` accounting error), the record stays in `skill_state["loaded"]` with no body injected — and every subsequent `load_skill`/`load_skill_status` for that skill returns "already loaded" forever in that session. The docstring's "a refused load leaves no partial state" claim is broader than what the code guarantees.
**Fix:** Wrap the append+inject in a compensating rollback:
```python
session.skill_state["loaded"] = loaded
try:
    await session.context.add_skill_message(info.name, body)
except Exception:
    loaded.remove(record)
    session.skill_state["loaded"] = loaded
    raise
```

### WR-05: Internal exception text leaked into RPC responses

**File:** `backend/rpc/dispatcher.py:79-86`
**Issue:** Unknown handler exceptions are returned verbatim as `"Internal error: {exc}"`. Exception text can embed absolute filesystem paths, environment details, or third-party internals (e.g., `SkillStore`/I/O errors from the skill load path), and the TUI surfaces this text as-is (`rpc-client.ts:180`). The `logger.exception(...)` already captures the full traceback server-side — the response message should be generic to avoid leaking internals across the API boundary.
**Fix:** Return a stable generic message and log the details:
```python
logger.exception("Handler error for method '%s'", request.method)
return RPCResponse(id=request.id, error=RPCError(code=INTERNAL_ERROR, message="Internal error"))
```

## Info

### IN-01: Dead `"not_found"` status in `SkillLoadStatus`

**File:** `tui-ink/src/types.ts:9`
**Issue:** The backend never returns `status: "not_found"` — unknown skills raise RPC error `-32001` (`adapter.py:107`), which rejects the `skills.load` promise in `rpc-client.ts`. A caller branching on `status === "not_found"` would silently mis-handle the error path.
**Fix:** Remove `"not_found"` from the union (the error path already covers it via thrown `Error`), or change the backend to return a result with that status instead of an RPC error.

### IN-02: Unused `logger` in `adapter.py`

**File:** `backend/rpc/adapter.py:9,16`
**Issue:** `import logging` and `logger = logging.getLogger(__name__)` are unused — no log call exists in the file.
**Fix:** Remove both.

### IN-03: Request timeout timer never cleared

**File:** `tui-ink/src/bridge/rpc-client.ts:94-99`
**Issue:** The 30s `setTimeout` is not cleared when the request resolves or rejects. Every request schedules a timer that fires later, keeps the Node event loop alive for up to 30s after the last request, and the callback only then discovers the pending entry is gone.
**Fix:** Capture the timer and `clearTimeout` inside the resolve/reject path, e.g. `const timer = setTimeout(...); this.pending.set(id, { resolve: (v) => { clearTimeout(timer); resolve(v) }, reject: (e) => { clearTimeout(timer); reject(e) } })`.

### IN-04: stderr write stream and process handle leaked across `start()`/`stop()` cycles

**File:** `tui-ink/src/bridge/rpc-client.ts:50, 158-167`
**Issue:** `createWriteStream("tui-ink-rpc.log")` is never closed in `stop()`, and `stop()` doesn't await process exit. Reconnecting the TUI (start→stop→start) leaks one open fd per cycle and leaves the old child's exit handlers attached.
**Fix:** Keep a reference to the stream and call `stderrStream.end()` (plus `this.proc.once("exit", ...)` cleanup) in `stop()`.

### IN-05: Responses carry both `result` and `error`

**File:** `backend/rpc/protocol.py:27-32` + `backend/rpc/server.py:126-131`
**Issue:** Dataclass defaults serialize `"result": null` on error responses and `"error": null` on success responses. JSON-RPC 2.0 requires exactly one of `result`/`error`. The current TUI tolerates it (`if (msg.error)` checked first, `rpc-client.ts:179`), but strict clients would reject the messages.
**Fix:** Build the response dict omitting the absent field (or make `RPCResponse` a normal class whose serialization drops the null field).

### IN-06: Deprecated `asyncio.get_event_loop()`

**File:** `main.py:251`
**Issue:** Inside `run_worker` (an async function), `asyncio.get_event_loop()` raises/emits deprecation warnings on 3.12+ depending on context; the running loop is available directly.
**Fix:** Use `loop = asyncio.get_running_loop()`.

### IN-07: Misleading INVALID_PARAMS message for present-but-blank names

**File:** `backend/rpc/adapter.py:101-102`
**Issue:** The check rejects `{"name": ""}`, `{"name": "   "}`, and `{"name": 123}` with `"Missing 'name' in params"` — but the key is present; the value is just invalid. The message misleads TUI-side debugging.
**Fix:** Split the check: `"Missing 'name' in params"` when the key is absent, `"Invalid 'name': must be a non-empty string"` otherwise.

### IN-08: RuntimeError → -32603 mapping conflates cap-breach with genuine internal failures

**File:** `backend/rpc/adapter.py:108-111`
**Issue:** `load_skill_status` raises `RuntimeError` for three distinct conditions — cap breach, `SkillStore` not configured, and no active session — and the adapter maps all of them to `-32603` with the verbatim message. The comment frames this as "the documented cap-breach contract", but the server cannot verify which condition actually occurred; any future `RuntimeError` added to the load path will be presented under the same contract. The message-string contract also makes the TUI depend on user-facing text.
**Fix:** Prefer a dedicated domain code for the cap breach (e.g., a new `SKILL_CAP_EXCEEDED = -32002`) so the TUI can branch structurally instead of string-matching, reserving `-32603` for genuine internal errors.

### IN-09: Unparseable stdout lines silently dropped → 30s hang

**File:** `tui-ink/src/bridge/rpc-client.ts:58-63`
**Issue:** The empty `catch` around `JSON.parse` drops any line that isn't valid JSON. If the backend ever writes a malformed *response* line (or a stray log line reaches stdout despite the stderr redirection), the matching pending promise is never settled and the caller waits the full 30s timeout. It also masks genuine serialization bugs in the backend.
**Fix:** Distinguish startup noise from protocol traffic — e.g., log skipped lines at debug level, and/or reject pending requests for an id referenced in a line that fails to parse.

---

_Reviewed: 2026-08-02T00:00:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
