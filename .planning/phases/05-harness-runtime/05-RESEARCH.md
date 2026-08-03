# Phase 5: Harness Runtime - Research

**Researched:** 2026-07-26
**Domain:** Python async in-process event bus, scheduler, session lifecycle, TUI↔Runtime integration
**Confidence:** HIGH

## Summary

Phase 5 creates a Harness Runtime layer that sits between the TUI (pure view layer) and the Agent. The Runtime owns request lifecycle (submit/cancel), event distribution (EventBus pub/sub), session management (create/switch/persist), and background scheduling (one-turn-at-a-time dispatching with pending backlog). This replaces the current inline wiring in `main.py` where `run_tui()` and `run_repl()` manage agent lifecycle directly.

**Primary recommendation:** Implement a lightweight `asyncio`-based `EventBus` (~60 lines) with typed event dataclasses and `asyncio.gather()` dispatch. Modify `Agent.run()` to accept an optional `emit` callback (no breaking changes). Build a `Scheduler` that owns the EventBus and runs one turn at a time with a simple `asyncio.Queue` backlog. Refactor `main.py` to create a `Runtime` instance that wires everything together.

The TUI subscribes to EventBus events in `on_mount()`, dispatching UI updates via `self.call_from_thread()` or directly (since same event loop). Cancellation uses cooperative `asyncio.CancelledError` propagation through `task.cancel()`.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** TUI is a pure view layer — no worker loops, no queue management, no agent lifecycle
- **D-02:** The harness/ module owns Runtime, EventBus, Scheduler, SessionManager, Cancellation
- **D-03:** agent/core.py stays as-is but gets event emission hooks (Agent emits events during run())
- **D-04:** jobqueue/ module is for worker/background mode only — not used by interactive TUI path
- **D-05:** Lightweight in-process async EventBus — simple subscribe/publish pattern
- **D-06:** Swappable implementation (start simple, upgrade to Redis/ZeroMQ later if needed)
- **D-07:** Events: turn_started, tool_call, tool_result, response_complete, error, cancelled
- **D-08:** Two paths: interactive prompts go directly to Scheduler (no queue); worker requests go through durable SQLite queue
- **D-09:** Scheduler dispatches one turn at a time — no concurrent agent execution
- **D-10:** Existing QueueManager + SQLiteJobStore reused for worker mode, not replaced
- **D-11:** If user submits while agent is busy, second prompt enters a simple in-memory pending backlog
- **D-12:** Python in-process async API — no IPC
- **D-13:** RuntimeAPI methods: submit_prompt(), cancel(), list_sessions(), switch_session()
- **D-14:** TUI subscribes to EventBus events on mount, updates chat view on each event
- **D-15:** Non-blocking — submit_prompt() returns immediately, TUI reacts to events

### OpenCode's Discretion
- Exact EventBus implementation details (subscriber management, error handling)
- Session Manager lifecycle (auto-save timing, crash recovery)
- Cancellation mechanism (asyncio task cancellation vs cooperative flag)
- Pending backlog behavior (size limit, overflow strategy)
- Existing REPL continues using direct Agent calls or adapts to Runtime

### Deferred Ideas (OUT OF SCOPE)
- Streaming agent responses
- Swap TUI framework (Textual → OpenTUI)
- Multi-agent routing in Scheduler
- WebSocket-based remote TUI

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Event distribution (pub/sub) | Runtime (EventBus) | — | D-02: harness/ owns EventBus |
| Request lifecycle (submit/cancel) | Runtime (Scheduler) | — | D-02: harness/ owns lifecycle |
| Turn execution (Agent.run) | Agent | Runtime (Scheduler initiates) | D-03: Agent stays unchanged, gets hooks |
| Session CRUD + persistence | Runtime (SessionManager) | session/store.py | SessionManager wraps existing store |
| UI rendering | TUI | — | D-01: TUI is pure view layer |
| Worker queue persistence | jobqueue/ | — | D-04: jobqueue/ for worker mode only |
| Pending backlog | Runtime (Scheduler) | — | D-11: in-memory list in Scheduler |
| Cancellation signals | Runtime | Agent (cooperative) | Scheduler cancels agent task, Agent observes at await points |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `asyncio` | 3.12 built-in | Event loop, tasks, CancelledError, Queue, Lock | Already used throughout project |
| Python stdlib `dataclasses` | 3.12 built-in | Typed event definitions | Zero-dependency, type-safe events |
| Textual | 8.2.8 | TUI framework | D-01: TUI view layer exists; Textual's `call_from_thread()` and `post_message()` bridge external events |

