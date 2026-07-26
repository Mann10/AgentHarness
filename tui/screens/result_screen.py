from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Header, Footer


class ResultScreen(Screen):
    def __init__(self, job_id: str, prompt: str, result: str | None, error: str | None) -> None:
        super().__init__()
        self._job_id = job_id
        self._prompt = prompt
        self._result = result
        self._error = error

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(self._build_content(), id="result-content")
        yield Footer()

    def _build_content(self) -> str:
        lines = [
            f"[bold]Job:[/bold] {self._job_id}",
            "",
            f"[bold]Prompt:[/bold] {self._prompt}",
            "",
        ]
        if self._result:
            lines.append("[bold green]Result:[/bold green]")
            lines.append(self._result)
        if self._error:
            lines.append("")
            lines.append(f"[bold red]Error:[/bold red] {self._error}")
        return "\n".join(lines)

    def key_escape(self) -> None:
        self.dismiss()
