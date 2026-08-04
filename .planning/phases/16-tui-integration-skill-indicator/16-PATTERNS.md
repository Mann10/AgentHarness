# Phase 16: TUI Integration (Skill Indicator) — Pattern Map

**Mapped:** 2026-08-03
**Files analyzed:** 12 (5 backend MOD + 1 backend NEW + 6 TUI MOD)
**Analogs found:** 12 / 12 — every file is a mechanical extension of an existing pattern (Phase 9 D-09 five-touchpoint pipeline, Phase 15 slash-command + store patterns). No new architecture, no new dependencies.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `harness/events.py` | model (event dataclass) | event-driven | same file — `TurnStarted`/`ToolCallEvent` (events.py:15-78) | exact (same file) |
| `harness/__init__.py` | config (barrel export) | n/a | same file — `__all__` block (lines 42-63) | exact (same file) |
| `harness/runtime.py` | service | event-driven (emission) | same file — `load_skill` (178-213) insertion point; publish pattern from `harness/scheduler.py:62-66` + `EventBus.publish` (event_bus.py:50-75) | role-match |
| `backend/rpc/protocol.py` | config (wire contract enum) | request-response | same file — `NotificationType` (78-87) | exact (same file) |
| `backend/rpc/server.py` | server (event forwarder) | event-driven | same file — `_DOMAIN_TO_NOTIFICATION` (53-61), `_PAYLOAD_EXTRACTORS` (115-123), `start()`/`shutdown()` (161-183) | exact (same file) |
| `tests/test_skill_loaded_notification.py` (NEW) | test | event-driven + request-response | `tests/test_skills_load_rpc.py` (fixtures 167-215), `tests/test_skills_e2e.py` (`_build_runtime` 54-75), `tests/test_agent_events.py` (collector 32-43) | role-match |
| `tui-ink/src/types.ts` | model (types) | request-response | same file — `EventPayload` union (67-74), payload interfaces (25-65), `Message` (88-95), `AgentState` (97-109) | exact (same file) |
| `tui-ink/src/store/agent-store.ts` | store (zustand) | event-driven | same file — `addNotice` (170-176), `addError` (178-185), `resetConversation` (197-204), `loadConversation` (206-218) | exact (same file) |
| `tui-ink/src/bridge/rpc-client.ts` | bridge/controller | event-driven | same file — `handleEvent` switch (199-282), `loadSkill()` (140-142) | exact (same file) |
| `tui-ink/src/app.tsx` | component (InputBar controller) | request-response | same file — `/session`/`/new`/`/sessions` branches (48-64) | exact (same file) |
| `tui-ink/src/components/footer.tsx` | component (view) | request-response | same file — hint row (4-15); `useWindowSize` from `session-picker.tsx:29` | exact (same file) |
| `tui-ink/src/components/message.tsx` | component (view) | request-response | same file — notice branch (43-51), error branch (53-61) | exact (same file) |

---

## Pattern Assignments

### `harness/events.py` (model, event-driven)

**Analog:** same file — existing event dataclasses (events.py:15-78)

**Event dataclass pattern** (events.py:15-19, 63-68 — `TurnStarted`, `TokenProduced`):
```python
@dataclass
class TurnStarted(HarnessEvent):
    """Emitted when a prompt begins processing by the agent."""
    session_id: str = ""
    prompt: str = ""
```
New `SkillLoadedEvent` follows identically: `@dataclass class SkillLoadedEvent(HarnessEvent)` with `session_id: str = ""` and `skill: str = ""`. Docstring should note D-07/D-08 (fires ONLY on real loads; `session_id` carried for wire `request_id`, NOT in payload — D-06 `{skill}` only).

**Event constant pattern** (events.py:71-78):
```python
# Event type name constants (for subscriber registration)
EVENT_TURN_STARTED = "TurnStarted"
...
EVENT_CANCELLED = "CancelledEvent"
```
Add `EVENT_SKILL_LOADED = "SkillLoadedEvent"` — **name == class name** is a hard contract: `EventBus.publish` routes on `type(event).__name__` (event_bus.py:58) and `_DOMAIN_TO_NOTIFICATION.get(domain_type, ...)` keys on it (server.py:210-211).

---

### `harness/__init__.py` (config, barrel export) — optional but for consistency

**Analog:** same file — import block (lines 9-25) + `__all__` (42-63)