[VERIFIED: pip show textual → 8.2.8, python --version → 3.12.5]

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `dataclasses` | stdlib | Event type definitions | All event types (D-07) — avoid stringly-typed events |
| `asyncio.Queue` | stdlib | Pending backlog (D-11) | Scheduler internal backlog |
| `asyncio.Lock` | stdlib | Thread-safe subscriber list mutations | EventBus subscribe/unsubscribe |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom EventBus | `pyzmq` / `redis-py` pubsub | D-06: swappable — start in-process, switch later. Custom is ~60 lines, zero deps |
| Custom EventBus | `eventiq` / `busline` library | Adds dependency for trivial pattern. D-05 confirms lightweight |
| `asyncio.CancelledError` | Cooperative flag (`_cancel_requested`) | CancelledError is simpler and correct for task-scoped cancellation. Flag needed only if you must suppress cancellation in cleanup sections |

**Installation:**
No additional dependencies required. Stdlib `asyncio` and `dataclasses` handle everything. Textual 8.2.8 already installed.

## Architecture Patterns

### System Architecture Diagram

```
User Input (TUI)
     │
     ▼
┌─────────────────────────────────────────────┐
│  RuntimeAPI                                  │
│  (submit_prompt / cancel / list_sessions     │
│   / switch_session)                          │
└─────┬───────────────────────────┬────────────┘
      │                           │
      ▼                           ▼
┌──────────┐           ┌──────────────────┐
│ Scheduler│           │ SessionManager   │
│          │           │ - create_session │
│ - 1 turn │           │ - load_session   │
│   at a   │           │ - save_session   │
│   time   │           │ - list_sessions  │
│ - backlog│           └──────┬───────────┘
│ - owns   │                  │
│  EventBus│           ┌──────▼───────────┐
└─────┬────┘           │ session/store.py │
      │                │ (JSONLSessionStore)│
      ▼                └──────────────────┘
┌──────────────┐
│  Agent.run() │
│  with emit() │
│  callback    │
└──────┬───────┘
       │ emit(turn_started)
       │ emit(tool_call)
       │ emit(tool_result)
       │ emit(response_complete)
       │ emit(error)
       └─────► EventBus ────► TUI subscribers
                                 (on_mount)
```

**Data flow for interactive path (D-08):**
1. User types in TUI → `InputBar.Submitted` fires
2. TUI calls `runtime.submit_prompt(text)` — immediately returns
3. Runtime creates session/local ID, Scheduler starts agent turn
4. Each agent event (`turn_started`, `tool_call`, etc.) emits through callback → EventBus → TUI widgets
5. TUI updates chat display reactively per event

**Data flow for worker path (D-08):**
1. External request enqueued to SQLite-backed QueueManager
2. Worker picks job, calls `runtime.submit_prompt()` (with session context)
3. Same event flow, but no TUI subscription needed (or optional)

### Recommended Project Structure
```
harness/
├── __init__.py
├── event_bus.py          # EventBus class + Event dataclasses
├── runtime.py             # RuntimeAPI class
├── scheduler.py           # Scheduler — one-turn dispatch + backlog
├── session_manager.py     # Session lifecycle (create/load/save/switch)
└── events.py              # Typed event dataclasses (turn_started, tool_call, etc.)
```

### Pattern 1: Typed Event Bus with asyncio.gather dispatch

**What:** A lightweight async EventBus with typed event objects, lock-safe subscriber lists, and concurrent handler dispatch via `asyncio.gather()`.

