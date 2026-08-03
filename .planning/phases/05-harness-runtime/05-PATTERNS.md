# Phase 5: Harness Runtime - Pattern Map

**Mapped:** 2026-07-26
**Files analyzed:** 9 (6 new, 3 modified)
**Analogs found:** 7 with matches / 9 total

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `harness/__init__.py` | config | N/A | `jobqueue/__init__.py` | exact |
| `harness/runtime.py` | controller/orchestrator | request-response | `jobqueue/manager.py` | role-match |
| `harness/event_bus.py` | utility/bus | event-driven | *(no exact analog — see notes at end)* | new |
| `harness/scheduler.py` | service | dispatch + CRUD | `jobqueue/manager.py` | role-match |
| `harness/session_manager.py` | service | CRUD | `session/store.py` | role-match |
| `harness/cancellation.py` | utility | event-driven | *(cooperative flag pattern from existing)* | partial |
| `agent/core.py` (modified) | service | request-response | `agent/core.py` (current) | self-analog |
| `tui/app.py` (modified) | component | event-driven | `tui/app.py` (current) | self-analog |
| `main.py` (modified) | config/wiring | startup | `main.py` (current) | self-analog |

---

## Pattern Assignments

### `harness/__init__.py` (config, N/A)

**Analog:** `jobqueue/__init__.py`

**File:** `C:\personal\AgentHarness\jobqueue\__init__.py` (full file, 5 lines)

```python
from jobqueue.models import Job, JobStatus, JobPriority
from jobqueue.store import SQLiteJobStore
from jobqueue.manager import QueueManager

__all__ = ["Job", "JobStatus", "JobPriority", "SQLiteJobStore", "QueueManager"]
```

**Pattern to copy:** Barrel-export every public class from the module. Use `__all__` to declare the public API surface. Use relative imports *within* the harness module; since `harness/` is a top-level package, import from `harness.<name>` internally.

**Copy:** Same structure, swapping names:
```python
from harness.runtime import RuntimeAPI
from harness.event_bus import EventBus
from harness.scheduler import Scheduler
from harness.session_manager import SessionManager
from harness.cancellation import CancellationToken

__all__ = ["RuntimeAPI", "EventBus", "Scheduler", "SessionManager", "CancellationToken"]
```

---

### `harness/runtime.py` (controller/orchestrator, request-response)

**Analog:** `jobqueue/manager.py`

**File:** `C:\personal\AgentHarness\jobqueue\manager.py` (82 lines)

**Imports pattern** (lines 1-9):
```python
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from jobqueue.models import Job, JobPriority, JobStatus
from jobqueue.store import SQLiteJobStore
```

**Class lifecycle pattern** (lines 13-27):
```python
class QueueManager:
    def __init__(self, store: SQLiteJobStore | None = None):
        self._store = store or SQLiteJobStore()
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._new_job_event = asyncio.Event()
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._store.reset_in_flight()

    async def shutdown(self) -> None:
        self._running = False
        self._new_job_event.set()
        self._store.close()
```

**Core async method pattern** (lines 29-44):
```python
    async def enqueue(
        self,
        prompt: str,
        priority: JobPriority = JobPriority.NORMAL,
        session_id: str | None = None,
    ) -> Job:
        job = Job(
            prompt=prompt,
            priority=priority,
            session_id=session_id,
        )
        self._store.enqueue(job)
        await self._queue.put(job)
        self._new_job_event.set()
        logger.info("Enqueued job %s: %s", job.short_id, job.prompt_preview)
        return job
```

**Logger pattern** (line 10):
```python
logger = logging.getLogger(__name__)
```

**Pattern to copy:**
- Constructor dependency injection with optional defaults (`store | None = None`)
- `async def start()` / `async def shutdown()` lifecycle pair
- `_running: bool` guard flag
- `logger = logging.getLogger(__name__)` at module level
- Private attributes prefixed with `_` throughout
- Return `self`-typed objects from factory/create methods
- `from __future__ import annotations` at top

