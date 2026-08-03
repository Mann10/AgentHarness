# UI-SPEC: Rich Textual TUI

**Phase:** 6
**Date:** 2026-07-26
**Status:** Draft

---

## 1. Layout

```
┌─ Header ──────────────────────────────────────────────────────┐
│ SessionName  │ Tokens: 4,231/8,192  │ Status: ● PROCESSING    │
├────────────────────────────────┬──────────────────────────────┤
│                                │                              │
│  ConversationView (2fr)        │  JobQueueSidebar (1fr)       │
│                                │                              │
│  ┌── MessageCard (user) ──┐   │  ┌─────────────────────────┐ │
│  │ > What's in this dir?  │   │  │ ● job3  COMPLETE 2m ago │ │
│  └────────────────────────┘   │  │ ◉ job2  ACTIVE    now   │ │
│                                │  │ ○ job1  PENDING         │ │
│  ┌── MessageCard (assistant) ┐ │  │ ○ job4  PENDING         │ │
│  │ Let me check...           │ │  │                          │ │
│  │                           │ │  │  Quick stats:            │ │
│  │  ┌── ToolCallCard ──────┐ │ │  │  Pending: 2              │ │
│  │  │ ▶ read_file          │ │ │  │  Active: 1               │ │
│  │  │ args: {path: ...}    │ │ │  │  Done:   1               │ │
│  │  │ result: "import..."  │ │ │  └─────────────────────────┘ │
│  │  └──────────────────────┘ │ │                              │
│  │                           │ │                              │
│  │ Here are the files:       │ │                              │
│  │ - main.py                 │ │                              │
│  └───────────────────────────┘ │                              │
│                                │                              │
├──────── ToolTimeline ──────────┴──────────────────────────────┤
│  read_file ✓  grep ✓  write_file ✓                   3 calls │
├───────────────────────────────────────────────────────────────┤
│ > Type a prompt...                                        [↩] │
└───────────────────────────────────────────────────────────────┘
```

## 2. Component Tree

```
App
├── Header (Textual Header, clock shown)
├── Horizontal
│   ├── ConversationView (VerticalScroll, id="conversation-panel", 2fr)
│   │   └── Dynamic list of:
│   │       ├── MessageCard (user)      — "> prompt text"
│   │       ├── MessageCard (assistant)  — Markdown(content)
│   │       └── ToolCallCard            — Collapsible card
│   └── JobQueueSidebar (VerticalScroll, id="sidebar-panel", 1fr)
│       └── Dynamic list of JobRow widgets
├── ToolTimeline (Horizontal, id="tool-timeline", dock=bottom)
│   └── Dynamic list of ToolChip widgets
├── InputBar (dock=bottom, id="input-bar", height=3)
└── StatusBar (dock=bottom)
```

## 3. Widget Specifications

### 3.1 ConversationView
- **File:** `tui/widgets/conversation_view.py`
- **Type:** `VerticalScroll`
- **Children:** `MessageCard`, `ToolCallCard`
- **Behavior:**
  - `add_user_message(content)` — appends user `MessageCard`
  - `add_assistant_message(content)` — appends assistant `MessageCard` (Markdown-rendered)
  - `add_tool_call(id, name, args)` — appends `ToolCallCard` (collapsed)
  - `update_tool_result(id, result)` — finds `ToolCallCard` by `id`, sets result, recolors
  - `add_error(error)` — appends red assistant card with error
  - `add_notice(text)` — appends dimmed system notice
  - Auto-scroll to bottom on mount and on new children added
  - Clears on `/new` session

### 3.2 MessageCard
- **File:** `tui/widgets/message_card.py`
- **Type:** `Static` with `Rich` renderable
- **Variants:**
  - **User:** prefix `>` in dimmed color, single line (truncated at 200 chars)
  - **Assistant:** full text rendered via `rich.markdown.Markdown` with syntax-highlighted code blocks
  - **Error:** red border `Panel`, error text
  - **Notice:** italics, dimmed
- **Styling:**
  - Margin: (0, 0, 0, 1) left, (0, 0, 1, 0) bottom
  - Assistant messages get a subtle left border (`║`) via Rich markup

### 3.3 ToolCallCard
- **File:** `tui/widgets/tool_call_card.py`
- **Type:** `Static` with `Rich` `Panel` renderable
- **States:**
  - **Pending:** blue border, spinner indicator, "waiting for result..."
  - **Success:** green border, checkmark, result preview (first 500 chars)
  - **Error:** red border, X icon, error message
- **Interaction:**
  - Click to toggle collapse/expand
  - Collapsed: single line — `▶ tool_name` or `▼ tool_name ✓`
  - Expanded: full args (rendered as `syntax-highlighted JSON`) + result (rendered as text)
- **Correlation:** Matched to `ToolCallEvent`/`ToolResultEvent` via `tool_call_id`

### 3.4 JobQueueSidebar
- **File:** `tui/widgets/job_queue_sidebar.py`
- **Type:** `VerticalScroll`
- **Children:** `JobRow` (Static)
- **Each row:**
  - Status dot: `●` green=complete, `◉` blue=processing, `○` dim=pending, `●` red=failed
  - Prompt preview (50 chars max)
  - Age (2m ago, just now, etc.)
  - Priority badge (high=red, normal=none, low=dim)
