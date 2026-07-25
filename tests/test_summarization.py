from __future__ import annotations

import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from context.context import ConversationContext


async def test_summarization_skips_when_below_threshold() -> None:
    call_count = 0

    async def mock_summarize(msgs: list[dict]) -> str:
        nonlocal call_count
        call_count += 1
        return "Summary."

    ctx = ConversationContext(
        count_tokens=lambda t: len(t.split()),
        token_limit=1000,
        summarize_fn=mock_summarize,
        summarize_threshold=0.75,
        keep_recent_exchanges=1,
    )

    await ctx.add_user_message("Hello")
    await ctx.add_assistant_message("Hi there!")

    assert call_count == 0


async def test_summarization_fires_at_threshold() -> None:
    call_count = 0

    async def mock_summarize(msgs: list[dict]) -> str:
        nonlocal call_count
        call_count += 1
        return "Summary."

    ctx = ConversationContext(
        count_tokens=lambda t: len(t.split()),
        token_limit=40,
        summarize_fn=mock_summarize,
        summarize_threshold=0.5,
        keep_recent_exchanges=1,
    )

    for i in range(3):
        await ctx.add_user_message(f"Task {i} with some extra context here")
        await ctx.add_assistant_message(f"Response {i} with details and analysis")

    assert call_count >= 1, "Should have fired at least once above threshold"

    summary_msgs = [m for m in ctx._messages if m.role == "system"]
    assert len(summary_msgs) >= 1
    assert "Summary." in summary_msgs[-1].content


async def test_summarization_keeps_recent_exchanges() -> None:
    call_count = 0

    async def mock_summarize(msgs: list[dict]) -> str:
        nonlocal call_count
        call_count += 1
        return "Summary."

    ctx = ConversationContext(
        count_tokens=lambda t: len(t.split()),
        token_limit=40,
        summarize_fn=mock_summarize,
        summarize_threshold=0.5,
        keep_recent_exchanges=2,
    )

    for i in range(6):
        await ctx.add_user_message(f"Task {i} with some extra context here")
        await ctx.add_assistant_message(f"Response {i} with details and analysis")

    recent_roles = [m.role for m in ctx._messages]
    assert recent_roles.count("user") == 2, f"Expected 2 user, got {recent_roles.count('user')}"
    assert recent_roles.count("assistant") == 2, f"Expected 2 assistant, got {recent_roles.count('assistant')}"
    assert recent_roles.count("system") >= 1, "Expected at least 1 summary"


async def test_summarization_preserves_system_messages() -> None:
    call_count = 0

    async def mock_summarize(msgs: list[dict]) -> str:
        nonlocal call_count
        for m in msgs:
            if m["role"] == "system":
                raise AssertionError("System messages should never be passed to summarize_fn")
        call_count += 1
        return "Summary."

    ctx = ConversationContext(
        count_tokens=lambda t: len(t.split()),
        token_limit=40,
        summarize_fn=mock_summarize,
        summarize_threshold=0.5,
        keep_recent_exchanges=1,
    )

    for i in range(5):
        await ctx.add_user_message(f"Task {i} with extra context")
        await ctx.add_assistant_message(f"Response {i} with analysis")

    assert call_count >= 1


async def test_summarization_soft_degrade_on_failure() -> None:
    call_count = 0

    async def failing_summarize(msgs: list[dict]) -> str:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("LLM unavailable")

    ctx = ConversationContext(
        count_tokens=lambda t: len(t.split()),
        token_limit=40,
        summarize_fn=failing_summarize,
        summarize_threshold=0.5,
        keep_recent_exchanges=1,
    )

    for i in range(5):
        await ctx.add_user_message(f"Task {i} with extra context")
        await ctx.add_assistant_message(f"Response {i} with analysis")

    assert call_count >= 1
    assert ctx.total_tokens > 0

    summary_msgs = [m for m in ctx._messages if m.role == "system"]
    assert len(summary_msgs) == 0, "No summary should exist after failed call"


async def test_summarization_token_total_consistent() -> None:
    async def mock_summarize(msgs: list[dict]) -> str:
        return "Summary of the previous discussion."

    ctx = ConversationContext(
        count_tokens=lambda t: len(t.split()),
        token_limit=40,
        summarize_fn=mock_summarize,
        summarize_threshold=0.5,
        keep_recent_exchanges=1,
    )

    for i in range(4):
        await ctx.add_user_message(f"Task {i} with some extra words here")
        await ctx.add_assistant_message(f"Response {i} with more details")

    computed = sum(m.token_count for m in ctx._messages)
    assert ctx.total_tokens == computed, f"total_tokens {ctx.total_tokens} != sum {computed}"


async def test_no_summarize_fn_does_nothing() -> None:
    ctx = ConversationContext(
        count_tokens=lambda t: len(t.split()),
        token_limit=40,
        summarize_fn=None,
        summarize_threshold=0.5,
    )

    for i in range(10):
        await ctx.add_user_message(f"Task {i}?")
        await ctx.add_assistant_message(f"Solution {i}.")

    assert len(ctx._messages) == 20


if __name__ == "__main__":
    tests = [
        test_summarization_skips_when_below_threshold,
        test_summarization_fires_at_threshold,
        test_summarization_keeps_recent_exchanges,
        test_summarization_preserves_system_messages,
        test_summarization_soft_degrade_on_failure,
        test_summarization_token_total_consistent,
        test_no_summarize_fn_does_nothing,
    ]

    passed = 0
    failed = 0

    for test in tests:
        name = test.__name__
        try:
            asyncio.run(test())
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            failed += 1

    print(f"\n{passed}/{passed + failed} tests passed")
