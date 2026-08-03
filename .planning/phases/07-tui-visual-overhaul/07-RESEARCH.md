# Phase 7: TUI Visual Overhaul - Research

**Researched:** 2026-07-27
**Domain:** Textual-based Python TUI visual redesign (Claude Code aesthetic)
**Confidence:** HIGH

## Summary

This phase transforms the existing functional-but-minimal Phase 6 Textual TUI into a professional-grade, Claude Code-inspired terminal interface. Research confirms that Textual 8.2.8 (installed, latest stable) provides all the CSS theming, animation, and rendering capabilities needed to achieve the Claude Code aesthetic without requiring additional dependencies.

**Claude Code's terminal aesthetic** is characterized by: warm dark backgrounds (`#181715`), cream-white body text (`#faf9f5`), coral primary accents (`#cc785c`), teal secondary accents (`#5db8a6`), subtle borders using box-drawing characters, inline tool calls within the message stream (collapsible), and a clean bottom-to-top layout with separator lines and minimal chrome. The polished feel comes from semantic color usage, intentional whitespace, and subtle visual hierarchy — not heavy decoration.

**Textual 8.2.8** supports: a full `Theme` dataclass system with 11 base colors and auto-generated shades, 20 border types (including `solid`, `round`, `tall`, `panel`, `heavy`), CSS transitions, programmatic animations with easing functions, pseudo-class selectors (`:focus`, `:disabled`, `:hover`, `:dark`), component classes for sub-widget CSS targeting, and scrollbar customization. All CSS styling can be done in an external `.tcss` file with live-reload via `textual-dev`.

**Primary recommendation:** Create a custom Textual `Theme` with a Claude Code-inspired palette, restyle all widgets via a single `.tcss` file, remove `StatusBar` and `JobQueueSidebar` widgets, redesign `InputBar` with processing state indicators, and create an `InlineToolCall` widget (replacing `ToolCallCard`) that renders as a compact, expandable component within the message stream.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Claude Code-inspired dark theme — clean dark backgrounds, subtle borders, high-contrast text, minimal chrome
- **D-02:** Drop Tokyo Night palette from UI-SPEC.md; adopt a new palette similar to Claude Code's dark theme (deep grays, clean white text, subtle accent colors for states)
- **D-03:** Consistent spacing, typography, and border treatment across all widgets
- **D-04:** Minimal layout — no persistent sidebar (remove JobQueueSidebar as permanent fixture)
- **D-05:** Conversation panel takes full width
- **D-06:** Bottom area reserved for input bar + compact indicators only
- **D-07:** Inline tool calls in message stream — tool calls render as compact inline entries within assistant messages, not separate ToolCallCard widgets
- **D-08:** Expandable inline entries for tool calls with large args/results
- **D-09:** Remove ToolCallCard as separate widget; integrate tool call display into message flow
- **D-10:** Claude Code-style minimal input — clean single-line, no extra chrome
- **D-11:** Visual state changes for idle vs processing (placeholder, color, disable state)
- **D-12:** Keep existing command history (up/down navigation) and /command autocomplete
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

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within TUI visual overhaul scope
</user_constraints>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Claude Code-inspired dark theme | Claude palette identified: warm dark bg `#181715`, cream text `#faf9f5`, coral `#cc785c`, teal `#5db8a6` [CITED: blog.vincentqiao.com, github.com/cameronsjo theme reference] |
| D-02 | Drop Tokyo Night, adopt new palette | Textual Theme system supports full custom palette; Theme dataclass with 11 base colors [VERIFIED: textual.textualize.io/guide/design/, textual.__version__ = 8.2.8] |
| D-04 | Remove persistent sidebar | Textual layout using Horizontal with width fractions; removing a widget from compose() reflows automatically |
| D-07 | Inline tool calls in message stream | Textual Static subclass widgets can be mounted as children of VerticalScroll; reactive attributes support collapse/expand [VERIFIED: textual.textualize.io/guide/widgets/] |
| D-10 | Claude Code-style minimal input | Textual Input widget supports placeholder, disabled state, CSS pseudoclasses; can be restyled without subclass changes |
| D-13 | Remove StatusBar widget | All StatusBar state can migrate to InputBar (placeholder text, tool + job count) and inline indicators |
| D-15 | Compact tool timeline + job indicators | InputBar can host child Static widgets for tool count and job count via compose() or mount() |

