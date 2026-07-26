from __future__ import annotations

import asyncio
import logging

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Header

from jobqueue.manager import QueueManager
from jobqueue.models import JobPriority
from tui.screens.result_screen import ResultScreen
from tui.widgets.input_bar import InputBar
from tui.widgets.job_grid import JobGrid
from tui.widgets.status_bar import StatusBar

logger = logging.getLogger(__name__)


class AgentHarnessTUI(App):
    TITLE = "AgentHarness"
    CSS = """
    Screen {
        layout: vertical;
    }
    #main-area {
        height: 1fr;
    }
    #input-bar {
        dock: bottom;
        height: 3;
    }
    """

    def __init__(self, queue_manager: QueueManager | None = None) -> None:
        super().__init__()
        self._manager = queue_manager or QueueManager()
        self._worker_tasks: list[asyncio.Task] = []
        self._worker_count = 1
        self._last_result: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            JobGrid(),
            id="main-area",
        )
        yield InputBar(id="input-bar")
        yield StatusBar()

    def on_mount(self) -> None:
        asyncio.get_event_loop().create_task(self._start_manager())
        self.set_interval(2, self._refresh)

    async def _start_manager(self) -> None:
        await self._manager.start()
        for i in range(self._worker_count):
            task = asyncio.get_event_loop().create_task(self._worker_loop(i))
            self._worker_tasks.append(task)

    async def _worker_loop(self, worker_id: int) -> None:
        logger.info("Worker %d started", worker_id)
        while True:
            try:
                job = await self._manager.wait_for_job()
                result = await self._run_agent_job(job.prompt)
                await self._manager.complete_job(job.id, result)
                self._last_result = result
                logger.info("Worker %d completed job %s", worker_id, job.short_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Worker %d error", worker_id)

    async def _run_agent_job(self, prompt: str) -> str:
        await asyncio.sleep(0)
        return f"Processed: {prompt}"

    async def _refresh(self) -> None:
        jobs = self._manager.list_jobs(limit=100)
        grid = self.query_one(JobGrid)
        grid.refresh_jobs(jobs)
        bar = self.query_one(StatusBar)
        bar.update_status(self._manager.pending_count, self._worker_count, self._last_result)

    @on(InputBar.Submitted)
    async def on_submit(self, event: InputBar.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt:
            return
        await self._manager.enqueue(prompt, priority=JobPriority.NORMAL)
        event.input.clear()

    @on(JobGrid.RowSelected)
    def on_row_selected(self, event: JobGrid.RowSelected) -> None:
        job_id = event.row.get_value(0)
        job = self._manager.get_job(job_id)
        if job is None:
            return
        self.push_screen(ResultScreen(job.id, job.prompt, job.result, job.error))
