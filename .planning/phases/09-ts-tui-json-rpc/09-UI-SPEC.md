# Phase 9: TypeScript TUI + JSON-RPC Adapter — UI Design Contract

**Created:** 2026-07-27
**Status:** Draft

## 1. Design Philosophy & Principles

**Terminal-first, content-maximal.** This is a professional AI coding assistant TUI inspired by Claude Code and OpenCode. Chrome is minimized. Every pixel row is dedicated to conversation content or immediate interaction state.

| Principle | Implication |
|-----------|-------------|
| **Minimal chrome** | No header, no title bar, no app logo. Status info is compact, single-line. |
| **Content is king** | The conversation list occupies maximum vertical space. Bottom bar is 3 rows. Stats bar (top) is 1 row. Error bar appears only when needed. |
| **Inline over modal** | Tool calls render inline within message flow. Errors render as dismissable bars. Session picker is a temporary overlay. |
| **Keyboard-first** | Every interaction has a keyboard binding. No mouse-dependent UI. Input bar is always focused unless a modal is open. |
| **Visual hierarchy via color** | Message roles distinguished by background color, not labels. Status changes communicated through color and symbol changes. |
| **Streaming-native** | The UI is built for streaming — content appears token-by-token. The store separates "streaming" from "finalized" content. |
| **React/Ink with custom components** | All components built on Ink primitives (`Box`, `Text`). No external component library. No shadcn (terminal UI). |

**Design references (from Phases 7, 8):**
- Claude Code dark theme — deep grays, high-contrast text, subtle accents
- OpenCode layout — split conversation + stats, no header, straight-to-chat
- Message bifurcation via background: assistant = subtle dark, user = transparent
- All tool calls inline, expandable within message flow

## 2. Visual Design

### Color Palette

**Carried forward from Phase 7 Claude Code-inspired theme** (adapted from existing `tui/theme.tcss` and Phase 8 softening).

| Token | Ink Color | Hex Equivalent | Usage |
|-------|-----------|----------------|-------|
| `$background` | `#1a1a1a` | n/a (terminal bg) | App background (softer dark per D-06) |
| `$surface` | `#222222` | — | Stats panel, message assistant bg, bottom bar bg |
| `$panel` | `#2a2a2a` | — | Border color, subtle dividers |
| `$text` | `#e0e0e0` | — | Primary text — assistant messages |
| `$text-muted` | `dimColor` | — | User messages, metadata, labels |
| `$primary` | `green` | — | Success states, completion indicators |
| `$secondary` | `yellow` | — | Processing states, tool call running |
| `$error` | `red` | — | Error messages, failed tool calls, error bar border |
| `$warning` | `yellowBright` | — | Warning/destructive confirmation |
| `$accent` | `blue` (bold) | — | Focus indicator, session picker cursor, selected item |