## Architectural Responsibility Map

This phase is a pure frontend/TUI redesign — no backend, database, or API changes.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Theme & color system | TUI App | — | Entirely within Textual's Theme and CSS system; no server involvement |
| Layout & widget composition | TUI App | — | Compose tree in app.py, CSS in .tcss file; pure client-side |
| Message rendering (Markdown) | TUI Widgets | Rich library | MessageCard uses Rich's Markdown renderer; no server changes |
| Inline tool call rendering | TUI Widgets | — | New InlineToolCall widget replaces ToolCallCard; within TUI layer |
| Input bar with state | TUI Widgets | — | InputBar subclass with processing states, embedded indicators |
| Tool timeline + job counter | TUI Widgets | InputBar | Compact indicators embedded in InputBar area, not separate widgets |
| Event wiring | TUI App | EventBus | Event subscription pattern unchanged from Phase 6 |
| Session management | Harness layer | — | No changes needed — RuntimeAPI remains data source |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Textual | 8.2.8 | Terminal UI framework | Installed, latest stable. Provides CSS, Theme, animation, all widget primitives needed. [VERIFIED: pip show textual] |
| Rich | 15.0.0 | Terminal rendering (Markdown, Syntax, Panel, Text) | Installed, used by Phase 6. Textual's rendering backend. [VERIFIED: pip show rich] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| textual-dev | (optional) | CSS live-reload, devtools | During development only — provides `textual run --dev` for hot-reload |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Textual Theme | Inline `.styles` assignments per widget | Theme provides centralized color management and runtime switching. Inline is brittle. |
| External `.tcss` file | Inline `CSS` classvar | External file supports live-reload via `textual-dev` and separates concerns |

**Installation:**
```bash
# Already installed:
# textual==8.2.8, rich==15.0.0

# Optional for development:
pip install textual-dev
```

**Version verification:**
```bash
pip show textual
# Version: 8.2.8 (2026-07-27 confirmed)
```

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  AgentHarnessTUI (App)                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  CSS (theme.tcss) ← custom Theme ─── Theme registry   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─ Screen ─────────────────────────────────────────────┐  │
│  │                                                      │  │
│  │  ┌─ #conversation-panel (VerticalScroll) ──────────┐ │  │
│  │  │  ┌─ MessageCard.user("> prompt") ──────────┐    │ │  │
│  │  │  │  prefix: "> " in muted color             │    │ │  │
│  │  │  └──────────────────────────────────────────┘    │ │  │
│  │  │  ┌─ MessageCard.assistant(markdown) ───────┐    │ │  │
│  │  │  │  Rich Markdown → code_theme="monokai"    │    │ │  │
│  │  │  └──────────────────────────────────────────┘    │ │  │
│  │  │  ┌─ InlineToolCall(tool_name, args) ───────┐    │ │  │
│  │  │  │  "Tool: read_file ○ running..."          │    │ │  │
│  │  │  │  [click to expand args/result]           │    │ │  │
│  │  │  └──────────────────────────────────────────┘    │ │  │
│  │  └──────────────────────────────────────────────────┘ │  │
│  │                                                      │  │
│  │  ┌─ #bottom-bar (Horizontal) ───────────────────────┐ │  │
│  │  │  ┌─ #tool-indicator ─┐ ┌─ #job-indicator ─┐    │ │  │
│  │  │  │  "3 calls"        │ │  "Jobs: 2"       │    │ │  │
│  │  │  └───────────────────┘ └───────────────────┘    │ │  │
│  │  │  ┌─ #input-bar (Input) ───────────────────────┐ │ │  │
│  │  │  │  "Thinking..." (processing) / ">" (idle)   │ │ │  │
│  │  │  └────────────────────────────────────────────┘ │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Event Bus ← RuntimeAPI (unchanged)                         │
│  TurnStarted → add_user_message + set_processing             │
│  ToolCallEvent → add_tool_call + update_indicator            │
│  ToolResultEvent → update_tool_result + update_indicator     │
│  ResponseComplete → add_assistant_message + set_idle         │
└─────────────────────────────────────────────────────────────┘
```

**Data flow:** User input → InputBar.Submitted → RuntimeAPI.submit_prompt() → EventBus events → Widget updates (conversation, indicators). All widget state changes are reactive, triggered by event handlers in the App class.

### Recommended Project Structure
```
tui/
├── app.py                    # App class with compose, events, theme registration
├── theme.tcss                # External CSS file for all styling
└── widgets/
    ├── __init__.py
    ├── conversation_view.py  # VerticalScroll wrapper for message list (keep + enhance)
    ├── message_card.py       # Message variants (user, assistant, error, notice)
    ├── inline_tool_call.py   # NEW: replaces ToolCallCard with compact inline rendering
    ├── input_bar.py          # Redesigned: processing state, tool/job indicators embedded
    └── (removed)             # StatusBar, ToolTimeline, JobQueueSidebar, ToolCallCard
