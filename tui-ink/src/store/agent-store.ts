import { create } from "zustand"
import type {
  AgentState,
  AgentStatus,
  Message,
  ToolCallStatus,
  SessionSummary,
} from "../types.js"

let msgCounter = 0
const nextId = () => `msg_${++msgCounter}`
let toolCounter = 0
const nextToolId = () => `tool_${++toolCounter}`

interface AgentActions {
  setSessions: (sessions: SessionSummary[]) => void
  setActiveSession: (id: string | null) => void
  addUserMessage: (content: string) => void
  startAssistantMessage: () => void
  appendToken: (chunk: string) => void
  addAssistantMessage: (content: string) => void
  completeAssistantMessage: (content: string) => void
  addToolCall: (name: string, args: Record<string, unknown> | null, callId: string) => void
  updateToolResult: (callId: string, result: string) => void
  setToolCallError: (callId: string) => void
  addNotice: (text: string) => void
  addError: (error: string) => void
  setStatus: (status: AgentStatus) => void
  setModel: (model: string) => void
  setTokenCount: (count: number) => void
  setResponseTime: (time: string) => void
  setBusy: (busy: boolean) => void
  resetConversation: () => void
  clearToolCalls: () => void
  incrementToolCallCount: () => void
}

export type AgentStore = AgentState & AgentActions

const now = () => Date.now()

export const useAgentStore = create<AgentStore>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  conversation: [],
  toolCalls: [],
  toolCallCount: 0,
  model: "unknown",
  status: "idle",
  tokenCount: 0,
  responseTime: "",
  error: null,
  busy: false,

  setSessions: (sessions) => set({ sessions }),

  setActiveSession: (id) => set({ activeSessionId: id }),

  addUserMessage: (content) =>
    set((s) => ({
      conversation: [
        ...s.conversation,
        { id: nextId(), role: "user", content, timestamp: now() },
      ],
    })),

  startAssistantMessage: () =>
    set((s) => ({
      conversation: [
        ...s.conversation,
        {
          id: nextId(),
          role: "assistant",
          content: "",
          timestamp: now(),
          isStreaming: true,
        },
      ],
      status: "streaming",
    })),

  appendToken: (chunk) =>
    set((s) => {
      const msgs = [...s.conversation]
      const last = msgs[msgs.length - 1]
      if (last && last.role === "assistant" && last.isStreaming) {
        msgs[msgs.length - 1] = { ...last, content: last.content + chunk }
      }
      return { conversation: msgs }
    }),

  addAssistantMessage: (content) =>
    set((s) => ({
      conversation: [
        ...s.conversation,
        { id: nextId(), role: "assistant", content, timestamp: now() },
      ],
    })),

  completeAssistantMessage: (content) =>
    set((s) => {
      const msgs = [...s.conversation]
      const last = msgs[msgs.length - 1]
      if (last && last.role === "assistant" && last.isStreaming) {
        msgs[msgs.length - 1] = {
          ...last,
          content,
          isStreaming: false,
        }
      }
      return { conversation: msgs, status: content ? "idle" : "idle" }
    }),

  addToolCall: (name, args, callId) =>
    set((s) => ({
      toolCalls: [
        ...s.toolCalls,
        {
          id: nextToolId(),
          name,
          args,
          status: "running",
          startedAt: now(),
          result: undefined,
          duration: undefined,
        },
      ],
      toolCallCount: s.toolCallCount + 1,
    })),

  updateToolResult: (callId, result) =>
    set((s) => ({
      toolCalls: s.toolCalls.map((tc) => {
        if (tc.name === callId || tc.id === callId) {
          return {
            ...tc,
            status: "success" as const,
            result,
            duration: now() - tc.startedAt,
          }
        }
        return tc
      }),
    })),

  setToolCallError: (callId) =>
    set((s) => ({
      toolCalls: s.toolCalls.map((tc) => {
        if (tc.name === callId || tc.id === callId) {
          return { ...tc, status: "error" as const, duration: now() - tc.startedAt }
        }
        return tc
      }),
    })),

  addNotice: (text) =>
    set((s) => ({
      conversation: [
        ...s.conversation,
        { id: nextId(), role: "notice", content: text, timestamp: now() },
      ],
    })),

  addError: (error) =>
    set((s) => ({
      conversation: [
        ...s.conversation,
        { id: nextId(), role: "error", content: error, timestamp: now() },
      ],
      status: "error",
    })),

  setStatus: (status) => set({ status }),

  setModel: (model) => set({ model }),

  setTokenCount: (count) => set({ tokenCount: count }),

  setResponseTime: (time) => set({ responseTime: time }),

  setBusy: (busy) => set({ busy }),

  resetConversation: () =>
    set({
      conversation: [],
      toolCalls: [],
      toolCallCount: 0,
      status: "idle",
      error: null,
    }),

  clearToolCalls: () => set({ toolCalls: [] }),

  incrementToolCallCount: () =>
    set((s) => ({ toolCallCount: s.toolCallCount + 1 })),
}))
