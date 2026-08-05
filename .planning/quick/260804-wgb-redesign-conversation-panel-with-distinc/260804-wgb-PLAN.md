---
phase: 260804-wgb
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tui-ink/src/components/message.tsx
  - tui-ink/src/panels/conversation-panel.tsx
autonomous: false
requirements:
  - quick-260804-wgb
user_setup: []

must_haves:
  truths:
    - "Every message — user, assistant, notice, and error — renders as its own full-width bordered sub-panel (Direction B, NOT chat bubbles, NOT two-column)"
    - "Each card shows a label-only header row (`You` / `Assistant` / `Notice` / `Error`) with no timestamps"
    - "Cards are role-colored: user=yellow border/#332a00 tint, assistant=green border/#002a1f tint, notice=gray border/#2a2a2a tint, error=red border/#2a2a2a tint"
    - "When the terminal lacks truecolor support, cards degrade to border-color-only (background omitted, borders and labels unchanged)"
    - "Streaming assistant messages render inside the assistant card with the blinking ▊ cursor preserved (StreamingText untouched)"
    - "Cards stack full-width in the existing reversed column with a 1-cell gap, auto-anchored to the latest message"
  artifacts:
    - path: "tui-ink/src/components/message.tsx"
      provides: "Bordered sub-panel rendering for all four message roles"
      contains: "CARD_BORDER"
    - path: "tui-ink/src/panels/conversation-panel.tsx"
      provides: "Inter-card spacing in the reversed conversation column"
      contains: "gap"
  key_links:
    - from: "tui-ink/src/components/message.tsx"
      to: "message.role"
      via: "Record lookup CARD_BORDER[role] / CARD_TINT[role] / CARD_LABELS[role]"
      pattern: "CARD_(BORDER|TINT|LABELS)\\[message\\.role\\]"
    - from: "tui-ink/src/components/message.tsx"
      to: "StreamingText"
      via: "StreamingText still rendered inside the assistant card body when isStreaming"
      pattern: "StreamingText"
    - from: "tui-ink/src/panels/conversation-panel.tsx"
      to: "MessageCard"
      via: "Reversed column maps conversation to MessageCard, gap={1} separates bordered cards"
      pattern: "gap"
---

<objective>
Redesign the TUI conversation panel so each message renders as its own distinct full-width bordered sub-panel (Direction B, per LOCKED CONTEXT decisions), with label-only header rows, subtle role-colored background tints, and a border-color-only fallback when the terminal lacks truecolor.

Purpose: Give user and AI messages visually distinct sub-panels so long conversations are scannable by speaker at a glance, while preserving the existing streaming behavior and the 09/11/16-UI-SPEC color vocabulary.
Output: Modified `MessageCard` (bordered sub-panel per role) + `ConversationPanel` inter-card gap. No backend, no new dependencies, no theme.ts.
</objective>

<execution_context>
@./.opencode/get-shit-done/workflows/execute-plan.md
@./.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260804-wgb-redesign-conversation-panel-with-distinc/260804-wgb-CONTEXT.md
@.planning/phases/16-tui-integration-skill-indicator/16-UI-SPEC.md

# Files touched by this plan (current state)

<interfaces>
<!-- Current MessageCard contract — executors implement against this, no exploration needed -->

From tui-ink/src/types.ts:
```typescript
export interface Message {
  id: string
  role: "user" | "assistant" | "notice" | "error"
  content: string
  timestamp: number
  isStreaming?: boolean
  truncated?: boolean
  tone?: "success" | "error"
}
```

From tui-ink/src/components/streaming-text.tsx (UNTOUCHED — reused as-is inside the assistant card):
```typescript
export function StreamingText({ text }: StreamingTextProps) // renders {text} + blinking green ▊ cursor
```

From tui-ink/src/components/message.tsx (current, lines 12-85): MessageCard switches on message.role:
- user: `<Text bold color="yellow">You{" "}</Text>` + `<Text color="white">{content}</Text>`
- assistant: column with `▸`/` ` green bold prefix + StreamingText (streaming) or white Text + optional `(truncated)` yellow dim italic
- notice: tone-based — success `✓` green bold / error `✗` red bold / undefined dim italic
- error: `✗` red bold
</interfaces>

Ink 7 Box supports (verified in node_modules/ink Box.d.ts): `borderStyle` ("single" from cli-boxes), `borderColor`, `backgroundColor`, `paddingX`, `gap`, `flexDirection`. ForegroundColorName includes "yellow", "green", "red", "gray".
</context>

<tasks>

