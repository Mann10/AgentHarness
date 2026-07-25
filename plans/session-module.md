# Session & SessionStore Module

## Goal
A persistent session layer inspired by local-first CLI architectures: append-only JSONL storage, system prompt owned by `Session` (not `ConversationContext`), instruction files re-read every turn, and REPL session management commands.

## Files to Create

| File | Contents |
|------|----------|
| `session/__init__.py` | Exports `Session`, `SessionStore`, `SessionSummary`, `JSONLSessionStore` |
| `session/models.py` | `Session` — owns system_prompt + ConversationContext; `SessionSummary` |
| `session/store.py` | `SessionStore` ABC + `JSONLSessionStore` (append-only format) |

## Files to Modify

| File | Changes |
|------|---------|
| `context/context.py` | Remove system prompt from `__init__`; simplify `_maybe_summarize`; `to_llm_messages()` returns only conversation messages |
| `context/message.py` | Add `Message.from_dict()` classmethod |
| `agent/core.py` | `Agent.__init__` takes `Session` instead of `ConversationContext`; use `session.to_llm_messages()` + `chat_from_messages()` in `run()` |
| `main.py` | Dynamic prompt assembly from config + AGENTS.md + env; integrate session lifecycle; session REPL commands |
| `llm/base.py` | Fix `chat_from_messages` type annotation to accept `list[Tool] \| list[dict]` (actual implementation already handles both) |
| `AGENTS.md` | Add subagent graphify dispatch rule |

## Not Modified

| Module | Reason |
|--------|--------|
| `llm/openai_client.py` | No change needed — `chat_from_messages()` already works with full message arrays |
| `tool/*` | Tool system is orthogonal |
| `config.py` | Stays as-is; `system_prompt` env var is the base prompt fed into Session |

---

## Design Details

### 1. Session Format — JSONL (append-only event log)

```
~/.agentharness/projects/{sha256(cwd)[:16]}/
├── abc123def456.jsonl
└── 7890abcdef12.jsonl
```

Each `.jsonl` file is one session. First line is metadata, subsequent lines are message events:

```jsonl
{"type":"meta","id":"abc123","title":"Refactor auth","created_at":"2026-07-25T10:00:00","updated_at":"2026-07-25T11:30:00","system_prompt":"You are a helpful assistant.","metadata":{}}
{"role":"user","content":"Help me refactor auth.py","token_count":8,"tool_calls":null,"tool_call_id":null}
{"role":"assistant","content":null,"token_count":15,"tool_calls":[{"id":"call_1","name":"read_file","arguments":{"path":"auth.py"}}],"tool_call_id":null}
{"role":"tool","content":"def login(): ...","token_count":120,"tool_calls":null,"tool_call_id":"call_1"}
```

**Append behavior:** `save()` appends only new events since last save using an in-memory cursor (`_last_saved_count`). Initial `save()` writes meta + all events. Subsequent saves append delta.

**Load:** Read all lines, skip meta, reconstruct `Message` objects, replay into `ConversationContext` via `add_message()`.

### 2. `session/models.py` — Session