Add `SkillLoadedEvent` to the `from harness.events import (...)` block and `EVENT_SKILL_LOADED` to the constant list, plus both names in `__all__`. This is a mechanical two-spot edit (imports + `__all__`); nothing lazy — `events.py` has no circular-import risk (comment at line 27 documents which modules are lazy and why).

---

### `harness/runtime.py` (service, event-driven emission)

**Analog:** same file `load_skill` (178-213) — the emission point is inserted there; publish pattern from `harness/scheduler.py:62-66` + `EventBus.publish` (event_bus.py:50-75)

**Import pattern** (runtime.py:19 — alongside existing EventBus import):
```python
from harness.event_bus import EventBus
```
Add: `from harness.events import SkillLoadedEvent`.

**Emission point** — insert strictly between runtime.py:212 and :213:
```python
        loaded.append({"name": info.name, "dir": str(info.path), "tokens": body_tokens})
        session.skill_state["loaded"] = loaded
        await session.context.add_skill_message(info.name, body)
        # D-07/D-08: emit ONLY after the body is in context — never on the
        # already_loaded early-return (:196) or cap refusal (:204-207).
        await self._event_bus.publish(SkillLoadedEvent(session_id=session.id, skill=info.name))
        return f"Loaded skill {info.name}"             # D-05 short ack
```

**Publish contract** (event_bus.py:50-75): `publish` is `async`, routes on `type(event).__name__`, runs handlers concurrently with `gather(return_exceptions=True)`, never propagates handler exceptions. Mirror of scheduler.py:62-66 (`async def _emit_to_bus(event): await self._bus.publish(event)`). The runtime already exposes `self._event_bus` (property at 162-165).

**Critical anti-patterns** (from RESEARCH): do NOT emit from `load_skill_status` (215-232) — it dedup-checks then delegates to `load_skill`; emitting there would double-fire. Do NOT emit on the `already_loaded` early-return (195-196), the `KeyError` lookup (192), or the cap-refusal `raise RuntimeError` (204-207).

---

### `backend/rpc/protocol.py` (config, wire contract enum)

**Analog:** same file — `NotificationType` (78-87)

**Enum pattern** (protocol.py:78-87):
```python
class NotificationType(str, Enum):
    """Maps domain event types to notification type strings (D-09)."""
    turn_started = "turn_started"
    tool_call = "tool_call"
    tool_result = "tool_result"
    token = "token"
    response_complete = "response_complete"
    cancelled = "cancelled"
    error = "error"
```
Add `skill_loaded = "skill_loaded"` as the 8th member. Note: `EventPayload` (59-64) and `RPCNotification` (67-72) need NO changes — the wire format is generic (`{type, request_id, payload}`).

---

### `backend/rpc/server.py` (server, event forwarder)

**Analog:** same file — mapping dict, extractor functions, `start()`/`shutdown()`

**Import addition** (extend the events import block, lines 30-46):
```python
from harness.events import (
    ...
    SkillLoadedEvent,
    ...
    EVENT_SKILL_LOADED,
)
```

**Mapping entry** (append to `_DOMAIN_TO_NOTIFICATION`, lines 53-61):
```python
_DOMAIN_TO_NOTIFICATION: dict[str, str] = {
    EVENT_TURN_STARTED: NotificationType.turn_started.value,
    ...
    EVENT_ERROR: NotificationType.error.value,
    EVENT_SKILL_LOADED: NotificationType.skill_loaded.value,   # NEW
}
```

**Extractor** (mirror `_extract_cancelled_payload`, lines 106-107 — the smallest existing extractor):
```python
def _extract_skill_loaded_payload(event: SkillLoadedEvent) -> dict:
    """D-06: payload is {skill: canonical name} ONLY — status lives in the RPC ack."""
    return {"skill": event.skill}
```

**Extractor registration** (append to `_PAYLOAD_EXTRACTORS`, lines 115-123):
```python
_PAYLOAD_EXTRACTORS: dict[str, callable] = {
    ...
    EVENT_ERROR: _extract_error_payload,
    EVENT_SKILL_LOADED: _extract_skill_loaded_payload,   # NEW
}
```

**subscribe/unsubscribe** (append in `start()`, lines 161-167, and mirror in `shutdown()`, lines 177-183):
```python
        await self._event_bus.subscribe(EVENT_SKILL_LOADED, self._on_event)   # start()
        ...
        await self._event_bus.unsubscribe(EVENT_SKILL_LOADED, self._on_event) # shutdown()
```

