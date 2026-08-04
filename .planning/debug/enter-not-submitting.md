---
status: resolving
trigger: "Debug why pressing Enter in the InputBar doesn't submit"
created: 2026-07-26
updated: 2026-07-26
---

## Current Focus

hypothesis: InputBar.action_submit() is synchronous but calls super().action_submit() which is async, so the coroutine is silently discarded and the Submitted message is never posted.
test: Made action_submit async with await super().action_submit(). Verified via Pilot test: [on_submit] Received Submit! fires, input clears, history populated.
expecting: Fixed
next_action: Return findings report

## Symptoms

expected: Typing text and pressing Enter submits the prompt, clears the input, and shows a processing indicator.
actual: Text stays in the input field, no processing indicator appears, nothing happens.
errors: RuntimeWarning: coroutine 'Input.action_submit' was never awaited (visible in stderr)
reproduction: python main.py --tui → type text → press Enter

## Eliminated

- hypothesis: InputBar.on_key() blocks Enter key
  evidence: Test shows on_key does NOT stop non-up/down keys; stopped=False after Enter. Binding system resolves independently from on_key handler.
  timestamp: 2026-07-26

- hypothesis: Binding chain doesn't find the enter→submit binding
  evidence: Test shows action_submit IS called (history is populated, "[action_submit] called with value='hello'" printed). The issue is that action_submit fails to post the Submitted message.
  timestamp: 2026-07-26

## Evidence

- timestamp: 2026-07-26
  checked: Test pressing Enter in InputBar with synchronous action_submit
  found: action_submit called but super().action_submit() returns coroutine without await; RuntimeWarning: coroutine 'Input.action_submit' was never awaited
  implication: The async Input.action_submit() is never executed, so Submitted message is never posted.

- timestamp: 2026-07-26
  checked: Test with async await fix
  found: [on_submit] Received Submit! fires, input clears, history populated
  implication: The async/await mismatch is the root cause.

## Resolution

root_cause: InputBar.action_submit() is defined as a synchronous method (def action_submit(self) -> None) but Input.action_submit() (the parent) is async. Calling super().action_submit() without await returns an unawaited coroutine that is silently discarded, so self.post_message(self.Submitted(...)) is never executed.

fix: Change InputBar.action_submit() to async def action_submit(self) -> None and use await super().action_submit().
verification: Pilot test confirms Submitted message fires after fix.
files_changed:
  - tui/widgets/input_bar.py: line 77 — change def to async def, add await before super().action_submit()
