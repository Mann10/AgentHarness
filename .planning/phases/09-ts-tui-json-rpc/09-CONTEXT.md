# Phase 9: TypeScript TUI + JSON-RPC Adapter - Context

**Gathered:** 2026-07-28 (updated)
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a JSON-RPC adapter layer to the existing Python backend runtime, then build a new TypeScript/Ink terminal UI that communicates exclusively over stdin/stdout JSON-RPC. The existing Python REPL and Textual TUI remain unchanged as fallbacks. This is a transport adapter + new frontend — no changes to RuntimeAPI, EventBus, Agent, tools, sessions, or memory.

</domain>

<spec_lock>
## Spec Lock Notice

**No SPEC.md exists for this phase.** Requirements and scope were defined during this discussion. All implementation decisions are captured below — no separate requirements document constrains this phase.

</spec_lock>

<decisions>
## Implementation Decisions

### RPC Adapter Architecture (Backend)
- **D-01:** New `backend/rpc/` module: `protocol.py` (message schemas), `dispatcher.py` (request routing, no business logic), `adapter.py` (RuntimeAPI wrapper), `server.py` (stdio read/write loop)
- **D-02:** RuntimeAPI and EventBus remain completely unchanged — no business logic in RPC layer
- **D-03:** Single notification method: `"event"` with typed payload — do NOT create many RPC notification methods (avoid `toolStarted`, `token`, `error` etc. as method names)
- **D-04:** Frontend switches on `event.type` string, never on RPC method names
- **D-05:** Transport: JSON-RPC 2.0 over stdin/stdout, NDJSON framing, flush after every message
- **D-06:** RPC method surface is small and user-intent-oriented (not internal-API-mirroring):
  - `chat` → `RuntimeAPI.submit_prompt()`
  - `cancel` → `RuntimeAPI.cancel()`
  - `sessions.list` → `RuntimeAPI.list_sessions()`
  - `sessions.switch` → `RuntimeAPI.switch_session()`
  - `sessions.create` → new `RuntimeAPI.create_session()` (to be added)
  - `sessions.delete` → new `RuntimeAPI.delete_session()` (to be added)
  - `ping` → health check

### Event Streaming
- **D-07:** Add `TokenProduced` domain event to `harness/events.py` — enables token-level streaming in the TUI
- **D-08:** Event-to-notification mapping: all EventBus events forward as `{"method":"event","params":{"type":"<event_type>","requestId":"...","payload":{...}}}`
- **D-09:** Notification types: `turn_started`, `tool_call`, `tool_result`, `token`, `response_complete`, `cancelled`, `error`

### TypeScript TUI (Frontend)
- **D-10:** New `frontend/` directory with React + Ink as the rendering engine
- **D-11:** Custom terminal-focused component library built on top of Ink — not generic React components
- **D-12:** Application logic is independent of both Ink and React component implementations
- **D-13:** Frontend structure: `rpc/` (client, protocol, transport), `state/` (store, reducers), `ui/` (components, screens), `App.tsx`
- **D-14:** State store holds only presentation state — conversation, streamed tokens, loading indicators, tool progress, active session, UI preferences
- **D-15:** Frontend must never import Python logic, call agent functions, know about LLMs, execute tools, or access memory directly

### Process Lifecycle
- **D-16:** TypeScript TUI spawns Python backend as a subprocess: `python -m agentharness --rpc`
- **D-17:** TUI connects to the subprocess stdin/stdout for JSON-RPC communication
- **D-18:** TUI kills the subprocess on exit (SIGTERM/CTRL+C propagation)

### Migration Strategy
- **D-19:** Keep existing Textual TUI as fallback — `--tui` flag continues to use Python Textual
- **D-20:** Add `--rpc` flag to Python entry point to start in JSON-RPC server mode
- **D-21:** Migration order: (1) RPC adapter + `--rpc` mode → (2) TypeScript client, verify streaming → (3) core screens (conversation, tools, status, sessions) → (4) feature parity with Textual → (5) make TS TUI default, deprecate Textual
- **D-22:** Throughout migration, RuntimeAPI and EventBus remain the source of truth — JSON-RPC is purely a transport adapter
- **D-23:** The existing Python REPL continues to use RuntimeAPI directly (no RPC layer needed)

