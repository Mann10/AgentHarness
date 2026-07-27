import { Box, Text, useInput } from 'ink';
import { useState, useEffect } from 'react';
import type { RpcClient } from '../../rpc/client.js';
import type { SessionInfo } from '../../state/store.js';

interface Props {
  client: RpcClient;
  sessions: SessionInfo[];
  onSwitch: (sessionId: string) => void;
  onCreate: () => void;
  onClose: () => void;
}

export default function SessionPicker({ client, sessions, onSwitch, onCreate, onClose }: Props) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [localSessions, setLocalSessions] = useState<SessionInfo[]>(sessions);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      const result = await client.request<Array<{ id: string; title?: string }>>('sessions.list');
      if (result.success && result.data) {
        setLocalSessions(result.data.map((s: any) => ({ id: s.id, title: s.title || 'untitled' })));
      }
      setLoading(false);
    })();
  }, [client]);

  useInput((input, key) => {
    if (key.escape || input === 'q') { onClose(); return; }
    if (key.return || input === ' ') {
      if (selectedIndex === 0) {
        onCreate();
      } else {
        const session = localSessions[selectedIndex - 1];
        if (session) onSwitch(session.id);
      }
      return;
    }
    if (key.upArrow) { setSelectedIndex(Math.max(0, selectedIndex - 1)); return; }
    if (key.downArrow) { setSelectedIndex(Math.min(localSessions.length, selectedIndex + 1)); return; }
    if (key.delete || input === 'd') {
      const session = localSessions[selectedIndex - 1];
      if (session) {
        client.request('sessions.delete', { session_id: session.id });
        setLocalSessions(prev => prev.filter(s => s.id !== session.id));
        setSelectedIndex(Math.max(0, selectedIndex - 1));
      }
      return;
    }
  });

  return (
    <Box flexDirection="column" padding={1}>
      <Text bold underline>Session Manager</Text>
      <Box marginTop={1} flexDirection="column">
        <Text>
          {selectedIndex === 0 ? '> ' : '  '}
          <Text bold={selectedIndex === 0} color="green">+ New Session</Text>
        </Text>
        {loading && <Text dimColor>Loading...</Text>}
        {localSessions.map((s, i) => (
          <Text key={s.id}>
            {selectedIndex === i + 1 ? '> ' : '  '}
            <Text bold={selectedIndex === i + 1}>
              {s.title.slice(0, 30)}{s.title.length > 30 ? '…' : ''}
            </Text>
            <Text dimColor>  ({s.id.slice(0, 8)})</Text>
          </Text>
        ))}
      </Box>
      <Box marginTop={1}>
        <Text dimColor>↑ ↓ navigate  •  Enter select  •  d delete  •  Esc/q close</Text>
      </Box>
    </Box>
  );
}
