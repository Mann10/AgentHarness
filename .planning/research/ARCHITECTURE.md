# Architecture Research

**Domain:** Skills System (v1.1) — progressive-disclosure SKILL.md loading for AgentHarness
**Researched:** 2026-08-01
**Confidence:** HIGH (all findings grounded in read source; LOW only where flagged)

## Standard Architecture

### System Overview

The Skills System is a **subsystem layered on top of the existing harness**, not a fork of it. It plugs into four existing seams — the system-prompt assembler, the tool registry, the conversation context, and the RPC/event pipeline — while keeping the skills domain (discovery, manifest, storage, filtering) in a new `skills/` package. Everything the agent *sees* is delivered through existing mechanisms: manifest via system prompt (D-06), skill bodies via system-role context messages (D-12), activation via a registered tool (D-08).

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Entry / CLI Layer (main.py)                     │
│   builds SkillStore + manifest · registers SkillToolProvider ·           │
│   REPL /skill branch (extended _handle_session_cmd)                      │
└───────────────┬──────────────────────────────────────┬───────────────────┘
                ▼                                      ▼
┌───────────────────────────────────────┐  ┌──────────────────────────────┐
│  Harness Runtime (RuntimeAPI)          │  │  JSON-RPC (TUI)              │
│  owns: SkillStore, SkillState attach,  │  │  RPC_METHODS + "skills.load" │
│  load_skill() → SkillLoadedEvent,      │  │  event "skill_loaded" → TUI  │
│  tool-filter construction              │  │  (protocol/server/adapter)   │
└───────┬───────────────────────┬────────┘  └──────────────┬───────────────┘
        ▼                       ▼                          │
┌───────────────┐   ┌─────────────────────┐                │
│  Agent        │   │  Session (models.py)│                │
│  (core.py)    │   │  _build_system_prompt│◄── manifest    │
│  tool_filter  │   │  + skills section    │    (D-06)      │
│  at loop      │   └──────────┬──────────┘                │
└───────┬───────┘              │                            │
        │ list_tools()         │ context system messages    │
        ▼                      ▼                            │
┌──────────────────────┐  ┌──────────────────────┐          │
│  ToolRegistry         │  │  ConversationContext │          │
│  "__skills__" provider│  │  add_message(system, │◄── skill │
│  → read_skill tool    │  │  persist=False)      │   body   │
│  (D-08/D-10)          │  │  summarization-exempt│  (D-12)  │
└──────────────────────┘  └──────────────────────┘          │
        │                                                    
        ▼                                                    
