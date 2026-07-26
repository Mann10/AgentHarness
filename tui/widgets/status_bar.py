from __future__ import annotations

from textual.widgets import Footer


class StatusBar(Footer):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._text = "Queue: 0 pending | Workers: 0 | Last: -"

    def update_status(self, pending: int, workers: int, last_result: str | None = None) -> None:
        last = last_result[:40] + "..." if last_result and len(last_result) > 40 else last_result or "-"
        self._text = f"Queue: {pending} pending | Workers: {workers} | Last: {last}"
        self.refresh()
