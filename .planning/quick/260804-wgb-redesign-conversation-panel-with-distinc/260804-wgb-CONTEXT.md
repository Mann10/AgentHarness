# Quick task 260804-wgb: Redesign conversation panel with distinct bordered subpanels for user and AI messages - Context

**Gathered:** 2026-08-04
**Status:** Ready for planning

<domain>
## task Boundary

Change the TUI conversation panel so user and AI messages render in distinct bordered subpanels (full-width cards), with notice/error messages also getting subpanel treatment. This is a visual/UX change to `tui-ink/` only — no backend changes.
</domain>

<decisions>
## Implementation Decisions

### Layout Style
- **Direction B — Full-width cards:** Each message renders as its own bordered sub-panel stacked full-width (NOT side-aligned chat bubbles, NOT two-column split).
- Each card gets a header row with a **role label only** (no timestamps).
- Cards stack vertically in the existing reversed column (auto-anchor to latest).

### Message Roles
- `user` → card, label `You`, yellow role color
- `assistant` → card, label `Assistant`, green role color
- `notice` → card, label `Notice`, dim/neutral treatment (tones preserved: success=green bold ✓, error=red bold ✗, info=dim italic)
- `error` → card, label `Error`, red role color

### Color / Background
- **Subtle background tint** via dark muted hex colors (e.g. user ~#332a00, AI ~#002a1f, notice/error ~#2a2a2a) with role-colored borders.
- **Fallback:** if the terminal lacks truecolor support, degrade to border-color-only cards (background omitted).

### Streaming
- AI streaming message blinks/streams **inside** its card (existing `StreamingText` behavior preserved inside the assistant card).

</decisions>

<specifics>
## Specific Ideas

No specific references — decisions fully captured above. Existing design system constraints apply:
- Terminal UI: Ink 7.1 + React 19, character-cell units, no CSS, styling via Ink props only
- 09/11/16-UI-SPEC color vocabulary: green=success/assistant, yellow=user, red=error, white=text, dimColor=muted
- No new dependencies (ink ^7.1.0, react ^19, zustand ^5 already present)
</specifics>

<canonical_refs>
## Canonical References

- .planning/phases/16-tui-integration-skill-indicator/16-UI-SPEC.md (live color/token vocabulary)
- .planning/phases/09-ts-tui-json-rpc/09-UI-SPEC.md (base design system)
- .planning/phases/11-session-popup-and-panel-layout/11-UI-SPEC.md (message/notice patterns)
</canonical_refs>
