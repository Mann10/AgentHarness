import { Box, Text } from 'ink';

interface Props {
  error: string | null;
  onDismiss: () => void;
}

export default function ErrorBar({ error, onDismiss }: Props) {
  if (!error) return null;

  return (
    <Box borderStyle="round" borderColor="red" paddingX={1}>
      <Text color="red">⚠ {error}</Text>
      <Text dimColor>  (press Esc to dismiss)</Text>
    </Box>
  );
}
