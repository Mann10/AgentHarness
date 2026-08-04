# Phase 7: TUI Visual Overhaul - Context

**Gathered:** 2026-07-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform the existing Textual TUI (Phase 6) from its current functional-but-minimal appearance to a professional-grade, Claude Code-inspired terminal interface. Focus is on visual design, layout simplification, and inline content rendering — not adding new backend capabilities.

</domain>

<decisions>
## Implementation Decisions

### Visual Design System
- **D-01:** Claude Code-inspired dark theme — clean dark backgrounds, subtle borders, high-contrast text, minimal chrome
- **D-02:** Drop Tokyo Night palette from UI-SPEC.md; adopt a new palette similar to Claude Code's dark theme (deep grays, clean white text, subtle accent colors for states)
- **D-03:** Consistent spacing, typography, and border treatment across all widgets

### Layout Architecture
- **D-04:** Minimal layout — no persistent sidebar (remove JobQueueSidebar as permanent fixture)
- **D-05:** Conversation panel takes full width
- **D-06:** Bottom area reserved for input bar + compact indicators only

### Content Rendering
- **D-07:** Inline tool calls in message stream — tool calls render as compact inline entries within assistant messages, not separate ToolCallCard widgets
- **D-08:** Expandable inline entries for tool calls with large args/results
- **D-09:** Remove ToolCallCard as separate widget; integrate tool call display into message flow

### Input Bar
- **D-10:** Claude Code-style minimal input — clean single-line, no extra chrome
- **D-11:** Visual state changes for idle vs processing (placeholder, color, disable state)
- **D-12:** Keep existing command history (up/down navigation) and /command autocomplete

### Status & Progress
- **D-13:** No separate StatusBar widget — remove it
- **D-14:** Processing state shown via input bar state (placeholder, styling) and inline indicators in message area
- **D-15:** Compact inline tool timeline indicator in input bar area showing recent tool call count
- **D-16:** Compact job queue counter in input bar area ("Jobs: N pending")

### OpenCode's Discretion
- Exact spacing, padding, and typography values
- Animation timing and transitions
- Specific Textual widget subclass implementation choices
- Inline tool call collapse/expand interaction detail
- Exact inline indicator design (tool count, job count)
- Color hex values for the new dark theme palette

</decisions>

<specifics>
## Specific Ideas

- "Like Claude" — Claude Code's terminal aesthetic is the primary reference
- Tool calls should feel like part of the conversation, not separate UI elements
- Maximize space for message content, minimize chrome

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing TUI
- `tui/app.py` — Current TUI app layout, CSS, event wiring
- `tui/widgets/conversation_view.py` — Message container
- `tui/widgets/message_card.py` — Message rendering (user, assistant, error, notice)
- `tui/widgets/tool_call_card.py` — Current tool call card (to be replaced/removed)
- `tui/widgets/status_bar.py` — Current status bar (to be removed)
- `tui/widgets/tool_timeline.py` — Current tool timeline (to be replaced with compact indicator)
- `tui/widgets/input_bar.py` — Current input bar (to be redesigned)
- `tui/widgets/job_queue_sidebar.py` — Current job queue sidebar (to be removed as persistent widget)

### Spec & Design
- `.planning/phases/06-rich-textual-tui/UI-SPEC.md` — Phase 6 UI spec (defines component tree and widget specs to be redesigned)

### Reference (Claude Code aesthetic)
- Claude Code's terminal UI — primary visual reference for dark theme, minimal layout, inline tool calls

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tui/widgets/conversation_view.py` — `ConversationView` (VerticalScroll) can be kept and enhanced
- `tui/widgets/message_card.py` — `MessageCard` factory methods can be refined but structure is sound
- `tui/widgets/input_bar.py` — History navigation, command list, processing animation logic reusable
- `tui/app.py` — Event subscription pattern, RuntimeAPI integration, orchestration logic stays

### Established Patterns
- Textual app with `App`, `ComposeResult`, `@on` decorators, reactive attributes
- EventBus subscription at mount time with typed event handlers
- Rich library for terminal rendering (Markdown, Panel, Syntax, Text)
- Widgets built as Static subclasses with `_refresh` pattern for updates

### Integration Points
- `RuntimeAPI` from harness/ remains the data source — no changes needed to harness layer
- Event types (TurnStarted, ToolCallEvent, ToolResultEvent, etc.) remain unchanged
- `InputBar.Submitted` message continues to trigger `runtime.submit_prompt()`
- SessionPicker screen and its keybindings remain unchanged

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within TUI visual overhaul scope

</deferred>

---

*Phase: 07-tui-visual-overhaul*
*Context gathered: 2026-07-27*