```

### Pattern 1: Custom Textual Theme Registration
**What:** Create and register a Theme object with Claude Code-inspired colors.
**When to use:** App startup, before any widgets mount.
**Example:**
```python
# In app.py on_mount()
from textual.theme import Theme

claude_theme = Theme(
    name="claude-code",
    primary="#cc785c",        # Coral accent
    secondary="#5db8a6",      # Teal accent
    accent="#cc785c",
    warning="#e8a55a",        # Amber
    error="#ff6b80",          # Soft red
    success="#4eba65",        # Green
    foreground="#faf9f5",     # Cream white text
    background="#181715",     # Warm dark background
    surface="#1f1e1b",        # Elevated surface
    panel="#252320",          # Panel background
    dark=True,
    variables={
        "block-cursor-foreground": "#faf9f5",
        "input-selection-background": "#cc785c40",
    },
)
self.register_theme(claude_theme)
self.theme = "claude-code"
```
[CITED: textual.textualize.io/guide/design/, VERIFIED: textual.theme.Theme API]

### Pattern 2: Inline Tool Call Widget with Collapse/Expand
**What:** A Static subclass that shows a compact one-line tool call summary by default, expanding to show args/result on click.
**When to use:** Replacing ToolCallCard per D-07, D-08.
**Example:**
```python
class InlineToolCall(Static):
    """Compact inline tool call within message stream. Click to expand/collapse."""
    
    _collapsed = reactive(True, always_update=True)
    
    def __init__(self, tool_call_id: str, name: str, args: dict) -> None:
        self._tool_call_id = tool_call_id
        self._name = name
        self._args = args
        self._result: str | None = None
        self._error: str | None = None
        super().__init__()
        self._render_content()
    
    def on_click(self) -> None:
        self._collapsed = not self._collapsed
    
    def watch__collapsed(self) -> None:
        self._render_content()
    
    def _render_content(self) -> None:
        if self._collapsed:
            # Compact: "● read_file  ✓" or "○ read_file  (running...)"
            status_icon = "✓" if self._result else ("✗" if self._error else "○")
            status_color = "green" if self._result else ("red" if self._error else "blue")
            self.update(f"[{status_color}]{status_icon}[/] {self._name}")
        else:
            # Expanded: show args (Syntax highlighted), result
            from rich.syntax import Syntax
            from rich.text import Text
            args_syntax = Syntax(json.dumps(self._args, indent=2), "json", theme="monokai")
            self.update(args_syntax)  # or Panel for visual grouping
```

### Anti-Patterns to Avoid
- **Over-styling with heavy borders:** Claude Code uses subtle, thin borders. Avoid `heavy` or `tall` border styles on message cards. Use `solid` with muted colors or `none`.
- **Mixing theme systems:** Don't set individual `.styles.background` on widgets if a CSS variable from the Theme would work. Stick to one source of truth (CSS variables → .tcss file).
- **Retaining Tokyo Night colors:** Search for all `#565f89`, `#7dcfff`, `#9ece6a`, `#f7768e`, `#7aa2f7` references and replace them with the new palette values.
- **Nesting too many containers:** Claude Code uses flat layout with minimal DOM depth. Avoid unnecessary `Container` or `Horizontal` wrappers.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Color system | Custom color management | Textual Theme + CSS variables | Theme auto-generates shades, guarantees contrast, supports runtime switching |
| Markdown rendering | Custom markdown parser | Rich Markdown via MessageCard | Rich 15.0.0 provides comprehensive markdown rendering with syntax highlighting |
| Animation framework | Timer-based manual animation | Textual `animate()` + CSS transitions | Built-in animator with easing functions, auto-refresh, on_complete callbacks |
| Scrollable message container | Custom scrolling logic | `VerticalScroll` widget | Built-in scrollbar, scroll_end(), keyboard navigation, mouse wheel support |
| Input with history | Full input system from scratch | `Input` widget subclass | Validation, placeholder, disabled state, cursor control, `-invalid`/`-valid` CSS classes |

