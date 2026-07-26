from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from datetime import datetime

from agent import Agent
from config import Config
from llm import OpenAIClient
from jobqueue.manager import QueueManager
from session import JSONLSessionStore, Session
from tool import LocalToolProvider, ToolRegistry, register_builtin_tools

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


SUMMARIZATION_PROMPT = """\
You are summarizing a conversation between a user and an AI coding assistant \
for the purpose of preserving context in a long-running session.

Read the following conversation history and produce a concise summary that captures:

1. **Current goal** — What the user is working on
2. **Key decisions** — Important choices made and why
3. **Progress made** — What has been accomplished so far
4. **Files/tools touched** — Which files were created/modified, tools invoked
5. **Open questions** — Any unresolved issues or next steps discussed
6. **Technical context** — Important technical details the assistant needs to know

Write this as a structured report (not a narrative). Use bullet points.
The summary will be read by an AI assistant to continue the conversation,
so include everything necessary to maintain continuity.
"""


def _make_summarize_fn(client: OpenAIClient):
    async def _summarize(msgs: list[dict]) -> str:
        response = await client.chat_from_messages(
            [
                {
                    "role": "system",
                    "content": SUMMARIZATION_PROMPT,
                },
                *msgs,
            ],
            temperature=0.3,
        )
        return response.content
    return _summarize


async def _resolve_session(
    store: JSONLSessionStore,
    config: Config,
    client: OpenAIClient,
    summarize_fn,
) -> Session:
    sessions = await store.list_sessions()
    if not sessions:
        return Session.create(
            system_prompt=config.system_prompt,
            count_tokens=client.count_tokens,
            token_limit=config.max_tokens,
            summarize_fn=summarize_fn,
        )

    sorted_sessions = sorted(sessions, key=lambda s: s.updated_at, reverse=True)
    print("\nSaved sessions:")
    for i, s in enumerate(sorted_sessions, 1):
        title = s.title or "untitled"
        print(f"  {i}. {s.id[:8]}  {title:<30} {s.message_count:>4} msgs")
    print("  n. Start a new session\n")

    while True:
        choice = (await asyncio.to_thread(input, "Choose session [1/n]: ")).strip().lower()
        if choice == "n":
            return Session.create(
                system_prompt=config.system_prompt,
                count_tokens=client.count_tokens,
                token_limit=config.max_tokens,
                summarize_fn=summarize_fn,
            )
        try:
            idx = int(choice) - 1
            selected = sorted_sessions[idx]
        except (ValueError, IndexError):
            print(f"Invalid. Enter a number 1-{len(sessions)} or 'n'.")
            continue

        saved = await store.load(selected.id)
        if saved is None:
            print(f"Session '{selected.id[:8]}' could not be loaded. Try another.")
            continue
        await saved.restore_context(
            count_tokens=client.count_tokens,
            token_limit=config.max_tokens,
            summarize_fn=summarize_fn,
        )
        label = saved.title or "untitled"
        print(f"Resumed \"{label}\" ({saved.id[:8]}, {len(saved.context._messages)} messages)")
        return saved


async def _handle_session_cmd(
    line: str,
    current: dict,
    store: JSONLSessionStore,
    config: Config,
    client: OpenAIClient,
    agent: Agent,
    summarize_fn,
) -> bool:
    parts = line.split(maxsplit=1)
    cmd = parts[0].lower()

    if cmd == "/sessions":
        summaries = await store.list_sessions()
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
        session = current["session"]
        session.updated_at = datetime.now()
        await store.save(session)
        old_id = session.id[:8]
        new_session = Session.create(
            system_prompt=config.system_prompt,
            count_tokens=client.count_tokens,
            token_limit=config.max_tokens,
            summarize_fn=summarize_fn,
        )
        agent.switch_session(new_session)
        current["session"] = new_session
        print(f"Session {old_id} saved. New session {new_session.id[:8]} started.")
        return True

    if cmd == "/resume":
        target = (parts[1] if len(parts) > 1 else "").strip()
        if not target:
            print("Usage: /resume <session_id>")
            return True
        session = current["session"]
        session.updated_at = datetime.now()
        await store.save(session)
        old_id = session.id[:8]
        saved = await store.load(target)
        if saved is None:
            print(f"Session '{target}' not found.")
            return True
        await saved.restore_context(
            count_tokens=client.count_tokens,
            token_limit=config.max_tokens,
            summarize_fn=summarize_fn,
        )
        agent.switch_session(saved)
        current["session"] = saved
        print(f"Session {old_id} saved. Resumed session {target[:8]}.")
        return True

    if cmd in ("/title", "/name"):
        title = parts[1] if len(parts) > 1 else ""
        if not title:
            print("Usage: /title <name>")
            return True
        current["session"].title = title
        print(f"Session renamed to \"{title}\".")
        return True

    return False


