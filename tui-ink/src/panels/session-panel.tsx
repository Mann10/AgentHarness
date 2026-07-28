import { Box, Text } from "ink"
import { useAgentStore } from "../store/agent-store.js"

interface SessionPanelProps {
  focused: boolean
}

export function SessionPanel({ focused }: SessionPanelProps) {
  const { sessions, activeSessionId } = useAgentStore()
  const borderColor = focused ? "green" : "gray"

  return (
    <Box
      flexDirection="column"
      width="30%"
      minWidth={24}
      borderStyle="single"
      borderColor={borderColor}
      paddingX={1}
    >
      <Text bold underline>
        Sessions
      </Text>
      <Box flexDirection="column" marginY={1}>
        {sessions.length === 0 && (
          <Text dimColor italic>
            No sessions yet
          </Text>
        )}
        {sessions.map((s) => {
          const isActive = s.id === activeSessionId
          const icon = isActive ? "●" : "○"
          const color = isActive ? "green" : "gray"
          const title = (s.title ?? "untitled").slice(0, 20)
          return (
            <Box key={s.id}>
              <Text color={color}>
                {icon} {title}
              </Text>
              <Box flexGrow={1} />
              <Text dimColor>{s.message_count}</Text>
            </Box>
          )
        })}
      </Box>
      <Box marginTop={1}>
        <Text dimColor>[n] new</Text>
        <Text> </Text>
        <Text dimColor>[d] delete</Text>
        <Text> </Text>
        <Text dimColor>[r] rename</Text>
      </Box>
    </Box>
  )
}
