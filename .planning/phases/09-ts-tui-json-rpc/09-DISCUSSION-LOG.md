# Phase 9: TypeScript TUI + JSON-RPC Adapter - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-07-28
**Phase:** 09-ts-tui-json-rpc
**Mode:** discuss (update)
**Areas analyzed:** Log suppression, Backend stdout isolation, Processing animation, StatsPanel widget

## Prior Context Loaded

- PROJECT.md — Terminal-first, provider-pluggable, session-persistent
- ROADMAP.md — Phase 9 scope: JSON-RPC adapter + TypeScript/Ink TUI, 4 plans created
- STATE.md — Phase 9 context gathered, ready for planning
- Phase 7 CONTEXT.md — Claude Code-inspired dark theme, inline tool calls, minimal layout
- Phase 8 CONTEXT.md — Message bifurcation, stats panel, header removal
- Phase 9 CONTEXT.md — 25 existing decisions (D-01 through D-25)
- Phase 9 UI-SPEC.md — Full design contract with component specs, color tokens, layout

## Assumptions Presented

### Log Suppression
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| console.error/warn calls in TUI code are polluting the terminal display | Confident | `rpc/client.ts` has 5 console.error/warn calls; `state/reducers.ts` has 1 console.warn |
| Store-based errors are the right replacement pattern | Confident | ConversationScreen already renders errors inline via store.error state |

### Backend stdout Isolation
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Python backend may leak print()/logging into stdout during --rpc mode | Likely | `main.py` has print/logging calls; --rpc mode uses stdout for NDJSON |
| File-only logging during --rpc mode is cleanest approach | Likely | Stdout stays pure NDJSON, stderr is visible in terminal but not mixed into protocol |

### Processing Animation
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Current InputBar shows static "waiting for response..." which is minimal but not Claude-like | Confident | `InputBar.tsx` line 51: static text |
| Cycling dots animation matches Claude Code behavior | Confident | UI-SPEC defines "Thinking" cycling pattern |

### StatsPanel Widget
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| UI-SPEC defines StatsPanel with 6 fields but widget not yet implemented | Confident | No StatsPanel component exists in `frontend/src/ui/` |
| Minimal (4 fields) matches user's "no unnecessary" preference | Likely | User explicitly wants clean, minimal output |

## User Corrections

- **Log Suppression:** Store-based errors (selected over file-only or env-gated)
- **Backend stdout:** File-only logging (selected over stderr routing or silent mode)
- **Processing Animation:** Cycling dots (selected over static text or spinner)
- **StatsPanel:** Minimal 4 fields (selected over full 6+clock version)

## Decisions Captured

### D-26: Log Suppression
All console.error/warn in frontend code replaced with store.setError(). Errors render inline in conversation flow.

### D-27: Backend stdout Isolation
Python --rpc mode routes all logging to agent_harness_debug.log. Stdout reserved for NDJSON only.

### D-28: Processing Animation
InputBar shows "Thinking" → "Thinking." → "Thinking.." → "Thinking..." cycling at 500ms.

### D-29: StatsPanel Widget
Right-side panel with 4 fields: session name, token count, response time, model name. No clock/date.

## Deferred Ideas

- Live clock in StatsPanel — not needed for minimal approach
- Date/time in StatsPanel — not needed for minimal approach
- All prior Phase 9 deferred ideas preserved

---

*Phase: 09-ts-tui-json-rpc*
*Discussion date: 2026-07-28*