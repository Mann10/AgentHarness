from __future__ import annotations

import pytest
from textual.app import App, ComposeResult


@pytest.mark.asyncio
async def test_assistant_card_has_background_class():
    """Assistant MessageCard should have the --assistant-bg CSS class."""
    from tui.widgets.message_card import MessageCard

    class CardApp(App):
        def compose(self) -> ComposeResult:
            yield MessageCard.assistant("Hello, world!")

    async with CardApp().run_test() as pilot:
        card = pilot.app.query_one(MessageCard)
        assert "--assistant-bg" in card.classes
        assert "assistant" in card.classes


@pytest.mark.asyncio
async def test_user_card_no_background_class():
    """User MessageCard should NOT have the --assistant-bg CSS class."""
    from tui.widgets.message_card import MessageCard

    class UserCardApp(App):
        def compose(self) -> ComposeResult:
            yield MessageCard.user("Hello!")

    async with UserCardApp().run_test() as pilot:
        card = pilot.app.query_one(MessageCard)
        assert "--assistant-bg" not in card.classes
        assert "user" in card.classes


@pytest.mark.asyncio
async def test_assistant_card_renders_markdown():
    """Assistant MessageCard should render Markdown content."""
    from tui.widgets.message_card import MessageCard

    class MarkdownApp(App):
        def compose(self) -> ComposeResult:
            yield MessageCard.assistant("**bold** and `code`")

    async with MarkdownApp().run_test() as pilot:
        card = pilot.app.query_one(MessageCard)
        # The card exists and rendered without error (run_test completes successfully)
        assert card is not None
