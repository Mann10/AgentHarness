import { Box, Text } from "ink"
import { useAgentStore } from "../store/agent-store.js"
import { ToolCallRow } from "../components/tool-call.js"

interface ToolMonitorPanelProps {
  focused: boolean
}

export function ToolMonitorPanel({ focused }: ToolMonitorPanelProps) {
  const { toolCalls, toolCallCount } = useAgentStore()

  if (toolCalls.length === 0) {
    return null
  }

  const recentCalls = toolCalls.slice(-5)

  return (
    <Box
      flexDirection="column"
      width="100%"
      borderStyle="single"
      borderColor={focused ? "green" : "gray"}
      paddingX={1}
    >
      <Box>
        <Text bold underline>
          Tool Calls
        </Text>
        <Box flexGrow={1} />
        <Text dimColor>{toolCallCount} total</Text>
      </Box>
      <Box flexDirection="column" marginY={1}>
        {recentCalls.map((tc) => (
          <ToolCallRow key={tc.id} call={tc} />
        ))}
      </Box>
    </Box>
  )
}
