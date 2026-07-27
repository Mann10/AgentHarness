import { Box, Text } from 'ink';

export default function App() {
  return (
    <Box flexDirection="column" padding={1}>
      <Text bold color="green">AgentHarness TUI</Text>
      <Text dimColor>Waiting for backend connection...</Text>
    </Box>
  );
}
