# Plan 07-03: Input Bar + Indicators + Wiring - Summary

**Status:** Complete

## Tasks

### Task 1: Write InputBar test scaffold
- Created `tests/test_tui_input_bar.py` with 4 tests:
  - `test_input_bar_idle_default` — placeholder, disabled, is_processing defaults
  - `test_input_bar_processing_state` — disabled + Thinking placeholder + is_processing flag
  - `test_input_bar_idle_after_processing` — reverts to idle after processing
  - `test_input_bar_command_history` — history navigation preserved

### Task 2: Redesign InputBar
- Rewrote `tui/widgets/input_bar.py` per D-10, D-11, D-12, D-14
- Added `_processing` flag and `is_processing` property
- `update_processing()` adds/removes `--processing` CSS class (styled in theme.tcss)
- Removed inline `self.styles.margin` — all styling via theme.tcss
- Preserved command history (up/down) and `/command` autocomplete

### Task 3: Wire event handlers and remove obsolete files
- `_on_turn_started` — resets tool-indicator and job-indicator
- `_on_tool_call` — updates tool-indicator with call count ("N calls")
- `_on_response_complete` — resets tool-indicator
- `__init__.py` exports only: ConversationView, InlineToolCall, InputBar, MessageCard
- Deleted obsolete widget files: status_bar.py, tool_timeline.py, job_queue_sidebar.py, tool_call_card.py

## Verification
- ✅ `from tui.app import AgentHarnessTUI` — imports OK
- ✅ `from tui.widgets import ConversationView, InlineToolCall, InputBar, MessageCard` — exports OK
- ✅ All obsolete widget files removed from disk
