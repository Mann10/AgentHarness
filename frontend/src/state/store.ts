/**
 * Presentation state store for the AgentHarness TUI.
 * Holds only presentation state — no business logic (D-14).
 * Completely independent of Ink/React (D-12).
 */

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'error';
  content: string;
  timestamp: number;
}

export interface ToolCallState {
  toolCallId: string;
  toolName: string;
  status: 'running' | 'completed' | 'error';
  result?: string;
}

export interface SessionInfo {
  id: string;
  title: string;
}

export interface StoreState {
  messages: Message[];
  activeToolCalls: ToolCallState[];
  isProcessing: boolean;
  streamedContent: string;
  activeSession: SessionInfo | null;
  sessions: SessionInfo[];
  error: string | null;
}

type Listener = () => void;

export class Store {
  private _state: StoreState;
  private _listeners = new Set<Listener>();

  constructor(initialState?: Partial<StoreState>) {
    this._state = {
      messages: [],
      activeToolCalls: [],
      isProcessing: false,
      streamedContent: '',
      activeSession: null,
      sessions: [],
      error: null,
      ...initialState,
    };
  }

  getState(): StoreState {
    return this._state;
  }

  /** Update state partially and notify listeners */
  setState(partial: Partial<StoreState>): void {
    this._state = { ...this._state, ...partial };
    for (const listener of this._listeners) {
      listener();
    }
  }

  /** Subscribe to state changes. Returns unsubscribe function. */
  subscribe(listener: Listener): () => void {
    this._listeners.add(listener);
    return () => this._listeners.delete(listener);
  }

  // --- Convenience methods ---

  addMessage(msg: Message): void {
    this.setState({ messages: [...this._state.messages, msg] });
  }

  /** Append to the currently streaming assistant message */
  appendStreamedContent(chunk: string): void {
    this.setState({ streamedContent: this._state.streamedContent + chunk });
  }

  /** Finalize a streamed message into a permanent assistant message */
  finalizeStream(requestId: string): void {
    if (this._state.streamedContent) {
      this.addMessage({
        id: `msg-${requestId}-${Date.now()}`,
        role: 'assistant',
        content: this._state.streamedContent,
        timestamp: Date.now(),
      });
    }
    this.setState({ streamedContent: '', isProcessing: false });
  }

  setProcessing(processing: boolean): void {
    this.setState({ isProcessing: processing });
  }

  addToolCall(toolCallId: string, toolName: string): void {
    this.setState({
      activeToolCalls: [
        ...this._state.activeToolCalls,
        { toolCallId, toolName, status: 'running' },
      ],
    });
  }

  updateToolCall(toolCallId: string, status: 'completed' | 'error', result?: string): void {
    this.setState({
      activeToolCalls: this._state.activeToolCalls.map(tc =>
        tc.toolCallId === toolCallId ? { ...tc, status, result } : tc
      ),
    });
  }

  setError(error: string | null): void {
    this.setState({ error });
  }
}

// Singleton instance
let _instance: Store | null = null;

export function createStore(): Store {
  if (!_instance) _instance = new Store();
  return _instance;
}