**Color application rules:**
- **60% — Dominant:** `$background` (#1a1a1a) — all non-content areas
- **30% — Secondary:** `$surface` (#222222) — StatsBar background, assistant message background, bottom bar
- **10% — Accent:** Reserved exclusively for: selection cursor in SessionPicker, status dot in StatsBar, focus state, new session "+" highlight
- **Semantic (destructive):** `$error` — only for error messages, failed tool calls, error borders

**Additional message-level colors (from existing `MessageCard`):**
| Role | Text Color | Background | Style |
|------|-----------|------------|-------|
| User | `$text-muted` (dim) | Transparent | Plain, dimmed |
| Assistant | `$text` (white) | `$surface` | Bold headers, markdown body |
| System/Notice | `$text-muted` (italic) | Transparent | Italic, dimmed |
| Error | `$error` (red) | Transparent | Bold, may have border |

### Typography

Terminal environment — fonts are terminal-controlled. Ink uses the terminal's monospace font. The only control is weight and color.

| Token | Ink Style | Usage |
|-------|-----------|-------|
| Body | `<Text>` default | Message content, labels |
| Bold | `<Text bold>` | Section headers (Session, Tokens in StatsBar), active item in SessionPicker |
| Dim | `<Text dimColor>` | User messages, metadata, timestamp/muted labels |
| Italic | `<Text italic>` | Notice messages, tool call names (running state) |
| Error | `<Text color="red">` | Error content |
| Success | `<Text color="green">` | Completed tool calls, connected status |
| Processing | `<Text color="yellow">` | Spinner, processing indicator |

**Terminal constraints:**
- No custom fonts, no font-size control (terminal font size)
- All sizing in character columns (`useStdoutDimensions` for width/height)
- Line height: 1 (terminal default — no control)
- Text wraps at terminal width

### Spacing & Layout

**Terminal grid units (1 unit = 1 character cell):**

| Scale | Value | Usage |
|-------|-------|-------|
| Padding X | 1 | Inner padding for boxes, cards |
| Padding Y | 0 or 1 | Vertical padding for panels (StatsBar) |
| Margin X | 1 | Between messages and edge |
| Margin Y | 0 | No inter-message gap (compact) |
| StatsBar height | 1 | Single-line top bar |
| Bottom bar height | 3 | InputBar (3 rows) |
| Stats Panel width | 30 | Right-side panel (from Phase 8 D-03) |
| Error bar height | auto | Content-dependent, max 3 rows |

### Theming

No CSS/styling framework. All theming is done via Ink's `color`, `backgroundColor`, `dimColor`, `bold`, `italic` props on `<Box>` and `<Text>`.

**Theme object structure** (for centralization in code):

```typescript
// Design tokens as constants — no CSS, all Ink props
const THEME = {
  colors: {
    background: '#1a1a1a',  // App background
    surface: '#222222',     // Panel/message bg
    text: '#e0e0e0',        // Primary text
    textMuted: '#888888',   // Dimmed text
    primary: 'green',       // Success
    secondary: 'yellow',    // Processing
    error: 'red',           // Error
    accent: 'blue',         // Focus/selection
    warning: 'yellowBright', // Destructive confirmation
  },
  spacing: {
    paddingX: 1,
    paddingY: 0,
    marginX: 1,
    marginY: 0,
  },
  layout: {
    statsBarHeight: 1,
    inputBarHeight: 3,
    statsPanelWidth: 30,
  },
} as const;
```

**Registry safety:** No shadcn, no third-party component registries. Custom Ink components only (D-11).

## 3. Component Design

### ConversationScreen

**Purpose:** Main scrollable message list — displays user prompts, assistant responses, inline tool calls, and notices in chronological order. Auto-scrolls to bottom on new content.

**States:**
| State | Visual |
|-------|--------|
| Empty (initial launch) | "No messages yet. Type a prompt to start." — dim/italic, centered |
| Has messages | Scrollable list of MessageCard + ToolCallIndicator entries |
| Streaming | Final message content updates as chunks arrive |
| Processing (no stream yet) | "Waiting for response..." — dimmed notice at bottom |
| Error | ErrorBar overlays the view |

**Behavior:**
- Renders `messages[]` from store in order
- After the last finalized message, if `streamedContent` is non-empty, renders a streaming assistant MessageCard
- After the streaming card, renders active `ToolCallIndicator` components
- Calls `ref.scrollToBottom()` via Ink `useRef` on every re-render with new content
- Conversation area takes `flexGrow: 1` within the flex column layout

**Visual spec:**
- Full width of conversation panel (1fr in horizontal split)
- Height: flexGrow 1 (fills between StatsBar/ErrorBar and bottom bar)
- Background: transparent (parent provides $background)
- No scrollbar chrome (terminal-native scroll via Shift+PageUp/PageDown)

**Copy:**
- Empty: `"No messages yet. Type a prompt to start."` (dim, italic)
- Processing: `"Waiting for response..."` (dim text, shown only if `isProcessing && streamedContent === ''`)

---

### MessageCard

**Purpose:** Renders a single conversation message with role-appropriate styling and content.

**States:**
| Variant | Visual |
|---------|--------|
| User | `<Text dimColor>` — plain text, transparent bg, 80-char prefix wrap |
| Assistant | `<Text>` — white text, `$surface` background, Markdown rendering (future) |
| System/Notice | `<Text dimColor italic>` — italic, dim, transparent bg |
| Error | `<Text color="red">` — red text, bordered box |

**Behavior:**
- User messages: wrap long lines at terminal width, prefix with `> ` (from MessageCard.user pattern)
- Assistant messages: render content as plain text for Phase 9 (Markdown parsing deferred), background set to `$surface`
- Error messages: render within a `red borderStyle="round"` box with `⚠` prefix
- Notice messages: plain dim italic text

**Visual spec:**
- Margin: 0 on all sides (compact — no gap between messages)
- Padding X: 1
- Assistant background: backgroundColor `$surface`
- User background: transparent

**Copy:** Dynamic — content comes from store messages. Static copy:
- User: rendered as received from backend `turn_started` event's prompt field
- Assistant: streamed content from `token` notifications, finalized in store

---

### InputBar

**Purpose:** Single-line text input for user prompts, with history navigation, `/command` support, and processing visual state.

**States:**
| State | Visual |
|-------|--------|
| Idle | Placeholder "Type a prompt..." — dim, cursor visible |
| Processing | Placeholder "Thinking..." — cycling dots animation, disabled, cursor hidden |
| Disconnected | Placeholder "Backend disconnected — press R to restart" — red/dim |

**Behavior:**
- Ink `<TextInput>` (custom built on `useInput`) — handles character input, cursor, backspace
- Enter key submits the current value (calls `client.request('chat', { prompt })`)
- Up/Down arrows navigate input history (50 entries max)
- Tab triggers `/command` autocomplete (commands: `/sessions`, `/new`, `/resume`, `/title`, `/help`, `/exit`)
- During processing: `disabled` state, no input accepted, placeholder cycles through `["Thinking", "Thinking.", "Thinking..", "Thinking..."]` at 500ms interval
- After submit: append to history, clear input, focus remains

**Visual spec:**
- Height: 3 terminal rows (allows one line of text with padding)
- Background: transparent (parent bottom bar provides `$surface`)
- Text color during idle: `$text`
- Text color during processing: `$primary` (green)
- Border: none (clean, no box)

**Copy:**
- Idle placeholder: `"Type a prompt..."`
- Processing placeholder: `"Thinking"` → `"Thinking."` → `"Thinking.."` → `"Thinking..."` (cycles)
- Disconnected: `"Backend disconnected. Press Ctrl+R to restart."`

---

### StatsBar

**Purpose:** Single-line top bar showing connection status, processing state, and active session name. Provides at-a-glance system state.

**States:**
| State | Visual |
|-------|--------|
| Connected, idle | Green `○` + "ready" + session name |
| Connected, processing | Yellow `◆` + "processing" + session name |
| Disconnected | Red `✗` + "disconnected" + "no session" |

**Behavior:**
- Renders at the very top of the app, always visible
- Reads from store: `activeSession`, `isProcessing`, `connected` prop
- Right-justified with padding to fill terminal width
- Uses `useStdoutDimensions()` to calculate padding

**Visual spec:**
- Height: 1 row
- Background: transparent (body background)
- Text: `dimColor` for labels, colored status dot
- Padding right: fills terminal width with spaces for right-justified feel (or left-aligned with gap)
- Format: `{statusSymbol} {statusLabel}  │  session: {sessionName}`

**Copy:**
- Status labels: "ready", "processing", "disconnected"
- No session: `"session: none"` (dim)
- With session: `"session: {title || id.slice(0,8)}"`

---

### ToolCallIndicator

**Purpose:** Compact inline display of active tool calls within the message stream, showing tool name and completion status.

**States:**
| State | Visual |
|-------|--------|
| No tool calls | render nothing (return null) |
| Running | Yellow spinner `⠋` + italic tool name |
| Completed | Green `✓` + tool name + dim result preview |
| Error | Red `✗` + tool name + dim error preview |

**Behavior:**
- Renders below the streaming message content, above the next message
- Each tool call is one line: `{icon} {toolName} {resultPreview}`
- Result preview truncated to 80 characters with `…` ellipsis
- Multiple concurrent tool calls stack vertically
- When a tool call transitions from running → completed/error, the line updates in-place

**Visual spec:**
- Margin top: 1 (space above tool call group)
- Margin left: 2 (indent from message text)
- Text color: yellow (running), green (completed), red (error) — via Ink color prop
- Tool name: bold
- Result: dimColor

**Copy:** Dynamic — tool name from event, result from event. No static copy.

---

### ErrorBar

**Purpose:** Dismissable error notification bar that appears above the conversation area when an error occurs.

**States:**
| State | Visual |
|-------|--------|
| No error | render nothing (return null) |
| Error | Red-bordered box with error message + dismiss hint |

**Behavior:**
- Appears at top of app (below StatsBar, above ConversationScreen)
- Esc key dismisses (hides until next error)
- Error content set via `store.setError(error)` — null to clear
- Max height: 3 rows (long errors truncated)
- Backend crash: "Backend process disconnected." — non-dismissable until restart

**Visual spec:**
- Border style: `single` (round)
- Border color: red
- Padding X: 1
- Text: red color for `⚠` prefix + message
- Dim text for "(press Esc to dismiss)" hint

**Copy:**
- Dismiss hint: `"  (press Esc to dismiss)"` (dim)
- Backend crash: `"⚠ Backend process disconnected. Press Ctrl+R to restart."` (no dismiss)
- Generic error: `"⚠ {error message}"`

---

### SessionPicker (modal overlay)

**Purpose:** Modal screen for session management — list, create, switch, and delete sessions. Rendered as a full-app overlay.

**States:**
| State | Visual |
|-------|--------|
| Loading sessions | "Loading..." dim text |
| Sessions loaded | Scrollable list with cursor |
| No sessions (empty) | "No sessions yet. Create one." dim text below "+ New Session" |
| Error loading | "Could not load sessions" red text |

**Behavior:**
- Opens on `Ctrl+S` keyboard shortcut
- Replaces the entire app content (rendered conditionally in App.tsx)
- Keyboard navigation:
  - `↑` / `↓` — move cursor
  - `Enter` / `Space` — select (if "+ New Session" → create; if session → switch)
  - `d` — delete selected session (no confirm dialog — immediate for Phase 9)
  - `Esc` / `q` — close picker
- On session switch: closes picker, clears message list for new session
- On session create: closes picker, creates new session, switches to it
- On session delete: removes from list, cursor moves to previous item

**Visual spec (ASCII layout):**
```
Session Manager
═══════════════

> + New Session
    session-title-1  (abc12345)
    session-title-2  (def67890)
    ...sessions listed...

↑ ↓ navigate  •  Enter select  •  d delete  •  Esc/q close
```

- Title: bold + underline
- Cursor: `>` prefix on selected line
- "+ New Session": green, bold when selected
- Session items: bold when selected, dim ID suffix
- Bottom hint: dim text, shows keybindings

**Copy:**
- Title: `"Session Manager"` (bold, underline)
- Create action: `"+ New Session"` (green when focused)
- Loading: `"Loading..."` (dim)
- Hint: `"↑ ↓ navigate  •  Enter select  •  d delete  •  Esc/q close"` (dim)

---

## 4. Interaction Design

### Keyboard & Input

| Key | Context | Action |
|-----|---------|--------|
| `Enter` | Input bar focused | Submit prompt via `client.request('chat', { prompt })` |
| `↑` / `↓` | Input bar focused | Navigate input history (50 entries) |
| `Tab` | Input bar focused | Trigger `/command` autocomplete |
| `Ctrl+C` | Any (input bar) | Send `cancel` RPC request (NOT exit app) |
| `Ctrl+S` | Any | Open SessionPicker overlay |
| `Esc` | ErrorBar visible | Dismiss error |
| `Esc` / `q` | SessionPicker open | Close SessionPicker |
| `↑` / `↓` | SessionPicker open | Navigate session list cursor |
| `Enter` / `Space` | SessionPicker open | Select focused item (create/switch) |
| `d` | SessionPicker open | Delete selected session |

**Input handling rules (per Ink):**
- `useInput` registered at App level with `isActive` gating based on current screen
- During InputBar focus: all printable characters go to text input, only special keys intercepted
- During SessionPicker: all keys intercepted by picker's `useInput`
- During processing: InputBar is disabled — no text input accepted
- `index.ts` uses `exitOnCtrlC: false` to prevent Ink from killing the app on Ctrl+C

### Navigation

| Transition | Trigger | Behavior |
|------------|---------|----------|
| App startup | Auto | Spawn Python → ping readiness → render ConversationScreen |
| App → SessionPicker | `Ctrl+S` | Full-screen overlay, state preserved underneath |
| SessionPicker → App | `Esc` / `q` | Return to conversation, state unchanged |
| SessionPicker → App (switched) | `Enter` on session | Close picker, messages cleared, new session active |
| App → exit | `Ctrl+D` (planned) | Graceful shutdown: kill Python backend, exit Ink app |

### Feedback & Loading

| Scenario | Indicator | Duration |
|----------|-----------|----------|
| Prompt submitted (waiting for first token) | InputBar shows "Thinking" cycling animation | Until first `token` or `turn_started` event |
| Streaming response | MessageCard content appends in real-time | Until `response_complete` event |
| Tool call running | ToolCallIndicator shows spinner `⠋` + yellow name | Until `tool_result` or error event |
| Tool call complete | ToolCallIndicator updates to `✓` + green name | Until next turn |
| Backend disconnected | StatsBar shows red `✗` + ErrorBar shows disconnect message | Until app restart |
| Session picker loading | "Loading..." dim text in SessionPicker | Until `sessions.list` response |
| Cancel requested | Processing state clears, no visual feedback needed | Immediate |

**Error notification patterns (D-07 delivery):**
- **Runtime errors** (from `error` event): ErrorBar with message + Esc to dismiss
- **Backend crash** (process exit): ErrorBar with "Backend disconnected" + Ctrl+R to restart
- **Request errors** (RPC method fails): ErrorBar with "Request failed: {message}"
- **Transient errors** (parse errors, network): console.warn only, no user-facing feedback

## 5. Screen Layouts

### Main App Layout

```
┌──────────────────────────────────────────────────────────────┐
│ ○ ready  │  session: my-session                               │  ← StatsBar (1 row)
├──────────────────────────────────────────────┬───────────────┤
│                                              │ Session       │
│  > What's the weather in Tokyo?              │  weather-tok  │
│                                              │               │
│  The weather in Tokyo is currently 22°C      │ Tokens        │
│  with light rain.                             │  1,234        │
│                                              │               │
│    ⠋ get_weather  — calling API...          │ Last Response │
│    ✓ get_weather  — {"temp": 22}             │  1.2s         │
│                                              │               │
│  Here are the details...                      │ Model         │
│  (streaming continues...)                     │  gpt-4o       │
│                                              │               │
│                                              │ Date          │
│                                              │  Jul 27, 2026 │
│                                              │               │
│                                              │ Time          │
│                                              │  2:34:56 PM   │
│                                              │               │
├──────────────────────────────────────────────┤               │
│ ⚠ Error: Something went wrong (Esc to dismiss)│               │
├──────────────────────────────────────────────┴───────────────┤
│ > Type a prompt...                                           │  ← InputBar (3 rows)
└──────────────────────────────────────────────────────────────┘
```

**Layout composition (Ink Box hierarchy):**
```
<Box flexDirection="column" height="100%">
  <StatsBar />                                    ← 1 row
  <ErrorBar />                                    ← auto (conditional)
  <Box flexDirection="row" flexGrow={1}>          ← fills remaining height
    <Box flexDirection="column" flexGrow={1}>     ← conversation area
      <ConversationScreen />                      ← flexGrow: 1, scrollable
    </Box>
    <StatsPanel />                                ← 30 cols fixed width
  </Box>
  <Box height={3}>                                ← bottom bar
    <ToolCallIndicator />                         ← inline tool call statuses
    <InputBar />                                  ← 3 rows
  </Box>
</Box>
```

**Conversation Panel** (left, flexGrow 1):
- Contains MessageCard and ToolCallIndicator components stacked vertically
- Auto-scrolls to bottom on new content
- Background: transparent (inherits app background)

**StatsPanel** (right, fixed 30 cols):
- Always visible per D-03 (Phase 8)
- Background: `$surface`
- Left border: `$panel`
- Padding: 1 on all sides
- Sections: Session name, Tokens, Last Response, Model, Date, Time
- Live clock updates every second

**Bottom bar** (fixed 3 rows):
- Background: `$surface`
- Top border: thin line in `$panel`
- Contains: ToolCallIndicator (if active) + InputBar
- During idle: only InputBar visible
- During processing: ToolCallIndicator shown above InputBar

### SessionPicker Overlay Layout

```
┌──────────────────────────────────────────────────────────────┐
│ Session Manager                                              │
│ ═══════════════════════════════════════════════════════════   │
│                                                              │
│  > + New Session                                             │
│    weather-agent       (abc12345)                            │
│    code-review-session (def67890)                            │
│    general-chat        (ghi13579)                            │
│                                                              │
│  ↑ ↓ navigate  •  Enter select  •  d delete  •  Esc/q close │
└──────────────────────────────────────────────────────────────┘
```

- Full terminal width and height (no visible "behind")
- Centered content with padding
- Title at top, session list in middle, keyboard hint at bottom
- Backend communication during open: `sessions.list` on mount, `sessions.create`/`sessions.switch`/`sessions.delete` on actions

### Empty State Layout

```
┌──────────────────────────────────────────────────────────────┐
│ ○ ready  │  session: untitled                                 │
├──────────────────────────────────────────────┬───────────────┤
│                                              │ Session       │
│                                              │  untitled     │
│  No messages yet.                            │               │
│  Type a prompt to start.                     │ Tokens        │
│                                              │  0            │
│                                              │               │
│                                              │ Last Response │
│                                              │  —            │
│                                              │               │
│                                              │ Model         │
│                                              │  gpt-4o       │
│                                              │               │
│                                              │ Date          │
│                                              │  Jul 27, 2026 │
│                                              │               │
│                                              │ Time          │
│                                              │  2:34:56 PM   │
│                                              │               │
├──────────────────────────────────────────────┴───────────────┤
│ > Type a prompt...                                           │
└──────────────────────────────────────────────────────────────┘
```

- Centered dim text: "No messages yet. Type a prompt to start."
- StatsPanel shows default "untitled" session, 0 tokens, "—" for time, model name
- InputBar active and ready

### Processing State Layout

```
┌──────────────────────────────────────────────────────────────┐
│ ◆ processing  │  session: weather-tok                         │
├──────────────────────────────────────────────┬───────────────┤
│                                              │ Session       │
│  > What's the weather in Tokyo?              │  weather-tok  │
│                                              │               │
│  The weather in Tokyo is currently 22°C      │ Tokens        │
│  with light rain.                             │  1,234        │
│                                              │               │
│    ⠋ get_weather                              │ Last Response │
│                                              │  —             │
│  Here are the details...                      │               │
│  (streaming)                                  │ Model         │
│                                              │  gpt-4o       │
│                                              │               │
│                                              │ ...           │
│                                              │               │
├──────────────────────────────────────────────┴───────────────┤
│ Thinking...                                                   │
└──────────────────────────────────────────────────────────────┘
```

- StatsBar: yellow `◆` + "processing"
- InputBar: disabled, "Thinking..." cycling placeholder
- User message visible, tool indicator shows running/complete
- Assistant message streaming (content grows)
- StatsPanel: Token count updates (via future `token` event tracking)

## 6. Design Tokens

```typescript
// frontend/src/ui/theme.ts (to be created — central token definition)
// All values derived from Phase 7 Claude Code-inspired + Phase 8 softer dark theme.

export const THEME = {
  colors: {
    background: '#1a1a1a',     // App background — softer dark (D-06)
    surface: '#222222',         // Secondary surface — panels, assistant bg, bottom bar
    panel: '#2a2a2a',           // Borders, dividers
    text: '#e0e0e0',            // Primary text (assistant messages)
    textMuted: '#888888',       // Dimmed text (user messages, labels)
    primary: 'green',           // Success, connected, completed
    secondary: 'yellow',        // Processing, running
    error: 'red',               // Errors, failures
    accent: 'blue',             // Selection, focus
    warning: 'yellowBright',    // Destructive actions
  },

  spacing: {
    paddingX: 1 as const,
    paddingY: 0 as const,
    marginX: 1 as const,
    marginY: 0 as const,
    toolIndent: 2 as const,     // Indent for inline tool calls
  },

  layout: {
    statsBarHeight: 1 as const,
    statsPanelWidth: 30 as const,
    inputBarHeight: 3 as const,
    maxMessageLines: 200,       // Max content lines before truncation
    inputHistorySize: 50,
    processingCycleIntervalMs: 500,
    backendHealthCheckMs: 2000,
  },

  icons: {
    connected: '○',
    processing: '◆',
    disconnected: '✗',
    toolRunning: '⠋',            // Spinner frame (will cycle)
    toolCompleted: '✓',
    toolError: '✗',
    error: '⚠',
    cursor: '>',
  },

  // Processing placeholder animation frames
  processingFrames: [
    'Thinking',
    'Thinking.',
    'Thinking..',
    'Thinking...',
  ],
} as const;
```

**Design token usage rules:**
- All colors are applied via Ink `color` and `backgroundColor` props on `<Box>` and `<Text>`
- No CSS files, no style objects — Ink uses JSX props only
- Token file is the single source of truth for all visual constants
- Components import from `theme.ts`, never hardcode values

---

## Appendix: Phase 9 Component Tree

```
App.tsx
├── StatsBar                          [1 row, always visible]
│   ├── connection status indicator
│   └── session name label
├── ErrorBar                          [conditional, dismissable]
│   ├── error icon + message
│   └── dismiss hint
├── [horizontal split, flexGrow=1]
│   ├── ConversationScreen            [flexGrow=1, scrollable]
│   │   ├── (empty state notice)
│   │   ├── MessageCard.user[]
│   │   ├── MessageCard.assistant[]
│   │   ├── MessageCard.streaming     [while streamedContent !== '']
│   │   └── ToolCallIndicator[]       [active tool calls]
│   └── StatsPanel                    [fixed 30 cols]
│       ├── Session name
│       ├── Token count
│       ├── Last response time
│       ├── Model name
│       └── Date/time (live clock)
└── [bottom bar, height=3]
    ├── ToolCallIndicator             [compact inline, if active]
    └── InputBar                      [3 rows]
        ├── Text input field
        ├── Placeholder (idle/processing)
        └── History navigation

SessionPicker (overlay, replaces App content):
└── SessionPicker
    ├── Title: "Session Manager"
    ├── Session list (scrollable)
    │   ├── "+ New Session" item
    │   └── Session entries [id, title]
    └── Keyboard hint bar
```

---

*Phase: 09-ts-tui-json-rpc*
*Created: 2026-07-27*
*Status: Draft*
