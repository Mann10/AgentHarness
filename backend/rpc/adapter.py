from __future__ import annotations

"""RuntimeAPI adapter — wraps RuntimeAPI and maps RPC method names to API calls.

This is the glue layer between JSON-RPC methods and the RuntimeAPI.
No business logic — pure delegation with dict serialization.
"""

import logging
from typing import Any

from backend.rpc.dispatcher import Dispatcher
from backend.rpc.protocol import RPCError, INVALID_PARAMS, INTERNAL_ERROR, SKILL_NOT_FOUND
from harness.runtime import RuntimeAPI

logger = logging.getLogger(__name__)


class RPCAdapter:
    """Wraps RuntimeAPI, mapping RPC method names to API calls.

    Each handle_* method accepts a params dict (or None) and returns
    a serializable dict suitable for JSON-RPC responses.
    """

    def __init__(self, runtime: RuntimeAPI) -> None:
        self._runtime = runtime

    async def handle_chat(self, params: dict | None) -> dict:
        """Submit a prompt for execution."""
        if params is None or "prompt" not in params:
            return {"status": "error", "message": "Missing 'prompt' in params"}
        await self._runtime.submit_prompt(params["prompt"])
        return {"status": "accepted"}

    def handle_cancel(self, params: dict | None) -> dict:
        """Cancel the currently executing agent turn."""
        self._runtime.cancel()
        return {"status": "cancelling"}

    async def handle_sessions_list(self, params: dict | None) -> list[dict]:
        """List all saved sessions."""
        summaries = await self._runtime.list_sessions()
        return [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "message_count": s.message_count,
            }
            for s in summaries
        ]

    async def handle_sessions_switch(self, params: dict | None) -> dict:
        """Switch to a different session by ID."""
        if params is None or "session_id" not in params:
            return {"success": False, "message": "Missing 'session_id' in params"}
        success = await self._runtime.switch_session(params["session_id"])
        return {"success": success}

    async def handle_sessions_create(self, params: dict | None) -> dict:
        """Create a new session."""
        session = await self._runtime.create_session()
        return {"session_id": session.id}

    async def handle_sessions_delete(self, params: dict | None) -> dict:
        """Delete a session by ID."""
        if params is None or "session_id" not in params:
            return {"deleted": False, "message": "Missing 'session_id' in params"}
        deleted = await self._runtime.delete_session(params["session_id"])
        return {"deleted": deleted}

    async def handle_sessions_get(self, params: dict | None) -> dict:
        """Return a session's stored conversation messages (chronological)."""
        if params is None or "session_id" not in params:
            return {"error": "Missing 'session_id' in params"}
        session_id = params["session_id"]
        if not isinstance(session_id, str) or not session_id.isalnum():
            return {"error": "Invalid session_id"}
        history = await self._runtime.get_session_history(session_id)
        if history is None:
            return {"error": "Session not found"}
        return {"messages": history}

    def handle_sessions_active(self, params: dict | None) -> dict:
        """Return the id of the runtime's active session (or null if none).

        The TUI binds this on connect so the panels show the real session
        name instead of a fallback when a fresh session is auto-created.
        """
        session = self._runtime.active_session
        return {"session_id": session.id if session is not None else None}

    def handle_ping(self, params: dict | None) -> dict:
        """Health check — returns ok."""
        return {"status": "ok"}

    async def handle_skills_load(self, params: dict | None) -> dict:
        """Load a skill by name — D-06/D-08. Errors raise RPCError (structured)."""
        if params is None or "name" not in params or not isinstance(params["name"], str) or not params["name"].strip():
            raise RPCError(code=INVALID_PARAMS, message="Missing 'name' in params")
        name = params["name"].strip()
        try:
            return await self._runtime.load_skill_status(name)
        except KeyError:
            raise RPCError(code=SKILL_NOT_FOUND, message=f"Skill '{name}' not found.")
        except RuntimeError as exc:
            # D-11 cap-breach contract: mapped to documented -32603 INTERNAL_ERROR
            # with the verbatim D-11 message (the message string IS the contract).
            raise RPCError(code=INTERNAL_ERROR, message=str(exc))

    def register_all(self, dispatcher: Dispatcher) -> None:
        """Register all 10 RPC methods with the given dispatcher."""
        dispatcher.register("chat", self.handle_chat)
        dispatcher.register("cancel", self.handle_cancel)
        dispatcher.register("sessions.list", self.handle_sessions_list)
        dispatcher.register("sessions.switch", self.handle_sessions_switch)
        dispatcher.register("sessions.create", self.handle_sessions_create)
        dispatcher.register("sessions.delete", self.handle_sessions_delete)
        dispatcher.register("sessions.get", self.handle_sessions_get)
        dispatcher.register("sessions.active", self.handle_sessions_active)
        dispatcher.register("ping", self.handle_ping)
        dispatcher.register("skills.load", self.handle_skills_load)
