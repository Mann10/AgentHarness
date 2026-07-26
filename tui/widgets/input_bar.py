from __future__ import annotations

from textual.widgets import Input


class InputBar(Input):
    def __init__(self, **kwargs) -> None:
        super().__init__(placeholder="Enter a prompt for the agent...", **kwargs)
        self.styles.margin = (1, 1)
