from __future__ import annotations

import asyncio
import logging

from agent import Agent
from agent.result import AgentResult
from harness.cancellation import CancellationToken
from harness.event_bus import EventBus
from harness.events import CancelledEvent

logger = logging.getLogger(__name__)


class Scheduler:
    """Dispatches agent turns one at a time (D-09).

    Owns the EventBus. Wires Agent's emit callback to bus.publish.
    Maintains a FIFO backlog for prompts submitted while busy (D-11).

    Interactive path (D-08): submit_prompt() -> direct to Scheduler.
    Worker path: prompts come through QueueManager, not Scheduler backlog.

    Design:
    - submit_prompt() is non-blocking (D-15) — returns immediately
    - If idle, creates asyncio.Task to run the turn
    - If busy, queues to backlog (FIFO asyncio.Queue)
    - After turn completes, drains the backlog automatically
    - cancel() cancels the current asyncio.Task (CancelledError propagates)
    """

    def __init__(
        self,
        agent: Agent,
        event_bus: EventBus,
        *,
        backlog_maxsize: int = 0,
    ) -> None:
        self._agent = agent
        self._bus = event_bus
        self._backlog: asyncio.Queue[str] = asyncio.Queue(maxsize=backlog_maxsize)
        self._current_task: asyncio.Task[AgentResult] | None = None
        self._cancellation_token: CancellationToken | None = None
        self._running = False

        # Wire Agent's emit callback to EventBus publish
        # The Agent already constructed with emit= or will be set externally
        # We wire it here by replacing agent._emit
        async def _emit_to_bus(event):
            await self._bus.publish(event)

        self._agent._emit = _emit_to_bus

    async def submit_prompt(self, prompt: str) -> None:
        """Submit a prompt for execution (non-blocking, D-15).

        If agent is idle: starts turn immediately as a background task.
        If agent is busy: queues to FIFO backlog (D-11).
        If backlog is full (maxsize>0 and queue full): logs warning and drops.
        """
        if not self._running:
            logger.warning("Scheduler not running, rejecting prompt")
            return

        if self._current_task is None or self._current_task.done():
            self._cancellation_token = CancellationToken()
            self._current_task = asyncio.create_task(
                self._run_turn(prompt, self._cancellation_token)
            )
            logger.debug("Started turn for prompt: %.50s", prompt)
        else:
            try:
                await self._backlog.put(prompt)
                logger.info(
                    "Agent busy, prompt queued (backlog: ~%d)",
                    self._backlog.qsize(),
                )
            except asyncio.QueueFull:
                logger.warning("Backlog full, dropping prompt: %.50s", prompt)

    async def cancel(self) -> None:
        """Cancel the current turn if one is active.

        Sets CancellationToken (cooperative flag) AND cancels the
        asyncio task (hard cancellation via CancelledError).
        """
        if self._cancellation_token is not None:
            self._cancellation_token.cancel()
        if self._current_task is not None and not self._current_task.done():
            self._current_task.cancel()

        # Wait briefly for CancelledError to propagate so the event fires
        if self._current_task is not None:
            try:
                await asyncio.wait_for(self._current_task, timeout=3.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            if self._current_task and not self._current_task.done():
                self._current_task.cancel()
                logger.info("Cancel requested for current turn")

    @property
    def is_busy(self) -> bool:
        """True if a turn is currently executing."""
        return (
            self._current_task is not None
            and not self._current_task.done()
        )

    @property
    def backlog_size(self) -> int:
        """Number of prompts waiting in the backlog."""
        return self._backlog.qsize()

    async def _run_turn(
        self,
        prompt: str,
        cancellation_token: CancellationToken,
    ) -> None:
        """Execute one turn and then drain the backlog.

        If the turn succeeds: emits response_complete (Agent handles this).
        If cancelled: CancelledError propagates, Scheduler catches and logs.
        After completion: processes next prompt from backlog.
        """
        try:
            result = await self._agent.run(prompt)
            logger.info(
                "Turn complete: %d iterations, %d tool calls",
                result.iterations,
                result.tool_calls_made,
            )
        except asyncio.CancelledError:
            logger.info("Turn cancelled via CancelledError")
            # Use safe attribute access for session_id — StubAgent has no _session
            session_id = ""
            try:
                session_id = self._agent._session.id
            except AttributeError:
                pass
            await self._bus.publish(CancelledEvent(session_id=session_id))
            raise
        except Exception as e:
            logger.exception("Turn failed: %s", e)
            raise

        # Drain backlog: process next queued prompt (FIFO)
        if not self._backlog.empty():
            next_prompt = self._backlog.get_nowait()
            self._cancellation_token = CancellationToken()
            self._current_task = asyncio.create_task(
                self._run_turn(next_prompt, self._cancellation_token)
            )

    async def start(self) -> None:
        """Start the scheduler."""
        self._running = True
        logger.info("Scheduler started")

    async def shutdown(self) -> None:
        """Shutdown the scheduler.

        Cancels current turn. Waits up to 5s for cancellation.
        Does NOT drain the backlog — remaining prompts are lost.
        """
        self._running = False
        await self.cancel()
        if self._current_task and not self._current_task.done():
            try:
                await asyncio.wait_for(self._current_task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        logger.info("Scheduler shut down")
