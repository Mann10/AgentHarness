from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from agent import Agent
from agent.result import AgentResult
from config import Config
from llm import OpenAIClient
from session.models import Session, SessionSummary, derive_title
from session.store import JSONLSessionStore
from skills.provider import SkillToolProvider
from skills.store import SkillStore
from tool import LocalToolProvider, ToolRegistry, register_builtin_tools

from harness.event_bus import EventBus
from harness.scheduler import Scheduler
from harness.session_manager import SessionManager

logger = logging.getLogger(__name__)


class RuntimeAPI:
    """Top-level orchestrator for the Harness Runtime.

    Owns EventBus, Scheduler, SessionManager, and Agent instances.
    Provides the public API surface (D-13) consumed by TUI and REPL.

    Architecture:
    - TUI calls RuntimeAPI methods (submit_prompt, cancel, etc.)
    - RuntimeAPI delegates to Scheduler -> Agent
    - Agent emits events -> EventBus -> TUI subscribers
    - SessionManager wraps JSONLSessionStore for persistence

    D-12: Pure Python in-process async API (no IPC).
    D-13: Four public API methods.
    D-15: submit_prompt() returns immediately (delegates to Scheduler).
    """

    def __init__(
        self,
        config: Config,
        client: OpenAIClient,
        registry: ToolRegistry,
        store: JSONLSessionStore | None = None,
        *,
        skill_store: SkillStore | None = None,
        backlog_maxsize: int = 10,
    ) -> None:
        self._config = config
        self._client = client
        self._registry = registry
        self._summarize_fn = self._make_summarize_fn(client)
        self._skill_store = skill_store

        # Runtime-owned subsystems
        self._event_bus = EventBus()
        self._session_manager = SessionManager(store)
        self._scheduler: Scheduler | None = None
        self._agent: Agent | None = None

        # Configuration
        self._backlog_maxsize = backlog_maxsize

    # -- Public API (D-13) ---------------------------------

    async def submit_prompt(self, prompt: str) -> None:
        """Submit a prompt for execution. Returns immediately (D-15).

        If no active session exists, creates one automatically.
        Delegates to Scheduler which handles dispatch and backlog.
        """
        if self._scheduler is None:
            logger.warning("Runtime not started, ignoring prompt")
            return
        if self._session_manager.active_session is None:
            await self._session_manager.create_session(
                system_prompt=self._config.system_prompt,
                count_tokens=self._client.count_tokens,
                token_limit=self._config.max_tokens,
                summarize_fn=self._summarize_fn,
            )
            await self._create_agent()
        # D-13: auto-title new sessions from their first prompt (REPL parity)
        session = self._session_manager.active_session
        if session is not None and session.title is None:
            session.title = derive_title(prompt)
            # D-13: persist the auto-title NOW (not just on_turn_complete) so a
            # list_sessions() issued right after the chat RPC resolves (TUI refresh)
            # reads the title from disk instead of None.
            await self._session_manager.save_session()
        await self._scheduler.submit_prompt(prompt)

    def cancel(self) -> None:
        """Cancel the currently executing agent turn."""
        if self._scheduler is not None:
            # asyncio.create_task to run async cancel without blocking
            asyncio.create_task(self._scheduler.cancel())

    async def list_sessions(self) -> list[SessionSummary]:
        """List all saved sessions."""
        return await self._session_manager.list_sessions()

    async def create_session(self) -> Session:
        """Create a new session and set it as active. Delegates to SessionManager."""
        session = await self._session_manager.create_session(
            system_prompt=self._config.system_prompt,
            count_tokens=self._client.count_tokens,
            token_limit=self._config.max_tokens,
            summarize_fn=self._summarize_fn,
        )
        await self._create_agent()
        return session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if deleted. Delegates to SessionManager."""
        summaries = await self._session_manager.list_sessions()
        if not any(s.id == session_id for s in summaries):
            return False
        await self._session_manager.delete_session(session_id)
        return True

    async def switch_session(self, session_id: str) -> bool:
        """Switch to a different session by ID.

        Loads the session from store, restores its conversation context, then
        creates a new Agent for it. Returns False if not found or if context
        restoration fails (matches the existing not-found contract).
        """
        session = await self._session_manager.load_session(session_id)
        if session is None:
            return False
        try:
            await session.restore_context(
                count_tokens=self._client.count_tokens,
                token_limit=self._config.max_tokens,
                summarize_fn=self._summarize_fn,
            )
        except Exception:
            logger.exception("Failed to restore context for session %s", session_id[:8])
            return False
        await self._create_agent()
        return True

    async def get_session_history(self, session_id: str) -> list[dict] | None:
        """Return a session's stored conversation messages in chronological order.

        Pure read — does NOT switch the active session. Returns None if the
        session doesn't exist or its file is corrupt (store.load already
        returns None in those cases).
        """
        session = await self._session_manager.get_session(session_id)
        if session is None:
            return None
        return session.get_messages()

    # -- Properties ----------------------------------------

    @property
    def event_bus(self) -> EventBus:
        """Expose EventBus for TUI subscription (D-14)."""
        return self._event_bus

    @property
    def active_session(self) -> Session | None:
        return self._session_manager.active_session

    @property
    def is_busy(self) -> bool:
        """True if an agent turn is currently executing."""
        return self._scheduler is not None and self._scheduler.is_busy

    # -- Skills (D-09 single shared load path) ------------------

    async def load_skill(self, name: str) -> str:
        """D-09: single shared load path (read_skill tool + /skill command later).

        Dedup (D-07) via session.skill_state['loaded'] → injection (D-08) via
        add_skill_message → short ack (D-05). Body flows as system message only.
        H-01: dedup compares the CANONICAL name from SkillStore.lookup()
        (case-insensitive on win32), never the raw caller name — case-variant
        re-loads are no-ops.
        """
        if self._skill_store is None:
            raise RuntimeError("SkillStore not configured")
        session = self._session_manager.active_session
        if session is None:
            raise RuntimeError("No active session")
        info = self._skill_store.lookup(name)          # KeyError → clear error (canonical name)
        loaded = session.skill_state.get("loaded", [])
        existing = next((e for e in loaded if e["name"] == info.name), None)
        if existing is not None:
            return f"Skill '{info.name}' already loaded"   # D-07 no-op ack (canonical name)
        body = self._skill_store.load(name)
        # H-03 hardening: mark the record BEFORE the injection await — any
        # concurrent load_skill caller sees the record (no TOCTOU double-inject).
        loaded.append({"name": info.name, "dir": str(info.path)})   # D-09 record (name + base dir)
        session.skill_state["loaded"] = loaded
        await session.context.add_skill_message(info.name, body)
        return f"Loaded skill {info.name}"             # D-05 short ack

    async def load_skill_status(self, name: str) -> dict:
        """D-06: structured load result — {skill: <canonical>, status: loaded|already_loaded}.

        No body echoed. KeyError propagates for unknown skills (adapter maps to
        SKILL_NOT_FOUND). The actual load goes through self.load_skill — the same
        shared path as read_skill (D-07), so activation cannot drift.
        """
        if self._skill_store is None:
            raise RuntimeError("SkillStore not configured")
        session = self._session_manager.active_session
        if session is None:
            raise RuntimeError("No active session")
        info = self._skill_store.lookup(name)          # KeyError → unknown skill
        loaded = session.skill_state.get("loaded", [])
        if any(e["name"] == info.name for e in loaded):   # canonical dedup (H-01)
            return {"skill": info.name, "status": "already_loaded"}
        await self.load_skill(info.name)                   # D-07 shared path
        return {"skill": info.name, "status": "loaded"}

    async def _read_skill_path(self, skill: str, rel: str) -> str:
        """read_skill_path handler — delegates to SkillStore (14-01 traversal guard)."""
        if self._skill_store is None:
            raise RuntimeError("SkillStore not configured")
        return self._skill_store.read_path(skill, rel)

    def make_skill_provider(self) -> SkillToolProvider:
        """Build the __skills__ provider bound to this runtime's load/read handlers.

        Registered by main.py BEFORE runtime.start() — the provider must be in the
        registry before registry.start() runs inside Agent.start().
        """
        return SkillToolProvider(
            load_handler=self.load_skill,
            read_handler=self._read_skill_path,
        )

    # -- Lifecycle -----------------------------------------

    async def start(self) -> None:
        """Initialize all subsystems.

        1. Create a default session
        2. Create Agent for that session
        3. Start Scheduler
        """
        await self._session_manager.create_session(
            system_prompt=self._config.system_prompt,
            count_tokens=self._client.count_tokens,
            token_limit=self._config.max_tokens,
            summarize_fn=self._summarize_fn,
        )
        await self._create_agent()

        self._scheduler = Scheduler(
            self._agent,
            self._event_bus,
            backlog_maxsize=self._backlog_maxsize,
            on_turn_complete=self._session_manager.save_session,
        )
        await self._scheduler.start()
        logger.info("RuntimeAPI started")

    async def shutdown(self) -> None:
        """Gracefully shut down all subsystems.

        1. Save active session
        2. Shutdown scheduler (cancels current turn with 5s timeout)
        3. Shutdown agent
        """
        if self._scheduler is not None:
            await self._scheduler.shutdown()
        await self._session_manager.save_session()
        if self._agent is not None:
            await self._agent.shutdown()
        logger.info("RuntimeAPI shut down")

    # -- Internal ------------------------------------------

    async def _create_agent(self) -> None:
        """Create an Agent for the active session.

        If an agent already exists, shuts it down first.
        The agent's emit callback is wired during Scheduler construction,
        not here -- Scheduler overrides agent._emit with bus.publish.
        """
        session = self._session_manager.active_session
        if session is None:
            raise RuntimeError("Cannot create agent: no active session")

        # Phase 12 seam: attach the skills manifest once per Session object.
        if session.skill_manifest is None and self._skill_store is not None:
            from skills.discovery import discover_skills
            from skills.manifest import build_manifest_text

            entries = discover_skills(self._skill_store._root)
            text = build_manifest_text(entries)
            if text:
                session.skill_manifest = text

        if self._agent is not None:
            await self._agent.shutdown()

        self._agent = Agent(
            self._client,
            self._registry,
            session,
            max_tool_iterations=self._config.max_tool_iterations,
        )
        await self._agent.start()
        if self._scheduler is not None:
            self._scheduler.set_agent(self._agent)

    @staticmethod
    def _make_summarize_fn(client: OpenAIClient) -> Callable[[list[dict]], Awaitable[str]]:
        """Create a summarize function from the LLM client.

        Duplicated from main.py to keep RuntimeAPI self-contained.
        Will replace main.py's version when integrated.
        """
        SUMMARIZATION_PROMPT = """\
You are summarizing a conversation between a user and an AI coding assistant \
for the purpose of preserving context in a long-running session.

Read the following conversation history and produce a concise summary that captures:

1. **Current goal** -- What the user is working on
2. **Key decisions** -- Important choices made and why
3. **Progress made** -- What has been accomplished so far
4. **Files/tools touched** -- Which files were created/modified, tools invoked
5. **Open questions** -- Any unresolved issues or next steps discussed
6. **Technical context** -- Important technical details the assistant needs to know

Write this as a structured report (not a narrative). Use bullet points.
The summary will be read by an AI assistant to continue the conversation,
so include everything necessary to maintain continuity.
"""

        async def _summarize(msgs: list[dict]) -> str:
            response = await client.chat_from_messages(
                [
                    {"role": "system", "content": SUMMARIZATION_PROMPT},
                    *msgs,
                ],
                temperature=0.3,
            )
            return response.content

        return _summarize