```python
@dataclass
class Session:
    id: str
    system_prompt: str                      # base from env, owned here
    title: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    _context: ConversationContext | None = None
    _last_saved_count: int = 0              # cursor for append-only save

    @property
    def context(self) -> ConversationContext:
        if self._context is None:
            raise RuntimeError("Session context not restored")
        return self._context

    # ── Assembly ──────────────────────────────────────────

    def to_llm_messages(self) -> list[dict]:
        """Full messages array for API consumption: system + conversation."""
        system_block = self._build_system_prompt()
        msgs = [{"role": "system", "content": system_block}]
        msgs.extend(self._context.to_llm_messages())
        return msgs

    def _build_system_prompt(self) -> str:
        """Dynamically assemble system prompt every turn."""
        parts = [self.system_prompt]
        agents_md = Path("AGENTS.md")
        if agents_md.exists():
            parts.append(f"# Project Instructions\n\n{agents_md.read_text()}")
        parts.append(f"# Environment\nCWD: {os.getcwd()}")
        return "\n\n---\n\n".join(parts)

    # ── Serialization ─────────────────────────────────────

    def to_events(self) -> list[dict]:
        """Serialise all messages as JSONL events."""
        events = []
        for msg in self._context._messages:
            d = {"role": msg.role, "content": msg.content,
                 "token_count": msg.token_count}
            if msg.tool_calls:
                d["tool_calls"] = [asdict(tc) for tc in msg.tool_calls]
            if msg.tool_call_id:
                d["tool_call_id"] = msg.tool_call_id
            events.append(d)
        return events

    def unpersisted_events(self) -> list[dict]:
        """Events not yet written to disk."""
        events = self.to_events()
        return events[self._last_saved_count:]

    def mark_saved(self) -> None:
        self._last_saved_count = len(self._context._messages)

    def to_snapshot_meta(self) -> dict:
        return {"type": "meta", "id": self.id,
                "title": self.title,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "system_prompt": self.system_prompt,
                "metadata": self.metadata}

    @classmethod
    def from_events(cls, events: list[dict]) -> Session:
        """Reconstruct from stored JSONL events (context NOT restored)."""
        meta = events[0]
        session = cls(
            id=meta["id"],
            system_prompt=meta["system_prompt"],
            title=meta.get("title"),
            created_at=datetime.fromisoformat(meta["created_at"]),
            updated_at=datetime.fromisoformat(meta["updated_at"]),
            metadata=meta.get("metadata", {}),
            _context=None,
        )
        session._stored_events = [e for e in events[1:]]   # replay later
        return session

    async def restore_context(
        self, count_tokens, token_limit,
        summarize_fn=None, **ctx_kwargs,
    ) -> None:
        """Rebuild ConversationContext from stored events."""
        ctx = ConversationContext(
            count_tokens=count_tokens, token_limit=token_limit,
            summarize_fn=summarize_fn, **ctx_kwargs,
        )
        for e in self._stored_events:
            msg = Message.from_dict(e)
            await ctx.add_message(msg)
        self._context = ctx
        self._last_saved_count = len(self._stored_events)
        del self._stored_events

    @classmethod
    def create(
        cls, system_prompt: str, count_tokens, token_limit,
        summarize_fn=None, **ctx_kwargs,
    ) -> Session:
        ctx = ConversationContext(
            count_tokens=count_tokens, token_limit=token_limit,
            summarize_fn=summarize_fn, **ctx_kwargs,
        )
        return cls(id=uuid4().hex, system_prompt=system_prompt, _context=ctx)
```

### 3. `session/store.py` — JSONLSessionStore

```python
class SessionStore(ABC):
    @abstractmethod
    async def save(self, session: Session) -> None: ...
    @abstractmethod
    async def load(self, session_id: str) -> Session | None: ...
    @abstractmethod
    async def delete(self, session_id: str) -> None: ...
    @abstractmethod
    async def list_sessions(self) -> list[SessionSummary]: ...


class JSONLSessionStore(SessionStore):
    def __init__(self, base_dir: str | None = None):
        if base_dir is None:
            h = hashlib.sha256(os.getcwd().encode()).hexdigest()[:16]
            base_dir = Path.home() / ".agentharness" / "projects" / h
        self._dir = Path(base_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, sid: str) -> Path:
        return self._dir / f"{sid}.jsonl"

    async def save(self, session: Session) -> None:
        path = self._path(session.id)
        # First save → write meta + all events
        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps(session.to_snapshot_meta(), ensure_ascii=False) + "\n")
                for ev in session.to_events():
                    f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
        else:
            # Subsequent saves → append only delta
            new = session.unpersisted_events()
            if not new:
                return
            with open(path, "a", encoding="utf-8") as f:
                for ev in new:
                    f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
        session.mark_saved()

    async def load(self, session_id: str) -> Session | None:
        path = self._path(session_id)
        if not path.exists():
            return None
        try:
            events = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
            if not events:
                return None
            return Session.from_events(events)
        except (json.JSONDecodeError, KeyError) as e:
            logging.warning("Corrupt session %s: %s", session_id, e)
            return None

    async def delete(self, session_id: str) -> None:
        self._path(session_id).unlink(missing_ok=True)

    async def list_sessions(self) -> list[SessionSummary]:
        summaries = []
        for path in sorted(self._dir.glob("*.jsonl")):
            try:
                line = path.read_text(encoding="utf-8").splitlines()[0]
                meta = json.loads(line)
                summaries.append(SessionSummary(
                    id=meta["id"], title=meta.get("title"),
                    created_at=datetime.fromisoformat(meta["created_at"]),
                    updated_at=datetime.fromisoformat(meta["updated_at"]),
                    message_count=len(meta.get("metadata", {})),  # placeholder; real count from events
                ))
            except (IndexError, json.JSONDecodeError, KeyError) as e:
                logging.warning("Skipping corrupt session file %s: %s", path, e)
        return summaries
```

