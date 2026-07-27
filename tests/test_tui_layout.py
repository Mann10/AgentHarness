from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from harness.event_bus import EventBus


class StubRuntime:
    def __init__(self) -> None:
        self.event_bus = EventBus()
        self.active_session = None

    async def submit_prompt(self, prompt: str) -> None:
        pass

    async def list_sessions(self) -> list:
        return []

    async def switch_session(self, session_id: str) -> bool:
        return False


@pytest.mark.asyncio
async def test_header_not_in_dom():
    from tui.app import AgentHarnessTUI

    runtime = StubRuntime()
    app = AgentHarnessTUI(runtime=runtime)
    async with app.run_test() as pilot:
        assert len(pilot.app.query("Header")) == 0


@pytest.mark.asyncio
async def test_stats_panel_in_layout():
    from tui.app import AgentHarnessTUI
    from tui.widgets.stats_panel import StatsPanel

    runtime = StubRuntime()
    app = AgentHarnessTUI(runtime=runtime)
    async with app.run_test() as pilot:
        panels = pilot.app.query(StatsPanel)
        assert len(panels) == 1
        assert panels[0].id == "stats-panel"


@pytest.mark.asyncio
async def test_bottom_bar_present():
    from tui.app import AgentHarnessTUI

    runtime = StubRuntime()
    app = AgentHarnessTUI(runtime=runtime)
    async with app.run_test() as pilot:
        assert len(pilot.app.query("#bottom-bar")) == 1
        assert len(pilot.app.query("#input-bar")) == 1
        assert len(pilot.app.query("#tool-indicator")) == 1
        assert len(pilot.app.query("#job-indicator")) == 1


@pytest.mark.asyncio
async def test_conversation_view_present():
    from tui.app import AgentHarnessTUI
    from tui.widgets.conversation_view import ConversationView

    runtime = StubRuntime()
    app = AgentHarnessTUI(runtime=runtime)
    async with app.run_test() as pilot:
        assert len(pilot.app.query(ConversationView)) == 1


@pytest.mark.asyncio
async def test_stats_panel_update_methods_exist():
    from tui.app import AgentHarnessTUI
    from tui.widgets.stats_panel import StatsPanel

    runtime = StubRuntime()
    app = AgentHarnessTUI(runtime=runtime)
    async with app.run_test() as pilot:
        panel = pilot.app.query_one(StatsPanel)
        # Methods should exist and be callable
        panel.update_session_name("Test")
        panel.update_token_count(100)
        panel.update_response_time("0.5s")
        panel.update_model_name("test-model")
        # No assertion needed — just checking no exception
