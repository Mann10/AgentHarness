/**
 * Pure function: maps RPC event notifications to state updates.
 * Completely independent of Ink/React (D-12).
 * This is the application logic layer — testable without rendering.
 */
import type { Store } from './store.js';
import type { EventPayload } from '../rpc/protocol.js';

export function handleEvent(store: Store, params: EventPayload): void {
  switch (params.type) {
    case 'turn_started': {
      const prompt = params.payload.prompt as string;
      store.addMessage({
        id: `user-${params.request_id}-${Date.now()}`,
        role: 'user',
        content: prompt,
        timestamp: Date.now(),
      });
      store.setProcessing(true);
      break;
    }

    case 'token': {
      const chunk = params.payload.chunk as string;
      store.appendStreamedContent(chunk);
      break;
    }

    case 'response_complete': {
      const requestId = params.request_id;
      store.finalizeStream(requestId);
      break;
    }

    case 'cancelled': {
      store.setProcessing(false);
      store.setError('Turn cancelled.');
      break;
    }

    case 'error': {
      const error = params.payload.error as string;
      store.setProcessing(false);
      store.setError(error);
      break;
    }

    case 'tool_call': {
      const toolName = params.payload.tool_name as string;
      const toolCallId = params.payload.tool_call_id as string;
      store.addToolCall(toolCallId, toolName);
      break;
    }

    case 'tool_result': {
      const toolCallId = params.payload.tool_call_id as string;
      const result = params.payload.result as string;
      store.updateToolCall(toolCallId, 'completed', result);
      break;
    }

    default:
      console.warn('[reducers] Unknown event type:', params.type);
  }
}
