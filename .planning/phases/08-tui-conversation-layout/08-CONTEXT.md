# Phase 8: TUI Conversation Layout - Context

**Gathered:** 2026-07-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform the TUI conversation area so user prompts and AI responses are visually distinct in a clear chronological sequence, with a professional dark theme, always-visible stats panel, and no header chrome. Building on the Phase 7 visual foundation (claude-dark theme, inline tool calls, compact bottom bar).

</domain>

<decisions>
## Implementation Decisions

### Header / Title Bar
- **D-01:** Remove Header widget entirely — no persistent header bar, no clock, no app title visible. Maximizes conversation space.

### Launch Behavior
- **D-02:** Launch straight into empty conversation view — no welcome/start screen. Clean startup, minimal chrome.

### Right Stats Panel
- **D-03:** Always-visible right-side panel (no toggle/collapse). Medium width (~30 characters). Shows:
  - Current session name (at top)
  - Token count consumed this session
  - Last response time
  - Current model name (e.g., "gpt-4o")
- Panel is persistent — splits layout with conversation panel.

### Message Bifurcation
- **D-04:** Visual separation via background color difference:
  - AI/assistant messages: subtle dark background ($surface or similar)
  - User messages: transparent/no background
  - No labels ("You" / "Assistant") — color difference is sufficient
  - No alignment difference — all messages left-aligned

### Tool Calls
- **D-05:** Keep Phase 7 inline expandable tool calls — compact inline entries within message stream, click to expand. No change from current approach.

### Window Background
- **D-06:** Lighter/softer dark than current claude-dark background. Shift from #181715 to a softer dark like #1a1a1a or #1e1e1e for a cleaner, more modern look.

### OpenCode's Discretion
- Exact background hex value for the softer dark
- Right panel exact width in characters/pixels
- Right panel styling (borders, spacing, typography)
- Message background exact color and padding
- Transition/animation details (if any)
- Session name font and format in right panel
- Token/time display format
- Bottom bar integration with split layout

</decisions>

<specifics>
## Specific Ideas

- "Like OpenCode" — OpenCode's terminal UI is the primary reference for layout, feel, and professionalism
- "Like Claude" — Claude Code's aesthetic for background, colors, and minimal chrome
- "Background kind of like Claude" — softer/lighter dark, not pitch black
- Right panel should feel integrated, not bolted on — consistent with the claude-dark theme
- Existing inline tool calls from Phase 7 are fine — no changes needed there

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing TUI
- `tui/app.py` — Current TUI app layout, event wiring, compose structure
- `tui/theme.tcss` — Current CSS theme (to be extended with right panel, new background, message styles)
- `tui/widgets/conversation_view.py` — Message container (to be split-layout with right panel)
- `tui/widgets/message_card.py` — Message rendering (to get new background styles)
- `tui/widgets/inline_tool_call.py` — Inline tool calls (no changes needed)

### Prior Phase Decisions
- `.planning/phases/07-tui-visual-overhaul/07-CONTEXT.md` — Phase 7 decisions (claude-dark theme, inline tool calls, minimal layout)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tui/theme.tcss` — Existing CSS variables and theme structure, extend for new layout
- `tui/widgets/conversation_view.py` — VerticalScroll container, add split layout with right panel
- `tui/widgets/message_card.py` — Factory methods for message types, add background styling to assistant variant
- `tui/app.py` — Compose, event handlers, theme registration — extend with right panel widget
- `tui/widgets/inline_tool_call.py` — Keep as-is, already satisfies Phase 7 requirements

### Established Patterns
- Textual App with `ComposeResult`, `@on` decorators, reactive attributes
- EventBus subscription pattern with typed event handlers
- CSS-driven theming via `theme.tcss`
- Widgets as Static subclasses for custom rendering

### Integration Points
- Right panel needs live updates from RuntimeAPI events (track tokens, time, model)
- Token counting needs a mechanism — currently not tracked in TUI, may need EventBus extension or RuntimeAPI query
- Response time needs timing — capture on TurnStarted, compute on ResponseComplete
- Model name — accessible from config or RuntimeAPI
- Bottom bar (tool-indicator, job-indicator, InputBar) must work within the new split layout
- Session name available from RuntimeAPI session manager

</code_context>

<deferred>
## Deferred Ideas

- Welcome/start page with recent sessions and quick commands — not needed per user decision
- Collapsible right panel — user chose always-visible
- Tool call history in right panel — user chose inline expandable instead
- Copy/edit/regenerate message actions — not discussed, future possibility

</deferred>

---

*Phase: 08-tui-conversation-layout*
*Context gathered: 2026-07-27*