**When to use:** In-process pub/sub where publishers (Agent/Scheduler) emit events and subscribers (TUI, loggers) react — exactly the D-05/D-07 scope.

**Source:** [CITED: oneuptime.com/blog/post/2026-01-25-event-bus-asyncio-python] — verified pattern matches community standards for minimal asyncio event buses.

**Example:**
```python
# harness/events.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


@dataclass
class HarnessEvent:
    """Base event with common fields."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TurnStarted(HarnessEvent):
    session_id: str = ""
    prompt: str = ""


@dataclass
class ToolCallEvent(HarnessEvent):
    session_id: str = ""
    tool_name: str = ""
    arguments: dict | None = None


@dataclass
class ToolResultEvent(HarnessEvent):
    session_id: str = ""
    tool_name: str = ""
    result: str = ""


@dataclass
class ResponseComplete(HarnessEvent):
    session_id: str = ""
    content: str = ""
    iterations: int = 0
    tool_calls_made: int = 0


@dataclass
class ErrorEvent(HarnessEvent):
    session_id: str = ""
    error: str = ""


@dataclass
class CancelledEvent(HarnessEvent):
    session_id: str = ""
```


```python
# harness/event_bus.py
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from harness.events import HarnessEvent

logger = logging.getLogger(__name__)

# Type alias: async handler that accepts any HarnessEvent
EventHandler = Callable[[HarnessEvent], Awaitable[None]]


class EventBus:
    """Lightweight in-process async event bus.

    Subscribe handlers to event types (by class or string name).
    Publish dispatches to all subscribed handlers concurrently.
    Swappable: swap this class for a Redis/ZeroMQ implementation later.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        async with self._lock:
            self._handlers[event_type].append(handler)

    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        async with self._lock:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h is not handler
            ]

    async def publish(self, event: HarnessEvent) -> None:
        event_type = type(event).__name__
        async with self._lock:
            handlers = list(self._handlers.get(event_type, []))
            # Also notify wildcard subscribers (e.g., loggers)
            handlers.extend(self._handlers.get("*", []))

        if not handlers:
            return

        results = await asyncio.gather(
            *[handler(event) for handler in handlers],
            return_exceptions=True,
        )
        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.error(
                    "EventBus handler %s error for %s: %s",
                    handler.__name__, event_type, result,
                )
```

**Key design decisions:**
- `asyncio.Lock` for subscriber list mutations — not `threading.Lock` because all usage is async
- `asyncio.gather(return_exceptions=True)` — one failing handler doesn't block others; errors logged, not propagated
- String `event_type` keys (type name) rather than class-based routing — simpler, swappable-compatible
- Wildcard `"*"` subscriber for loggers/monitoring
- Thread safety: `asyncio.Lock` is single-thread/multi-coroutine; if TUI runs on different thread, `call_from_thread` is needed (see Pitfall 2)

### Pattern 2: Agent Callback Injection (non-breaking)

**What:** `Agent.__init__` accepts an optional `emit: Callable` parameter. `Agent.run()` calls `emit(event)` at lifecycle points. No existing callers break because `emit` defaults to a no-op.

**When to use:** Always — this is the D-03 contract. The callback is called from within the same async context as `Agent.run()`.

