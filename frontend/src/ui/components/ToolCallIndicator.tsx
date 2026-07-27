import { Box, Text } from 'ink';
import type { ToolCallState } from '../../state/store.js';

interface Props {
  toolCalls: ToolCallState[];
}

export default function ToolCallIndicator({ toolCalls }: Props) {
  if (toolCalls.length === 0) return null;

  return (
    <Box flexDirection="column" marginTop={1} marginBottom={1}>
      {toolCalls.map((tc) => (
        <Box key={tc.toolCallId}>
          <Text>
            {tc.status === 'running' ? '⠋' : tc.status === 'completed' ? '✓' : '✗'}{' '}
            <Text color={tc.status === 'error' ? 'red' : tc.status === 'completed' ? 'green' : 'yellow'}>
              {tc.toolName}
            </Text>
            {tc.result && <Text dimColor> — {tc.result.slice(0, 80)}{tc.result.length > 80 ? '…' : ''}</Text>}
          </Text>
        </Box>
      ))}
    </Box>
  );
}
