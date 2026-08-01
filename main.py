from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from datetime import datetime

from config import Config
from harness import RuntimeAPI
from llm import OpenAIClient
from session import Session
from tool import LocalToolProvider, ToolRegistry, register_builtin_tools

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def _resolve_session(
    runtime: RuntimeAPI,
    config: Config,
    client: OpenAIClient,
) -> Session | None:
    sessions = await runtime.list_sessions()
    if not sessions:
        return None  # RuntimeAPI will auto-create on first submit

    sorted_sessions = sorted(sessions, key=lambda s: s.updated_at, reverse=True)
    print("\nSaved sessions:")
    for i, s in enumerate(sorted_sessions, 1):
        title = s.title or "untitled"
        print(f"  {i}. {s.id[:8]}  {title:<30} {s.message_count:>4} msgs")
    print("  n. Start a new session\n")

    while True:
        choice = (await asyncio.to_thread(input, "Choose session [1/n]: ")).strip().lower()
        if choice == "n":
            return None  # RuntimeAPI auto-creates
        try:
            idx = int(choice) - 1
            selected = sorted_sessions[idx]
        except (ValueError, IndexError):
            print(f"Invalid. Enter a number 1-{len(sessions)} or 'n'.")
            continue

        success = await runtime.switch_session(selected.id)
        if success:
            label = runtime.active_session.title or "untitled"
            print(f"Resumed \"{label}\" ({runtime.active_session.id[:8]})")
            return runtime.active_session
        else:
            print(f"Session '{selected.id[:8]}' could not be loaded.")
            continue


async def _handle_session_cmd(
    line: str,
    current: dict,
    runtime: RuntimeAPI,
    config: Config,
    client: OpenAIClient,
) -> bool:
    parts = line.split(maxsplit=1)
    cmd = parts[0].lower()

    if cmd == "/sessions":
        summaries = await runtime.list_sessions()
        if not summaries:
            print("No saved sessions.")
            return True
        for s in sorted(summaries, key=lambda x: x.updated_at, reverse=True):
            title = s.title or "untitled"
            age_s = (datetime.now() - s.updated_at).total_seconds()
            age = f"{age_s/60:.0f}m ago" if age_s < 3600 else f"{age_s/3600:.0f}h ago"
            print(f"  {s.id[:8]}  {title:<30} {s.message_count:>4} msgs  {age}")
        return True

    if cmd == "/new":
        session = runtime.active_session
        if session:
            await runtime._session_manager.save_session()
            print(f"Session {session.id[:8]} saved.")
        await runtime._session_manager.create_session(
            system_prompt=config.system_prompt,
            count_tokens=client.count_tokens,
            token_limit=config.max_tokens,
        )
        # Recreate agent for the new session
        await runtime._create_agent()
        current["session"] = runtime.active_session
        print(f"New session {runtime.active_session.id[:8]} started.")
        return True

    if cmd == "/resume":
        target = (parts[1] if len(parts) > 1 else "").strip()
        if not target:
            print("Usage: /resume <session_id>")
            return True
        session = runtime.active_session
        if session:
            await runtime._session_manager.save_session()
            print(f"Session {session.id[:8]} saved.")
        success = await runtime.switch_session(target)
        if not success:
            print(f"Session '{target}' not found.")
            return True
        current["session"] = runtime.active_session
        print(f"Resumed session {target[:8]}.")
        return True

    if cmd in ("/title", "/name"):
        title = parts[1] if len(parts) > 1 else ""
        if not title:
            print("Usage: /title <name>")
            return True
        runtime.active_session.title = title
        print(f"Session renamed to \"{title}\".")
        return True

    return False


async def run_repl(
    config: Config,
    client: OpenAIClient,
    registry: ToolRegistry,
    runtime: RuntimeAPI,
) -> None:
    await _resolve_session(runtime, config, client)

    session = runtime.active_session
    if session and session.title:
        print(f"Agent Harness v2 — session \"{session.title}\" ({session.id[:8]})")
    else:
        print("Agent Harness v2 — type 'exit' or 'quit' to stop.")

    all_tools = registry.list_tools()
    if all_tools:
        tool_cols = 4
        rows = [all_tools[i : i + tool_cols] for i in range(0, len(all_tools), tool_cols)]
        logger.info("Available tools (%d):", len(all_tools))
        for row in rows:
            logger.info("  %s", "  ".join(f"{t.name:<25}" for t in row))
    else:
        logger.warning("No tools available.")

    current = {"session": runtime.active_session}

    try:
        while True:
            try:
                line = (await asyncio.to_thread(input, "> ")).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not line:
                continue
            if line.lower() in ("exit", "quit"):
                break

            # Session commands still handled locally
            if await _handle_session_cmd(line, current, runtime, config, client):
                continue

            # Submit through RuntimeAPI (non-blocking)
            await runtime.submit_prompt(line)

            # For REPL: wait for result by subscribing to EventBus
            result_event = asyncio.Event()
            result_content = []

            async def _on_complete(event):
                result_content.append(event.content)
                result_event.set()

            await runtime.event_bus.subscribe("ResponseComplete", _on_complete)

            try:
                await asyncio.wait_for(result_event.wait(), timeout=300.0)
                if result_content:
                    print(result_content[0])
                    s = runtime.active_session
                    if s and s.title is None:
                        s.title = line[:50] + ("..." if len(line) > 50 else "")
            except asyncio.TimeoutError:
                print("[Timeout waiting for response]")
            finally:
                await runtime.event_bus.unsubscribe("ResponseComplete", _on_complete)
    finally:
        await runtime.shutdown()