**Example:**
```python
# agent/core.py (modified)
from collections.abc import Awaitable, Callable
from typing import Any

class Agent:
    def __init__(
        self,
        llm_client: BaseLLMClient,
        tool_registry: ToolRegistry,
        session: Session,
        *,
        max_tool_iterations: int = 15,
        emit: Callable[[Any], Awaitable[None]] | None = None,  # NEW
    ):
        # ... existing init ...
        self._emit = emit or (lambda _: _dummy_awaitable())

    async def run(self, user_input: str) -> AgentResult:
        # ... existing setup ...
        await self._emit(TurnStarted(session_id=self._session.id, prompt=user_input))

        while iterations < self._max_iterations:
            # ... llm call ...
            if not response.tool_calls:
                # ... handle text response ...
                await self._emit(ResponseComplete(
                    session_id=self._session.id,
                    content=response.content,
                    iterations=iterations,
                    tool_calls_made=total_tool_calls,
                ))
                return AgentResult(...)

            for tc in response.tool_calls:
                await self._emit(ToolCallEvent(
                    session_id=self._session.id,
                    tool_name=tc.name,
                    arguments=tc.arguments,
                ))

            # ... execute tools ...
            for tc, result in zip(response.tool_calls, results):
                content = "Error: ..." if isinstance(result, Exception) else result.content
                await self._emit(ToolResultEvent(
                    session_id=self._session.id,
                    tool_name=tc.name,
                    result=content,
                ))
                await self._context.add_tool_message(tc.id, content)

            # ...

        except Exception as e:
            await self._emit(ErrorEvent(session_id=self._session.id, error=str(e)))
            raise
```

**Key design decisions:**
- `emit` defaults to `None`, resolved to a no-op — zero breakage of existing REPL/worker callers
- Events emitted at natural points in `run()` — after LLM response parsed, after tool call starts, after tool result received
- `except` block catches errors and emits `ErrorEvent` before re-raising (no silent failures)
- Callback is async — `Agent.run()` already has an `await` at every point we need to emit
- Uses typed `HarnessEvent` dataclasses — subscribers pattern-match on type

### Pattern 3: Scheduler — One Turn at a Time with Pending Backlog

**What:** Scheduler owns the EventBus, runs exactly one Agent turn at a time (D-09), maintains an in-memory backlog queue for submissions that arrive while busy (D-11).

**When to use:** Central to Runtime. Scheduler mediates all Agent interactions.

**Example:**
```python
# harness/scheduler.py
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from agent import Agent
from agent.result import AgentResult
from harness.event_bus import EventBus

logger = logging.getLogger(__name__)


class Scheduler:
    """Dispatches agent turns one at a time.
    
    - submit_prompt(): if idle, starts turn immediately; if busy, queues to backlog
    - cancel(): cancels current turn's asyncio task
    - backlog: simple asyncio.Queue, FIFO
    """

    def __init__(self, agent: Agent, event_bus: EventBus) -> None:
        self._agent = agent
        self._bus = event_bus
        self._backlog: asyncio.Queue[str] = asyncio.Queue()
        self._current_task: asyncio.Task[AgentResult] | None = None
        self._shutdown_event = asyncio.Event()

    async def submit_prompt(self, prompt: str) -> None:
        """Submit a prompt for execution.
        
        If the agent is idle, starts immediately.
        If busy, enters the pending backlog (FIFO).
        Returns immediately — results delivered via EventBus.
        """
        if self._current_task is None or self._current_task.done():
            self._current_task = asyncio.create_task(
                self._run_turn(prompt)
            )
        else:
            await self._backlog.put(prompt)
            logger.info("Agent busy, prompt queued (backlog: ~%d)", self._backlog.qsize())

    def cancel(self) -> None:
        """Cancel the current turn if one is active."""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            logger.info("Cancel requested for current turn")

    async def _run_turn(self, prompt: str) -> None:
        """Execute one turn and then drain the backlog."""
        try:
            result = await self._agent.run(prompt)
            logger.info(
                "Turn complete: %d iterations, %d tool calls",
                result.iterations, result.tool_calls_made,
            )
        except asyncio.CancelledError:
            logger.info("Turn cancelled")
            # EventBus already notified via Agent's emit → cancelled event
            raise
        except Exception as e:
            logger.exception("Turn failed: %s", e)
            raise

        # Drain backlog: process next queued prompt
        if not self._backlog.empty():
            next_prompt = self._backlog.get_nowait()
            self._current_task = asyncio.create_task(self._run_turn(next_prompt))

    async def shutdown(self) -> None:
        self.cancel()
        if self._current_task:
            try:
                await asyncio.wait_for(self._current_task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
```

### Pattern 4: TUI ↔ EventBus Integration

