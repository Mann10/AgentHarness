import { Box, Text } from "ink"
import type { ToolCallStatus } from "../types.js"

interface ToolCallProps {
  call: ToolCallStatus
}

export function ToolCallRow({ call }: ToolCallProps) {
  const icon = call.status === "running" ? "⏳" : call.status === "success" ? "✅" : "❌"
  const color = call.status === "running" ? "yellow" : call.status === "success" ? "green" : "red"
  const duration = call.duration != null ? `${(call.duration / 1000).toFixed(1)}s` : "..."

  return (
    <Box>
      <Text color={color}>
        {icon} {call.name}
      </Text>
      <Box flexGrow={1} />
      <Text dimColor>{duration}</Text>
    </Box>
  )
}