<task type="auto">
  <name>task 1: Restructure MessageCard into bordered role sub-panels</name>
  <files>tui-ink/src/components/message.tsx</files>
  <action>
    Rewrite `MessageCard` in `tui-ink/src/components/message.tsx` so every message role renders as a full-width bordered sub-panel card with a label-only header row. Honor LOCKED decisions D-01 (Direction B full-width cards), D-02 (label-only header, no timestamps), D-03 (all roles get cards), D-04 (tints + truecolor fallback), D-05 (streaming inside the assistant card).

    Step 1 — Add module-local constants at the top of the file (per 11-UI-SPEC §10 convention — NO theme.ts):
    ```typescript
    const NOTICE_OK = "✓"                     // green, bold — success tone (existing, keep)
    const NOTICE_ERR = "✗"                    // red, bold — error tone (existing, keep)

    const CARD_LABELS: Record<Message["role"], string> = {
      user: "You",
      assistant: "Assistant",
      notice: "Notice",
      error: "Error",
    }

    const CARD_BORDER: Record<Message["role"], "yellow" | "green" | "gray" | "red"> = {
      user: "yellow",       // $secondary — user identity (09/11-UI-SPEC)
      assistant: "green",   // $primary — assistant identity
      notice: "gray",       // dim/neutral treatment (locked)
      error: "red",         // $error
    }

    const CARD_TINT: Record<Message["role"], string> = {
      user: "#332a00",      // dark muted yellow-brown (locked D-04)
      assistant: "#002a1f", // dark muted green (locked D-04)
      notice: "#2a2a2a",    // neutral dark gray (locked D-04)
      error: "#2a2a2a",     // neutral dark gray (locked D-04)
    }

    function supportsTruecolor(): boolean {
      if (process.env.COLORTERM === "truecolor") return true
      try {
        const s = process.stdout as unknown as { hasColors?: (count?: number) => boolean }
        return s.hasColors?.(2 ** 24) ?? false
      } catch {
        return false
      }
    }

    const HAS_TRUECOLOR = supportsTruecolor()   // evaluated once at module load
    ```

    Step 2 — Rebuild `MessageCard` as a single card wrapper with a per-role header row, then the EXISTING per-role content rendering (verbatim, moved into the card body):
    ```typescript
    export function MessageCard({ message }: MessageProps) {
      return (
        <Box
          flexDirection="column"
          borderStyle="single"
          borderColor={CARD_BORDER[message.role]}
          backgroundColor={HAS_TRUECOLOR ? CARD_TINT[message.role] : undefined}
          paddingX={1}
        >
          <Box>{renderLabel(message.role)}</Box>
          <Box>{renderContent(message)}</Box>
        </Box>
      )
    }
    ```
    - `renderLabel(role)` — one header row, label ONLY (no timestamp, no content):
      - user: `<Text bold color="yellow">You</Text>`
      - assistant: `<Text bold color="green">Assistant</Text>`
      - notice: `<Text dimColor>Notice</Text>`
      - error: `<Text bold color="red">Error</Text>`
    - `renderContent(message)` — preserve the existing per-role rendering EXACTLY, minus anything now redundant:
      - user: `<Text color="white">{message.content}</Text>` (the old `You{" "}` prefix is removed — the label now lives in the header row; do NOT duplicate it in content)
      - assistant: same structure as today, moved inside the card body — `<Text bold color="green">{message.isStreaming ? "▸" : " "}{" "}</Text>` then `{message.isStreaming ? <StreamingText text={message.content} /> : <Text color="white">{message.content}</Text>}` then the existing `{message.truncated && <Text color="yellow" dimColor italic>{" "}(truncated)</Text>}`. StreamingText stays INSIDE the assistant card — do not modify streaming-text.tsx and do not move the cursor anywhere else.
      - notice: the existing three tone branches unchanged (success = `✓` green bold, error = `✗` red bold, undefined = dim italic).
      - error: the existing `✗ {content}` red bold unchanged.
      - unknown role: return null (keep the existing final fallback).
    - Do NOT add a blank gap between the label row and the content row (keep cards compact — the locked design's row cost is border-top + label + content + border-bottom + 1 inter-card gap; no extra rows).
    - Do NOT touch `NOTICE_OK`/`NOTICE_ERR` glyphs or any copy strings. Do NOT introduce chat bubbles, side-alignment, or two-column layouts (locked: Direction B full-width only).

    ⚠ Avoid: wrapping the outer card in any extra margin/padding (the panel task handles spacing), using a hex borderColor (Ink borderColor takes ANSI names here — role identity must survive the no-truecolor fallback, so borders are named ANSI colors, not hex), or creating a theme.ts.
  </action>
  <verify>
    <automated>npm run typecheck</automated>
  </verify>
  <done>
    MessageCard renders one bordered sub-panel per message with label header (You/Assistant/Notice/Error), role-colored named-ANSI border, tinted background only when HAS_TRUECOLOR, streaming + notice tones + truncated indicator + ✗ error glyph preserved verbatim inside the card body, `npm run typecheck` passes in tui-ink/.
  </done>
</task>

<task type="auto">
  <name>task 2: Add inter-card spacing in the conversation column</name>
  <files>tui-ink/src/panels/conversation-panel.tsx</files>
  <action>
    In `tui-ink/src/panels/conversation-panel.tsx`, add a `gap={1}` prop to the reversed conversation column (the `<Box flexDirection="column-reverse" flexGrow={1} marginY={1}>` at line 32) so adjacent bordered cards never touch (a zero-gap stack would render a broken double-line `┘┌` seam).

    Changes are limited to that single prop. Leave EVERYTHING else untouched:
    - The panel's outer border, `Conversation · {title}` header row, and `paddingX={1}` (cards sit 1 cell inside the panel frame — border nesting is exactly 2 levels, accepted per the locked Direction B design).
    - The `● thinking` / `● processing...` status lines (status lines are NOT message roles — they get no card, per CONTEXT: only user/assistant/notice/error get cards).
    - The empty-state line `Type a message to start a conversation` and the `[...conversation].reverse().map((msg) => <MessageCard key={msg.id} message={msg} />)` mapping.

    ⚠ Avoid: changing the reversal logic (the array is reversed AND the column is reversed — latest stays anchored at the bottom), touching the panel's outer border, or adding margins to MessageCard (spacing is the panel's job via gap).
  </action>
  <verify>
    <automated>npm run typecheck; if ($?) { npm run build }</automated>
  </verify>
  <done>
    Reversed column has `gap={1}`; cards render with a visible 1-cell separation; latest message anchored at bottom; thinking indicators and empty state unchanged; `npm run typecheck` and `npm run build` both pass in tui-ink/.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>task 3: Human visual verification of sub-panel redesign</name>
  <what-built>
    Full-width bordered sub-panel cards per message role: user (yellow border, dark amber tint), assistant (green border, dark green tint), notice (gray border, neutral tint), error (red border, neutral tint) — each with a label-only header row, and the streaming cursor blinking inside the assistant card. (If the terminal lacks truecolor, backgrounds are omitted — borders/labels still carry the role color.)
  </what-built>
  <how-to-verify>
    Backend + TUI must be running (same setup used for prior Phase 16 E2E checks). Run `npm run dev` (watch build) in `tui-ink/` and `npm start` in a second terminal, or the project's usual TUI launch command. Then:
    1. Send a message (e.g. "hi") and confirm the **user message renders as a full-width card** with a yellow border, `You` label row, and content below the label. Expected (colors omitted in ASCII):
       ```
       ┌──────────────────────────┐
       │ You                      │
       │ hi                       │
       └──────────────────────────┘
       ```
    2. While the model replies, confirm the **assistant message renders as a green-bordered card** with `Assistant` label row, `▸` prefix, and the **blinking green ▊ cursor inside the card body** (D-05). After completion the cursor disappears and the full reply stays inside the card.
    3. Type `/skill demo-greeter` and confirm a **notice card** appears: gray border, `Notice` label (dim), content `✓ Loaded skill demo-greeter` in green bold.
    4. Type `/skill nope` and confirm a **notice card with error tone**: `✗ Skill 'nope' not found` in red bold.
    5. Confirm cards are **full-width, stacked with a 1-cell gap** (no `┘┌` seam), auto-anchored to the latest message, and that the `● thinking` indicator + `Conversation · {title}` header + footer chip/hints are unchanged.
    6. Confirm the window-resize and `Tab` panel-focus behaviors still work (borders stay aligned, no layout break at 60-col width).
  </resume-signal>Type "approved" or describe the specific issue(s).</how-to-verify>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| terminal → TUI render | The terminal's color-capability detection (`COLORTERM`/`hasColors`) is read-only environment introspection; no untrusted input crosses into the app. |

