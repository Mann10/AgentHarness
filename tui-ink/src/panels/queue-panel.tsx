import stringWidth from "string-width"
import { Box, Text, useWindowSize } from "ink"
import { useAgentStore } from "../store/agent-store.js"

const PANEL_TITLE = "Queue"
const PADDING_X = 1
const BORDER_CELLS = 2          // single border: left + right
const QUOTE_CELLS = 2           // surrounding quotes
const ELLIPSIS = "…"
const MORE_SUFFIX = (n: number) => ` (+${n} more waiting)`

// D-v10: truncate the queued prompt to display width (date-panel pattern,
// measured with stringWidth — display columns, not UTF-16 code units). Cut
// one code unit at a time; append the ellipsis when truncated so the total
// still fits the budget.
function truncateToWidth(prompt: string, W: number): string {
  if (stringWidth(prompt) <= W) return prompt
  let cut = prompt
  while (stringWidth(cut) + stringWidth(ELLIPSIS) > W) {
    cut = cut.slice(0, -1)
  }
  return cut + ELLIPSIS
}

export function QueuePanel() {
  const { depth, nextPrompt } = useAgentStore((s) => s.queue) // selector-scoped re-render (footer.tsx pattern)
  const { columns } = useWindowSize()

  // Panel disappears when the backlog drains to zero (LOCKED) — the backend
  // emits depth=0 on drain and cancel; no TUI-local queue, no inference.
  if (depth === 0) return null

  const W = Math.max(10, (columns ?? 80) - PADDING_X * 2 - BORDER_CELLS - QUOTE_CELLS)
  const body = truncateToWidth(nextPrompt, W)
  const suffix = depth > 1 ? MORE_SUFFIX(depth - 1) : "" // N = depth − 1 (LOCKED example)

  return (
    <Box
      flexDirection="column"
      width="100%"
      borderStyle="single"
      borderColor="gray"     // informational, NOT focusable — no `focused` prop
      paddingX={PADDING_X}
    >
      <Box>
        <Text bold underline>
          {PANEL_TITLE}
        </Text>
      </Box>
      <Box marginY={1}>
        <Text color="yellow">"{body}"</Text>
        {suffix && <Text dimColor>{suffix}</Text>}
      </Box>
    </Box>
  )
}
