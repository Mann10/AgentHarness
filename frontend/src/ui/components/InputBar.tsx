import { Box, Text } from 'ink';
import { useInput } from 'ink';

interface InputBarProps {
  /** Current input value */
  value: string;
  /** Called when the input value changes (character appended) */
  onChange: (value: string) => void;
  /** Called when Enter is pressed with a non-empty value */
  onSubmit: (value: string) => void;
  /** Whether the backend is currently processing a request */
  disabled?: boolean;
}

/**
 * Text input bar with submission on Enter.
 * Built on Ink's useInput hook — no external input library needed.
 */
export function InputBar({ value, onChange, onSubmit, disabled }: InputBarProps) {
  useInput((input, key) => {
    if (disabled) return;

    if (key.return) {
      const trimmed = value.trim();
      if (trimmed) {
        onSubmit(trimmed);
      }
      return;
    }

    if (key.backspace || key.delete) {
      onChange(value.slice(0, -1));
      return;
    }

    // Ignore control characters and escape sequences
    if (key.ctrl || key.meta || key.shift) return;
    if (input.length === 0) return;

    onChange(value + input);
  });

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={disabled ? 'gray' : 'cyan'}>
      <Box>
        <Text bold color="green">{'>'}</Text>
        <Text> </Text>
        <Text dimColor={disabled}>{value || (disabled ? 'Waiting...' : 'Type your message...')}</Text>
      </Box>
    </Box>
  );
}
