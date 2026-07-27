from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

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
from tui.screens.session_picker import SessionPicker
from tui.widgets.conversation_view import ConversationView
from tui.widgets.input_bar import InputBar
from tui.widgets.stats_panel import StatsPanel

logger = logging.getLogger(__name__)

# File logger for TUI debug — terminal output hidden by Textual
_tui_log = logging.getLogger("tui_debug")
_tui_log.setLevel(logging.DEBUG)
_fh = logging.FileHandler("tui_debug.log", mode="w", encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
_tui_log.addHandler(_fh)


class AgentHarnessTUI(App):
    TITLE = "AgentHarness"
    BINDINGS = [("ctrl+s", "open_sessions", "Sessions")]
    CSS_PATH = "theme.tcss"

    def __init__(self, runtime: RuntimeAPI, model_name: str = "") -> None:
        super().__init__()
        self._runtime = runtime
        self._model_name = model_name or "unknown"
        self._last_result: str | None = None
        self._tool_call_count: int = 0
        self._turn_start_time: datetime | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="main-content"):
            yield ConversationView(id="conversation-panel")
            yield StatsPanel(id="stats-panel")
        with Horizontal(id="bottom-bar"):
            yield Static(id="tool-indicator")
            yield Static(id="job-indicator")
            yield InputBar(id="input-bar")

    async def on_mount(self) -> None:
        from textual.theme import Theme

        theme = Theme(
            name="claude-dark",
            primary="#cc785c",
            secondary="#5db8a6",
            accent="#cc785c",
            warning="#e8a55a",
            error="#ff6b80",
            success="#4eba65",
            foreground="#faf9f5",
            background="#1e1e1e",
            surface="#252525",
            panel="#2a2a2a",
            boost="#cc785c20",
            dark=True,
            variables={"input-selection-background": "#cc785c40"},
        )
        self.register_theme(theme)
        self.theme = "claude-dark"
        bus = self._runtime.event_bus
        await self._subscribe_to_events(bus)
        self.query_one(InputBar).focus()
        # Initialize StatsPanel with session name and model
        self._update_stats_panel_session()

    def _update_stats_panel_session(self) -> None:
        """Update StatsPanel with current session name and model."""
        panel = self.query_one("#stats-panel", StatsPanel)
        session = self._runtime.active_session
        name = session.title if session and session.title else "Untitled"
        panel.update_session_name(name)
        panel.update_model_name(self._model_name)

    def _update_stats_panel_after_response(self) -> None:
        """Update StatsPanel with token count and response time after a response completes."""
        panel = self.query_one("#stats-panel", StatsPanel)
        session = self._runtime.active_session
        if session:
            panel.update_token_count(session.context.total_tokens)
        if self._turn_start_time:
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            elapsed = (now - self._turn_start_time).total_seconds()
            panel.update_response_time(f"{elapsed:.1f}s")
            self._turn_start_time = None

    async def _subscribe_to_events(self, bus: EventBus) -> None:
        await bus.subscribe(EVENT_TURN_STARTED, self._on_turn_started)
        await bus.subscribe(EVENT_TOOL_CALL, self._on_tool_call)
        await bus.subscribe(EVENT_TOOL_RESULT, self._on_tool_result)
        await bus.subscribe(EVENT_RESPONSE_COMPLETE, self._on_response_complete)
        await bus.subscribe(EVENT_ERROR, self._on_error)
        await bus.subscribe(EVENT_CANCELLED, self._on_cancelled)

    async def _on_turn_started(self, event: TurnStarted) -> None:
        _tui_log.debug("_on_turn_started fired: prompt=%s", event.prompt[:60])
        self._tool_call_count = 0
        try:
            conv = self.query_one(ConversationView)
            conv.add_user_message(event.prompt)
            inp = self.query_one(InputBar)
            inp.update_processing(True)
            tool_indicator = self.query_one("#tool-indicator", Static)
            tool_indicator.update("")
            job_indicator = self.query_one("#job-indicator", Static)
            job_indicator.update("")
        except Exception:
            _tui_log.exception("_on_turn_started failed")
            raise

    async def _on_tool_call(self, event: ToolCallEvent) -> None:
        self._tool_call_count += 1
        conv = self.query_one(ConversationView)
        conv.add_tool_call(event.tool_call_id, event.tool_name, event.arguments or {})
        indicator = self.query_one("#tool-indicator", Static)
        indicator.update(f"{self._tool_call_count} calls")

    async def _on_tool_result(self, event: ToolResultEvent) -> None:
        conv = self.query_one(ConversationView)
        conv.update_tool_result(event.tool_call_id, event.result)

    async def _on_response_complete(self, event: ResponseComplete) -> None:
        _tui_log.debug("_on_response_complete fired: content_len=%d", len(event.content))
        self._last_result = event.content[:60]
        try:
            conv = self.query_one(ConversationView)
            conv.add_assistant_message(event.content)
        except Exception:
            _tui_log.exception("_on_response_complete widget update failed")
        finally:
            inp = self.query_one(InputBar)
            inp.update_processing(False)
            indicator = self.query_one("#tool-indicator", Static)
            indicator.update("")

    async def _on_error(self, event: ErrorEvent) -> None:
        _tui_log.debug("_on_error fired: error=%s", event.error[:200])
        try:
            conv = self.query_one(ConversationView)
            conv.add_error(event.error)
        except Exception:
            _tui_log.exception("_on_error widget update failed")
        finally:
            inp = self.query_one(InputBar)
            inp.update_processing(False)

    async def _on_cancelled(self, event: CancelledEvent) -> None:
        _tui_log.debug("_on_cancelled fired")
        try:
            conv = self.query_one(ConversationView)
            conv.add_notice("Cancelled")
        except Exception:
            _tui_log.exception("_on_cancelled widget update failed")
        finally:
            inp = self.query_one(InputBar)
            inp.update_processing(False)

    @on(InputBar.Submitted)
    async def on_submit(self, event: InputBar.Submitted) -> None:
        prompt = event.value.strip()
        _tui_log.debug("on_submit: prompt=%s", prompt[:80])
        if not prompt:
            return
        if prompt == "/sessions":
            self.push_screen(SessionPicker(self._runtime))
            event.input.clear()
            return
        inp = self.query_one(InputBar)
        inp.update_processing(True)
        await self._runtime.submit_prompt(prompt)
        event.input.clear()

    def action_open_sessions(self) -> None:
        self.push_screen(SessionPicker(self._runtime))