**Why the extractor only governs `payload`:** `_event_to_notification` (202-233) derives `request_id` automatically via `getattr(event, "session_id", "") or event.event_id` (line 214) — that's why `SkillLoadedEvent.session_id` must exist on the dataclass even though D-06 excludes it from the payload. If the extractor were missing, the fallback `asdict(event)` (line 222) would leak `session_id` and `event_id` into the payload — the extractor is the enforcement point for the `{skill}`-only contract.

---

### `tests/test_skill_loaded_notification.py` (NEW — test, event-driven + request-response)

**Analogs:** `test_skills_load_rpc.py` (fixtures: `skills_root` 167-176, `store` 179-181, `runtime` 184-215), `test_skills_e2e.py` (`_build_runtime` 54-75), `test_agent_events.py` (async collector 32-43). No test currently drives `RPCServer` — the round-trip test introduces the in-process `RPCServer` + monkeypatched `_write_json` approach (RESEARCH validation architecture).

**`skills_root` fixture** (test_skills_load_rpc.py:167-176 — copy verbatim; creates one demo skill):
```python
@pytest.fixture
def skills_root(tmp_path: Path) -> Path:
    """A skills root with one demo skill (frontmatter-name authority, D-04)."""
    skill_dir = tmp_path / "demo-greeter"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-greeter\ndescription: A demo skill\n---\n\n# Demo\n\nHello body\n",
        encoding="utf-8",
    )
    return tmp_path
```

**`_build_runtime` real-stack pattern** (test_skills_e2e.py:54-75 — real SkillStore + real ToolRegistry + SkillToolProvider; only the LLM client stubbed via `_make_stub_client` at 31-51). The round-trip test also needs the `SkillToolProvider` registered (`registry.add_provider("__skills__", runtime.make_skill_provider(), namespace=None)`, line 74) if it exercises the model-driven `read_skill` path.

**Event collector pattern** (test_agent_events.py:32-43 — subscribe to the bus, assert received):
```python
    received = []
    async def collector(event):
        received.append(event)
    await runtime.event_bus.subscribe("SkillLoadedEvent", collector)
    await runtime.load_skill("demo-greeter")
    assert [e for e in received if isinstance(e, SkillLoadedEvent)]
```

**Round-trip wire-format pattern** (NEW, no existing analog — RESEARCH dictates the shape): build `RPCServer(runtime)` in-process, monkeypatch `server._write_json` to append to a list, `await server.start()`, dispatch `skills.load` via `server._dispatcher` (or directly call `_adapter.handle_skills_load`), then filter collected messages: the RPC response `{result: {skill, status}}` and the notification `{"jsonrpc":"2.0","method":"event","params":{"type":"skill_loaded","request_id":...,"payload":{"skill":"demo-greeter"}}}`. **Assert them independently — never assume wire order** (the notification fires inside the `await` in `load_skill`, before the dispatcher writes the response; RESEARCH Pitfall 2).

**`runtime` fixture** (test_skills_load_rpc.py:184-215) — copy for unit tests: `MagicMock` config/client/registry, `client.count_tokens = len`, `store=JSONLSessionStore(tempfile.mkdtemp())`, `skill_store=store`.

---

### `tui-ink/src/types.ts` (model, request-response)

**Analog:** same file — payload interfaces (25-65), `EventPayload` union (67-74), `Message` (88-95), `AgentState` (97-109)

**New payload interface** (mirror `CancelledPayload`, lines 63-65):
```ts
export interface CancelledPayload {
  session_id: string
}

export interface SkillLoadedPayload {
  skill: string        // canonical name (D-06: { skill } only)
}
```

**Union member** (append to `EventPayload`, lines 67-74):
```ts
export type EventPayload =
  | { type: "turn_started"; payload: TurnStartedPayload }
  ...
  | { type: "cancelled"; payload: CancelledPayload }
  | { type: "skill_loaded"; payload: SkillLoadedPayload }
```

**`Message.tone`** (add optional field to `Message`, lines 88-95):
```ts
export interface Message {
  id: string
  role: "user" | "assistant" | "notice" | "error"
  content: string
  timestamp: number
  isStreaming?: boolean
  truncated?: boolean
  tone?: "success" | "error"      // NEW — notice variants (UI-SPEC §6.3)
}
```

**`AgentState.loadedSkills`** (add to interface, lines 97-109 — MUST match the store, or `npm run typecheck` fails with "Property 'loadedSkills' is missing"; RESEARCH Pitfall 3):
```ts
export interface AgentState {
  sessions: SessionSummary[]
  ...
  busy: boolean
  loadedSkills: string[]          // NEW — consumed by Footer chip (must match store!)
}
```