### Extensibility Guarantees
- **D-24:** Replacing JSON-RPC with another transport (WebSocket, gRPC, IPC) requires only replacing the adapter layer — not the runtime or the UI state model
- **D-25:** The architecture supports future consumers (VS Code extension, web UI, MCP integration, remote execution, multiple concurrent chats, background tasks) without changing RuntimeAPI

### Log & Console Hygiene (TUI)
- **D-26:** All console.error/warn calls in frontend TypeScript code must be replaced with store.setError() calls. Errors render inline in the conversation flow via the existing ErrorBar/ConversationScreen — never to terminal stdout. Affected files: `rpc/client.ts` (transport errors, parse failures, unhandled messages, event handler errors), `state/reducers.ts` (unknown event types), `App.tsx` (error handling).

### Backend stdout Isolation
- **D-27:** During `--rpc` mode, the Python backend must route all logging to a file (e.g., `agent_harness_debug.log`), never to stdout. Stdout is reserved exclusively for NDJSON-framed JSON-RPC messages. Any stray `print()`, `logging.info()`, or unhandled traceback to stdout will break the protocol and produce parse errors in the TUI.

### Processing Animation
- **D-28:** The InputBar shows a cycling text animation while waiting for a response: "Thinking" → "Thinking." → "Thinking.." → "Thinking..." at 500ms intervals. Matches Claude Code behavior. Uses Ink `useInterval` or `useEffect` with `setInterval` for frame cycling.

### StatsPanel Widget
- **D-29:** Right-side StatsPanel displays 4 fields only — session name, token count, response time (from last turn), and model name. No live clock or date display. Values update on `response_complete` event. Fixed 30-column width per UI-SPEC. Background: `$surface` with left border.

### OpenCode's Discretion
- Exact Pydantic/dataclass schema design for protocol messages
- `TokenProduced` event field details (chunk only, or chunk + metadata)
- Frontend component tree and widget hierarchy
- State store implementation (useReducer, Zustand, or similar)
- Build tooling (Vite, esbuild, tsconfig setup)
- CSS/styling approach for Ink components
- Testing framework choices for both stacks
- Keyboard shortcut bindings
- Startup readiness protocol (RPC handshake)
- Exact hex values for Claude-style theme (outlined in UI-SPEC.md)
- InputBar history navigation implementation detail
- StatsPanel exact layout and spacing within its 30-col width
- ErrorBar dismissal animation (instant vs fade)
- SessionPicker confirmation before delete

</decisions>

<specifics>
## Specific Ideas

- "Backend works fine but TUI is shit" — motivation for this phase
- "Treat JSON-RPC as a transport adapter, not as the application's architecture" — architectural principle
- "The RTM remains the single source of truth" — RuntimeAPI is never bypassed
- "Expose user intents, not internal APIs" — RPC method design philosophy
- Inspired by Claude Code, OpenCode, and modern AI coding assistants
- "No logs nothing else unnecessary" — clean TUI output, no console pollution (drives D-26, D-27)
- "Claude Code style" — primary visual reference for dark theme, minimal chrome, inline tool calls, cycling Thinking animation (drives D-28)

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Runtime Core (unchanged — must understand interfaces)
- `harness/runtime.py` — RuntimeAPI public API surface (submit_prompt, cancel, list_sessions, switch_session)
- `harness/events.py` — Current EventBus event types (TurnStarted, ToolCallEvent, ToolResultEvent, ResponseComplete, ErrorEvent, CancelledEvent)
- `harness/event_bus.py` — EventBus subscribe/publish mechanism
- `agent/core.py` — Agent lifecycle (indirectly relevant — events originate here)
- `session/models.py` — Session data model (Session, SessionSummary)

### Existing TUI (reference for feature parity)
- `tui/app.py` — Current TUI app layout, event subscription pattern, RuntimeAPI integration
- `tui/widgets/conversation_view.py` — Message container
- `tui/widgets/message_card.py` — Message rendering (user, assistant, error, notice)
- `tui/widgets/inline_tool_call.py` — Inline tool call rendering
- `tui/widgets/stats_panel.py` — Stats display (tokens, time, model, session name)
- `tui/widgets/input_bar.py` — Input handling with history and /commands
- `tui/screens/session_picker.py` — Session management screen
- `tui/theme.tcss` — Current CSS theme

