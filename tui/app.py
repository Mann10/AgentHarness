from __future__ import annotations

import asyncio
import logging

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Header

from harness import RuntimeAPI
from harness.event_bus import EventBus
from harness.events import (
    EVENT_TURN_STARTED,
    EVENT_TOOL_CALL,
    EVENT_TOOL_RESULT,
    EVENT_RESPONSE_COMPLETE,
    EVENT_ERROR,
    EVENT_CANCELLED,
    TurnStarted,
    ToolCallEvent,
    ToolResultEvent,
    ResponseComplete,
    ErrorEvent,
    CancelledEvent,
)
from tui.screens.result_screen import ResultScreen
from tui.widgets.input_bar import InputBar
from tui.widgets.job_grid import JobGrid
from tui.widgets.status_bar import StatusBar

logger = logging.getLogger(__name__)


class AgentHarnessTUI(App):
    TITLE = "AgentHarness"
    CSS = """
    Screen {
        layout: vertical;
    }
    #main-area {
        height: 1fr;
    }
    #input-bar {
        dock: bottom;
        height: 3;
    }
    """

    def __init__(self, runtime: RuntimeAPI) -> None:
        super().__init__()
        self._runtime = runtime
        self._last_result: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            JobGrid(),
            id="main-area",
        )
        yield InputBar(id="input-bar")
        yield StatusBar()

    def on_mount(self) -> None:
        """Subscribe to Runtime EventBus events (D-14).

        Event handlers update the UI reactively as events arrive.
        All handlers run on the same asyncio loop as the Runtime,
        so no thread bridging is needed.
        """
        bus = self._runtime.event_bus
        asyncio.create_task(self._subscribe_to_events(bus))

    async def _subscribe_to_events(self, bus: EventBus) -> None:
        """Register event handlers for Runtime events."""
        await bus.subscribe(EVENT_TURN_STARTED, self._on_turn_started)
        await bus.subscribe(EVENT_TOOL_CALL, self._on_tool_call)
        await bus.subscribe(EVENT_TOOL_RESULT, self._on_tool_result)
        await bus.subscribe(EVENT_RESPONSE_COMPLETE, self._on_response_complete)
        await bus.subscribe(EVENT_ERROR, self._on_error)
        await bus.subscribe(EVENT_CANCELLED, self._on_cancelled)

    async def _on_turn_started(self, event: TurnStarted) -> None:
        """Show that processing has started."""
        bar = self.query_one(StatusBar)
        bar.update_processing(True)
        logger.info("Turn started: %.50s", event.prompt)

    async def _on_tool_call(self, event: ToolCallEvent) -> None:
        """Log tool calls — UI could show inline card in future."""
        logger.debug("Tool call: %s", event.tool_name)

    async def _on_tool_result(self, event: ToolResultEvent) -> None:
        """Log tool results."""
        logger.debug("Tool result: %s = %s", event.tool_name, event.result[:60])

    async def _on_response_complete(self, event: ResponseComplete) -> None:
        """Update status bar with completion info."""
        self._last_result = event.content[:60]
        bar = self.query_one(StatusBar)
        bar.update_processing(False)
        bar.update_last_result(self._last_result)

    async def _on_error(self, event: ErrorEvent) -> None:
        """Log errors from agent execution."""
        bar = self.query_one(StatusBar)
        bar.update_processing(False)
        logger.error("Runtime error: %s", event.error)

    async def _on_cancelled(self, event: CancelledEvent) -> None:
        """Handle turn cancellation."""
        bar = self.query_one(StatusBar)
        bar.update_processing(False)
        logger.info("Turn cancelled")

    @on(InputBar.Submitted)
    async def on_submit(self, event: InputBar.Submitted) -> None:
        """Submit prompt via Runtime instead of queue."""
        prompt = event.value.strip()
        if not prompt:
            return
        await self._runtime.submit_prompt(prompt)
        event.input.clear()

    @on(JobGrid.RowSelected)
    def on_row_selected(self, event: JobGrid.RowSelected) -> None:
        """Show job detail screen from grid row data."""
        job_id = event.row.get_value(0)
        prompt = event.row.get_value(1)
        self.push_screen(ResultScreen(job_id, prompt, None, None))
