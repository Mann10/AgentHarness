import { Box, Text } from 'ink';
import { useEffect, useState } from 'react';
import { MessageCard } from '../components/MessageCard.js';
import { InputBar } from '../components/InputBar.js';
import type { Store } from '../../state/store.js';

interface ConversationScreenProps {
  store: Store;
  onPrompt: (prompt: string) => void;
}

/**
 * Main conversation view — message list + input bar.
 * Subscribes to the state store and re-renders on changes.
 */
export function ConversationScreen({ store, onPrompt }: ConversationScreenProps) {
  const [, setTick] = useState(0);
  const [inputValue, setInputValue] = useState('');

  // Subscribe to state store changes
  useEffect(() => {
    const unsub = store.subscribe(() => {
      setTick(t => t + 1);
    });
    return unsub;
  }, [store]);

  const state = store.getState();

  const handleSubmit = (value: string) => {
    onPrompt(value);
    setInputValue('');
  };

  return (
    <Box flexDirection="column" flexGrow={1}>
      {/* Header */}
      <Box>
        <Text bold color="green">AgentHarness</Text>
        {state.activeSession && (
          <Text dimColor> — {state.activeSession.title}</Text>
        )}
        {state.isProcessing && (
          <Text color="yellow"> [processing...]</Text>
        )}
      </Box>

      <Box flexDirection="column" flexGrow={1} marginY={1}>
        {state.messages.length === 0 ? (
          <Text dimColor>No messages yet. Type a prompt below to start a conversation.</Text>
        ) : (
          state.messages.map(msg => (
            <Box key={msg.id} marginBottom={1}>
              <MessageCard message={msg} />
            </Box>
          ))
        )}

        {/* Streaming content */}
        {state.streamedContent && (
          <Box marginBottom={1}>
            <MessageCard
              message={{
                id: 'streaming',
                role: 'assistant',
                content: state.streamedContent,
                timestamp: Date.now(),
              }}
            />
          </Box>
        )}

        {/* Error display */}
        {state.error && (
          <Box marginBottom={1}>
            <Text color="red">{state.error}</Text>
          </Box>
        )}
      </Box>

      {/* Input bar at the bottom */}
      <InputBar
        value={inputValue}
        onChange={setInputValue}
        onSubmit={handleSubmit}
        disabled={state.isProcessing}
      />
    </Box>
  );
}
