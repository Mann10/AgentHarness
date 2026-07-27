import { Box, Text } from 'ink';
import { useEffect, useState } from 'react';
import { ConversationScreen } from './ui/screens/ConversationScreen.js';
import { createStore } from './state/store.js';
import { handleEvent } from './state/reducers.js';
import { RpcClient } from './rpc/client.js';
import type { EventPayload } from './rpc/protocol.js';

/**
 * Root application component.
 *
 * Lifecycle:
 * 1. Creates state store singleton
 * 2. Spawns Python backend process via RpcClient
 * 3. Subscribes to RPC event notifications → dispatches to handleEvent
 * 4. Renders ConversationScreen bound to store + RPC client
 * 5. On unmount, stops the RPC client (kills backend subprocess)
 */
export default function App() {
  const store = createStore();
  const [client, setClient] = useState<RpcClient | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Path to the Python backend — use python on PATH, spawn with --rpc
    const rpcClient = new RpcClient('python', ['-m', 'agentharness', '--rpc']);

    // Subscribe to all notification types and dispatch to state reducers
    const eventTypes = [
      'turn_started',
      'token',
      'response_complete',
      'cancelled',
      'error',
      'tool_call',
      'tool_result',
    ];

    const unsubscribers = eventTypes.map(type =>
      rpcClient.on(type, (params: EventPayload) => {
        handleEvent(store, params);
      })
    );

    // Start the backend process
    rpcClient.start()
      .then(() => {
        setClient(rpcClient);
      })
      .catch((err: Error) => {
        setError(`Failed to start backend: ${err.message}`);
      });

    // Cleanup on unmount
    return () => {
      for (const unsub of unsubscribers) {
        unsub();
      }
      rpcClient.stop().catch(() => {});
    };
  }, [store]);

  // Show error screen if backend failed to start
  if (error) {
    return (
      <Box flexDirection="column" padding={1}>
        <Text bold color="red">Backend Error</Text>
        <Text color="red">{error}</Text>
      </Box>
    );
  }

  // Show connecting screen while backend starts
  if (!client) {
    return (
      <Box flexDirection="column" padding={1}>
        <Text bold color="green">AgentHarness TUI</Text>
        <Text dimColor>Starting backend connection...</Text>
      </Box>
    );
  }

  // Conversation screen bound to store + RPC client
  const handlePrompt = (prompt: string) => {
    client.request('chat', { prompt }).catch(err => {
      store.setError(`Failed to send prompt: ${err.message}`);
    });
  };

  return (
    <ConversationScreen
      store={store}
      onPrompt={handlePrompt}
    />
  );
}
