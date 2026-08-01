import { useEffect, useRef } from "react"
import { Box, Text } from "ink"
import { useAgentStore } from "../store/agent-store.js"
import { MessageCard } from "../components/message.js"

interface ConversationPanelProps {
  focused: boolean
}

export function ConversationPanel({ focused }: ConversationPanelProps) {
  const { conversation, status, sessions, activeSessionId } = useAgentStore()
  const borderColor = focused ? "green" : "gray"
  const active = sessions.find((s) => s.id === activeSessionId)
  const title = active?.title ?? "untitled"

  return (
    <Box
      flexDirection="column"
      flexGrow={1}
      borderStyle="single"
      borderColor={borderColor}
      paddingX={1}
    >
      <Box>
        <Text bold underline>
          Conversation
        </Text>
        <Text dimColor>
          {"  "}· {title}
        </Text>
      </Box>
      <Box flexDirection="column-reverse" flexGrow={1} marginY={1}>
        {status === "thinking" && conversation.length > 0 && (
          <Box>
            <Text color="yellow" dimColor>
              ● thinking
            </Text>
          </Box>
        )}
        {status === "thinking" && conversation.length === 0 && (
          <Box>
            <Text color="yellow" dimColor>
              ● processing...
            </Text>
          </Box>
        )}
        {[...conversation].reverse().map((msg) => (
          <MessageCard key={msg.id} message={msg} />
        ))}
        {conversation.length === 0 && (
          <Text dimColor italic>
            Type a message to start a conversation
          </Text>
        )}
      </Box>
    </Box>
  )
}