**Additional analog — main.py wiring pattern** (`C:\personal\AgentHarness\main.py`, lines 344-366):
```python
async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _parse_args()
    config = Config()
    client = OpenAIClient(config)
    registry = ToolRegistry()
    await registry.load_config(config.mcp_config_path)

    local_provider = LocalToolProvider()
    register_builtin_tools(local_provider)
    registry.add_provider("__builtin__", local_provider)

    summarize_fn = _make_summarize_fn(client)
    store = JSONLSessionStore()
    queue_manager = QueueManager()
    await queue_manager.start()

    if args.tui:
        await run_tui(config, client, registry, queue_manager, args.workers)
    elif args.worker:
        await run_worker(config, client, registry, queue_manager, args.workers)
    else:
        await run_repl(config, client, registry, store, summarize_fn)
```

**RuntimeAPI pattern to produce:** An orchestrator class that owns `EventBus`, `Scheduler`, `SessionManager`, `CancellationToken`. Exposes `submit_prompt()`, `cancel()`, `list_sessions()`, `switch_session()` as public API. Follows the constructor-DI + start/shutdown pattern from QueueManager.

---

### `harness/event_bus.py` (utility/bus, event-driven)

**No exact analog exists in the codebase** — this is the first event-driven component. However, the project's **async patterns** and **asyncio concurrency primitives** are consistently used throughout. Use these existing async patterns as the foundation:

**Reference — asyncio.Event usage from `jobqueue/manager.py`** (lines 16-17, 26, 40):
```python
self._new_job_event = asyncio.Event()  # line 17
self._new_job_event.set()              # line 26 (shutdown)
self._new_job_event.set()              # line 42 (wake waiter)
```

**Reference — logging convention from all files:**
```python
logger = logging.getLogger(__name__)
```

**Reference — agent event types from `agent/core.py`** (lines 44-118):
The Agent's `run()` method has clear lifecycle stages that become event types:
```python
    # turn_started event
    response = await self._llm.chat_from_messages(...)   # after this
    # tool_call event (one per tool call in response.tool_calls)
    results = await asyncio.gather(*tasks, return_exceptions=True)   # after this
    # tool_result event (per result)
    # response_complete event
```

**Event types derived from context (D-07):**
- `turn_started` — When a prompt begins processing
- `tool_call` — When agent requests a tool execution
- `tool_result` — When tool returns
- `response_complete` — When agent finishes a turn with text
- `error` — When something fails
- `cancelled` — When user cancels

**Pattern to use for EventBus implementation:**
- `subscribe(event_type, callback)` — store in dict of `event_type -> list[callable]`
- `publish(event_type, data)` — iterate and `await` callbacks
- Typed event data via `@dataclass` (project convention, see `tool/models.py`)
- Constructor dependency injection for swappable backend (D-06)

---

### `harness/scheduler.py` (service, dispatch + CRUD)

**Analog:** `jobqueue/manager.py` (full file, 82 lines) — same wait-for-work pattern

**Core dispatch pattern from manager** (lines 46-64):
```python
    async def wait_for_job(self) -> Job:
        while self._running:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                updated = self._store.dequeue()
                if updated:
                    logger.info("Dequeued job %s: %s", updated.short_id, updated.prompt_preview)
                    return updated
                else:
                    logger.warning("Job %s was stolen or already dequeued", job.short_id)
                    continue
            except asyncio.TimeoutError:
                if not self._store.pending_count():
                    continue
                job_from_db = self._store.dequeue()
                if job_from_db:
                    logger.info("Dequeued stale job %s from DB", job_from_db.short_id)
                    return job_from_db
                continue
```

**Agent dispatch target from `agent/core.py`** (lines 44-45, 57-72):
```python
    async def run(self, user_input: str) -> AgentResult:
        await self._context.add_user_message(user_input)
        ...
        response = await self._llm.chat_from_messages(
            self._session.to_llm_messages(), tools=tools if tools else None
        )
        if not response.tool_calls:
            ...
            await self._context.add_assistant_message(response.content)
            return AgentResult(content=response.content, ...)
```

**Pattern to copy for Scheduler:**
- `self._pending_backlog: list[tuple[str, str]]` — simple in-memory list (D-11: "simple in-memory pending backlog")
- `self._busy: bool` — flag when agent is executing
- `self._running: bool` — lifecycle flag
- `async def dispatch(prompt: str, session_id: str)` — either runs immediately or enqueues to backlog
- `async def _execute_next()` — pops from backlog, calls `agent.run()`, publishes events
- QueueManager's `wait_for_job` pattern adapted to single-threaded dispatch
- Constructor DI: receives `agent: Agent`, `event_bus: EventBus`, optionally `queue_manager: QueueManager` for worker path

