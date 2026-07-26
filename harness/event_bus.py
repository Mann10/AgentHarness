from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from harness.events import HarnessEvent

logger = logging.getLogger(__name__)

# Type alias: async handler that accepts any HarnessEvent
EventHandler = Callable[[HarnessEvent], Awaitable[None]]


class EventBus:
    """Lightweight in-process async event bus.

    Subscribe handlers to event types (by string class name).
    Publish dispatches to all subscribed handlers concurrently.
    Swappable: swap this class for a Redis/ZeroMQ implementation later (D-06).

    Thread safety: asyncio.Lock protects subscriber list mutations.
    Handler isolation: asyncio.gather(return_exceptions=True) ensures
    one failing handler doesn't prevent others from receiving the event.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for an event type.

        Args:
            event_type: The string class name of the event (e.g. 'TurnStarted')
                       or '*' for all events.
            handler: Async callable that accepts a HarnessEvent.
        """
        async with self._lock:
            self._handlers[event_type].append(handler)

    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a previously registered handler."""
        async with self._lock:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h is not handler
            ]

    async def publish(self, event: HarnessEvent) -> None:
        """Publish an event to all subscribed handlers.

        - Routes by type(event).__name__
        - Also notifies wildcard '*' subscribers (e.g., loggers)
        - All handlers run concurrently via asyncio.gather
        - Exceptions are logged, not propagated
        """
        event_type = type(event).__name__
        async with self._lock:
            handlers = list(self._handlers.get(event_type, []))
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

    @property
    def subscriber_count(self) -> int:
        """Return total registered handlers across all event types."""
        return sum(len(h) for h in self._handlers.values())
