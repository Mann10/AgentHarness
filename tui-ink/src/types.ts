export interface SessionSummary {
  id: string
  title: string | null
  created_at: string
  updated_at: string
  message_count: number
}

export interface TurnStartedPayload {
  session_id: string
  prompt: string
}

export interface ToolCallPayload {
  session_id: string
  tool_name: string
  arguments: Record<string, unknown> | null
  tool_call_id: string
}

export interface ToolResultPayload {
  session_id: string
  tool_name: string
  result: string
  tool_call_id: string
}

export interface TokenPayload {
  session_id: string
  chunk: string
  request_id: string
}

export interface ResponseCompletePayload {
  session_id: string
  content: string
  iterations: number
  tool_calls_made: number
  forced: boolean
}

export interface ErrorPayload {
  session_id: string
  error: string
}

export interface CancelledPayload {
  session_id: string
}

export type EventPayload =
  | { type: "turn_started"; payload: TurnStartedPayload }
  | { type: "tool_call"; payload: ToolCallPayload }
  | { type: "tool_result"; payload: ToolResultPayload }
  | { type: "token"; payload: TokenPayload }
  | { type: "response_complete"; payload: ResponseCompletePayload }
  | { type: "error"; payload: ErrorPayload }
  | { type: "cancelled"; payload: CancelledPayload }

export type AgentStatus = "idle" | "thinking" | "streaming" | "error"

export interface ToolCallStatus {
  id: string
  name: string
  args: Record<string, unknown> | null
  status: "running" | "success" | "error"
  result?: string
  duration?: number
  startedAt: number
}

export interface Message {
  id: string
  role: "user" | "assistant" | "notice" | "error"
  content: string
  timestamp: number
  isStreaming?: boolean
}

export interface AgentState {
  sessions: SessionSummary[]
  activeSessionId: string | null
  conversation: Message[]
  toolCalls: ToolCallStatus[]
  toolCallCount: number
  model: string
  status: AgentStatus
  tokenCount: number
  responseTime: string
  error: string | null
  busy: boolean
}