---

### `harness/session_manager.py` (service, CRUD)

**Analog:** `session/store.py` (105 lines)

**Imports pattern** (lines 1-11):
```python
from __future__ import annotations

import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from session.models import Session, SessionSummary
```

**Core CRUD pattern** (lines 31-37, 42-58):
```python
class JSONLSessionStore(SessionStore):

    def __init__(self, base_dir: str | None = None):
        if base_dir is None:
            base_dir = Path.cwd() / ".agentharness"
        self._dir = Path(base_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    async def save(self, session: Session) -> None:
        path = self._path(session.id)
        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps(session.to_snapshot_meta(), ensure_ascii=False) + "\n")
                for ev in session.to_events():
                    f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
        else:
            new_events = session.unpersisted_events()
            if not new_events:
                return
            with open(path, "a", encoding="utf-8") as f:
                for ev in new_events:
                    f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
        session.mark_saved()
```

**Session switching pattern from `main.py`** (lines 132-146):
```python
    if cmd == "/new":
        session = current["session"]
        session.updated_at = datetime.now()
        await store.save(session)
        old_id = session.id[:8]
        new_session = Session.create(
            system_prompt=config.system_prompt,
            count_tokens=client.count_tokens,
            token_limit=config.max_tokens,
            summarize_fn=summarize_fn,
        )
        agent.switch_session(new_session)
        current["session"] = new_session
        print(f"Session {old_id} saved. New session {new_session.id[:8]} started.")
```

**Logger pattern** (line 13):
```python
logger = logging.getLogger(__name__)
```

**Pattern to copy for SessionManager:**
- Wraps `JSONLSessionStore` or similar store
- Methods: `create_session()`, `switch_session(session_id)`, `save_session()`, `list_sessions()`, `load_session()`
- Calls `agent.switch_session()` when switching sessions
- Auto-save before switch: save current, then load new
- Constructor DI: receives `store: JSONLSessionStore | None = None` with default creation
- Follows same `async` signatures as JSONLSessionStore

---

### `harness/cancellation.py` (utility, event-driven)

**No direct analog class** — Cancellation is handled ad-hoc. Two existing patterns:

**Pattern A — asyncio.CancelledError + graceful break** from `tui/app.py` (lines 62-74):
```python
    async def _worker_loop(self, worker_id: int) -> None:
        while True:
            try:
                job = await self._manager.wait_for_job()
                ...
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Worker %d error", worker_id)
```

**Pattern B — asyncio.Event as shutdown signal** from `main.py` (lines 260-270, 295-300):
```python
    shutdown_event = asyncio.Event()

    def _handle_sig() -> None:
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_sig)
        except NotImplementedError:
            pass
    ...
    await shutdown_event.wait()
    logger.info("Shutting down workers...")
    for task in worker_tasks:
        task.cancel()
    await asyncio.gather(*worker_tasks, return_exceptions=True)
```

**Pattern to use for CancellationToken:**
- `class CancellationToken:` with `self._cancelled = False` and `self._event = asyncio.Event()`
- `def cancel()` — sets `_cancelled = True`, sets `_event`
- `cancelled` property
- `async def wait()` — awaits `_event`
- Cooperative checking pattern: Scheduler and Agent check `token.cancelled` at yield points
- Follow project's constructor-DI convention: `CancellationToken` passed to Scheduler, which checks before dispatching each turn

---

### `agent/core.py` (modified — add event emission hooks)

**Self-analog:** `C:\personal\AgentHarness\agent\core.py` (current, 130 lines)

**Current `Agent.__init__`** (lines 15-28):
```python
class Agent:
    def __init__(
        self,
        llm_client: BaseLLMClient,
        tool_registry: ToolRegistry,
        session: Session,
        *,
        max_tool_iterations: int = 15,
    ):
        self._llm = llm_client
        self._registry = tool_registry
        self._session = session
        self._context = session.context
        self._max_iterations = max_tool_iterations
```