┌───────────────────────────────────────────────────────────┐
│  skills/ package (NEW — pure domain)                      │
│  models.py · discovery.py · manifest.py · store.py        │
│  provider.py · filter.py                                  │
│  data: .agentharness/skills/<name>/SKILL.md (+ refs)      │
└───────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **SkillStore** | Scans `.agentharness/skills/`, parses frontmatter, dedupes (D-05), sorts deterministically; owns path-scoped reads (D-10) and the load operation (read SKILL.md → inject system message → apply restrictions) | `skills/store.py` — pure domain object; no EventBus, no Agent imports |
| **SkillDiscovery** | One-pass directory scan → `list[SkillInfo]`; malformed → log+skip (D-04); duplicate → first-wins (D-05); token-budget trim support (D-07) | `skills/discovery.py` — minimal hand-rolled frontmatter parser (no PyYAML dep) |
| **ManifestBuilder** | Formats `SkillInfo` list → system-prompt section text, capped at budget; `None` when no skills (skip section) | `skills/manifest.py` — pure function |
| **SkillToolProvider** | Exposes `read_skill(name[, path])` as an async `ToolProvider` (the protocol requires async — load has side effects, unlike `LocalToolProvider`'s sync handlers); delegates to injected `load_handler`/`read_handler` | `skills/provider.py` — thin adapter, registered as `__skills__` (no namespace → un-prefixed `read_skill`) |
| **SkillState** | Per-session loaded-skill set + active `allowed-tools` restriction set | `skills/models.py` — dataclass attached to `Session`, **not serialized** (D-13: lost on `/new`/restart) |
| **ToolFilter** | Whitelist-filtering of `list_tools()` output while restrictions active; always retains `read_skill` | `skills/filter.py` — pure function; injected into `Agent` as a callable |
| **Session (modified)** | Carries `skill_manifest` string + `skill_state`; appends Skills section in `_build_system_prompt()`; excludes `persist=False` messages from `to_events()`/`mark_saved()` | `session/models.py` |
| **RuntimeAPI (modified)** | Single wiring point: attaches manifest/state at `_create_agent()`, exposes `load_skill()`, builds tool filter, constructs+registers SkillToolProvider, emits `SkillLoadedEvent` | `harness/runtime.py` |

## Recommended Project Structure

```
agentharness/
├── skills/                     # NEW package — skills domain, no circular deps
│   ├── __init__.py             # exports SkillStore, SkillToolProvider, ...
│   ├── models.py               # SkillInfo, SkillState, SkillLoadResult (pure dataclasses)
│   ├── discovery.py            # scan + frontmatter parse (D-03/D-04/D-05) + budget trim (D-07)
│   ├── manifest.py             # build_manifest_text(entries, budget) -> str | None
│   ├── store.py                # SkillStore: index, load(session, name), read_path(name, rel)
│   ├── provider.py             # SkillToolProvider (async ToolProvider protocol)
│   └── filter.py               # build_tool_filter(session) -> Callable[[list[Tool]], list[Tool]]
│
├── session/models.py           # MODIFIED: +skill_manifest, +skill_state; skills section in
│                               #   _build_system_prompt(); persist-filter in to_events/mark_saved
├── context/message.py          # MODIFIED: +persist: bool = True field
├── agent/core.py               # MODIFIED: apply injected tool_filter in run() loop (~2 lines)
├── harness/events.py           # MODIFIED: +SkillLoadedEvent, EVENT_SKILL_LOADED
├── harness/runtime.py          # MODIFIED: skill wiring (attach, load_skill, filter, provider)
├── backend/rpc/protocol.py     # MODIFIED: RPC_METHODS + "skills.load"; NotificationType + skill_loaded
├── backend/rpc/server.py       # MODIFIED: skill_loaded extractor + mapping + subscription
├── backend/rpc/adapter.py      # MODIFIED: handle_skills_load + register
├── main.py                     # MODIFIED: build SkillStore+manifest; REPL /skill branch
│
├── tests/                      # NEW: test_skills_discovery, _manifest, _store, _provider,
│                               #   _filter, _rpc_skills; MODIFIED: test_store/test_session (persist)
│
└── tui-ink/src/                # MODIFIED (TypeScript):
    ├── types.ts                # +SkillLoadedPayload, EventPayload union
    ├── store/agent-store.ts    # +loadedSkills, skill_loaded handler
    ├── bridge/rpc-client.ts    # +loadSkill(), skill_loaded event case
    ├── app.tsx                 # +"/skill " branch in InputBar (intercept, never forward as prompt)
    └── components/footer.tsx   # optional persistent "skill: <name>" chip (D-14 discretion)
```

### Structure Rationale

- **`skills/` as a new top-level package:** mirrors the existing `tool/`, `session/`, `context/` package layout; keeps skills domain code (parsing, budgets, filtering policy) out of the agent loop and session model, which stay generic. Dependency direction is one-way: `skills/models.py` is imported by `session/models.py`; `skills/store.py` imports `session/models.py`; **neither imports `agent/`** — no cycles (verified: `session/models.py` → `context/` → `tool/`; `skills/*` adds only `session/` + `context/` edges).
- **Pure functions at the edges (`discovery.py`, `manifest.py`, `filter.py`):** unit-testable without a harness; the risky I/O (path reads) is isolated in `store.py`.
- **No new Python dependency:** frontmatter needs only `name`, `description`, optional `allowed-tools` — a ~40-line minimal parser (`---` delimiters, `key: value` scalars, `key:` + `- item` lists) suffices and matches the project's tiny `requirements.txt` footprint. Add PyYAML only if frontmatter grows multiline/list-complex features (future authoring milestone).
- **Modified files are touch-points only:** Session (prompt assembly + serialization), Message (one flag), Agent (one filter line), events/RPC (one more event + method). No file gets rewritten.

## Architectural Patterns

### Pattern 1: Provider-as-tool (read_skill via `ToolProvider` protocol)

**What:** `read_skill` registers through the existing provider pattern (`tool/models.py:7` `@runtime_checkable ToolProvider`) as a dedicated `__skills__` provider — the same seam `__builtin__` and MCP servers use.
**When to use:** any tool that needs access to harness state beyond its own arguments (here: the active session's context and event bus).
**Trade-offs:** correct layering + automatic inclusion in `list_tools()`/`call_tool()`; costs one provider class. `LocalToolProvider` cannot be reused — its handlers are **sync** `Callable[[dict], str]` (`tool/local_provider.py:15`) and skill loading must `await` context injection and event emission.

**Example:**
```python
class SkillToolProvider:  # implements ToolProvider protocol (async)
    async def fetch_tools(self) -> list[Tool]:
        return [Tool(name="read_skill",
                     description="Load a skill's instructions (name) or read a bundled file (name+path).",
                     input_schema={"type": "object",
                                   "properties": {"name": {"type": "string"},
                                                  "path": {"type": "string"}},
                                   "required": ["name"]})]

    async def call_tool(self, name: str, arguments: dict) -> ToolResult:
        if name != "read_skill":
            raise ValueError(f"Unknown skill tool '{name}'")
        if "path" in arguments:            # D-10: sibling file read, no side effects
            content = await self._read_handler(arguments["name"], arguments["path"])
        else:                               # D-08: load → inject system message → confirm
            result = await self._load_handler(arguments["name"])
            content = result.confirmation
        return ToolResult(tool_call_id=name, content=content)
```

### Pattern 2: Session-scoped mutable state on the `Session` object

**What:** loaded-skill state (`SkillState`) and the manifest string live as **non-serialized fields on `Session`**, set post-construction by RuntimeAPI — never in the registry, never in a runtime dict keyed by session id.
**When to use:** state that must follow the session across switches and reset on `/new` (D-13).
**Trade-offs:** automatic reset semantics (each `from_events()`/`create()` gets a fresh default); no session-id bookkeeping in RuntimeAPI. Requires discipline: **do not** add these fields to `to_snapshot_meta()`/`from_events()` — the JSONL format stays untouched and the manifest re-attaches on restore.

**Example:**
```python
# session/models.py (dataclass)
@dataclass
class Session:
    ...
    skill_manifest: str | None = None       # NOT in to_snapshot_meta(); from_events leaves None
    skill_state: SkillState = field(default_factory=SkillState)   # from skills/models.py

# runtime.py — single choke point, covers create/switch/restore AND REPL /new,/resume
async def _create_agent(self) -> None:
    session = self._session_manager.active_session
    if session.skill_manifest is None:      # guard: attach once per Session object
        session.skill_manifest = self._manifest_text
        session.skill_state = SkillState()
    ...
```

### Pattern 3: Load-once-shared-handler (one load path for tool AND slash command)

**What:** model-driven activation (`read_skill`) and user-driven activation (`/skill`) converge on **one** backend load path: `RuntimeAPI.load_skill(name)` → `SkillStore.load(session, name)` → inject system message + apply restrictions → emit `SkillLoadedEvent`. The tool provider receives this as an injected `load_handler` closure, not its own copy.
**When to use:** two triggers with identical side effects — one implementation prevents drift (e.g. forgetting to emit the TUI event from one path).
**Trade-offs:** RuntimeAPI owns the orchestration (correct — it owns the session and bus); the provider stays a thin adapter.

### Pattern 4: Event-notification fan-out for the TUI indicator (D-14)

**What:** a new `SkillLoadedEvent` flows the **existing** pipeline end-to-end with zero new machinery: `harness/events.py` dataclass → `server.py` `_DOMAIN_TO_NOTIFICATION` + extractor → `protocol.py` `NotificationType.skill_loaded` → `rpc-client.ts` `handleEvent` → `store.addNotice("Skill loaded: <name>")`. The TUI already renders `notice`-role messages inline (conversation-panel) — the indicator is free.
**When to use:** any new user-visible backend fact; never invent a second channel.

## Data Flow

### Request Flow 1 — Startup manifest assembly (D-06, SKL-02)

```
main.py
  ↓  SkillStore(root=".agentharness/skills")      # mkdir(parents=True, exist_ok=True), mirrors JSONLSessionStore
  ↓  store.discover()  → sorted SkillInfo[]       # frontmatter parse, D-04 skip, D-05 first-wins
  ↓  manifest.build_manifest_text(entries, budget=1500)  → str | None (D-07 trim)
  ↓  RuntimeAPI(..., skill_store=store, skill_manifest=text)
  ↓  _create_agent() → session.skill_manifest = text     # guard: once per Session object
  ↓
Session._build_system_prompt()  [per LLM call]
  parts = [system_prompt, "# Project Instructions\n"+AGENTS.md, "# Available Skills\n"+manifest?, "# Environment\nCWD: ..."]
  → to_llm_messages()[0]  (system block)           # rebuilt per call; summarization never touches it
```

### Request Flow 2 — Model-driven activation (D-08, SKL-03)

```
LLM call #N: manifest in system prompt → model sees "skill X matches task"
  ↓  model requests tool read_skill(name="X")
  ↓  Agent.run loop: tools = registry.list_tools()  → filter → LLM  (tool list includes read_skill)
  ↓  registry.call_tool("read_skill", {name:"X"}) → SkillToolProvider.call_tool
  ↓  injected load_handler → SkillStore.load(session, "X")
       · read .agentharness/skills/X/SKILL.md
       · session.context.add_message(Message(role="system", content=body, persist=False))   # D-12
       · session.skill_state.mark_loaded(X, allowed_tools)                                  # D-16
       · emit SkillLoadedEvent(session_id, skill_name) → bus → RPC notification → TUI notice
  ↓  ToolResult = short confirmation ("Skill 'X' loaded — instructions added as system message")
  ↓  context.add_tool_message(tc.id, confirmation)         # body NOT duplicated in tool result
  ↓
LLM call #N+1: to_llm_messages() = [system(manifest) | ... | assistant(call) | tool(confirm) | system(SKILL.md body)]
  ↓  model now behaves per skill instructions
```

### Request Flow 3 — User-driven activation (`/skill`, SKL-04)

```
TUI InputBar: user types "/skill X"
  ↓  intercepted in useInput (like "/new") — NEVER forwarded as chat prompt
  ↓  client.loadSkill("X") → RPC request {method:"skills.load", params:{name:"X"}}
  ↓  RPCAdapter.handle_skills_load → RuntimeAPI.load_skill("X")
  ↓     (same load path as Flow 2: store.load → inject → restrict → SkillLoadedEvent)
  ↓  RPC response {loaded:true, name:"X"} → TUI shows confirmation
  ↓  notification skill_loaded → store.addNotice("Skill loaded: X")   # D-14 transparency
REPL parity: main.py _handle_session_cmd("/skill X") → runtime.load_skill("X")
```

### Request Flow 4 — allowed-tools filtering at the tool-list boundary (D-16)

```
Agent.run(), each iteration:
  tools = registry.list_tools()                     # unchanged registry (no signature change)
  if self._tool_filter: tools = self._tool_filter(tools)
      # skills/filter.py reads session.skill_state.active_restrictions
      #  · no loaded skill with allowed-tools  → return tools unchanged (open skill not clamped)
      #  · restrictions active                 → whitelist: t.name in allowed_union or t.name=="read_skill"
  → _stream_llm_call(messages, tools=tools)        # LLM only sees permitted tools
Restrictions last exactly as long as the skill stays in session.skill_state (session scope).
```

### State Management

| State | Owner | Lifetime | Persisted? |
|-------|-------|----------|------------|
| Skill index (`SkillInfo[]`) | SkillStore | process (rebuilt at startup; rebuild timing deferred) | no (reads disk) |
| Manifest text (`str|None`) | Session field | process + session object | no (re-attached on restore) |
| Loaded skills + restrictions (`SkillState`) | Session field | session only — reset on `/new`, switch, restart | **no** (D-13) |
| Skill bodies (system messages) | ConversationContext | session; summarization-exempt (context.py:88) | **no** (`persist=False` filtered in `to_events`) |
| `read_skill` tool | ToolRegistry (`__skills__`) | process | n/a |

### Key Data Flows

1. **Manifest → system prompt:** startup discovery → static string → `Session` → rebuilt system block per call (Flow 1).
2. **Skill body → context → next LLM call:** injected mid-turn, visible from iteration N+1 (Flow 2). A loaded skill affects the very same agent turn that triggered it.
3. **Restriction → tool list:** per-iteration filter after `list_tools()`, driven by session-scoped `SkillState` (Flow 4).
4. **Load event → TUI:** one `SkillLoadedEvent` → notification → inline notice + optional footer chip (Pattern 4).

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0–50 skills | Current design is fine — manifest budget caps prompt size; discovery is a single startup scan; `list_tools()` filter is O(n) per iteration. |
| 50–500 skills | Manifest budget becomes the binding constraint: entries get trimmed (D-07). Discovery stays startup-only; consider mtime-based caching (deferred: "manifest rebuild timing / frontmatter caching"). |
| 500+ skills | Move discovery to a background watcher + cache (still deferred); consider per-skill-index JSON like Claude Code's. No architectural change needed — the seams hold. |

### Scaling Priorities

1. **First bottleneck — prompt cost, not code:** the manifest budget (D-07) and the fact that each loaded skill body consumes context budget (`total_tokens` includes system messages, so summarization can trigger earlier) are the only real pressure points. Keep descriptions trigger-aware and short; enforce the 1,500-char cap in `manifest.py`, not in prose.
2. **Second bottleneck — multiple loaded skills:** restriction semantics get ambiguous (union vs latest). v1.1 handles "any loaded skill without allowed-tools ⇒ no filtering" (simple, safe); full combined-filtering is a documented deferred edge case.

## Anti-Patterns

### Anti-Pattern 1: Returning the full skill body as the `read_skill` tool result

**What people do:** the tool returns the SKILL.md text it read; the agent loop also injects the body as a system message.
**Why it's wrong:** the body appears twice in every subsequent request — double token cost, and the model sees redundant content.
**Do this instead:** the injected system message IS the delivery mechanism (D-12). `read_skill` returns a short confirmation string ("Skill 'X' loaded — full instructions added as a system message; use read_skill(path=...) for bundled files"). Only `path` reads return full content.

### Anti-Pattern 2: Skill bodies leaking into the JSONL session file

**What people do:** rely on the summarization exemption (context.py:88) and assume persistence is handled.
**Why it's wrong:** summarization exemption ≠ serialization exemption. `Session.to_events()` serializes **all** messages including system role (`session/models.py:73-82`) — skill bodies would land in `.agentharness/*.jsonl`, violating D-13 (loaded skills lost on close/`/new`).
**Do this instead:** `Message.persist: bool = True` (new field, default True preserves existing behavior); skill bodies created with `persist=False`; `to_events()` filters them out. **Critical pairing:** `mark_saved()` must count the same filtered set — `_last_saved_count` currently counts raw `len(self._context._messages)` while `unpersisted_events()` slices `to_events()` (filtered), so an unfixed `mark_saved()` causes index drift and event loss/duplication on save.

### Anti-Pattern 3: Path traversal through `read_skill(path=...)`

**What people do:** naive `open(base_dir / path)` in the handler.
**Why it's wrong:** the LLM is the caller; `../../etc/passwd` becomes readable. This is the exact class of bug `test_rpc_adapter.py` T-11-01 already guards against for `sessions.get`.
**Do this instead:** resolve and contain — `p = (base_dir / rel).resolve(); if not p.is_relative_to(base_dir.resolve()): raise ValueError`. (`Path.is_relative_to` is available on Python 3.12.) Mirror the T-11-01 test pattern for the new handler.

### Anti-Pattern 4: Re-scanning the skills directory per LLM call

**What people do:** call `store.discover()` inside `_build_system_prompt()`.
**Why it's wrong:** `_build_system_prompt()` runs on **every** iteration of **every** turn (agent/core.py:114). Disk I/O + frontmatter parsing per call is pure waste and can interleave with tool execution.
**Do this instead:** discover once at startup; hold the formatted manifest as a string on `Session`. Manifest rebuild timing is explicitly deferred (MILESTONE-CONTEXT "deferred ideas").

### Anti-Pattern 5: Forwarding `/skill x` as a chat prompt

**What people do:** the TUI InputBar's default branch sends any non-matched input via `client.submitPrompt`.
**Why it's wrong:** the literal string `/skill x` becomes a user message; the LLM may echo it or misbehave, and no skill loads.
**Do this instead:** intercept `/skill ` in `useInput` exactly like `/session`/`/new` (app.tsx:48-60 pattern) and call the `skills.load` RPC. Add the REPL branch to `_handle_session_cmd` (main.py) so the two frontends agree.

### Anti-Pattern 6: `allowed-tools` filtering hiding `read_skill` itself

**What people do:** whitelist filter removes every tool not in `allowed-tools`, including the loader.
**Why it's wrong:** the skill can no longer be re-read/loaded, and path reads (D-10) die with it.
**Do this instead:** the filter always retains `read_skill` (union result: `allowed ∪ {"read_skill"}`).

### Anti-Pattern 7: Storing loaded-skill state globally (runtime dict keyed by session id)

**What people do:** `self._loaded_skills: dict[session_id, ...]` on RuntimeAPI.
**Why it's wrong:** every create/switch/delete path must remember to clean up; session switches leak state; `/new` needs explicit reset.
**Do this instead:** put `SkillState` on the `Session` object (Pattern 2) — scope and reset come free.

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `main.py` → `skills/store.py`, `skills/manifest.py` | direct construction | main builds SkillStore + manifest once, passes to RuntimeAPI (all 4 RuntimeAPI construction sites: REPL, RPC, worker, main — must pass the same store/manifest) |
| `RuntimeAPI` → `Session` (`skill_manifest`, `skill_state`) | attribute set at `_create_agent()` | single choke point covers create/switch/restore and REPL `/new`,`/resume` (both call `_create_agent`); guard with `if session.skill_manifest is None` |
| `SkillToolProvider` → `RuntimeAPI.load_skill` / `store.read_path` | injected async closures | one load path for model-driven + user-driven activation; provider stays thin (Pattern 3) |
| `Agent` → tool filter | injected `tool_filter: Callable[[list[Tool]], list[Tool]] \| None` (default None) | keeps `agent/core.py` free of skills imports; filter reads `session.skill_state` at call time |
| `SkillStore.load` → `ConversationContext.add_message` | `Message(role="system", persist=False)` | system role → summarization-exempt (context.py:88) → survives compaction for the session |
| `SkillStore.load` → `harness/events.py` `SkillLoadedEvent` | RuntimeAPI emits to EventBus | → server.py map/extractor → `NotificationType.skill_loaded` → TUI `handleEvent` → notice (Pattern 4) |
| TUI InputBar → RPC `skills.load` | intercept, then `client.loadSkill(name)` | never as `chat` prompt (Anti-Pattern 5) |

### Integration Point Detail — the 5 requested seams

1. **Manifest assembly in `Session._build_system_prompt()`:** append a `# Available Skills` part from `session.skill_manifest` (string field, precomputed at startup) when non-empty. This is the OpenCode-discretion hook; the "parts list" pattern (models.py:63-69) extends naturally. Keep the manifest OUT of context (summarization never sees it — it's in the system block, rebuilt per call).
2. **`read_skill` registration:** dedicated `SkillToolProvider` (async protocol) registered `registry.add_provider("__skills__", provider)` in RuntimeAPI (not `register_builtin_tools` — that one registers into `__builtin__` and its handlers are sync). No namespace → tool name stays `read_skill`.
3. **Skill bodies as system-role messages:** `context.add_message()` already accepts system role; the only new work is `persist=False` on the `Message` so `to_events()` (JSONL) excludes them. Note `to_llm_messages()` places the body mid-list (after the triggering assistant/tool messages) — a second system message after content. This pattern already exists (`_maybe_summarize` inserts a system summary at context index 0); flag: confirm your OpenAI-compatible endpoint tolerates multiple system messages (default is a local proxy at `localhost:20128` — LOW confidence, verify once).
4. **`/skill` slash command — TUI or backend RPC?** **Backend RPC.** Loading mutates backend session state (context injection + restrictions) and must emit the event — the TUI cannot do this. The TUI only intercepts and forwards via `skills.load`; the REPL forwards via `RuntimeAPI.load_skill`. Both share the single load path (Pattern 3).
5. **allowed-tools filtering at `list_tools()`:** the boundary is `Agent.run()` immediately after `registry.list_tools()` (agent/core.py:108), implemented as an injected filter callable from `skills/filter.py`. The registry itself stays untouched — no signature change, no skills knowledge in `tool/`.

### External Services

None — the skills system adds no external services. It reads `.agentharness/skills/` from the local filesystem (co-located with session JSONLs, same convention as `JSONLSessionStore.base_dir`, D-01) and rides the existing LLM/RPC/EventBus infrastructure.

## Suggested Build Order

Dependency-aware ordering (each step's tests land with it; pure → integrated):

1. **`skills/models.py` + `skills/discovery.py` + `skills/manifest.py` + tests** — pure domain, zero integration risk. Covers D-03/D-04/D-05/D-07 (frontmatter, malformed-skip, dedupe, budget). The hand-rolled parser and budget trim are fully unit-testable.
2. **Session/context plumbing** — `Message.persist`, `Session.skill_manifest`/`skill_state` fields, Skills section in `_build_system_prompt()`, `persist` filter in `to_events()` **with the `mark_saved()` index fix** (Anti-Pattern 2). Covers SKL-02 (manifest visible to the LLM) with no tool yet. Depends on 1 (manifest text input).
3. **`skills/store.py`** — `load(session, name)` + `read_path(name, rel)` with traversal guard (Anti-Pattern 3). Depends on 1. Testable against a temp skills dir.
4. **`read_skill` tool end-to-end** — `skills/provider.py`, `SkillLoadedEvent` + event pipeline (`events.py`, `server.py`, `protocol.py`), RuntimeAPI wiring (`_create_agent` attach, `load_skill`, provider registration). Covers SKL-03. Depends on 2 + 3.
5. **allowed-tools filtering** — `skills/filter.py` + `SkillState` restrictions + `Agent.tool_filter` injection. Covers D-16. Depends on 2 + 4 (state must exist before it filters).
6. **RPC + TUI** — `skills.load` method (`protocol.py`, `adapter.py`), `rpc-client.ts`, `app.tsx` `/skill` intercept, `types.ts`, `agent-store.ts`, footer chip (D-14 discretion). Covers SKL-04. Depends on 4.
7. **REPL parity** — `main.py` `_handle_session_cmd` `/skill` branch + manifest/store construction passing into all RuntimeAPI sites. Depends on 4.
8. **E2E verification** — manual script: author a skill under `.agentharness/skills/`, confirm manifest in prompt, force-load via `/skill`, confirm system-role injection, confirm JSONL untouched, confirm `allowed-tools` filtering, confirm indicator.

**Ordering rationale:** pure discovery first (fastest feedback, no harness risk); manifest-in-prompt before any tool exists (SKL-02 is the cheapest user-visible win); store before provider (the tool's side effects depend on load/read); filtering after state exists; RPC/TUI strictly last (every backend path is already proven by 4). The `mark_saved()`/`persist` pairing is the highest-risk change and should be second, not last, so the persist-filter is in place before any real skill body ever flows through `to_events()`.

## Sources

- Read in full: `agent/core.py`, `tool/registry.py`, `tool/local_provider.py`, `tool/models.py`, `context/context.py`, `context/message.py`, `session/models.py`, `session/store.py`, `harness/runtime.py`, `harness/scheduler.py`, `harness/session_manager.py`, `harness/events.py`, `harness/event_bus.py`, `backend/rpc/{protocol,server,dispatcher,adapter}.py`, `main.py`, `config.py`, `requirements.txt`, `tui-ink/src/{app,rpc-client,types,agent-store,conversation-panel,footer}.{ts,tsx}`, `tests/conftest.py`, `tests/test_rpc_adapter.py`
- `.planning/MILESTONE-CONTEXT.md` (decisions D-01…D-16) — authoritative for all locked decisions
- `.planning/codebase/ARCHITECTURE.md`, `INTEGRATIONS.md` — existing architecture invariants (layered, DI-through-constructors, no module singletons)
- Claude Code Agent Skills model (canonical refs in MILESTONE-CONTEXT): progressive-disclosure rationale, ~1,500-char manifest budget, session persistence of loaded content, allowed-tools
- Confidence notes: all integration-point claims are HIGH (verified in source above). LOW: multi-system-message tolerance of the configured OpenAI-compatible endpoint (local proxy default); exact Claude Code budget constant (OpenCode discretion per D-07).

---
*Architecture research for: AgentHarness v1.1 Skills System*
*Researched: 2026-08-01*
