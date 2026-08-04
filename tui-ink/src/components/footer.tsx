import stringWidth from "string-width"
import { Box, Text, useWindowSize } from "ink"
import { useAgentStore } from "../store/agent-store.js"

const CHIP_LABEL = "Skill:"                     // dim — static label
const CHIP_SEPARATOR = " · "                    // skill-name join (3 cells)
const CHIP_MORE_SUFFIX = (n: number) => `+${n} more`   // dim — truncation count
const CHIP_PADDING_X = 1                        // matches existing footer paddingX

// UI-SPEC §6.1 truncation (locked, WR-04): full-row width budget. The rendered row is
// <Box paddingX={CHIP_PADDING_X}><Text dimColor>{CHIP_LABEL} </Text>... so reserve
// CHIP_PADDING_X*2 (2 cells) + stringWidth(CHIP_LABEL + " ") (7 cells) before the names.
// All measurements use display columns, not UTF-16 code units.
// Join all names with " · "; if the joined text fits → render all. Otherwise drop
// trailing names until kept + " · +N more" fits (N = dropped count, never hidden).
// Hard floor (§9): if even "Skill: +{N}" exceeds W (< ~18-col terminal), return
// null so the caller hides the whole chip row.
function formatChip(names: string[], columns: number): string | null {
  const W = columns - CHIP_PADDING_X * 2 - stringWidth(CHIP_LABEL + " ")
  const joined = names.join(CHIP_SEPARATOR)
  if (stringWidth(joined) <= W) return joined
  for (let drop = 1; drop < names.length; drop++) {
    const kept = names.slice(0, names.length - drop)
    const text = kept.join(CHIP_SEPARATOR) + CHIP_SEPARATOR + CHIP_MORE_SUFFIX(drop)
    if (stringWidth(text) <= W) return text
  }
  return null
}

export function Footer() {
  const loadedSkills = useAgentStore((s) => s.loadedSkills)   // re-renders on chip changes only
  const { columns } = useWindowSize()                          // Ink 7.1 — returns {columns, rows}
  const chip = loadedSkills.length > 0 ? formatChip(loadedSkills, columns) : null

  return (
    <Box flexDirection="column" width="100%">
      {chip && (
        <Box paddingX={CHIP_PADDING_X}>
          <Text dimColor>{CHIP_LABEL} </Text>
          <Text bold color="white">
            {chip}
          </Text>
        </Box>
      )}
      <Box width="100%" paddingX={1}>
        {/* existing hint row unchanged — exactly today's set */}
        <Text dimColor>[?] help</Text>
        <Text> </Text>
        <Text dimColor>[/session] sessions</Text>
        <Text> </Text>
        <Text dimColor>[/new] new chat</Text>
        <Text> </Text>
        <Text dimColor>[Tab] panels</Text>
        <Text> </Text>
        <Text dimColor>[q] quit</Text>
      </Box>
    </Box>
  )
}
