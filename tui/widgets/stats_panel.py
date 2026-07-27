from __future__ import annotations

from rich.text import Text
from textual.widgets import Static


class StatsPanel(Static):
    """Right-side stats panel showing session info, token count, response time, and model.

    Per D-03: Always-visible right-side panel (~30 chars wide) that shows:
    - Current session name (at top)
    - Token count consumed this session
    - Last response time
    - Current model name

    Values are updated externally (by app.py event handlers or other controllers).
    The panel is persistent and cannot be collapsed (per user decision).
    """

    def __init__(self, model_name: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._session_name = "No session"
        self._token_count = 0
        self._response_time = ""
        self._model_name = model_name or "unknown"
        self._render_content()

    def update_session_name(self, name: str) -> None:
        """Set the displayed session name."""
        self._session_name = name or "Untitled"
        self._render_content()

    def update_token_count(self, count: int) -> None:
        """Set the displayed token count."""
        self._token_count = count
        self._render_content()

    def update_response_time(self, time_str: str) -> None:
        """Set the last response time display string (e.g. '1.2s')."""
        self._response_time = time_str
        self._render_content()

    def update_model_name(self, name: str) -> None:
        """Set the displayed model name."""
        self._model_name = name
        self._render_content()

    def _render_content(self) -> None:
        """Build the Rich Text layout for the panel."""
        lines = [
            Text("\n"),
            Text.assemble(
                ("Session\n", "bold"),
                (f"  {self._session_name}\n", ""),
            ),
            Text.assemble(
                ("Tokens\n", "bold"),
                (f"  {self._token_count:,}\n", "dim"),
            ),
            Text.assemble(
                ("Last Response\n", "bold"),
                (f"  {self._response_time}\n", "dim") if self._response_time else ("  —\n", "dim"),
            ),
            Text.assemble(
                ("Model\n", "bold"),
                (f"  {self._model_name}", "dim"),
            ),
        ]
        combined = Text("\n")
        for line in lines:
            combined.append_text(line)
        self.update(combined)
