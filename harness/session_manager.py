from __future__ import annotations

import logging
from datetime import datetime

from session.models import Session, SessionSummary
from session.store import JSONLSessionStore

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages session lifecycle — wraps existing JSONLSessionStore.

    Tracks an active session. All operations (create, load, switch)
    update the active session pointer. Save is explicit (called by
    Scheduler after turn completion and by Runtime on shutdown).

    Follows project patterns:
    - Constructor DI with optional default (D-10: reuse existing store)
    - Private attrs prefixed with _
    - Async methods for I/O operations
    """

    def __init__(self, store: JSONLSessionStore | None = None):
        self._store = store or JSONLSessionStore()
        self._active_session: Session | None = None

    @property
    def active_session(self) -> Session | None:
        """Return the currently active session, or None if no session loaded."""
        return self._active_session

    async def create_session(self, **kwargs) -> Session:
        """Create a new session and set it as active.

        Accepts the same kwargs as Session.create():
        system_prompt, count_tokens, token_limit, summarize_fn, etc.
        """
        session = Session.create(**kwargs)
        await self._store.save(session)
        self._active_session = session
        logger.info("Created session %s", session.id[:8])
        return session

    async def load_session(self, session_id: str) -> Session | None:
        """Load a session from the store and set it as active.

        Returns None if the session doesn't exist or is corrupt.
        """
        session = await self._store.load(session_id)
        if session is not None:
            self._active_session = session
            logger.debug("Loaded session %s", session_id[:8])
        return session

    async def get_session(self, session_id: str) -> Session | None:
        """Load a session from the store WITHOUT making it active (pure read).

        Unlike load_session, does not touch the active-session pointer —
        used by the history RPC so fetching history has zero side effects.
        """
        return await self._store.load(session_id)

    async def save_session(self) -> None:
        """Persist the active session if one exists.

        Called after turn completion (Scheduler) and on shutdown.
        Idempotent if no active session.
        """
        if self._active_session is not None:
            self._active_session.updated_at = datetime.now()
            await self._store.save(self._active_session)
            logger.debug("Saved session %s", self._active_session.id[:8])

    async def switch_session(self, session: Session) -> None:
        """Switch to a different session.

        Saves the current active session first, then sets the new one.
        """
        await self.save_session()
        self._active_session = session
        logger.info("Switched to session %s", session.id[:8])

    async def list_sessions(self) -> list[SessionSummary]:
        """List all available sessions (delegates to store)."""
        return await self._store.list_sessions()

    async def delete_session(self, session_id: str) -> None:
        """Delete a session from the store.

        If the deleted session is the active one, sets active to None.
        """
        if self._active_session is not None and self._active_session.id == session_id:
            self._active_session = None
        await self._store.delete(session_id)
        logger.info("Deleted session %s", session_id[:8])