**Key insight:** Textual 8.x has matured significantly. Nearly every UI primitive needed (themes, animations, CSS transitions, scrollable containers, input with validation) is built-in. The redesign should be primarily CSS changes + one new widget class (`InlineToolCall`), not a rewrite.

## Common Pitfalls

### Pitfall 1: CSS Transition Only Works on Class Changes
**What goes wrong:** Developers set CSS `transition` rules expecting them to animate programmatic `.styles.background = "red"` changes, but transitions only animate changes triggered by CSS class toggles.
**Why it happens:** Textual's CSS `transition` property only applies when CSS selectors change (e.g., adding/removing a class). Programmatic style changes use the `animate()` method instead.
**How to avoid:** Use `widget.styles.animate("opacity", value=0.0, duration=2.0)` for programmatic animations. Use CSS `transition` for class-based state changes (e.g., `:focus`, `:disabled`, custom classes).
**Warning signs:** Style changes happen instantly despite CSS transition rules being set.
[CITED: textual.textualize.io/guide/animation/, youtube.com Textualize tutorial]

### Pitfall 2: Theme Changes Not Reflected in Inline Styles
**What goes wrong:** After registering and switching themes, inline `.styles.background` assignments still show old colors because they were set with hardcoded values.
**Why it happens:** Theme CSS variables (`$primary`, `$surface`) only apply within `.tcss` files or the `CSS` classvar. Programmatic `.styles` assignments use absolute values.
**How to avoid:** Always use CSS variables from the `.tcss` file for styling. Reserve `.styles` for dynamic values that genuinely change at runtime (e.g., processing state colors).
[CITED: textual.textualize.io/guide/design/]

### Pitfall 3: Overlapping Docked Widgets
**What goes wrong:** After removing StatusBar (docked: bottom), if the remaining docked widgets (InputBar, tool/job indicators) don't account for each other's height, they overlap.
**Why it happens:** Textual's dock layout stacks docked widgets in mount order. Each docked widget occupies space, and later widgets dock to the remaining space.
**How to avoid:** Use a single `#bottom-bar` Horizontal container docked to bottom, containing InputBar and indicator widgets. This gives one dock point with internal horizontal layout.
**Detection:** Visual overlap at the bottom of the screen when running the app.

### Pitfall 4: Textual Input Height Changes
**What goes wrong:** The Textual `Input` widget has default styling that includes a border, which adds height. Attempting to make it single-line without understanding the box model can break the layout.
**Why it happens:** Input's default border takes 2 cells (top + bottom). Setting `height: 1` with `box-sizing: border-box` can conflict with content requirements.
**How to avoid:** Set `border: none` on the Input to remove border spacing, or use `height: 3` for a 1-line input with 1 cell padding top and bottom.
[CITED: textual.textualize.io/guide/styles/, textual.textualize.io/styles/height/]

## Code Examples

### Custom Theme Registration (verified with Textual 8.2.8 API)

```python
from textual.theme import Theme

# Create and register in App.on_mount()
def on_mount(self) -> None:
    theme = Theme(
        name="claude-dark",
        primary="#cc785c",       # Coral — brand accent
        secondary="#5db8a6",     # Teal — secondary accent
        accent="#cc785c",        # Coral for highlights
        warning="#e8a55a",       # Amber
        error="#ff6b80",         # Soft red
        success="#4eba65",       # Green
        foreground="#faf9f5",    # Cream-white text
        background="#181715",    # Warm dark background
        surface="#1f1e1b",       # Elevated surface
        panel="#252320",         # Panel / card background
        boost="#cc785c20",       # Transparent coral for selections
        dark=True,
        variables={
            "input-selection-background": "#cc785c40",
        },
    )
    self.register_theme(theme)
    self.theme = "claude-dark"
```
[SOURCE: textual.textualize.io/guide/design/, VERIFIED: textual.theme.Theme signature]

