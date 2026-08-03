import { Box, Text, useWindowSize } from "ink"
import { useAgentStore } from "../store/agent-store.js"

const CHIP_LABEL = "Skill:"                     // dim — static label
const CHIP_SEPARATOR = " · "                    // skill-name join (3 cells)
const CHIP_MORE_SUFFIX = (n: number) => `+${n} more`   // dim — truncation count
const CHIP_PADDING_X = 1                        // matches existing footer paddingX

// UI-SPEC §6.1 truncation (locked): W = columns - 4 (2 cells padding each side).
// Join all names with " · "; if the joined text fits → render all. Otherwise drop
// trailing names until kept + " · +N more" fits (N = dropped count, never hidden).
// Hard floor (§9): if even "Skill: +{N}" exceeds W (< ~18-col terminal), return
// null so the caller hides the whole chip row.
function formatChip(names: string[], columns: number): string | null {
  const W = columns - 4
  const joined = names.join(CHIP_SEPARATOR)
  if (joined.length <= W) return joined
  for (let drop = 1; drop < names.length; drop++) {
    const kept = names.slice(0, names.length - drop)
    const text = kept.join(CHIP_SEPARATOR) + CHIP_SEPARATOR + CHIP_MORE_SUFFIX(drop)
    if (text.length <= W) return text
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
