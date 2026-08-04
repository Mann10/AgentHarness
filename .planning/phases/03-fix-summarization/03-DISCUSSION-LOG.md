# Phase 3: Fix Summarization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-07-25
**Phase:** 03-fix-summarization
**Mode:** discuss (free-form)

## Areas Discussed

### Scope
- User wanted to "make summarization proper" — full rework, not just crash fix
- Testing infrastructure deferred to its own phase
- Decision: Address all 3 bugs (NameError, O(n²), LLMResponse type mismatch) + prompt + error handling

### Summarization Strategy
- **Proposed:** Summarize all messages, keep only summary in context
- **User's vision:** "Once threshold breached, summarize all messages, keep summary only, continue with new messages"
- **Refinement:** Keep `_keep_recent_exchanges` configurable (default 1) so last exchange survives
- **Outcome:** Agreed — adopted as D-01 through D-05

### Error Handling
- Options discussed: Hard failure, silent degrade, soft degrade
- **Selected:** Soft degrade — log warning, skip summarization, continue without crashing
- **Outcome:** Adopted as D-09, D-10

### Summarization Prompt
- User suggested using Claude Code's summarization prompt style
- **Structured:** Goal, decisions, progress, files/tools, open questions, technical context
- **Outcome:** Adopted as D-11 through D-14, prompt wording left to OpenCode's discretion