### CSS File Structure (theme.tcss)

```css
/* Screen base */
Screen {
    background: $background;
}

/* Conversation panel — full width, no sidebar */
#conversation-panel {
    width: 1fr;
    height: 1fr;
    overflow-y: auto;
    scrollbar-color: $surface;
    scrollbar-color-hover: $primary;
}

/* Bottom bar — input + compact indicators */
#bottom-bar {
    dock: bottom;
    height: auto;
    layout: horizontal;
    background: $surface;
    border-top: solid $panel;
}

/* Tool call count indicator */
#tool-indicator {
    width: auto;
    padding: 0 1;
    color: $secondary;
    text-style: bold;
}

/* Job queue counter */
#job-indicator {
    width: auto;
    padding: 0 1;
    color: $text-muted;
}

/* Input bar — minimal, no extra chrome */
#input-bar {
    width: 1fr;
    height: 3;
    border: none;
    background: transparent;
    color: $text;
    placeholder-color: $text-muted;
}

#input-bar.--processing {
    color: $primary;
    placeholder-color: $primary;
}

/* Message cards */
MessageCard {
    margin: 0 1;
    padding: 0 1;
}

MessageCard.user {
    color: $text-muted;
}

MessageCard.assistant {
    color: $text;
}

/* Inline tool call — compact one-line by default */
InlineToolCall {
    margin: 0 1 0 2;
    padding: 0 1;
    color: $secondary;
    text-style: italic;
}

InlineToolCall.--expanded {
    color: $text;
    background: $surface;
    border: solid $panel 50%;
}

/* Keep existing Header */
Header {
    dock: top;
    background: $surface;
    color: $text;
}
```

### Animation Pattern for Processing State

```python
# In InputBar, when processing state changes:
def update_processing(self, is_processing: bool) -> None:
    if is_processing:
        self.disabled = True
        self.placeholder = "Thinking..."
        # Animate color transition
        self.styles.animate("color", value=self._processing_color, duration=0.3)
        if self._processing_timer:
            self._processing_timer.resume()
    else:
        self.disabled = False
        self.placeholder = "Type a prompt..."
        self.styles.animate("color", value=self._idle_color, duration=0.3)
        if self._processing_timer:
            self._processing_timer.pause()
```
[CITED: textual.textualize.io/guide/animation/]

### Inline Tool Call — Collapse/Expand with Reactive

