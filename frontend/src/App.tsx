import { Box, Text, useInput } from 'ink';
import { useEffect, useState, useRef, useCallback } from 'react';
import { RpcClient } from './rpc/client.js';
import { createStore } from './state/store.js';
import { handleEvent } from './state/reducers.js';
import { ConversationScreen } from './ui/screens/ConversationScreen.js';
import SessionPicker from './ui/screens/SessionPicker.js';
import StatsBar from './ui/components/StatsBar.js';
import ErrorBar from './ui/components/ErrorBar.js';

const PYTHON_COMMAND = process.platform === 'win32' ? 'python' : 'python3';

export default function App() {
  const [store] = useState(() => createStore());
  const [client] = useState(() => new RpcClient(PYTHON_COMMAND, ['-m', 'agentharness', '--rpc']));
  const [connected, setConnected] = useState(false);
  const [showSessionPicker, setShowSessionPicker] = useState(false);
  const stateRef = useRef(store.getState());
  const clientRef = useRef(client);
  const [, forceUpdate] = useState(0);

  stateRef.current = store.getState();

  // Subscribe to store changes for re-render
  useEffect(() => {
    const unsub = store.subscribe(() => forceUpdate(n => n + 1));
    return unsub;
  }, [store]);

  // Initialize: connect, subscribe to events, ping readiness
  useEffect(() => {
    const c = clientRef.current;
    let cancelled = false;

    (async () => {
      try {
        await c.start();

        const unsubTurn = c.on('turn_started', (p) => handleEvent(store, p));
        const unsubToken = c.on('token', (p) => handleEvent(store, p));
        const unsubComplete = c.on('response_complete', (p) => handleEvent(store, p));
        const unsubCancelled = c.on('cancelled', (p) => handleEvent(store, p));
        const unsubError = c.on('error', (p) => handleEvent(store, p));
        const unsubToolCall = c.on('tool_call', (p) => handleEvent(store, p));
        const unsubToolResult = c.on('tool_result', (p) => handleEvent(store, p));

        const ping = await c.request('ping');
        if (!cancelled) setConnected(ping.success);

        return () => {
          unsubTurn(); unsubToken(); unsubComplete();
          unsubCancelled(); unsubError(); unsubToolCall(); unsubToolResult();
        };
      } catch (err) {
        if (!cancelled) {
          setConnected(false);
          store.setError(`Failed to start backend: ${err}`);
        }
      }
    })();

    return () => { cancelled = true; };
  }, [store]);

  // Backend crash detection
  useEffect(() => {
    const c = clientRef.current;
    const interval = setInterval(() => {
      if (!c.isRunning && connected) {
        setConnected(false);
        store.setError('Backend process disconnected.');
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [connected, store]);

  // Keyboard handling
  useInput((input, key) => {
    if (key.ctrl && input === 'c') {
      clientRef.current.request('cancel');
      return;
    }
    if (key.ctrl && input === 's') {
      clientRef.current.request<Array<{ id: string; title?: string }>>('sessions.list').then(r => {
        if (r.success && r.data) {
          store.setState({
            sessions: r.data.map((s: any) => ({ id: s.id, title: s.title || 'untitled' })),
          });
        }
      });
      setShowSessionPicker(true);
      return;
    }
  });

  const handleSwitchSession = useCallback(async (sessionId: string) => {
    const result = await clientRef.current.request('sessions.switch', { session_id: sessionId });
    if (result.success) {
      store.setState({ messages: [], streamedContent: '' });
    } else {
      store.setError(`Failed to switch session: ${result.error}`);
    }
    setShowSessionPicker(false);
  }, [store]);

  const handleCreateSession = useCallback(async () => {
    const result = await clientRef.current.request('sessions.create');
    if (result.success) {
      const data = result.data as { session_id: string };
      store.setState({
        messages: [],
        streamedContent: '',
        activeSession: { id: data.session_id, title: 'untitled' },
      });
    } else {
      store.setError(`Failed to create session: ${result.error}`);
    }
    setShowSessionPicker(false);
  }, [store]);

  const handleDismissError = useCallback(() => {
    store.setError(null);
  }, [store]);

  const handlePrompt = useCallback((prompt: string) => {
    clientRef.current.request('chat', { prompt }).catch((err: Error) => {
      store.setError(`Failed to send prompt: ${err.message}`);
    });
  }, [store]);

  // Kill backend on exit
  useEffect(() => {
    return () => {
      clientRef.current.stop().catch(() => {});
    };
  }, []);

  const state = stateRef.current;

  if (showSessionPicker) {
    return (
      <SessionPicker
        client={clientRef.current}
        sessions={state.sessions}
        onSwitch={handleSwitchSession}
        onCreate={handleCreateSession}
        onClose={() => setShowSessionPicker(false)}
      />
    );
  }

  return (
    <Box flexDirection="column">
      <StatsBar
        session={state.activeSession}
        connected={connected}
        processing={state.isProcessing}
      />
      <ErrorBar error={state.error} onDismiss={handleDismissError} />
      <ConversationScreen
        store={store}
        onPrompt={handlePrompt}
      />
    </Box>
  );
}