**What:** TUI subscribes to EventBus events in `on_mount()` and updates widgets reactively. Because the TUI shares the same event loop as the Runtime, no IPC or thread bridging is needed — event handlers can call Textual widget methods directly.

**When to use:** Always — this is the D-14 contract. The TUI is a pure view layer that reacts to events.

**Source:** [CITED: textual.textualize.io/guide/events/] — Textual's async handler pattern officially supports awaiting external events in handlers.

**Example (TUI integration approach):**

```python
# In tui/app.py (refactored)
class AgentHarnessTUI(App):
    def __init__(self, runtime: RuntimeAPI) -> None:
        super().__init__()
        self._runtime = runtime

    def on_mount(self) -> None:
        """Subscribe to Runtime EventBus events."""
        bus = self._runtime.event_bus
        
        # Fire-and-forget: create async task to subscribe
        asyncio.create_task(self._setup_subscriptions(bus))

    async def _setup_subscriptions(self, bus: EventBus) -> None:
        """Register event handlers (runs as a background task)."""
        await bus.subscribe("TurnStarted", self._on_turn_started)
        await bus.subscribe("ToolCallEvent", self._on_tool_call)
        await bus.subscribe("ToolResultEvent", self._on_tool_result)
        await bus.subscribe("ResponseComplete", self._on_response_complete)
        await bus.subscribe("ErrorEvent", self._on_error)
        await bus.subscribe("CancelledEvent", self._on_cancelled)

    async def _on_response_complete(self, event: ResponseComplete) -> None:
        """Update chat view with final response."""
        chat = self.query_one("#chat-area")
        chat.add_message("assistant", event.content)
        
    @on(InputBar.Submitted)
    async def on_submit(self, event: InputBar.Submitted) -> None:
        """Submit prompt via Runtime instead of direct agent call."""
        event.input.clear()
        await self._runtime.submit_prompt(event.value.strip())
```

**Key consideration:** TUI event handlers run on the same asyncio loop as the Runtime. Short UI updates inside handlers (<50ms) are fine. Avoid blocking operations — if a handler needs to do I/O, use `asyncio.create_task()`.

### Anti-Patterns to Avoid

- **Agent running emit callback from synchronous code:** `emit` is async; `Agent.run()` has `await` points everywhere. Never call sync handlers with async — always `await emit(...)`.
- **EventBus blocking publish waiting for all handlers:** `asyncio.gather()` with `return_exceptions=True` ensures one slow handler doesn't block others. If needed, add per-handler timeout via `asyncio.wait_for()`.
- **TUI blocking on agent completion:** D-15 requires `submit_prompt()` to return immediately. Never `await agent.run()` inside a TUI handler — always go through Scheduler.
- **Mutable event objects:** Events should be frozen dataclasses (or treated as immutable). Subscribers must not mutate event fields.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async task cancellation | Custom flag system | `asyncio.Task.cancel()` + `CancelledError` | Built-in, correct propagation through await hierarchy (D-09: one turn at a time) |
| In-process pub/sub (swappable) | Full framework | Simple EventBus (~60 lines) | D-05/D-06: current scope fits in one file; Redis/ZeroMQ later |
| Session persistence | Custom format | Existing `JSONLSessionStore` | Phase 2 already built this; SessionManager just wraps it |
| Worker queue persistence | Custom SQLite | Existing `QueueManager + SQLiteJobStore` | Phase 4 built this; D-10: reuse not replace |

**Key insight:** Every "don't hand-roll" item above is already in the stdlib or previous phases. The Runtime is an *orchestrator*, not a new persistence or concurrency primitive.

## Common Pitfalls

### Pitfall 1: Swallowing CancelledError creates zombie tasks
**What goes wrong:** A task refuses to die. After `cancel()`, the task remains pending forever, blocking shutdown.
**Why it happens:** Broad `except Exception` (Python 3.8+ `CancelledError` inherits from `BaseException`, so this is rarer now) or catching `CancelledError` without re-raising after cleanup.
**How to avoid:** Use `try/finally` for cleanup (never catch CancelledError unless you re-raise). In Scheduler, the `_run_turn` coroutine must let CancelledError propagate. The `cancel()` call drains via `await` or `gather(return_exceptions=True)`.
**Warning signs:** Shutdown hangs; `asyncio.all_tasks()` shows non-empty set; "Task was destroyed but it is pending" warning.

