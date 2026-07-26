from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class CancellationToken:
    """Cooperative cancellation token for agent turn cancellation.

    Two mechanisms:
    1. `cancelled` property — synchronous check at yield points
    2. `wait()` coroutine — await for cancellation signal (wraps asyncio.Event)

    Used alongside asyncio.Task.cancel() for the primary cancellation path.
    The token provides a cooperative flag for code that needs to clean up
    before raising CancelledError.

    Pattern: Scheduler creates one token per turn, passes to components
    that need cancellation awareness.
    """

    def __init__(self) -> None:
        self._cancelled = False
        self._event = asyncio.Event()

    def cancel(self) -> None:
        """Signal cancellation. Idempotent."""
        self._cancelled = True
        self._event.set()
        logger.debug("CancellationToken set")

    @property
    def cancelled(self) -> bool:
        """Check if cancellation has been requested. Non-blocking."""
        return self._cancelled

    async def wait(self) -> None:
        """Block until cancellation is requested. Returns immediately if already cancelled."""
        await self._event.wait()

    def reset(self) -> None:
        """Reset the token for reuse. Clears both flag and event."""
        self._cancelled = False
        self._event.clear()
