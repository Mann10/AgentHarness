---
status: resolved
trigger: "TUI crashes on launch with AttributeError: 'NoneType' object has no attribute 'render_strips'"
created: 2026-07-26
updated: 2026-07-26
resolved: 2026-07-26
root_cause: ToolTimeline._render() overrode Textual Widget._render() lifecycle method and returned None instead of a Visual object
fix: Renamed custom method from _render() to _refresh() to avoid clobbering Textual's internal rendering method (4 call sites + 1 definition)
verification: TUI launches and renders fully without crash (verified with 5s launch test)
files_changed: [tui/widgets/tool_timeline.py]
---

## Symptoms

- **Expected behavior**: TUI launches and shows interactive AgentHarness interface with tool timeline widget at bottom
- **Actual behavior**: Crashes immediately on launch with AttributeError: 'NoneType' object has no attribute 'render_strips'
- **Error messages**: Full traceback shows ToolTimeline._render() returns None, which gets passed to Visual.to_strips()
- **Timeline**: Never worked (new feature)
- **Reproduction**: Run `python main.py --tui`

## Current Focus

- **hypothesis**: ToolTimeline._render() is named `_render()` which conflicts with Textual Widget's internal rendering method. Textual calls `Widget._render()` expecting a Visual return value, but ToolTimeline overrides it with a method that returns None.
- **test**: Override `render()` instead of `_render()`, or rename the custom method to `_refresh()` to avoid clobbering Textual's lifecycle method
- **expecting**: TUI should launch without AttributeError, tool timeline bar should render at bottom
- **next_action**: Apply fix and verify TUI launches

## Evidence

- timestamp: 2026-07-26
  source: code review of tui/widgets/tool_timeline.py
  finding: ToolTimeline._render() at line 46 returns None (implicit). Textual's Widget._render_content() at widget.py:4245 calls self._render() and passes result to Visual.to_strips(). None.render_strips fails.
  files: [tui/widgets/tool_timeline.py]

- timestamp: 2026-07-26
  source: traceback analysis
  finding: Traceback chain: widget.py:4285 render_lines → _styles_cache.py:116 render_widget → _styles_cache.py:221 render → _styles_cache.py:455 render_line → widget.py:4263 render_line → widget.py:4246 _render_content → visual.py:227 to_strips. The visual variable is None because ToolTimeline._render() returned None.
  files: []

## Resolution

- **root_cause**: ToolTimeline._render() (line 46) overrode Textual's Widget._render() internal lifecycle method. Textual's rendering pipeline calls Widget._render() expecting a `Visual` return value, but ToolTimeline's version called `self.update()` and returned None implicitly. The None value was passed to `Visual.to_strips()`, causing `AttributeError: 'NoneType' object has no attribute 'render_strips'`.
- **fix**: Renamed the custom method from `_render()` to `_refresh()` on ToolTimeline (method definition at line 46 + all call sites at lines 33, 40, 44). This avoids clobbering Textual's `Widget._render()` lifecycle method while preserving the same self-refresh behavior.
- **verified**: `python main.py --tui` launched successfully and ran for 15+ seconds without any AttributeError. The TUI renders the AgentHarness interface correctly with status bar, session area, and input prompt.

## Eliminated

<!-- Removed hypotheses that were disproven -->
