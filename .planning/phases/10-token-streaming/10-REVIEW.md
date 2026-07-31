---
phase: 10-token-streaming
reviewed: 2026-07-31T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - agent/core.py
  - llm/base.py
  - llm/openai_client.py
  - tests/test_agent_events.py
  - tests/test_agent_streaming.py
  - tests/test_stream_chat.py
  - tui-ink/src/bridge/rpc-client.ts
  - tui-ink/src/components/message.tsx
  - tui-ink/src/panels/conversation-panel.tsx
  - tui-ink/src/store/agent-store.ts
  - tui-ink/src/types.ts
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-07-31T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Reviewed the Phase 10 (Token Streaming) changes: the `StreamChunk` contract and `stream_chat()` async generator in `llm/base.py` and `llm/openai_client.py`, the agent's `_stream_llm_call` emitting `TokenProduced` in `agent/core.py`, the migrated/new tests, and the TUI truncation + bottom-anchored auto-scroll changes. Cross-traced the event flow end-to-end (agent → EventBus → RPC server → `rpc-client.ts` → zustand store → panels) and verified the backend RPC path (`adapter.py`, `server.py`, `scheduler.py`, `context/context.py`) and pytest config (`asyncio_mode = auto` in pytest.ini, so the markerless async tests are valid).

The streaming core is sound: mid-stream failures correctly keep partial content out of persisted context (D-05), tool-call turns emit zero `TokenProduced`, and the tool-call delta assembly handles fragmented `id`/`name`/`arguments` correctly. No security vulnerabilities or data-loss defects were found.

