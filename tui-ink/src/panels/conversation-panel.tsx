import { useEffect, useRef } from "react"
import { Box, Text } from "ink"
import { useAgentStore } from "../store/agent-store.js"
import { MessageCard } from "../components/message.js"

interface ConversationPanelProps {
  focused: boolean
}

export function ConversationPanel({ focused }: ConversationPanelProps) {
  const { conversation, status } = useAgentStore()
  const borderColor = focused ? "green" : "gray"

  return (
    <Box
      flexDirection="column"
      flexGrow={1}
      borderStyle="single"
      borderColor={borderColor}
      paddingX={1}
    >
      <Text bold underline>
        Conversation
      </Text>
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