No new trust boundary is introduced by this plan — it is a rendering-only change to `tui-ink/` with no I/O, no user input handling, and no data flow changes.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-260804-wgb-01 | T | `supportsTruecolor()` (message.tsx) | mitigate | Wrap `process.stdout.hasColors` access in try/catch and default to `false` — a hostile/absent tty must degrade to border-color-only cards, never crash the render |
| T-260804-wgb-02 | D | `CARD_TINT` / `CARD_BORDER` records | accept | Static compile-time records keyed by the `Message["role"]` union; unknown roles hit the existing `return null` fallback — no runtime lookup of user data |
</threat_model>

<verification>
1. `npm run typecheck` passes in `tui-ink/` (task 1 + task 2).
2. `npm run build` passes in `tui-ink/` (task 2).
3. Human checkpoint: user/assistant/notice/error cards all render with label header + role border + tint (or border-only fallback), streaming cursor inside the assistant card, 1-cell card gap, no regressions to thinking indicator / header / footer.
</verification>

<success_criteria>
- Every message in the conversation is a distinct full-width bordered sub-panel with a label-only header row (`You` / `Assistant` / `Notice` / `Error`), stacked with a 1-cell gap and anchored to the latest.
- Role colors follow the live vocabulary: user=yellow, assistant=green, notice=gray/dim, error=red; subtle dark hex tints applied only under truecolor, border-color-only otherwise.
- Streaming, notice tones (✓/✗), truncated indicator, and error ✗ rendering are preserved verbatim inside their cards; `StreamingText` is untouched.
- Only two files changed: `tui-ink/src/components/message.tsx` and `tui-ink/src/panels/conversation-panel.tsx`. No new dependencies, no backend changes, no theme.ts.
</success_criteria>

<output>
After completion, create `.planning/quick/260804-wgb-redesign-conversation-panel-with-distinc/260804-wgb-SUMMARY.md`
</output>