Three warnings were identified, the most significant being that the streaming path **silently drops text content that accompanies tool calls** (a real, common OpenAI behavior the phase's docstring asserts away), and that malformed tool-call JSON from the model bypasses the error-mapping contract. A pre-existing display-correctness chain (tool call IDs never reaching the TUI, results matched by tool name) is also surfaced since it directly affects the tool-turn display this phase's streaming work feeds.

## Warnings

### WR-01: Streaming path discards text content that accompanies tool calls

**File:** `agent/core.py:91-93` (interacts with `agent/core.py:148` and `context/context.py:44`)

**Issue:** `_stream_llm_call` returns `LLMResponse(content=None, tool_calls=tool_calls)` whenever `tool_calls is not None`, discarding the accumulated `content_parts` — even though `TokenProduced` events for that content were already emitted to the UI. The docstring asserts "tool-call turns produce no token events; their content is null anyway," but OpenAI models commonly emit a text preamble ("I'll check the weather for you") *then* the tool-call deltas in the same streamed completion. The non-streaming path (`_call_sdk`, `openai_client.py:84-94`) preserves `content=msg.content` alongside `tool_calls`; the streaming path does not. Consequences:
1. The model's preamble text is dropped from the persisted conversation history (`add_assistant_tool_message(content or "", ...)` stores `""`), so on the next LLM call the history omits words the model actually produced.
2. The TUI streamed those tokens into a streaming assistant message, then `completeAssistantMessage` overwrites it with only the final `ResponseComplete` content — display/history divergence.

**Fix:** Preserve accumulated content on the tool-call response:
```python
if tool_calls is not None:
    return LLMResponse(content=content or None, tool_calls=tool_calls)
return LLMResponse(content=content, tool_calls=None)
```
(and update the docstring to describe the hybrid content+tool_calls turn instead of asserting it can't happen).

### WR-02: Unhandled `json.JSONDecodeError` on malformed assembled tool-call arguments

**File:** `llm/openai_client.py:171`

**Issue:** `json.loads(parts["arguments"])` in the final tool-call assembly sits **outside** the `try/except APIConnectionError/APIError` block (lines 138-164). If the model emits fragments that don't concatenate into valid JSON, the raw `JSONDecodeError` propagates out of `stream_chat`, bypassing the `LLMResponseError` mapping that every other failure path in this client honors. `agent.run()`'s broad `except Exception` will emit `ErrorEvent`, so it won't crash the process — but the user sees a raw parser message ("Expecting value: line 1 column 1 (char 0)") instead of a mapped, actionable error, and any direct consumer of `stream_chat` (e.g., the agent's mid-stream test) gets an undocumented exception type.

**Fix:**
```python
arguments = parts["arguments"]
try:
    parsed = json.loads(arguments) if arguments else {}
except json.JSONDecodeError as e:
    raise LLMResponseError(f"Model returned malformed tool-call JSON: {e}") from e
calls = [
    ToolCall(id=parts["id"], name=parts["name"], arguments=parsed)
    for _, parts in sorted(tool_call_parts.items())
]
```

### WR-03: Tool call IDs never reach the TUI — tool results matched by tool name, not call

**Files:** `agent/core.py:153-158, 173-177`; `tui-ink/src/bridge/rpc-client.ts:203-215`; `tui-ink/src/store/agent-store.ts:126-156`

**Issue:** The tool-call identity chain is broken end-to-end:
1. `agent/core.py` emits `ToolCallEvent` and `ToolResultEvent` **without** `tool_call_id` (both dataclass fields default to `""`), even though `tc.id` is available and is correctly used for `add_tool_message(tc.id, ...)`.
2. `rpc-client.ts`'s `tool_result` handler ignores the payload's `tool_call_id` and calls `store.updateToolResult(p.tool_name, p.result)`.
3. `agent-store.ts`'s `addToolCall` declares but never stores its `callId` parameter; `updateToolResult`/`setToolCallError` match `tc.name === callId || tc.id === callId`.

Net effect: when a single turn issues **multiple tool calls** (e.g., two `get_weather` calls for different cities — a standard pattern), every `tool_result` event updates *every* entry with that name; each entry ends up showing the last result, and `duration` is computed against the wrong start. Pre-existing, but it directly corrupts the display of the tool turns this phase's streaming feed now enables (and the `tc.id === callId` branch is dead code, since the caller always passes a tool name).

**Fix:** thread the real call ID through the chain:
```python
# agent/core.py
await self._emit(ToolCallEvent(
    session_id=self._session.id,
    tool_name=tc.name,
    arguments=tc.arguments,
    tool_call_id=tc.id,
))
```
```ts
// agent-store.ts
addToolCall: (name, args, callId) =>
  set((s) => ({
    toolCalls: [...s.toolCalls, { id: callId || nextToolId(), name, args, status: "running", startedAt: now() }],
    toolCallCount: s.toolCallCount + 1,
  })),
updateToolResult: (callId, result) =>
  set((s) => ({
    toolCalls: s.toolCalls.map((tc) =>
      tc.id === callId ? { ...tc, status: "success" as const, result, duration: now() - tc.startedAt } : tc
    ),
  })),
```
```ts
// rpc-client.ts
case "tool_result": {
  const p = payload as { session_id: string; tool_name: string; result: string; tool_call_id: string }
  store.updateToolResult(p.tool_call_id, p.result)
  break
}
```

## Info

### IN-01: Unused imports in conversation panel

**File:** `tui-ink/src/panels/conversation-panel.tsx:1`

**Issue:** `useEffect` and `useRef` are imported from `react` but never used (auto-scroll is implemented via `column-reverse`, no refs/effects involved). `tsconfig` has `strict: true` but no `noUnusedLocals`, so this compiles silently.

**Fix:** `import { Box, Text } from "ink"` only.

### IN-02: Pointless ternary in `completeAssistantMessage`

**File:** `tui-ink/src/store/agent-store.ts:112`

**Issue:** `status: content ? "idle" : "idle"` — both branches yield `"idle"`. Reads as leftover intent (possibly `content ? "idle" : "error"`), but as written it's dead logic.

**Fix:** `return { conversation: msgs, status: "idle" }`.

### IN-03: RPC stderr log stream robustness

**File:** `tui-ink/src/bridge/rpc-client.ts:50`

**Issue:** `createWriteStream("tui-ink-rpc.log", { flags: "a" })` (a) resolves relative to `process.cwd()` even when the process was started with `--cwd` pointing elsewhere, (b) is never closed/ended in `stop()`, and (c) has no `error` handler — an unhandled `error` event on a Node write stream (e.g., read-only cwd, disk full) throws and crashes the TUI. Pre-existing, but adjacent to this phase's TUI work.

**Fix:** Resolve the path against the resolved project root (`join(cwd, "tui-ink-rpc.log")`), add `stderrStream.on("error", () => {})`, and `stderrStream.end()` in `stop()`.

### IN-04: Empty `tool_calls` list (not `None`) would persist `content: null`

**File:** `agent/core.py:88-93`

**Issue:** `if chunk.tool_calls is not None: tool_calls = chunk.tool_calls` treats `[]` as a tool-call turn, returning `LLMResponse(content=None, tool_calls=[])`. In `run()`, `not response.tool_calls` is then truthy for the empty list, so the text branch runs `add_assistant_message(None)` and `ResponseComplete(content=None)` — the next `to_llm_messages()` call would emit `{"role": "assistant", "content": null}`, which the OpenAI API rejects. The shipped `OpenAIClient` can't produce `tool_calls=[]` (guarded by `if tool_call_parts:`), so this only triggers with a non-conforming `BaseLLMClient` implementation — but the agent should not assume the contract.

**Fix:** `if tool_calls:` instead of `is not None`, or coerce: `tool_calls = chunk.tool_calls or None`.

## Noted (non-findings)

- The markerless `async def` tests in `test_agent_streaming.py`/`test_stream_chat.py` are valid — `pytest.ini` sets `asyncio_mode = auto`.
- The 30s `RpcClient.request` timeout is not a bug for `chat`: `handle_chat` (`adapter.py:28-33`) returns `{"status": "accepted"}` immediately and `submit_prompt` is non-blocking (D-15), so completion is signaled solely via events.
- `message.tsx` renders both the `▸` prefix and the blinking `▊` cursor while streaming — cosmetic duplication, not worth a finding.
- No TUI-side tests exist for the new truncation/auto-scroll/token flow; the store mutations are only exercised manually. Consider adding a zustand store unit test for `truncateStreamingMessage`/`appendToken`/`completeAssistantMessage` ordering in a future phase.

---

_Reviewed: 2026-07-31T00:00:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
