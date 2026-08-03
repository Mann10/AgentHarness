import { Box, Text } from "ink"
import type { Message } from "../types.js"
import { StreamingText } from "./streaming-text.js"

const NOTICE_OK = "✓"                    // green, bold — success tone (09-UI-SPEC §6)
const NOTICE_ERR = "✗"                   // red, bold — error tone (09-UI-SPEC §6)

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
          {message.truncated && (
            <Text color="yellow" dimColor italic>
              {" "}(truncated)
            </Text>
          )}
        </Box>
      </Box>
    )
  }

  if (message.role === "notice") {
    if (message.tone === "success") {
      return (
        <Box>
          <Text color="green" bold>
            {NOTICE_OK} {message.content}
          </Text>
        </Box>
      )
    }
    if (message.tone === "error") {
      return (
        <Box>
          <Text color="red" bold>
            {NOTICE_ERR} {message.content}
          </Text>
        </Box>
      )
    }
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