### 4. `context/context.py` — Changes

**Remove system prompt from constructor:**

```python
class ConversationContext:
    def __init__(
        self, *,                          # system_prompt removed
        count_tokens: Callable[[str], int],
        token_limit: int,
        summarize_fn: ... = None,
        summarize_threshold: float = 0.75,
        keep_recent_exchanges: int = 2,
    ) -> None:
        self._count_tokens = count_tokens
        self.token_limit = token_limit
        self._summarize_fn = summarize_fn
        self._summarize_threshold = summarize_threshold
        self._keep_recent_exchanges = keep_recent_exchanges
        self._messages: list[Message] = []
        self.total_tokens: int = 0
        # No system prompt handling
```

**Simplify `_maybe_summarize`** — remove system message filtering:

```python
async def _maybe_summarize(self) -> None:
    if not self._summarize_fn:
        return
    if self.total_tokens < self.token_limit * self._summarize_threshold:
        return

    keep_count = self._keep_recent_exchanges * 2
    recent = self._messages[-keep_count:] if keep_count > 0 else []
    to_summarize = [m for m in self._messages if m not in recent]
    if not to_summarize:
        return
    # ... rest stays the same
```

### 5. `agent/core.py` — Changes

```python
class Agent:
    def __init__(
        self,
        llm_client: BaseLLMClient,
        tool_registry: ToolRegistry,
        session: Session,                 # was ConversationContext
        *,
        max_tool_iterations: int = 15,
    ):
        self._llm = llm_client
        self._registry = tool_registry
        self._session = session
        self._context = session.context    # convenience alias
        self._max_iterations = max_tool_iterations

    async def run(self, user_input: str) -> AgentResult:
        await self._context.add_user_message(user_input)
        iterations = 0
        total_tool_calls = 0

        while iterations < self._max_iterations:
            iterations += 1
            tools = self._registry.list_tools()

            response = await self._llm.chat_from_messages(
                self._session.to_llm_messages(),   # system + context
                tools=tools if tools else None,
            )

            if not response.tool_calls:
                await self._context.add_assistant_message(response.content)
                return AgentResult(...)

            await self._context.add_assistant_tool_message(...)
            tasks = [self._registry.call_tool(tc.name, tc.arguments) for tc in response.tool_calls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for tc, result in zip(response.tool_calls, results):
                content = f"Error: {result}" if isinstance(result, Exception) else result.content
                await self._context.add_tool_message(tc.id, content)
            total_tool_calls += len(response.tool_calls)

        response = await self._llm.chat_from_messages(
            self._session.to_llm_messages(), tools=None)
        await self._context.add_assistant_message(response.content)
        return AgentResult(..., forced=True)
```

### 6. `main.py` — Full rewrite

```python
async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config = Config()
    client = OpenAIClient(config)
    registry = ToolRegistry()
    await registry.load_config(config.mcp_config_path)
    local_provider = LocalToolProvider()
    register_builtin_tools(local_provider)
    registry.add_provider("__builtin__", local_provider)

    summarize_fn = lambda msgs: client.chat_from_messages(
        [{"role": "system",
          "content": "Summarize the following conversation concisely while preserving key details."},
         *msgs],
        temperature=0.3,
    )

    store = JSONLSessionStore()
    session = await _resolve_session(store, config, client, summarize_fn)

    agent = Agent(client, registry, session)
    await agent.start()

    all_tools = registry.list_tools()
    if all_tools:
        tool_cols = 4
        rows = [all_tools[i:i + tool_cols] for i in range(0, len(all_tools), tool_cols)]
        logger.info("Available tools (%d):", len(all_tools))
        for row in rows:
            logger.info("  %s", "  ".join(f"{t.name:<25}" for t in row))

    if session.title:
        print(f'Agent Harness v2 — session "{session.title}" ({session.id[:8]})')
    else:
        print("Agent Harness v2 — type 'exit' or 'quit' to stop.")

    try:
        while True:
            try:
                line = (await asyncio.to_thread(input, "> ")).strip()
            except (EOFError, KeyboardInterrupt):
                print(); break
            if not line: continue
            if line.lower() in ("exit", "quit"): break
            if await _handle_session_cmd(line, current, store, config): continue

            result = await agent.run(line)
            if session.title is None:
                session.title = line[:50] + ("..." if len(line) > 50 else "")
            print(result.content)
            if result.forced:
                print(f"\n[Max tool iterations ({result.iterations}) reached. Forced response.]")
            print(f"[{agent._context.total_tokens}/{config.max_tokens} tokens]")
    finally:
        session.updated_at = datetime.now()
        await store.save(session)
        print(f"\nSession saved: {session.id[:8]}")
        await agent.shutdown()
```

