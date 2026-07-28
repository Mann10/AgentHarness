import { Box, Text } from "ink"
import type { Message } from "../types.js"
import { StreamingText } from "./streaming-text.js"

interface MessageProps {
  message: Message
}

export function MessageCard({ message }: MessageProps) {
  if (message.role === "user") {
    return (
      <Box>
        <Text bold color="yellow">
          You{" "}
        </Text>
        <Text color="white">{message.content}</Text>
      </Box>
    )
  }

  if (message.role === "assistant") {
    return (
      <Box flexDirection="column">
        <Box>
          <Text bold color="green">
            {message.isStreaming ? "▸" : " "}{" "}
          </Text>
          {message.isStreaming ? (
            <StreamingText text={message.content} />
          ) : (
            <Text color="white">{message.content}</Text>
          )}
        </Box>
      </Box>
    )
  }

  if (message.role === "notice") {
    return (
      <Box>
        <Text dimColor italic>
          {message.content}
        </Text>
      </Box>
    )
  }

  if (message.role === "error") {
    return (
      <Box>
        <Text color="red" bold>
          ✗ {message.content}
        </Text>
      </Box>
    )
  }

  return null
}