**Event emission insertion points in `run()`** (lines 44-118):
```python
    async def run(self, user_input: str) -> AgentResult:
        await self._context.add_user_message(user_input)
        # → EMIT turn_started(user_input)

        iterations = 0
        total_tool_calls = 0

        while iterations < self._max_iterations:
            iterations += 1
            # ...
            response = await self._llm.chat_from_messages(...)

            if not response.tool_calls:
                # → EMIT response_complete(response.content)
                return AgentResult(content=response.content, ...)

            # → EMIT tool_call(tc) for each tool call
            tasks = [...]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for tc, result in zip(response.tool_calls, results):
                # → EMIT tool_result(tc, result)
                ...
```

**Pattern to add:**
- Add `emit_callback: Callable[[str, Any], Awaitable[None]] | None = None` to `__init__`
- Optional parameter — backward compatible if not provided
- At each lifecycle point: `if self._emit: await self._emit(event_type, data)`
- Event types: `"turn_started"`, `"tool_call"`, `"tool_result"`, `"response_complete"`, `"error"`
- The callback receives `(event_type: str, data: dict)` or use typed dataclass
- Use `from collections.abc import Awaitable, Callable` for typing (existing project convention in `session/models.py`)

---

### `tui/app.py` (modified — refactor to pure event subscriber)

**Self-analog:** `C:\personal\AgentHarness\tui\app.py` (current, 101 lines)

**Current TUI patterns to RETAIN** (TUI framework patterns stay):
```python
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Header
```

**Current patterns to REMOVE:**
- `self._manager = queue_manager or QueueManager()` (line 38) — Runtime owns this
- `self._worker_tasks: list[asyncio.Task] = []` (line 39) — Runtime owns workers
- `_worker_loop`, `_start_manager` (lines 56-74) — Runtime owns scheduling
- `self.set_interval(2, self._refresh)` (line 54) — EventBus replaces polling

**New pattern to ADD — event subscription via `on_mount`:**
```python
    def __init__(self, runtime: RuntimeAPI, event_bus: EventBus) -> None:
        super().__init__()
        self._runtime = runtime
        self._event_bus = event_bus

    def on_mount(self) -> None:
        self._event_bus.subscribe("turn_started", self._on_turn_started)
        self._event_bus.subscribe("tool_call", self._on_tool_call)
        self._event_bus.subscribe("tool_result", self._on_tool_result)
        self._event_bus.subscribe("response_complete", self._on_response_complete)
        self._event_bus.subscribe("error", self._on_error)
        self._event_bus.subscribe("cancelled", self._on_cancelled)
```

**New pattern — submit goes through Runtime:**
```python
    @on(InputBar.Submitted)
    async def on_submit(self, event: InputBar.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt:
            return
        self._runtime.submit_prompt(prompt)
        event.input.clear()
```

---

### `main.py` (modified — use Runtime instead of inline wiring)

**Self-analog:** `C:\personal\AgentHarness\main.py` (current, 370 lines)

**Current pattern — inline wiring** (lines 344-366):
```python
async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _parse_args()
    config = Config()
    client = OpenAIClient(config)
    registry = ToolRegistry()
    await registry.load_config(config.mcp_config_path)

    local_provider = LocalToolProvider()
    register_builtin_tools(local_provider)
    registry.add_provider("__builtin__", local_provider)

    summarize_fn = _make_summarize_fn(client)
    store = JSONLSessionStore()
    queue_manager = QueueManager()
    await queue_manager.start()

    if args.tui:
        await run_tui(config, client, registry, queue_manager, args.workers)
    elif args.worker:
        await run_worker(config, client, registry, queue_manager, args.workers)
    else:
        await run_repl(config, client, registry, store, summarize_fn)
```

**Pattern to change to:**
```python
async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _parse_args()
    config = Config()
    # ... client, registry setup stays the same ...

    runtime = RuntimeAPI(
        client=client,
        registry=registry,
        config=config,
        # SessionStore and QueueManager now owned by Runtime internals
    )
    await runtime.start()

    if args.tui:
        app = AgentHarnessTUI(runtime=runtime, event_bus=runtime.event_bus)
        await app.run_async()
    elif args.worker:
        await runtime.run_worker(count=args.workers)
    else:
        await runtime.run_repl()
```

