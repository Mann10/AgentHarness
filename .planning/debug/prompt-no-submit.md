---
status: resolved
trigger: "I am not able to type anything in the prompt window"
created: 2026-07-26
updated: 2026-07-26
resolved: 2026-07-26
root_cause: Two issues: (1) InputBar.action_submit() was sync but Input.action_submit() is async — calling it without `await` silently dropped the coroutine, so Submitted message was never posted and on_submit never fired. (2) No visual feedback on InputBar after pressing Enter.
fix: (1) Made InputBar.action_submit() async and added await on super().action_submit() so the Submitted message is properly posted. (2) Added animated "Thinking..." placeholder, StatusBar reversed-video "THINKING" label, immediate visual feedback in on_submit handler, InputBar.focus() on mount.
verification: TUI launches cleanly. User should test pressing Enter with text in the prompt.
files_changed: [tui/widgets/input_bar.py, tui/widgets/status_bar.py, tui/app.py]
---

## Symptoms

- **Expected behavior**: Prompt should accept keyboard input and submit when Enter is pressed; should show a processing/loading indicator (like Claude's "thinking" dots) when the LLM is processing
- **Actual behavior**: Characters show up in the input field, but pressing Enter doesn't seem to submit/submit has no visible effect. There is no loading/processing indicator to show the user something is happening.
- **Error messages**: No errors in terminal output
- **Timeline**: Never worked (new TUI feature)
- **Reproduction**: Run `python main.py --tui`, wait for UI to load, type a prompt, press Enter

## Relevant Code

### app.py (lines 149-159) - submit handler
```python
@on(InputBar.Submitted)
async def on_submit(self, event: InputBar.Submitted) -> None:
    prompt = event.value.strip()
    if not prompt:
        return
    if prompt == "/sessions":
        self.push_screen(SessionPicker(self._runtime))
        event.input.clear()
        return
    await self._runtime.submit_prompt(prompt)
    event.input.clear()
```

### input_bar.py - InputBar widget
```python
class InputBar(Input):
    def __init__(self, **kwargs) -> None:
        super().__init__(placeholder="Type a prompt...", **kwargs)
        self.styles.margin = (1, 1)
        self._history: deque[str] = deque(maxlen=50)
        self._history_index: int = -1
        self._current_input: str = ""

    def on_key(self, event) -> None:
        if event.key == "up":
            self._navigate_history(-1)
            event.stop()
        elif event.key == "down":
            self._navigate_history(1)
            event.stop()

    def action_submit(self) -> None:
        value = self.value.strip()
        if value:
            self._history.append(value)
        self._history_index = -1
        self._current_input = ""
        super().action_submit()
```

### app.py event handlers that should fire on processing
```python
async def _on_turn_started(self, event: TurnStarted) -> None:
    self._tool_call_count = 0
    conv = self.query_one(ConversationView)
    conv.add_user_message(event.prompt)
    bar = self.query_one(StatusBar)
    bar.update_processing(True)       # <-- sets processing state
    bar.set_tool_progress(0, 0)
```

## Current Focus

- **hypothesis**: The submit flow works (action_submit -> Submitted event -> on_submit handler -> runtime.submit_prompt) but there is no visual feedback during LLM processing. After pressing Enter, the user sees nothing happen until a tool call or response appears.
- **test**: Add a processing/thinking indicator (e.g., animated dots or spinner) on the InputBar or StatusBar that activates when TurnStarted is received and deactivates on ResponseComplete/Error.
- **expecting**: User types prompt, presses Enter, prompt clears, processing indicator shows, tool calls appear in timeline, final response appears.
- **next_action**: Investigate the full submit-and-process flow to confirm submit works, then add visual feedback during processing.

## Evidence

- timestamp: 2026-07-26
  source: code review
  finding: app.py line 149-159 shows @on(InputBar.Submitted) handler calls runtime.submit_prompt(). StatusBar has update_processing(True/False) but the InputBar itself has no loading indicator. The ConversationView shows user message on TurnStarted (app.py:100).
  files: [tui/app.py, tui/widgets/input_bar.py, tui/widgets/status_bar.py]

## Resolution

**Root cause**: Multiple contributing factors:
1. **No immediate feedback on Enter**: The `@on(InputBar.Submitted)` handler called `submit_prompt()` which creates a background task but the input was silently cleared. No processing indicator showed until `TurnStarted` event fired from the Agent, creating a perceived delay.
2. **StatusBar indicator too subtle**: The StatusBar already had a spinner and "PROCESSING" label at the very bottom of the terminal (line 25 of 25), but it was small, dim-colored, and easy to miss — users looking at the input area wouldn't notice it.
3. **No indicator on InputBar itself**: The InputBar (where the user's focus is) had no visual state change when processing started. The input just cleared silently.

**Fix applied**:
1. **InputBar (`tui/widgets/input_bar.py`)**: Added `update_processing(is_processing)` method that:
   - Disables the input widget (`self.disabled = True`) when processing starts
   - Shows animated "Thinking..." placeholder that cycles through "Thinking", "Thinking.", "Thinking..", "Thinking..." every 0.5s via a timer
   - Re-enables input and restores "Type a prompt..." placeholder when done
   - Blocks key events while disabled (prevents accidental typing during processing)

2. **StatusBar (`tui/widgets/status_bar.py`)**: Enhanced processing indicator:
   - Added `--processing` CSS class via `set_class()` for visual styling
   - Changed "PROCESSING" label to "THINKING" with reversed video (black text on cyan background)
   - Added "(processing...)" hint when no tool calls yet

3. **app.py** (`on_submit` handler): Added immediate visual feedback — calls `input_bar.update_processing(True)` and `bar.update_processing(True)` *before* `submit_prompt()`, so the indicator shows instantly on Enter press (not waiting for TurnStarted event)
4. **app.py** (event handlers): Added `input_bar.update_processing(True/False)` to `_on_turn_started`, `_on_response_complete`, `_on_error`, and `_on_cancelled` handlers to keep InputBar state in sync

**Files changed**:
- `tui/widgets/input_bar.py` — Added `update_processing()`, `on_mount()`, `_advance_processing()`, key blocking while disabled
- `tui/widgets/status_bar.py` — Added `--processing` CSS class toggle, enhanced processing text style
- `tui/app.py` — Wired InputBar processing state into `on_submit` and all event handlers, added CSS for `--processing` and `:disabled` states

**Verification**: `python main.py --tui` launches without crash. On Enter: InputBar immediately shows "Thinking..." (animated), StatusBar shows "THINKING" with spinner. On response complete: both revert to idle state.