def _build_runtime(
    config: Config,
    client: OpenAIClient,
    registry: ToolRegistry,
) -> RuntimeAPI:
    """Construct the RuntimeAPI with the SkillStore and register the __skills__ provider.

    The __skills__ provider MUST be registered BEFORE runtime.start() — registry.start()
    runs inside Agent.start() during _create_agent(). Returns the started-by-caller runtime.
    """
    from pathlib import Path
    from skills.store import SkillStore

    skill_store = SkillStore(Path.cwd() / ".agentharness" / "skills")
    runtime = RuntimeAPI(config, client, registry, skill_store=skill_store)
    skill_provider = runtime.make_skill_provider()
    registry.add_provider("__skills__", skill_provider)  # namespace=None → un-prefixed (D-02)
    return runtime


async def run_worker(
    config: Config,
    client: OpenAIClient,
    registry: ToolRegistry,
    worker_count: int,
) -> None:
    runtime = _build_runtime(config, client, registry)
    await runtime.start()
    assert "read_skill" in [t.name for t in registry.list_tools()], (
        "D-03: __skills__ provider failed to register read_skill"
    )

    from jobqueue.manager import QueueManager
    queue_manager = QueueManager()
    await queue_manager.start()

    worker_tasks = []
    shutdown_event = asyncio.Event()

    def _handle_sig() -> None:
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_sig)
        except NotImplementedError:
            pass

    async def _worker(worker_id: int) -> None:
        logger.info("Worker %d started", worker_id)
        while not shutdown_event.is_set():
            try:
                job = await queue_manager.wait_for_job()
                if job is None:
                    continue
                logger.info("Worker %d processing job %s", worker_id, job.short_id)
                await runtime.submit_prompt(job.prompt)
                # Worker mode needs to wait for completion
                # Poll the scheduler until turn completes
                while runtime.is_busy:
                    await asyncio.sleep(0.5)
                await queue_manager.complete_job(
                    job.id,
                    runtime.active_session.context._messages[-1].content
                    if runtime.active_session else "",
                )
                logger.info(
                    "Worker %d completed job %s",
                    worker_id, job.short_id,
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Worker %d error: %s", worker_id, e)

    for i in range(worker_count):
        task = asyncio.create_task(_worker(i))
        worker_tasks.append(task)

    await shutdown_event.wait()
    logger.info("Shutting down workers...")
    for task in worker_tasks:
        task.cancel()
    await asyncio.gather(*worker_tasks, return_exceptions=True)
    await queue_manager.shutdown()
    await runtime.shutdown()


async def run_rpc(config: Config, client: OpenAIClient, registry: ToolRegistry) -> None:
    """Start RuntimeAPI and enter JSON-RPC server mode over stdin/stdout.

    RPC mode is designed for the TypeScript TUI subprocess workflow (D-16, D-17).
    All output must be NDJSON on stdout — stderr for logging only.
    """
    runtime = _build_runtime(config, client, registry)
    await runtime.start()
    assert "read_skill" in [t.name for t in registry.list_tools()], (
        "D-03: __skills__ provider failed to register read_skill"
    )

    from backend.rpc.server import RPCServer
    server = RPCServer(runtime)

    try:
        await server.start()
        # Keep running until stdin closes or shutdown is requested
        while server._running:
            await asyncio.sleep(1.0)
    finally:
        await server.shutdown()
        await runtime.shutdown()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AgentHarness")
    parser.add_argument("--rpc", action="store_true", help="Start in JSON-RPC server mode")
    parser.add_argument("--worker", action="store_true", help="Run in worker mode")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker tasks")
    parser.add_argument("--queue-path", type=str, default=None, help="Path to queue SQLite db")
    parser.add_argument("--resume", type=str, default=None, help="Session ID to resume")
    return parser.parse_args()


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _parse_args()
    config = Config()
    client = OpenAIClient(config)
    registry = ToolRegistry()
    await registry.load_config(config.mcp_config_path)

    local_provider = LocalToolProvider()
    register_builtin_tools(local_provider)
    registry.add_provider("__builtin__", local_provider)

    if args.worker:
        await run_worker(config, client, registry, args.workers)
    elif args.rpc:
        await run_rpc(config, client, registry)
    else:
        runtime = _build_runtime(config, client, registry)
        await runtime.start()
        assert "read_skill" in [t.name for t in registry.list_tools()], (
            "D-03: __skills__ provider failed to register read_skill"
        )
        try:
            await run_repl(config, client, registry, runtime)
        finally:
            await runtime.shutdown()


if __name__ == "__main__":
    # File logger to capture all debug output (hidden by TUI)
    _root_logger = logging.getLogger()
    _root_logger.setLevel(logging.DEBUG)
    _fh = logging.FileHandler("agent_harness_debug.log", mode="w", encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    _root_logger.addHandler(_fh)
    asyncio.run(main())