**Import changes** — `main.py` currently imports directly from `agent`, `llm`, `session`, `tool`, `jobqueue`. After refactoring:
- RETRAIN: `from agent import Agent`, `from config import Config`, `from llm import OpenAIClient`, `from tool import ...`
- ADD: `from harness import RuntimeAPI`
- REMOVE: direct imports of `QueueManager`, `JSONLSessionStore` (now owned by Runtime)
- REMOVE: `run_repl`, `run_worker`, `run_tui`, `_resolve_session`, `_handle_session_cmd` functions (now methods on RuntimeAPI)

---

## Shared Patterns

### Package Init (Barrel Exports)
**Source:** `jobqueue/__init__.py` (5 lines), `agent/__init__.py` (4 lines)
**Apply to:** `harness/__init__.py`

```python
from harness.runtime import RuntimeAPI
from harness.event_bus import EventBus
from harness.scheduler import Scheduler
from harness.session_manager import SessionManager
from harness.cancellation import CancellationToken

__all__ = ["RuntimeAPI", "EventBus", "Scheduler", "SessionManager", "CancellationToken"]
```

### Class Lifecycle (start/shutdown)
**Source:** `jobqueue/manager.py` lines 13-27
**Apply to:** `RuntimeAPI`, `Scheduler`, `SessionManager`

```python
class SomeManager:
    def __init__(self, dep: DepType | None = None):
        self._dep = dep or DefaultDep()
        self._running = False

    async def start(self) -> None:
        self._running = True

    async def shutdown(self) -> None:
        self._running = False
```

### Constructor Dependency Injection
**Source:** Every class in the codebase — `agent/core.py` line 16, `jobqueue/manager.py` line 14, `session/store.py` line 33
**Apply to:** Every new class

Pattern: receive dependencies as optional constructor parameters with `| None = None` and default construction. Private attributes prefixed with `_`.

### Logging
**Source:** Every module
**Apply to:** Every new file

```python
import logging
logger = logging.getLogger(__name__)
```

### Async I/O Throughout
**Source:** `agent/core.py`, `jobqueue/manager.py`, `session/store.py`
**Apply to:** All methods that involve I/O, event publishing, or agent dispatch

Every public method except trivial getters is `async def`. All I/O uses `asyncio` primitives (`asyncio.Event`, `asyncio.Queue`, `asyncio.gather`).

### Error Handling
**Source:** `jobqueue/manager.py` lines 70-73, `tui/app.py` lines 71-74
**Apply to:** Scheduler (dispatch errors), Runtime (event errors)

```python
# Error logging pattern — log exception, don't crash the loop
except Exception as e:
    logger.exception("Contextual message: %s", e)
```

### Cancellation Pattern
**Source:** `main.py` lines 262-270, `tui/app.py` lines 71-72
**Apply to:** `CancellationToken`, Scheduler dispatch loop

```python
# Graceful CancelledError handling
except asyncio.CancelledError:
    break  # or return — clean exit, no re-raise
```

### Dataclass Models
**Source:** `tool/models.py`, `session/models.py`, `agent/result.py`, `jobqueue/models.py`
**Apply to:** EventBus event data types

```python
from dataclasses import dataclass, field

@dataclass
class SomeModel:
    name: str
    value: int = 0
```

### `from __future__ import annotations`
**Source:** Almost all files in the project
**Apply to:** Every new file

```python
from __future__ import annotations
```

---

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns or standard library references instead):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `harness/event_bus.py` | utility/bus | event-driven | No existing pub/sub event bus in the project. Use Python's `asyncio` primitives + simple dict-of-lists pattern. Reference: `asyncio.Event` usage in `jobqueue/manager.py` lines 17, 26, 42. |
| `harness/cancellation.py` | utility | event-driven | No existing `CancellationToken` class. Use `asyncio.Event` based cooperative cancellation. Reference: signal handler + Event pattern in `main.py` lines 260-270. |

---

## Metadata

**Analog search scope:** `agent/`, `tui/`, `jobqueue/`, `session/`, `main.py`, `llm/`, `tool/`, `context/`, `tests/`
**Files scanned:** 34 Python source files
**Pattern extraction date:** 2026-07-26