### 7. `context/message.py` — New Method

```python
@classmethod
def from_dict(cls, d: dict) -> Message:
    tool_calls = None
    if d.get("tool_calls"):
        tool_calls = [ToolCall(**tc) for tc in d["tool_calls"]]
    return cls(
        role=d["role"],
        content=d.get("content", ""),
        token_count=d.get("token_count", 0),
        tool_calls=tool_calls,
        tool_call_id=d.get("tool_call_id"),
    )
```

### 8. `AGENTS.md` — Subagent Rule

Append after existing rules:

```
## Subagent dispatches
When spinning up an `explore` or `task` subagent to investigate code, prepend:
"Before reading files or grepping, check if graphify-out/graph.json exists and run
\`graphify query "<question>"\` — returns a scoped subgraph faster than raw browsing."
```

---

## Modules Changed Summary

| Module | Lines changed | Nature |
|--------|---------------|--------|
| `session/models.py` (new) | ~100 | Session dataclass, serialization, dynamic prompt assembly |
| `session/store.py` (new) | ~80 | JSONL append-only store |
| `session/__init__.py` (new) | ~5 | Exports |
| `context/context.py` | ~10 | Remove system prompt, simplify `_maybe_summarize` |
| `context/message.py` | ~10 | Add `from_dict()` |
| `agent/core.py` | ~10 | Accept `Session`, use `chat_from_messages` |
| `main.py` | ~120 | Session lifecycle, commands, dynamic prompt |
| `llm/base.py` | ~1 | Fix type annotation |
| `AGENTS.md` | ~5 | Subagent rule |

**Total: ~340 lines new/modified across 9 files.**

---

## Open Questions / Edge Cases

| Concern | Proposal |
|---------|----------|
| **AGENTS.md changes mid-session** | Detected naturally — `_build_system_prompt()` reads the file on every `to_llm_messages()` call. Changes take effect next turn. |
| **System prompt token count in totals** | Not included in `context.total_tokens`. Display shows conversation tokens only. API counts it server-side. |
| **JSONL meta line outdated on incremental saves** | Acceptable for v1. Future: rewrite meta line in-place or store `updated_at` in a separate index. |
| **Workspace hash collision** | SHA-256 truncated to 16 hex chars = 2^64 namespace. Negligible. |
| **Concurrent session access** | Not supported in single-user REPL. JSONL append is atomic per-line. |
| **Very large sessions (10k+ messages)** | Load all events into memory. Future: lazy-load or paginate by timestamp. |
| **`chat_from_messages` tools param type** | Fix annotation to `list[Tool] \| list[dict] \| None` — runtime already handles both. |
| **Agent `session` variable scoping in REPL** | Use mutable wrapper (`current: dict[str, Session]`) so `/new` and `/resume` can replace it. |

---

## Implementation Order

1. **Phase 1 — Foundation**: Add `Message.from_dict()` in `context/message.py`; remove system prompt from `context/context.py`
2. **Phase 2 — Session model**: `session/models.py` — `Session` + `SessionSummary`
3. **Phase 3 — Session store**: `session/store.py` — `SessionStore` ABC + `JSONLSessionStore`
4. **Phase 4 — Package init**: `session/__init__.py`
5. **Phase 5 — Agent update**: `agent/core.py` — take `Session`, use `chat_from_messages`; fix `llm/base.py` annotation
6. **Phase 6 — REPL rewrite**: `main.py` — dynamic prompt, session lifecycle, `/sessions`, `/new`, `/resume`, `/title`
7. **Phase 7 — Graphify rule**: Update `AGENTS.md`
8. **Phase 8 — Verify**: Start REPL → exchange messages → exit → restart → verify resume → `/new` → `/resume <id>` → `/title`
