from __future__ import annotations

from textual.widgets import Footer


class StatusBar(Footer):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._processing = False
        self._last_result: str | None = None
        self._text = "Status: Idle | Last: -"

    def update_status(self, pending: int, workers: int, last_result: str | None = None) -> None:
        """Legacy method — kept for backward compat during transition."""
        last = last_result[:40] + "..." if last_result and len(last_result) > 40 else last_result or "-"
        self._text = f"Queue: {pending} pending | Workers: {workers} | Last: {last}"
        self.refresh()

    def update_processing(self, is_processing: bool) -> None:
        """Update processing indicator (called from TUI event handlers)."""
        self._processing = is_processing
        status = "Processing" if is_processing else "Idle"
        last = self._last_result or "-"
        self._text = f"Status: {status} | Last: {last}"
        self.refresh()

    def update_last_result(self, result: str) -> None:
        """Update the last result display (called from ResponseComplete handler)."""
        self._last_result = result[:40] + "..." if result and len(result) > 40 else result or "-"
        self._text = f"Status: Idle | Last: {self._last_result}"
        self.refresh()
