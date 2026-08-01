import { useEffect, useState } from "react"
import { Box, Text, useWindowSize } from "ink"
import { useAgentStore } from "../store/agent-store.js"

const DATE_PANEL_WIDTH = 28          // cells (D-05 band 24–30, 28 chosen — UI-SPEC §3)
const MIN_TERMINAL_WIDTH = 68        // 40 conversation + 28 date panel (UI-SPEC §9 floor)
const CONTENT_WIDTH = 24             // 28 - 2 border - 2 paddingX

const pad = (n: number) => String(n).padStart(2, "0")

export function DatePanel() {
  const { columns } = useWindowSize()
  const { sessions, activeSessionId } = useAgentStore()
  const [now, setNow] = useState(() => new Date())

  // D-14/D-15/D-16: live clock — useEffect + setInterval (Ink 7.1 has no timer hook)
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  // UI-SPEC §9 floor pressure: hide below 68 cols, conversation takes full width
  if (columns < MIN_TERMINAL_WIDTH) return null

  const dateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}` // ISO YYYY-MM-DD
  const timeStr = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}` // 24h HH:MM:SS
  const active = sessions.find((s) => s.id === activeSessionId)
  const title = active?.title ?? "untitled"
  const truncated = title.length > CONTENT_WIDTH ? title.slice(0, CONTENT_WIDTH - 1) + "…" : title

  return (
    <Box
      flexDirection="column"
      width={DATE_PANEL_WIDTH}
      borderStyle="single"
      borderColor="gray"
      paddingX={1}
    >
      <Text bold underline>Date &amp; Time</Text>
      <Box flexDirection="column" marginY={1}>
        <Text>{dateStr}</Text>
        <Text bold>{timeStr}</Text>
      </Box>
      <Box flexDirection="column" marginY={1}>
        <Text dimColor>Session</Text>
        <Text>{truncated}</Text>
      </Box>
    </Box>
  )
}
