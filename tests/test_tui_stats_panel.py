from __future__ import annotations

import pytest
from textual.app import App, ComposeResult


@pytest.mark.asyncio
async def test_stats_panel_display_default():
    from tui.widgets.stats_panel import StatsPanel

    class PanelApp(App):
        def compose(self) -> ComposeResult:
            yield StatsPanel(id="stats-panel")

    async with PanelApp().run_test() as pilot:
        panel = pilot.app.query_one("#stats-panel", StatsPanel)
        assert panel is not None


@pytest.mark.asyncio
async def test_stats_panel_updates_session_name():
    from tui.widgets.stats_panel import StatsPanel

    class PanelApp(App):
        def compose(self) -> ComposeResult:
            yield StatsPanel(id="stats-panel")

    async with PanelApp().run_test() as pilot:
        panel = pilot.app.query_one("#stats-panel", StatsPanel)
        panel.update_session_name("My Session")
        rendered = panel.render()
        text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
        assert "My Session" in text


@pytest.mark.asyncio
async def test_stats_panel_updates_token_count():
    from tui.widgets.stats_panel import StatsPanel

    class PanelApp(App):
        def compose(self) -> ComposeResult:
            yield StatsPanel(id="stats-panel")

    async with PanelApp().run_test() as pilot:
        panel = pilot.app.query_one("#stats-panel", StatsPanel)
        panel.update_token_count(1234)
        rendered = panel.render()
        text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
        assert "1,234" in text


@pytest.mark.asyncio
async def test_stats_panel_updates_response_time():
    from tui.widgets.stats_panel import StatsPanel

    class PanelApp(App):
        def compose(self) -> ComposeResult:
            yield StatsPanel(id="stats-panel")

    async with PanelApp().run_test() as pilot:
        panel = pilot.app.query_one("#stats-panel", StatsPanel)
        panel.update_response_time("1.2s")
        rendered = panel.render()
        text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
        assert "1.2s" in text


@pytest.mark.asyncio
async def test_stats_panel_updates_model_name():
    from tui.widgets.stats_panel import StatsPanel

    class PanelApp(App):
        def compose(self) -> ComposeResult:
            yield StatsPanel(id="stats-panel")

    async with PanelApp().run_test() as pilot:
        panel = pilot.app.query_one("#stats-panel", StatsPanel)
        panel.update_model_name("gpt-4o")
        rendered = panel.render()
        text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
        assert "gpt-4o" in text
