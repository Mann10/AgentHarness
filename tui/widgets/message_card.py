from __future__ import annotations

from rich.markdown import Markdown
from rich.panel import Panel
from rich.style import Style
from rich.text import Text
from textual.widgets import Static


class MessageCard(Static):
    """A single message bubble in the conversation view.

    Factory methods create variants: user, assistant (Markdown), error, notice.
    """

    USER_STYLE = Style(color="#565f89")
    ASSISTANT_STYLE = Style(color="#a9b1d6")
    ERROR_STYLE = Style(color="#db4b4b")
    NOTICE_STYLE = Style(color="#565f89", italic=True)

    @staticmethod
    def user(content: str) -> MessageCard:
        content = content[:200] + "..." if len(content) > 200 else content
        t = Text.assemble(("> ", MessageCard.USER_STYLE), (content, MessageCard.USER_STYLE))
        card = MessageCard(t)
        card.add_class("user")
        return card

    @staticmethod
    def assistant(content: str) -> MessageCard:
        card = MessageCard(Markdown(content, code_theme="monokai"))
        card.add_class("--assistant-bg")
        card.add_class("assistant")
        return card

    @staticmethod
    def error(text: str) -> MessageCard:
        panel = Panel(
            Text(text, style=MessageCard.ERROR_STYLE),
            border_style=Style(color="#f7768e"),
            title="Error",
            padding=(0, 1),
        )
        return MessageCard(panel)

    @staticmethod
    def notice(text: str) -> MessageCard:
        t = Text(text, style=MessageCard.NOTICE_STYLE)
        return MessageCard(t)
