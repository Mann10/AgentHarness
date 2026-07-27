// JSON-RPC 2.0 message types

export interface RPCRequest {
  jsonrpc: "2.0";
  id: number | string;
  method: string;
  params?: Record<string, unknown>;
}

export interface RPCError {
  code: number;
  message: string;
  data?: unknown;
}

export interface RPCResponse {
  jsonrpc: "2.0";
  id: number | string | null;
  result?: unknown;
  error?: RPCError;
}

export interface EventPayload {
  type: string;
  request_id: string;
  payload: Record<string, unknown>;
}

export interface RPCNotification {
  jsonrpc: "2.0";
  method: "event";
  params: EventPayload;
}

/** Notification type constants (matching D-09) */
export const NOTIFICATION_TYPES = {
  TURN_STARTED: "turn_started",
  TOOL_CALL: "tool_call",
  TOOL_RESULT: "tool_result",
  TOKEN: "token",
  RESPONSE_COMPLETE: "response_complete",
  CANCELLED: "cancelled",
  ERROR: "error",
} as const;

/** RPC method names (matching D-06) */
export const RPC_METHODS = [
  "chat",
  "cancel",
  "sessions.list",
  "sessions.switch",
  "sessions.create",
  "sessions.delete",
  "ping",
] as const;

export type RpcMethod = typeof RPC_METHODS[number];
export type NotificationType = typeof NOTIFICATION_TYPES[keyof typeof NOTIFICATION_TYPES];

/** Typed params for each RPC method */
export interface ChatParams { prompt: string }
export interface SessionsSwitchParams { session_id: string }
export interface SessionsDeleteParams { session_id: string }
export type SessionsCreateParams = Record<string, never>;
export type CancelParams = Record<string, never>;
export type SessionsListParams = Record<string, never>;
export type PingParams = Record<string, never>;