### Pitfall 2: TUI event handler blocks the message pump
**What goes wrong:** UI freezes. Textual widgets have an internal message queue. If an event handler (e.g., `_on_turn_started`) does a long operation, the widget can't process new messages (key presses, mouse clicks).
**Why it happens:** D-14 means TUI subscribes to Runtime events. A slow handler blocks the Textual message pump.
**How to avoid:** Keep handlers short (<50ms). Offload work via `asyncio.create_task()` if needed. Textual's `call_later()` can defer work to after current message processing.
**Warning signs:** Typing feels laggy; TUI doesn't respond to mouse after an event.

### Pitfall 3: EventBus handler exception kills publish
**What goes wrong:** One bad handler (exception) prevents remaining handlers from receiving the event. No UI updates, silent failure.
**Why it happens:** Naive `for handler in handlers: await handler(event)` — if handler A raises, handler B never runs.
**How to avoid:** Use `asyncio.gather(return_exceptions=True)` — all handlers run, exceptions are logged, not propagated.
**Warning signs:** Sporadic "half-updated" UI state; some widgets show old data.

### Pitfall 4: Mixing sync and async emit in Agent
**What goes wrong:** `TypeError: 'NoneType' object is not awaitable` or synchronous call blocks the event loop during LLM I/O.
**Why it happens:** `emit` is `Callable[[Any], Awaitable[None]]` but code calls it without `await`.
**How to avoid:** Always `await self._emit(...)`. The Agent already has `await` at every emission point. If a future use case requires synchronous emit, add a `sync_emit` parameter that uses `asyncio.create_task()` to fire events.
**Warning signs:** Random "coroutine was never awaited" warnings at certain execution paths.

## Code Examples

### EventBus Integration Test Pattern

```python
@pytest.mark.asyncio
async def test_event_bus_routes_to_subscribers():
    bus = EventBus()
    received = []

    async def handler(event: HarnessEvent) -> None:
        received.append(event)

    await bus.subscribe("TurnStarted", handler)
    await bus.publish(TurnStarted(session_id="s1", prompt="hello"))

    assert len(received) == 1
    assert isinstance(received[0], TurnStarted)
    assert received[0].prompt == "hello"
```

### Scheduler Cancel and Drain

```python
async def test_scheduler_cancel_during_turn():
    agent = _make_stub_agent(delay=1.0)  # run() takes 1 second
    bus = EventBus()
    scheduler = Scheduler(agent, bus)

    await scheduler.submit_prompt("long task")
    await asyncio.sleep(0.05)  # let it start

    scheduler.cancel()  # CancelledError injected into agent.run()
    await asyncio.sleep(0.1)
    
    assert scheduler._current_task is not None
    assert scheduler._current_task.cancelled()
```

### SessionManager Wrapping Existing Store

