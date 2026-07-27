import { Box, Text } from 'ink';
import { useStdout } from 'ink';
import type { SessionInfo } from '../../state/store.js';

interface Props {
  session: SessionInfo | null;
  connected: boolean;
  processing: boolean;
}

export default function StatsBar({ session, connected, processing }: Props) {
  const { stdout } = useStdout();
  const columns = stdout.columns;

  const sessionLabel = session ? `session: ${session.title || session.id.slice(0, 8)}` : 'no session';
  const statusIcon = connected ? (processing ? '◆' : '○') : '✗';
  const statusColor = connected ? (processing ? 'yellow' : 'green') : 'red';
  const statusLabel = connected ? (processing ? 'processing' : 'ready') : 'disconnected';

  const status = `${statusIcon} ${statusLabel}  |  ${sessionLabel}`;
  const padding = Math.max(0, columns - status.length - 2);

  return (
    <Box>
      <Text dimColor>
        <Text color={statusColor}>{statusIcon}</Text>
        {' '}{statusLabel}  │  {sessionLabel}
        {' '.repeat(padding)}
      </Text>
    </Box>
  );
}
