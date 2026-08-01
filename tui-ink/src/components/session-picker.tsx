import { useEffect, useState } from "react"
import { Box, Text, useInput, useWindowSize } from "ink"
import { useAgentStore } from "../store/agent-store.js"
import type { RpcClient } from "../bridge/rpc-client.js"
import type { SessionSummary } from "../types.js"

const ACCENT = "blue"            // picker border + cursor + cursor-row title ONLY (UI-SPEC §5)
const CURSOR = ">"
const ACTIVE_MARK = "●"
const INACTIVE_MARK = "  "       // 2-space placeholder keeps prefix alignment
const HINT_LINE = "↑ ↓ navigate  •  Enter select  •  Esc/q close"
const ROW_PREFIX = 4             // cells: cursor(2) + active-mark(2)
const ID_COLUMN = 8

function relativeAge(iso: string): string {
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 60) return "just now"
  if (s < 3600) return `${Math.round(s / 60)}m ago`
  if (s < 86400) return `${Math.round(s / 3600)}h ago`
  return `${Math.round(s / 86400)}d ago`
}

interface SessionPickerProps {
  client: RpcClient
  onClose: () => void
}

export function SessionPicker({ client, onClose }: SessionPickerProps) {
  const { rows: termRows } = useWindowSize()
  const activeSessionId = useAgentStore((s) => s.activeSessionId)
  const [rows, setRows] = useState<SessionSummary[] | null>(null) // null = loading
  const [cursor, setCursor] = useState(0)
  const [scrollOffset, setScrollOffset] = useState(0)
  const [switching, setSwitching] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // On mount: list sessions, sort most-recent first (research Pitfall 5), seed store
  useEffect(() => {
    let cancelled = false
    client.listSessions()
      .then((sessions) => {
        if (cancelled) return
        const sorted = [...sessions].sort((a, b) => b.updated_at.localeCompare(a.updated_at))
        setRows(sorted)
        useAgentStore.getState().setSessions(sorted)
      })
      .catch(() => { if (!cancelled) setError("Could not load sessions") })
    return () => { cancelled = true }
  }, [client])

  const visibleCount = Math.max(1, termRows - 6) // title + blanks + hint + borders ≈ 6

  const select = (s: SessionSummary) => {
    setSwitching(true)
    setError(null)
    client.switchSession(s.id)
      .then((ok) => {
        if (!ok) { setError(`Failed to load session: ${s.id.slice(0, 8)}`); setSwitching(false); return }
        return client.getSessionHistory(s.id)
      })
      .then((history) => {
        if (!history) return
        const store = useAgentStore.getState()
        store.setActiveSession(s.id)
        store.loadConversation(history)
        onClose()
      })
      .catch((err: Error) => { setError(`Failed to load session: ${err.message}`); setSwitching(false) })
  }

  useInput((input, key) => {
    if (switching) return
    if (key.escape || input === "q") { onClose(); return }   // UI-SPEC §6.3 item 4: Esc AND q close
    if (!rows || rows.length === 0) return
    if (key.upArrow) { setCursor((c) => Math.max(0, c - 1)); return }    // clamp, no wrap
    if (key.downArrow) { setCursor((c) => Math.min(rows.length - 1, c + 1)); return }
    if (key.return) { select(rows[cursor]); return }
  })

  // Window scroll: keep cursor visible (UI-SPEC §6.3 item 5)
  useEffect(() => {
    if (cursor < scrollOffset) setScrollOffset(cursor)
    else if (cursor >= scrollOffset + visibleCount) setScrollOffset(cursor - visibleCount + 1)
  }, [cursor, scrollOffset, visibleCount])

  return (
    <Box flexDirection="column" width="100%" height="100%" borderStyle="single" borderColor={ACCENT} paddingX={1}>
      <Text bold underline>Switch Session</Text>
      <Box flexGrow={1} flexDirection="column" marginY={1}>
        {rows === null && !error && <Text dimColor>Loading sessions...</Text>}
        {error !== null && <Text color="red">{error}</Text>}
        {rows !== null && rows.length === 0 && !error && (
          <Text dimColor italic>No sessions yet. Press Esc and type /new to start one.</Text>
        )}
        {rows !== null && rows.slice(scrollOffset, scrollOffset + visibleCount).map((s, i) => {
          const rowIndex = scrollOffset + i
          const isCursorRow = rowIndex === cursor
          const isActive = s.id === activeSessionId
          const prefix = isCursorRow ? `${CURSOR} ` : "  "
          const mark = isActive ? `${ACTIVE_MARK} ` : INACTIVE_MARK
          return (
            <Box key={s.id}>
              <Text bold color={ACCENT}>{prefix}</Text>
              <Text color={isActive ? "green" : undefined}>{mark}</Text>
              <Text bold={isCursorRow} color={isCursorRow ? ACCENT : undefined}>{s.title ?? "untitled"}</Text>
              <Box flexGrow={1} />
              <Text dimColor>{s.id.slice(0, ID_COLUMN)}</Text>
              <Text dimColor>{"  "}{s.message_count} msgs</Text>
              <Text dimColor>{"  "}{relativeAge(s.updated_at)}</Text>
            </Box>
          )
        })}
      </Box>
      {switching && <Text dimColor>Loading session…</Text>}
      <Text dimColor>{HINT_LINE}</Text>
    </Box>
  )
}
