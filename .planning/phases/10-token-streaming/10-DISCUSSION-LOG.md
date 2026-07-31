# Phase 10: Token Streaming - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-07-31
**Phase:** 10-token-streaming
**Mode:** discuss

## Areas Discussed

1. **Streaming scope** — Which LLM turns stream tokens to the TUI?
   - Option A: "Final text turns only" (Recommended)
   - Option B: "Stream all turns" — requires tool_call delta assembly, little visible benefit
   - **User chose:** Recommended (final text turns only)

2. **Partial content on cancel/error** — What happens to partial text already streamed?
   - Option A: "Keep partial, mark truncated" (Recommended)
   - Option B: "Discard partial message"
   - **User chose:** Recommended (keep + mark truncated)

3. **TUI streaming UX** — How should the TUI present streaming output?
   - Option A: "Chunk-by-chunk live stream" (Recommended) — Ink re-renders per chunk, blinking cursor, auto-scroll
   - Option B: "Batch render + indicator"
   - **User chose:** Recommended (chunk-by-chunk live stream)

4. **REPL streaming** — Should the Python REPL also stream tokens?
   - Option A: "TUI-only streaming" (Recommended)
   - Option B: "Stream in REPL too"
   - **User chose:** Recommended (TUI-only)

5. **Tool-call turn detection** — How does the agent decide a turn is a "final text turn" before streaming?
   - Option A: "Stream all calls, emit tokens only for text" (Recommended) — client inspects deltas, no duplicate LLM calls
   - Option B: "Batch-first, re-stream final text" — wasteful second LLM call per final response
   - **User chose:** Recommended (stream all calls, emit tokens only for text)

6. **Partial persistence** — Should partial text be persisted to session JSONL?
   - Option A: "TUI-only, not persisted" (Recommended) — session context gets only complete assistant messages
   - Option B: "Persist partial to session"
   - **User chose:** Recommended (TUI-only, not persisted)

## Notes

- Phase input was a question ("What can we integrate next in our agent harness") rather than a phase number — interpreted as an integration-discussion, resolved to Phase 10: Token Streaming
- Phase 9 verification gap 1 ("TokenProduced event never emitted") is the exact defect this phase closes
- All six decisions were confirmed with the recommended option; no corrections
- OpenCode's discretion items: `stream_chat()` implementation detail, signature fix (sync Generator → async), TUI truncation marker styling, auto-scroll detail, chunk flush cadence

## Deferred Ideas

- Token streaming in the Python REPL — TUI-only for this phase
- Persisting partial/cut-off messages to session history — display-only
- Streaming in worker/background mode — future concern