### TypeScript TUI (current implementation)
- `frontend/src/ui/theme.ts` — Design tokens (colors, symbols, spacing)
- `frontend/src/ui/components/StatsBar.tsx` — Top status bar with connection dot
- `frontend/src/ui/components/MessageCard.tsx` — Message rendering with role prefixes
- `frontend/src/ui/components/InputBar.tsx` — Input bar with prompt symbol
- `frontend/src/ui/components/ToolCallIndicator.tsx` — Inline tool call tree
- `frontend/src/ui/components/ErrorBar.tsx` — Inline error display
- `frontend/src/ui/screens/ConversationScreen.tsx` — Main conversation view
- `frontend/src/ui/screens/SessionPicker.tsx` — Session management overlay
- `frontend/src/rpc/client.ts` — RPC client (needs console output cleanup per D-26)
- `frontend/src/state/reducers.ts` — Event → state mapping (needs console output cleanup per D-26)
- `frontend/src/state/store.ts` — State store
- `frontend/src/App.tsx` — App shell and lifecycle

### Prior Phase Decisions (design continuity)
- `.planning/phases/07-tui-visual-overhaul/07-CONTEXT.md` — Claude Code-inspired dark theme, inline tool calls, minimal layout
- `.planning/phases/08-tui-conversation-layout/08-CONTEXT.md` — Message bifurcation, stats panel, header removal

### Design Spec
- `.planning/phases/09-ts-tui-json-rpc/09-UI-SPEC.md` — Full UI design contract (component specs, layout, color tokens, interaction design)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `harness/runtime.py` — RuntimeAPI with 4 public methods + EventBus exposure — the core interface the RPC adapter wraps
- `harness/events.py` — 6 typed event dataclasses — each maps to an RPC notification type
- `harness/event_bus.py` — EventBus subscribe/publish — RPC adapter subscribes here to emit notifications
- `tui/app.py` — Event subscription pattern, conversation flow, stats tracking logic — reference for TS TUI behavior
- `tui/widgets/stats_panel.py` — Token count, response time, model name, session name display — reference for TS equivalent
- `frontend/src/ui/theme.ts` — Design tokens already created, color palette derived from UI-SPEC
- `frontend/src/ui/components/*.tsx` — All core TUI components implemented (StatsBar, MessageCard, InputBar, ToolCallIndicator, ErrorBar)
- `frontend/src/ui/screens/ConversationScreen.tsx` — Conversation layout with streaming, tool calls, errors inline

### Established Patterns
- **Event-driven architecture** — Runtime emits typed events via EventBus, consumers subscribe
- **Async-first** — All Python code uses asyncio; TypeScript TUI uses async event processing via Ink hooks
- **Dependency injection** — RuntimeAPI receives its dependencies (Config, OpenAIClient, ToolRegistry) via constructor
- **Typed events** — Dataclass-based HarnessEvent hierarchy with string constants for subscription keys
- **Store-based state** — Presentation state lives in Store class, components subscribe for re-renders
- **Inline errors** — Errors display in conversation flow, not as modal popups or console output

### Integration Points
- RPC adapter wraps `RuntimeAPI` methods — maps RPC requests to API calls
- RPC adapter subscribes to `EventBus` — maps domain events to RPC notifications
- `TokenProduced` event (new) — needs to be emitted from LLM client or agent streaming loop
- `--rpc` flag — new entry point mode in `main.py` or a new entry point module
- Spawned as subprocess by TS TUI — needs stdout-only NDJSON output (no log interleaving, per D-27)
- StatsPanel reads from store: session title, token count, response time, model name
- Log suppression (D-26) affects: `rpc/client.ts` (5 console calls), `state/reducers.ts` (1 console call), `App.tsx` (error handler)

</code_context>

<deferred>
## Deferred Ideas

- VS Code extension frontend — future consumer of same RPC adapter
- Web UI frontend — future consumer of same RPC adapter
- MCP integration at RPC level — future transport extension
- Remote execution mode — future transport extension
- Multiple concurrent chats — future RuntimeAPI enhancement
- Background tasks and live logs — future feature
- Progress bars and file uploads — future TUI features
- Image generation display — future TUI enhancement
- Welcome/start page with recent sessions — future TUI screen
- Live clock in StatsPanel — user chose minimal (4 fields), clock not needed
- Date/time display in StatsPanel — user chose minimal, not needed

</deferred>

---

*Phase: 09-ts-tui-json-rpc*
*Context gathered: 2026-07-28 (updated)*