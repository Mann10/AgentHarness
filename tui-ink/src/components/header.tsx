import { Box, Text } from "ink"
import { useAgentStore } from "../store/agent-store.js"

export function Header() {
  const { sessions, activeSessionId, model, status } = useAgentStore()
  const activeSession = sessions.find((s) => s.id === activeSessionId)
  const label = activeSession?.title ?? "No session"

  const statusColors: Record<string, string> = {
    idle: "gray",
    thinking: "yellow",
    streaming: "green",
    error: "red",
  }

  return (
    <Box borderStyle="single" borderColor="cyan" paddingX={1} width="100%">
      <Text bold color="cyan">
        AgentHarness
      </Text>
      <Text> </Text>
      <Text dimColor>—</Text>
      <Text> </Text>
      <Text>{label}</Text>
      <Box flexGrow={1} />
      <Text dimColor>{model}</Text>
      <Text> </Text>
      <Text color={statusColors[status] ?? "gray"}>{status}</Text>
    </Box>
  )
}