```python
from textual.reactive import reactive

class InlineToolCall(Static):
    DEFAULT_CSS = """
    InlineToolCall {
        height: auto;
        margin: 0 0 0 2;
        color: $secondary;
        text-style: italic;
    }
    InlineToolCall .tool-status {
        color: $secondary;
    }
    InlineToolCall .tool-success {
        color: $success;
    }
    InlineToolCall .tool-error {
        color: $error;
    }
    """
    
    _collapsed = reactive(True)
    
    def __init__(self, tool_call_id: str, name: str, args: dict) -> None:
        self._tool_call_id = tool_call_id
        self._name = name
        self._args = args
        self._result: str | None = None
        self._error: str | None = None
        super().__init__()
        self._render_content()
    
    def set_result(self, result: str) -> None:
        self._result = result
        self._error = None
        self._render_content()
    
    def set_error(self, error: str) -> None:
        self._error = error
        self._result = None
        self._render_content()
    
    def on_click(self) -> None:
        self._collapsed = not self._collapsed
    
    def watch__collapsed(self) -> None:
        self._render_content()
    
    @property
    def tool_call_id(self) -> str:
        return self._tool_call_id
    
    def _render_content(self) -> None:
        if self._collapsed:
            # One-line: "read_file  ✓  " or "read_file  ○  (running...)"
            if self._result:
                icon = "[green]✓[/green]"
            elif self._error:
                icon = "[red]✗[/red]"
            else:
                icon = "[blue]○[/blue]"
            self.update(f"  {icon} [italic]{self._name}[/italic]")
        else:
            # Expanded: show args + result
            from rich.console import Group
            from rich.syntax import Syntax
            from rich.text import Text
            
            args_syntax = Syntax(
                json.dumps(self._args, indent=2), "json",
                theme="monokai", word_wrap=True
            )
            
            if self._error:
                body = Text(self._error, style="red")
            elif self._result:
                result_preview = (self._result[:500] + "...") if len(self._result) > 500 else self._result
                body = Text.assemble(
                    ("Arguments:\n", "bold"),
                    args_syntax,
                    ("\n\nResult:\n", "bold"),
                    (result_preview, "green"),
                )
            else:
                body = Text("Waiting for result...", style="dim italic")
            
            self.update(body)
```
[VERIFIED: textual.textualize.io/guide/widgets/, textual.textualize.io/guide/animation/]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tokyo Night palette (hardcoded) | Claude Code-inspired Theme | Phase 7 | Centralized color management, no hardcoded hex values |
| Separate StatusBar widget | No status bar — input bar shows state | Phase 7 (D-13, D-14) | More screen space, cleaner bottom area |
| ToolCallCard as separate widget | InlineToolCall in message stream | Phase 7 (D-07, D-09) | Tool calls feel like conversation, not separate elements |
| JobQueueSidebar as persistent fixture | Compact job counter in input bar | Phase 7 (D-04, D-16) | Full-width conversation, reduced chrome |
| ToolTimeline horizontal bar | Compact tool call count in input bar | Phase 7 (D-15) | Less visual noise, integrated with input area |
| Inline CSS in app.py CSS classvar | External theme.tcss file | Phase 7 | Live-reload via textual-dev, separation of concerns |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Claude Code uses warm dark `#181715` as base background | Claude Code Palette | Low — hex values are under OpenCode's discretion; any warm dark will work |
| A2 | Claude Code uses coral `#cc785c` as primary accent | Claude Code Palette | Low — primary accent is a Discretion choice; can be adjusted |
| A3 | Claude Code uses teal `#5db8a6` as secondary accent | Claude Code Palette | Low — secondary accent is a Discretion choice |
| A4 | Terminal supports 24-bit true color for all hex values | Theme Implementation | LOW — Apple Terminal downgrades to 256-color. Textual auto-handles this per Rich's color system, but some hues may shift. |
| A5 | Textual CSS `transition` will auto-animate InputBar state changes | Code Examples | MEDIUM — CSS transitions only animate class-based changes, not `.styles =` assignments. Verified via Textual docs. Code examples use `animate()` method correctly. |

## Open Questions

1. **How should the InlineToolCall expand interaction work?**
   - What we know: Click toggles collapse/expand (D-08). Claude Code uses Ctrl+O for transcript viewer.
   - What's unclear: Should clicking the inline tool call expand it inline (within the message stream) or push a detail overlay? Click-to-expand-inline is simpler and matches D-07 intent.
   - Recommendation: Click toggles inline expand/collapse of args and result within the message stream.

2. **Should the tool/job indicators be part of InputBar or siblings in bottom-bar?**
   - What we know: D-15/D-16 say "compact ... indicator in input bar area" — this means the bottom area, not necessarily inside the Input widget.
   - What's unclear: Whether indicators are inside the Input's border or adjacent to it.
   - Recommendation: Use a Horizontal container docked to bottom with [tool count] [job count] [Input] as siblings. This avoids Input widget height complications and keeps indicators visible.

3. **How to handle the "Thinking" animation without a separate StatusBar?**
   - What we know: D-14 says processing state via input bar placeholder + styling.
   - What's unclear: Should the spinner/animation happen entirely in the Input placeholder, or should there be a subtle one-line above the input (like Claude Code's spinner line above the separator)?
   - Recommendation: Use Input placeholder for simple "Thinking..." animation (existing code reuses this pattern). If visual polish demands it, add a thin spinner line above the input bar (Claude Code style).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Textual | Core TUI framework | ✓ | 8.2.8 (2026-07-27) | — |
| Rich | Terminal rendering | ✓ | 15.0.0 | — |
| textual-dev | Development (hot-reload) | ✗ | — | Edit CSS, rerun app |

**Missing dependencies with no fallback:** None — core deps installed.

**Missing dependencies with fallback:** textual-dev is optional; dev experience is slower without it (manual restarts instead of hot-reload), but not blocking.

## Validation Architecture

