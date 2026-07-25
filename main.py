from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime

from agent import Agent
from config import Config
from llm import OpenAIClient
from session import JSONLSessionStore, Session
from tool import LocalToolProvider, ToolRegistry, register_builtin_tools

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _make_summarize_fn(client: OpenAIClient):
    return lambda msgs: client.chat_from_messages(
        [
            {
                "role": "system",
                "content": "Summarize the following conversation concisely while preserving key details.",
            },
            *msgs,
        ],
        temperature=0.3,
    )


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


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config = Config()
    client = OpenAIClient(config)
    registry = ToolRegistry()
    await registry.load_config(config.mcp_config_path)

    local_provider = LocalToolProvider()
    register_builtin_tools(local_provider)
    registry.add_provider("__builtin__", local_provider)

    summarize_fn = _make_summarize_fn(client)

    store = JSONLSessionStore()
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


if __name__ == "__main__":
    asyncio.run(main())
