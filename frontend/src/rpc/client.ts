import { StdioTransport } from './transport.js';
import type { RPCResponse, RPCNotification, EventPayload, RpcMethod } from './protocol.js';

export type EventHandler = (payload: EventPayload) => void;
export type RpcResult<T = unknown> = { success: true; data: T } | { success: false; error: string; code?: number };

export class RpcClient {
  private _transport: StdioTransport;
  private _requestId = 0;
  private _pending = new Map<number | string, { resolve: (res: RPCResponse) => void; reject: (err: Error) => void }>();
  private _eventHandlers = new Map<string, EventHandler[]>();

  constructor(command: string, args: string[]) {
    this._transport = new StdioTransport({
      command,
      args,
      onMessage: (line) => this._handleMessage(line),
      onError: (err) => console.error('[RPC] Transport error:', err),
      onClose: (code) => {
        console.warn('[RPC] Backend process exited with code', code);
        // Reject all pending requests
        for (const [, { reject }] of this._pending) {
          reject(new Error(`Backend process exited with code ${code}`));
        }
        this._pending.clear();
      },
    });
  }

  async start(): Promise<void> {
    await this._transport.start();
  }

  async stop(): Promise<void> {
    await this._transport.stop();
  }

  /** Send a request and wait for response */
  async request<T = unknown>(method: RpcMethod, params?: Record<string, unknown>): Promise<RpcResult<T>> {
    const id = ++this._requestId;
    const message = JSON.stringify({
      jsonrpc: '2.0',
      id,
      method,
      params: params ?? {},
    });

    return new Promise((resolve, reject) => {
      this._pending.set(id, {
        resolve: (res) => {
          if (res.error) {
            resolve({ success: false, error: res.error.message, code: res.error.code });
          } else {
            resolve({ success: true, data: res.result as T });
          }
        },
        reject,
      });

      try {
        this._transport.send(message);
      } catch (err) {
        this._pending.delete(id);
        reject(err);
      }

      // Timeout after 300s
      setTimeout(() => {
        if (this._pending.has(id)) {
          this._pending.delete(id);
          resolve({ success: false, error: 'Request timed out', code: -32000 });
        }
      }, 300_000);
    });
  }

  /** Fire-and-forget notification (no response expected) */
  notify(method: string, params?: Record<string, unknown>): void {
    const message = JSON.stringify({
      jsonrpc: '2.0',
      method,
      params: params ?? {},
    });
    this._transport.send(message);
  }

  /** Register an event handler for a notification type */
  on(eventType: string, handler: EventHandler): () => void {
    const handlers = this._eventHandlers.get(eventType) ?? [];
    handlers.push(handler);
    this._eventHandlers.set(eventType, handlers);
    // Return unsubscribe function
    return () => {
      const idx = handlers.indexOf(handler);
      if (idx >= 0) handlers.splice(idx, 1);
    };
  }

  get pid(): number | undefined { return this._transport.pid; }
  get isRunning(): boolean { return this._transport.isRunning; }

  // --- Internal ---

  private _handleMessage(line: string): void {
    let msg: RPCResponse | RPCNotification;
    try {
      msg = JSON.parse(line);
    } catch {
      console.error('[RPC] Failed to parse message:', line.slice(0, 100));
      return;
    }

    // Notification (has "method" field, no "id")
    if ('method' in msg && msg.method === 'event') {
      const notification = msg as unknown as RPCNotification;
      this._dispatchEvent(notification.params);
      return;
    }

    // Response (has "id" field)
    if ('id' in msg && msg.id != null) {
      const response = msg as RPCResponse;
      if (response.id == null) return;
      const pending = this._pending.get(response.id);
      if (pending) {
        this._pending.delete(response.id);
        pending.resolve(response);
      }
      return;
    }

    console.warn('[RPC] Unhandled message:', msg);
  }

  private _dispatchEvent(params: EventPayload): void {
    const handlers = this._eventHandlers.get(params.type);
    if (handlers) {
      for (const handler of handlers) {
        try { handler(params); } catch (err) {
          console.error(`[RPC] Event handler error for ${params.type}:`, err);
        }
      }
    }
  }
}