> workflow.nyquist_validation not configured — validation section included by default.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (Python) |
| Config file | none detected — likely in pyproject.toml or setup.cfg |
| Quick run command | `pytest tests/ -x` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01/D-02 | Custom Theme registers and applies | unit | `pytest tests/ -k "theme" -x` | ❌ Wave 0 |
| D-07/D-09 | InlineToolCall renders in message stream | integration | `pytest tests/ -k "inline_tool" -x` | ❌ Wave 0 |
| D-10/D-11 | InputBar shows processing/idle states | unit | `pytest tests/ -k "input_bar" -x` | ❌ Wave 0 |
| D-13 | StatusBar removed without error | smoke | `pytest tests/ -k "no_status_bar" -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -k "tui" -x`
- **Per wave merge:** Full TUI integration test suite
- **Phase gate:** Manual visual verification (TUI is inherently visual)

### Wave 0 Gaps
- [ ] `tests/test_tui_theme.py` — verifies Theme registration applies correctly, no crash
- [ ] `tests/test_tui_inline_tool.py` — verifies InlineToolCall create/expand/collapse
- [ ] `tests/test_tui_input_bar.py` — verifies processing state transitions

## Security Domain

> Omitted — security_enforcement not applicable to TUI visual redesign. No authentication, authorization, input validation beyond existing patterns, or cryptography involved. The TUI is a frontend rendering layer with no security-sensitive logic.

## Sources

### Primary (HIGH confidence)
- [Textual 8.2.8] Official docs — Guide to Design (themes), CSS, Animation, Widgets, Layout, Border, Styles [CITED: textual.textualize.io/guide/design/, textual.textualize.io/guide/CSS/, textual.textualize.io/guide/animation/]
- [Textual 8.2.8] Source code — `textual/theme.py` Theme dataclass, `textual/css/styles.py` Styles properties [CITED: github.com/Textualize/textual]
- [Textual 8.2.8] Border rendering — 20 border types, vs outline behavior [CITED: textual.textualize.io/styles/border/, deepwiki.com/Textualize/textual/4.6-border-rendering]
- [Rich 15.0.0] Markdown, Syntax, Panel, Text rendering [VERIFIED: pip show rich]
- [Claude Code] Terminal UI layout anatomy — bottom-to-top, separators, spinner line, input bar [CITED: tuicommander.com/docs/architecture/agents/claude-code.html]
- [Claude Code] 69 color tokens documented, 35 official + 34 internal [CITED: github.com/anthropics/claude-code/issues/55815]
- [Claude Code] Dark theme hex values: `#181715`, `#faf9f5`, `#cc785c`, `#5db8a6` [CITED: github.com/Hmbown/CodeWhale/pull/2267]

### Secondary (MEDIUM confidence)
- [Claude Code] Theme reference v2.1.x — full token catalog, color formats [VERIFIED: gist.github.com/cameronsjo/34a6fb8ade2b44c8380e1a2adebbac2b]
- [Claude Code] Ink-based React rendering, custom renderer with double buffer [CITED: claude-code-from-source.com/ch13-terminal-ui/]
- [Terminal UI Design] APCA contrast for dark themes, WCAG limitations [CITED: dev.to/palo_alto_ai/why-wcag-ratios-misled-me-building-a-dark-terminal-theme]
- [Terminal UI Design] Dark theme best practices: avoid pure black/white, 7:1-11:1 contrast, warm vs cool palettes [CITED: moltamp.com/blog/terminal-themes-that-dont-suck/]
- [Claude Code] Theme variants: dark/light/daltonized/ansi [CITED: blog.vincentqiao.com/en/posts/claude-code-theme/]

### Tertiary (LOW confidence)
- Textual CSS transition only works on class changes [CITED: youtube.com Textualize tutorial] — verified against official docs
- Claude Code's exact tool call collapse UX detail [ASSUMED based on feature requests #36462, #67005]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Textual 8.2.8 and Rich 15.0.0 verified installed. Theme API confirmed.
- Architecture: HIGH - Widget composition, event flow, and layout pattern verified against existing codebase.
- Pitfalls: HIGH - All identified from official Textual docs or verified experiences.
- Claude Code color palette: MEDIUM - Community-sourced values approximate; exact brand colors may vary but are under OpenCode's discretion.
- Animation/transition: HIGH - Textual's API documented and verified via official guide.

**Research date:** 2026-07-27
**Valid until:** 30 days (stable libraries, fast-moving terminal UI space)