---

### `tui-ink/src/store/agent-store.ts` (store, event-driven)

**Analog:** same file — `addNotice` (170-176), `addError` (178-185), `resetConversation` (197-204), `loadConversation` (206-218)

**`AgentActions` interface additions** (extend lines 16-39):
```ts
  addNotice: (text: string) => void
  addError: (error: string) => void
  addLoadedSkill: (name: string) => void              // NEW
  addSkillNotice: (text: string, tone?: "success" | "error") => void  // NEW
```

**State init** (extend the `create<AgentStore>` initial state, lines 45-56):
```ts
  busy: false,
  loadedSkills: [] as string[],
```

**`addLoadedSkill` — dedup-append** (mirror `addNotice`'s `set((s) => ...)` shape; belt-and-suspenders since backend dedups — D-07):
```ts
  addLoadedSkill: (name) =>
    set((s) =>
      s.loadedSkills.includes(name)
        ? s                                  // dedup-append (backend also dedups, D-07)
        : { loadedSkills: [...s.loadedSkills, name] }   // load order preserved (D-03)
    ),

  addSkillNotice: (text, tone) =>
    set((s) => ({
      conversation: [
        ...s.conversation,
        { id: nextId(), role: "notice", content: text, timestamp: now(), ...(tone && { tone }) },
      ],
    })),   // NEVER touches status/busy/error — addError is NOT reused (UI-SPEC §6.3)
```

**Reset in BOTH reset paths** — the classic pitfall (RESEARCH Pitfall 1). `resetConversation` (197-204, the `/new` path):
```ts
  resetConversation: () =>
    set({
      conversation: [],
      toolCalls: [],
      toolCallCount: 0,
      status: "idle",
      error: null,
      loadedSkills: [],          // NEW — D-09: chip clears on /new
    }),
```
`loadConversation` (206-218, the session-switch path via `session-picker.tsx:65`):
```ts
  loadConversation: (messages) =>
    set({
      conversation: messages.map((m) => ({ ... })),
      toolCalls: [],
      toolCallCount: 0,
      status: "idle",
      error: null,
      loadedSkills: [],          // NEW — D-09: chip clears on session switch
    }),
```
`setActiveSession` (line 60) is NOT a reset — it only sets the id; both reset points above are required.

---

### `tui-ink/src/bridge/rpc-client.ts` (bridge, event-driven)

**Analog:** same file — `handleEvent` switch (199-282), `loadSkill()` (140-142)

**`loadSkill()` already exists** (140-142) — the `/skill` InputBar branch calls this directly:
```ts
  async loadSkill(name: string): Promise<SkillLoadResult> {
    return (await this.request("skills.load", { name })) as SkillLoadResult
  }
```

**New `handleEvent` case** — model after the `cancelled` case (274-280) in the switch (207-281):
```ts
      case "cancelled": {
        store.truncateStreamingMessage()
        store.addNotice("Cancelled")
        store.setStatus("idle")
        store.setBusy(false)
        break
      }
      case "skill_loaded": {
        // D-07/D-08: chip state ONLY — no notice, no stream message, no
        // status/busy (ROADMAP criterion 4). Model-driven loads must not
        // inject into the conversation.
        const p = payload as { skill: string }
        store.addLoadedSkill(p.skill)
        break
      }
```
Note the case ordering: `case "cancelled":` currently falls through to the closing `}` of the switch without a `default` — the new case can be appended after it inside the switch block. TypeScript narrowing: `handleEvent` receives `params: { type: string; request_id: string; payload: Record<string, unknown> }` (199-203), so the payload cast `as { skill: string }` follows the existing convention (e.g. line 209, 216).

---

### `tui-ink/src/app.tsx` (component, request-response)

**Analog:** same file — InputBar `useInput` intercept branches (45-67)

**Module-local constants** (top of `InputBar`/file, per UI-SPEC §10 — no theme.ts):
```ts
const SKILL_USAGE_LINE = "Usage: /skill <name>"        // bare /skill copy (D-05)
const SKILL_CMD = /^\/skill(?:\s+(.+))?$/              // bare OR /skill <name>; NEVER matches /skills
const SKILL_LOAD_FAILED = (msg: string) => `Failed to load skill: ${msg}`
```

**New branch inside the `key.return` if/else-if chain** (insert after the `/sessions` branch at line 60-61, before the final `else` at 62-64):
```ts
        } else if (trimmed === "/sessions") {
          refreshSessions()
        } else if (SKILL_CMD.test(trimmed)) {
          // Branch gate is the anchored regex ITSELF (research Pitfall 6) — `/skills`
          // fails the test and falls through to the final else → submitPrompt. NOT startsWith.
          const m = trimmed.match(SKILL_CMD)        // non-null here — same regex, no /g flag
          const store = useAgentStore.getState()
          const name = m?.[1]?.trim()
          if (!name) {
            store.addSkillNotice(SKILL_USAGE_LINE)  // info tone (bare, D-05) — not forwarded
          } else {
            client.loadSkill(name)
              .then((result) => {
                // result: { skill: canonical, status: loaded|already_loaded } — 15-CONTEXT D-06
                const s = useAgentStore.getState()
                if (result.status === "loaded") s.addSkillNotice(`Loaded skill ${result.skill}`, "success")
                else s.addSkillNotice(`Skill '${result.skill}' already loaded`)  // info (no tone)
              })
              .catch((err: Error) => {
                const s = useAgentStore.getState()
                // D-04: SKILL_NOT_FOUND surfaces the BARE verbatim copy — the RPC client
                // rejects with only the message (rpc-client.ts:180) and adapter.py:107
                // builds it from the exact trimmed name, so equality is deterministic.
                if (err.message === `Skill '${name}' not found.`) {
                  s.addSkillNotice(`Skill '${name}' not found`, "error")   // D-04 verbatim (no trailing period)
                } else {
                  s.addSkillNotice(SKILL_LOAD_FAILED(err.message), "error") // other RPC failures
                }
              })
          }
        } else {
          client.submitPrompt(trimmed).then(refreshSessions)
        }
        setInput("")
        return
```
Existing intercept structure to preserve: exact-match on trimmed input, handled inline, `setInput("")` + `return` at 65-66 — the `else` at 62-64 is the ONLY path to `submitPrompt` (no fall-through, D-05). **The branch is gated on `SKILL_CMD.test(trimmed)` — the anchored regex itself (NOT exact-match, NOT `startsWith`)** — RESEARCH locks the anchored regex so `/skills` fails the test and falls through to `submitPrompt`. No `busy` flag during the load (UI-SPEC §6.2).

---

### `tui-ink/src/components/footer.tsx` (component, view)

**Analog:** same file — hint row (4-15); `useWindowSize` pattern from `session-picker.tsx:29`

**Module-local constants** (per UI-SPEC §10):
```ts
const CHIP_LABEL = "Skill:"                // dim — static label
const CHIP_SEPARATOR = " · "               // skill-name join (3 cells)
const CHIP_MORE_SUFFIX = (n: number) => `+${n} more`   // dim — truncation count
const CHIP_PADDING_X = 1                   // matches existing footer paddingX
```

**New chip row above hints** — restructure the root `Box` to `flexDirection="column"`, existing hint row untouched:
```tsx
export function Footer() {
  const loadedSkills = useAgentStore((s) => s.loadedSkills)   // re-renders on chip changes only
  const { columns } = useWindowSize()                          // Ink 7.1 — returns {columns, rows}

  return (
    <Box flexDirection="column" width="100%">
      {loadedSkills.length > 0 && (
        <Box paddingX={CHIP_PADDING_X}>
          <Text dimColor>{CHIP_LABEL} </Text>
          <Text bold color="white">{formatChip(loadedSkills, columns)}</Text>
        </Box>
      )}
      <Box width="100%" paddingX={1}>
        <Text dimColor>[?] help</Text>
        {/* ... existing hint row unchanged ... */}
      </Box>
    </Box>
  )
}
```
`useWindowSize` import from `"ink"` (same import line as `Box, Text` — session-picker.tsx:2 shows the pattern). Truncation algorithm (UI-SPEC §6.1, locked): `W = columns - 4`; join all with ` · `; if too long, drop trailing names until `kept + " · +N more"` fits (suffix dim); hard floor — hide the whole row if even `Skill: +{N}` exceeds W.

---

### `tui-ink/src/components/message.tsx` (component, view)

**Analog:** same file — notice branch (43-51), error branch (53-61)

**Module-local glyph constants** (per UI-SPEC §10, 09-UI-SPEC §6 vocabulary):
```ts
const NOTICE_OK = "✓"                      // green, bold — success tone
const NOTICE_ERR = "✗"                     // red, bold — error tone
```

**Tone rendering in the `notice` branch** (replace lines 43-51 — keep the existing info style as the default/fallback):
```tsx
  if (message.role === "notice") {
    if (message.tone === "success") {
      return (
        <Box>
          <Text color="green" bold>
            {NOTICE_OK} {message.content}
          </Text>
        </Box>
      )
    }
    if (message.tone === "error") {
      return (
        <Box>
          <Text color="red" bold>
            {NOTICE_ERR} {message.content}
          </Text>
        </Box>
      )
    }
    return (
      <Box>
        <Text dimColor italic>
          {message.content}
        </Text>
      </Box>
    )
  }
```
Existing `error` role branch (53-61) already renders `✗` red bold — the new `error` tone mirrors it. Copy strings are locked verbatim (UI-SPEC §11): `Loaded skill <name>` (success), `Skill '<name>' already loaded` + `Usage: /skill <name>` (info), `Skill '<name>' not found` + `Failed to load skill: {message}` (error) — `<name>` is the **canonical** name from `result.skill`, never the raw typed string.

---

## Shared Patterns

### Five-touchpoint typed notification extension (D-08)
**Source:** `harness/events.py` → `backend/rpc/server.py` → `backend/rpc/protocol.py` → `tui-ink/src/bridge/rpc-client.ts` → `tui-ink/src/store/agent-store.ts`
**Apply to:** the whole Phase 16 pipeline — this is the 8th member of the Phase 9 D-09 pattern. The exact 5-edit extension checklist (RESEARCH Pattern 1): (1) event dataclass + `EVENT_*` constant, (2) server import + mapping entry + extractor + `_PAYLOAD_EXTRACTORS` entry + subscribe/unsubscribe, (3) `NotificationType` member, (4) `handleEvent` switch case, (5) store state + action (+ `types.ts`).

### Slash-command intercept, never fall-through (D-05)
**Source:** `tui-ink/src/app.tsx:45-67`
**Apply to:** InputBar `/skill` branch — exact-match trimmed input, handle inline, `setInput("")` + `return`; only the final `else` reaches `submitPrompt`. The `/skill` branch is gated on the anchored regex test `SKILL_CMD.test(trimmed)` (never prefix-greedy over `/skills`; `startsWith` is forbidden — Pitfall 6).

### Event-bus publish contract
**Source:** `harness/event_bus.py:50-75`, publish mirror at `harness/scheduler.py:62-66`
**Apply to:** `harness/runtime.py` emission — `await self._event_bus.publish(...)` is async, routes on `type(event).__name__`, exceptions isolated via `gather(return_exceptions=True)`.

### Notice-message role (no `addError` reuse)
**Source:** `tui-ink/src/store/agent-store.ts:170-185`
**Apply to:** `/skill` outcome notices — `addSkillNotice(text, tone?)` pushes `{role: "notice", content, timestamp, tone?}` and NEVER touches `status`/`busy`/`error`. `addError` (178-185) sets `status: "error"` which flips the Header red (header.tsx error→red mapping) — a failed slash command must not put the app in an error state.

### Store reset discipline (both paths)
**Source:** `tui-ink/src/store/agent-store.ts:197-218`
**Apply to:** `loadedSkills: []` must be added to BOTH `resetConversation()` and `loadConversation()` — `setActiveSession` (line 60) is not a reset. Missing either path is the #1 typecheck-passes-but-behavior-wrong pitfall (RESEARCH Pitfall 1).

### In-process RPCServer round-trip testing (new for the suite)
**Source:** RESEARCH Validation Architecture (no existing test drives `RPCServer`)
**Apply to:** `tests/test_skill_loaded_notification.py` — in-process `RPCServer(runtime)` + monkeypatched `_write_json` collector; assert RPC response and notification independently, never assume wire order (the notification fires inside the `await` of `load_skill`, before the dispatcher writes the response).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/test_skill_loaded_notification.py` round-trip section | test | event-driven | No existing test constructs `RPCServer` in-process or monkeypatches `_write_json`; the pattern is dictated by RESEARCH (validation architecture) and composes existing fixture patterns (`skills_root` from test_skills_load_rpc.py, `_build_runtime` from test_skills_e2e.py, collector from test_agent_events.py) |

## Metadata

**Analog search scope:** `harness/`, `backend/rpc/`, `tests/`, `tui-ink/src/` (full source trees read; no graphify needed — every analog is same-file or a directly-named test twin)
**Files scanned:** 12 target files + 9 analog files (events.py, event_bus.py, __init__.py, runtime.py, protocol.py, server.py, adapter.py, scheduler.py, skills/provider.py, 3 test files, 6 TUI files)
**Pattern extraction date:** 2026-08-03