```python
# harness/session_manager.py
from session.models import Session, SessionSummary
from session.store import JSONLSessionStore


class SessionManager:
    """Manages session lifecycle — wraps existing JSONLSessionStore."""
    
    def __init__(self, store: JSONLSessionStore | None = None):
        self._store = store or JSONLSessionStore()
        self._active_session: Session | None = None

    @property
    def active_session(self) -> Session | None:
        return self._active_session

    async def create_session(self, **kwargs) -> Session:
        session = Session.create(**kwargs)
        await self._store.save(session)
        self._active_session = session
        return session

    async def load_session(self, session_id: str) -> Session | None:
        session = await self._store.load(session_id)
        if session is not None:
            self._active_session = session
        return session

    async def save_session(self) -> None:
        if self._active_session is not None:
            self._active_session.updated_at = datetime.now()
            await self._store.save(self._active_session)

    async def switch_session(self, session: Session) -> None:
        await self.save_session()
        self._active_session = session

    async def list_sessions(self) -> list[SessionSummary]:
        return await self._store.list_sessions()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `main.py` inline wiring (`run_tui` creates Agent directly) | Runtime wires Agent, Scheduler, EventBus, SessionManager | Phase 5 | Centralized lifecycle, testable, swappable |
| `tui/app.py` embeds worker loop + Agent | TUI is pure view, receives events | Phase 5 | D-01: TUI no longer manages agent lifecycle |
| Agent has no observability hooks | Agent emits typed events via callback | Phase 5 | D-03: TUI and loggers observe without coupling |
| Session persistence inline in REPL | SessionManager owns lifecycle | Phase 5 | Consistent save timing, crash recovery path |

**Deprecated/outdated:**
- `tui/app.py` worker loop pattern (`_worker_loop`, `_run_agent_job`) — replaced by Runtime Scheduler
- Direct `agent.run()` in TUI handlers — replaced by `runtime.submit_prompt()`
- Manual session save in REPL `finally` block — replaced by SessionManager auto-save

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Textual `call_from_thread()` not needed because TUI shares same event loop as Runtime | Patterns: Pattern 4 | Lower risk — Textual 8.x runs its own event loop, but `asyncio.create_task()` from TUI context still works on same loop. If TUI ran on separate thread, would need `call_from_thread()` |
| A2 | Agent existing callers pass no `emit` kwarg → default no-op is fine | Patterns: Pattern 2 | Low risk — grep confirms `Agent(` in `main.py` and tests; caller always uses `Agent(llm, reg, sess)` positional args |
| A3 | Backlog overflow strategy is discretionary (size limit) | OpenCode's Discretion | Low risk — in-memory `asyncio.Queue` has no upper bound by default; `maxsize` can be added |
| A4 | Python 3.12 TaskGroup or timeout() not needed for Scheduler | Patterns: Pattern 3 | MEDIUM — `TaskGroup` would provide structured concurrency for multiple turns, but D-09 says one turn at a time. Upgrade to TaskGroup if Scheduler later supports parallel agent execution |

## Open Questions (RESOLVED)

1. **REPL → Runtime adaptation (OpenCode's Discretion)**
   - What we know: The REPL currently calls `agent.run()` directly in `run_repl()`. D-08 says two paths: interactive goes through Scheduler, worker through queue.
   - What's unclear: Should the REPL also use RuntimeAPI, or remain a direct Agent caller as legacy path?
   - Recommendation: Refactor REPL to use RuntimeAPI for consistency. The change is small: create Runtime in `main()`, use `runtime.submit_prompt()`, wire EventBus events to console output.

2. **Session auto-save timing (OpenCode's Discretion)**
   - What we know: `SessionManager.save_session()` persists the active session. The REPL saves in `finally` on exit.
   - What's unclear: After every turn? On a timer? Only on session switch or shutdown?
   - Recommendation: Save after every completed turn (in Scheduler after `_run_turn` completes). Add timer-based auto-save (every 30s) for crash recovery. Keep save non-blocking via `asyncio.create_task()`.

3. **Cancellation flow: Scheduler → Agent → LLM**
   - What we know: `scheduler.cancel()` calls `task.cancel()` on the `_run_turn` task. CancelledError propagates through `agent.run()` at the next `await`.
   - What's unclear: Does canceling the agent also cancel the in-flight LLM HTTP request? The `OpenAIClient.chat_from_messages()` is not cancellable mid-stream (no streaming, no aiohttp session exposed).
   - Recommendation: For now, cancellation only prevents tool results from being processed. The LLM call completes but its result is discarded. Document this limitation. Future streaming support will naturally fix it.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | None detected — create pytest.ini or pyproject.toml |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-05 | EventBus subscribes and publishes to handlers | unit | `pytest tests/test_event_bus.py -x -q` | ❌ Wave 0 |
| D-07 | All 6 event types can be published | unit | `pytest tests/test_events.py -x -q` | ❌ Wave 0 |
| D-09 | Scheduler runs one turn at a time | unit | `pytest tests/test_scheduler.py -x -q` | ❌ Wave 0 |
| D-11 | Pending backlog queues prompts when busy | unit | `pytest tests/test_scheduler.py -x -q` | ❌ Wave 0 |
| D-13 | RuntimeAPI exposes 4 methods | unit | `pytest tests/test_runtime.py -x -q` | ❌ Wave 0 |
| D-03 | Agent emits events via callback hook | unit | `pytest tests/test_agent_events.py -x -q` | ❌ Wave 0 |
| D-14 | TUI subscribes to EventBus on mount | integration | Manual — needs Textual app | ❌ |
| D-15 | submit_prompt() returns immediately | unit | `pytest tests/test_scheduler.py -x -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_event_bus.py tests/test_scheduler.py tests/test_agent_events.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_event_bus.py` — covers EventBus subscribe/publish/error handling
- [ ] `tests/test_scheduler.py` — covers one-turn dispatch, backlog, cancel
- [ ] `tests/test_agent_events.py` — covers agent emit callback integration
- [ ] `tests/test_runtime.py` — covers RuntimeAPI 4 methods
- [ ] `tests/test_session_manager.py` — covers session lifecycle
- [ ] `tests/conftest.py` — shared fixtures (stub agent, stub event bus)
- [ ] Framework: `pip install pytest pytest-asyncio` if not installed
- [ ] `pytest.ini` — add `asyncio_mode = auto` for pytest-asyncio

*(No existing test infrastructure detected — all files are Wave 0)*

## Security Domain

> `security_enforcement` — no config.json found. Treating as not explicitly false. However, this phase has no network I/O, no user data processing, and no authentication. Included for completeness.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No user auth in Runtime |
| V3 Session Management | partial | SessionManager tracks active session; no auth tokens |
| V4 Access Control | no | Single-user tool, no multi-tenant |
| V5 Input Validation | yes | Prompt text is user input — validate length (prevent OOM via billions of char input) |
| V6 Cryptography | no | No secrets handled by Runtime |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unbounded prompt backlog | DoS | Set `maxsize` on backlog Queue; overflow → reject with error |
| Handler exception in EventBus | Tampering | `asyncio.gather(return_exceptions=True)` — one handler failure doesn't corrupt bus |

## Sources

### Primary (HIGH confidence)
- [VERIFIED: Python stdlib asyncio] — Python 3.12.5 official docs — Task cancellation, CancelledError, Queue, Lock patterns
- [VERIFIED: npm registry / pip] — Textual 8.2.8 installed — event handlers, workers, message pump docs
- [CITED: textual.textualize.io/guide/events/] — Textual message queue, async handlers, custom messages
- [CITED: textual.textualize.io/guide/workers/] — Textual Worker API, thread workers, posting messages
- [CITED: async-concurrency.com/cancellation-patterns] — asyncio cooperative cancellation, shield, drain patterns
- [CITED: docs.python.org/3/library/asyncio-task.html] — Task.cancel(), CancelledError propagation, TaskGroup, gather

### Secondary (MEDIUM confidence)
- [CITED: oneuptime.com/blog/post/2026-01-25-event-bus-asyncio-python] — Community event bus pattern with asyncio.Lock + gather dispatch — verified against official Python docs for Lock and gather usage
- [CITED: stackoverflow.com/questions/71631247] — Textual long-running async pattern (use create_task, don't await infinite loop)

### Tertiary (LOW confidence)
- None — all critical claims are HIGH. Discretionary items (backlog strategy, auto-save timing) are flagged as Assumptions or Open Questions.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, already installed and verified
- Architecture: HIGH — matches existing project patterns (async/await, constructor DI, modular package layout)
- Pitfalls: HIGH — CancelledError swallowing is a well-documented asyncio pitfall; TUI blocking is from Textual docs; all mitigations verified

**Research date:** 2026-07-26
**Valid until:** 2026-08-26 (stable stdlib; Textual 8.x is semver-stable)
