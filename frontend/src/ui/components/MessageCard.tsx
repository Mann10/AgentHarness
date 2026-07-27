import { Box, Text } from 'ink';
import type { Message } from '../../state/store.js';

interface MessageCardProps {
  message: Message;
}

/**
 * Renders a single message with role-based styling.
 * - User messages: green bold prefix, wrapped content
 * - Assistant messages: standard output
 * - Error messages: red colored
 * - System messages: dim/yellow
 */
export function MessageCard({ message }: MessageCardProps) {
  switch (message.role) {
    case 'user':
      return (
        <Box flexDirection="column">
          <Text bold color="green">You:</Text>
          <Text>{message.content}</Text>
        </Box>
      );

    case 'assistant':
      return (
        <Box flexDirection="column">
          <Text bold color="cyan">Assistant:</Text>
          <Text>{message.content}</Text>
        </Box>
      );

    case 'error':
      return (
        <Box flexDirection="column">
          <Text bold color="red">Error:</Text>
          <Text color="red">{message.content}</Text>
        </Box>
      );

    case 'system':
      return (
        <Box flexDirection="column">
          <Text dimColor color="yellow">{message.content}</Text>
        </Box>
      );
  }
}
