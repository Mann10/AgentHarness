# Phase 8: TUI Conversation Layout - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-27
**Phase:** 08-tui-conversation-layout
**Areas discussed:** Header/Title Bar, Launch Behavior, Right Stats Panel, Message Bifurcation, Tool Calls, Window Background

---

## Header / Title Bar

| Option | Description | Selected |
|--------|-------------|----------|
| Remove entirely | No persistent header at all — like Claude Code | ✓ |
| Thin brand bar | Minimal single-line title like OpenCode | |
| Keep but restyle | Smaller font, no clock, darker background | |

**User's choice:** Remove entirely
**Notes:** User initially chose this, then said "get to prior question" but ultimately confirmed removal.

---

## Launch Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Start screen (like OpenCode) | Show version, recent sessions, quick commands | |
| Straight to conversation | Launch into empty conversation view | ✓ |

**User's choice:** Straight to conversation

---

## Right Stats Panel

| Option | Description | Selected |
|--------|-------------|----------|
| Always visible | Persistent right panel, splits layout | ✓ |
| Collapsible / toggle | Hidden by default, shown via keybind | |
| Bottom bar | Tokens/time as compact text in bottom bar | |

**User's choice:** Always visible
**Notes:** Width ~30 chars. Shows session name + tokens + response time + model name.

---

## Message Bifurcation

| Option | Description | Selected |
|--------|-------------|----------|
| Background color difference | AI msgs get subtle dark bg, user transparent | ✓ |
| Labeled entries | Each msg starts with 'You' / 'Assistant' | |
| Both — label + background | Most explicit approach | |

**User's choice:** Background color difference
**Notes:** No labels, no alignment difference — color difference is sufficient.

---

## Tool Calls

| Option | Description | Selected |
|--------|-------------|----------|
| Keep inline expandable | Current Phase 7 approach | ✓ |
| Nest inside assistant msg | Tool calls as sub-sections within assistant msg | |
| Right panel tool log | Move tool history to right panel | |

**User's choice:** Keep inline expandable

---

## Window Background

| Option | Description | Selected |
|--------|-------------|----------|
| Lighter/softer dark | #1a1a1a or #1e1e1e — softer than current | ✓ |
| Claude Code exact black | True near-black #0a0a0a | |
| Keep current warm dark | #181715 from claude-dark theme | |

**User's choice:** Lighter/softer dark

---

## OpenCode's Discretion

- Exact background hex value
- Right panel exact width and styling
- Message background color and padding
- Token/time display format
- Session name font and format
- Bottom bar integration with split layout

## Deferred Ideas

- Welcome/start page — not needed per user decision
- Collapsible right panel — user chose always-visible
- Tool call history in right panel — user chose inline expandable
- Copy/edit/regenerate actions — not discussed