- **Interaction:**
  - Click to focus that job in conversation (shows its messages)
  - Selected row highlighted
- **Header:** "Jobs" with counts summary
- Auto-refreshes from `QueueManager` periodically

### 3.5 ToolTimeline
- **File:** `tui/widgets/tool_timeline.py`
- **Type:** `Static` (single-line Rich renderable)
- **Content:** Horizontal list of tool chips
  - Each chip: `name status_icon` — e.g., `read_file ✓`, `search_web ○`
  - Colors match tool call card states
  - Max 10 visible, overflow shows "+N more"
  - Cleared when a `ResponseComplete` fires (turn is done)

### 3.6 StatusBar (enhanced)
- **File:** `tui/widgets/status_bar.py` (modify existing)
- **Content (pipe-separated):**
  - Session name (truncated to 20 chars)
  - Token count: `4,231 / 8,192`
  - Processing spinner: `◐◓◑◒` (animated, frame on refresh)
  - Queue depth: `Queue: 3`
  - Tool progress: `tool 2/5` (when processing)
  - Last result preview (existing)

### 3.7 InputBar (enhanced)
- **File:** `tui/widgets/input_bar.py` (modify existing)
- **Features:**
  - Command history (up/down arrow navigation)
  - `/` command autocomplete (popup suggestions for /sessions, /new, /resume, /title)
  - Non-blocking submit (already implemented)
  - Character count on right side
  - Placeholder varies: "Type a prompt..." or "Type / for commands"

## 4. Screen Specifications

### 4.1 SessionPicker (modal)
- **File:** `tui/screens/session_picker.py`
- **Type:** `Screen` with overlay
- **Content:**
  - List of sessions: `[icon] title  msgs:12  2h ago`
  - Icon: `●`=active, `○`=inactive
- **Actions:**
  - `Enter` — resume selected session
  - `n` — create new session
  - `r` — rename selected session
  - `d` — delete selected session (confirmation)
  - `Esc` — close modal
- **Data source:** `RuntimeAPI.list_sessions()`

## 5. Event Wiring

| Event | Handler | UI Action |
|---|---|---|
| `TurnStarted` | `_on_turn_started` | `conversation.add_user_message(prompt)`, `sidebar.update_job_status(processing)`, `status.update_processing(True)`, `status.set_tool_progress(0, 0)` |
| `ToolCallEvent` | `_on_tool_call` | `conversation.add_tool_call(id, name, args)`, `timeline.add_chip(name, "pending")`, `status.set_tool_progress(current, total)` |
| `ToolResultEvent` | `_on_tool_result` | `conversation.update_tool_result(id, result)`, `timeline.update_chip(id, "done")` |
| `ResponseComplete` | `_on_response_complete` | `conversation.add_assistant_message(content)` (Markdown), `sidebar.update_job_status(complete)`, `timeline.clear()`, `status.update_processing(False)`, `status.update_last_result(content)` |
| `ErrorEvent` | `_on_error` | `conversation.add_error(error)`, `sidebar.update_job_status(failed)`, `timeline.update_chip(id, "error")`, `status.update_processing(False)` |
| `CancelledEvent` | `_on_cancelled` | `conversation.add_notice("Cancelled")`, `timeline.clear()`, `status.update_processing(False)` |

## 6. Events Changes

### ToolCallEvent (add field)
```python
@dataclass
class ToolCallEvent(HarnessEvent):
    session_id: str = ""
    tool_name: str = ""
    arguments: dict | None = None
    tool_call_id: str = ""  # NEW — correlates call → result
```

### ToolResultEvent (add field)
```python
@dataclass
class ToolResultEvent(HarnessEvent):
    session_id: str = ""
    tool_name: str = ""
    result: str = ""
    tool_call_id: str = ""  # NEW — correlates result → call
```

### Agent (pass id)
In `agent/core.py`, pass `tc.id` when emitting both `ToolCallEvent` and `ToolResultEvent`.

## 7. Color Palette

| Role | Color |
|---|---|
| User message | `#565f89` (dimmed text) |
| Assistant message | `#a9b1d6` (bright text) |
| Tool call pending | `#7aa2f7` (blue) |
| Tool call success | `#9ece6a` (green) |
| Tool call error | `#f7768e` (red) |
| Error text | `#db4b4b` (bright red) |
| Notice | `#565f89` (dimmed) |
| Status active | `#7dcfff` (cyan) |
| Status idle | `#565f89` (dimmed) |
| Selected row | `#3b4261` (highlight bg) |

## 8. Phasing

The work is split into 3 waves:

### Wave 1 — Data plumbing + conversation (Plan 06-01)
1. Add `tool_call_id` to events + agent emission
2. Build `MessageCard`
3. Build `ToolCallCard`
4. Build `ConversationView`
5. Wire into `app.py` with new CSS layout

### Wave 2 — Sidebar + timeline + bars (Plan 06-02)
1. Build `JobQueueSidebar`
2. Build `ToolTimeline`
3. Enhance `StatusBar`
4. Enhance `InputBar`
5. Wire all into `app.py`

### Wave 3 — Session picker + cleanup (Plan 06-03)
1. Build `SessionPicker` screen
2. Remove old `JobGrid` and `ResultScreen`
3. Update `__init__` exports
4. Manual testing and edge case polish
