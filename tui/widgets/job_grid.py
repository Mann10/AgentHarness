from __future__ import annotations

from datetime import datetime, timezone

from textual.widgets import DataTable

from jobqueue.models import Job


class JobGrid(DataTable):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.styles.margin = (1, 1)

    def on_mount(self) -> None:
        self.add_columns("ID", "Prompt", "Status", "Priority", "Created")

    def refresh_jobs(self, jobs: list[Job]) -> None:
        self.clear()
        for job in jobs:
            self.add_row(
                job.short_id,
                job.prompt_preview,
                job.status.value,
                job.priority.name,
                _format_time(job.created_at),
            )


def _format_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    if delta.total_seconds() < 60:
        return "just now"
    if delta.total_seconds() < 3600:
        return f"{int(delta.total_seconds() / 60)}m ago"
    return f"{int(delta.total_seconds() / 3600)}h ago"