async def run_repl(
    config: Config,
    client: OpenAIClient,
    registry: ToolRegistry,
    store: JSONLSessionStore,
    summarize_fn,
) -> None:
    session = await _resolve_session(store, config, client, summarize_fn)
    agent = Agent(client, registry, session)
    await agent.start()

    all_tools = registry.list_tools()
    if all_tools:
        tool_cols = 4
        rows = [all_tools[i : i + tool_cols] for i in range(0, len(all_tools), tool_cols)]
        logger.info("Available tools (%d):", len(all_tools))
        for row in rows:
            logger.info("  %s", "  ".join(f"{t.name:<25}" for t in row))
    else:
        logger.warning("No tools available.")

    if session.title:
        print(f"Agent Harness v2 — session \"{session.title}\" ({session.id[:8]})")
    else:
        print("Agent Harness v2 — type 'exit' or 'quit' to stop.")

    current = {"session": session}

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
            if await _handle_session_cmd(line, current, store, config, client, agent, summarize_fn):
                continue

            result = await agent.run(line)

            s = current["session"]
            if s.title is None and result.content:
                s.title = line[:50] + ("..." if len(line) > 50 else "")

            print(result.content)
            if result.forced:
                print(f"\n[Max tool iterations ({result.iterations}) reached. Forced response.]")
            print(f"[{agent.context.total_tokens}/{config.max_tokens} tokens]")
    finally:
        session = current["session"]
        session.updated_at = datetime.now()
        await store.save(session)
        print(f"\nSession saved: {session.id[:8]}")
        await agent.shutdown()


async def run_worker(
    config: Config,
    client: OpenAIClient,
    registry: ToolRegistry,
    queue_manager: QueueManager,
    worker_count: int,
) -> None:
    session = Session.create(
        system_prompt=config.system_prompt,
        count_tokens=client.count_tokens,
        token_limit=config.max_tokens,
    )
    agent = Agent(client, registry, session)
    await agent.start()

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
                result = await agent.run(job.prompt)
                await queue_manager.complete_job(job.id, result.content)
                logger.info(
                    "Worker %d completed job %s (%d tokens, %d iterations)",
                    worker_id, job.short_id, agent.context.total_tokens, result.iterations,
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
    await agent.shutdown()


async def run_tui(
    config: Config,
    client: OpenAIClient,
    registry: ToolRegistry,
    queue_manager: QueueManager,
    worker_count: int,
) -> None:
    session = Session.create(
        system_prompt=config.system_prompt,
        count_tokens=client.count_tokens,
        token_limit=config.max_tokens,
    )
    agent = Agent(client, registry, session)
    await agent.start()

    from tui.app import AgentHarnessTUI
    app = AgentHarnessTUI(queue_manager=queue_manager)
    app._worker_count = worker_count

    async def _agent_run(prompt: str) -> str:
        result = await agent.run(prompt)
        return result.content

    app._run_agent_job = _agent_run

    async def _run() -> None:
        await app.run_async()

    await asyncio.gather(_run())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AgentHarness")
    parser.add_argument("--tui", action="store_true", help="Launch Textual TUI")
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

    summarize_fn = _make_summarize_fn(client)
    store = JSONLSessionStore()
    queue_manager = QueueManager()
    await queue_manager.start()

    if args.tui:
        await run_tui(config, client, registry, queue_manager, args.workers)
    elif args.worker:
        await run_worker(config, client, registry, queue_manager, args.workers)
    else:
        await run_repl(config, client, registry, store, summarize_fn)


if __name__ == "__main__":
    asyncio.run(main())
