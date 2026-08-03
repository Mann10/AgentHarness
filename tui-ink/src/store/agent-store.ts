import { create } from "zustand"
import type {
  AgentState,
  AgentStatus,
  Message,
  ToolCallStatus,
  SessionSummary,
  SessionMessage,
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
  truncateStreamingMessage: () => void
  addToolCall: (name: string, args: Record<string, unknown> | null, callId: string) => void
  updateToolResult: (callId: string, result: string) => void
  setToolCallError: (callId: string) => void
  addNotice: (text: string) => void
  addSkillNotice: (text: string, tone?: "success" | "error") => void
  addError: (error: string) => void
  setStatus: (status: AgentStatus) => void
  setModel: (model: string) => void
  setTokenCount: (count: number) => void
  setResponseTime: (time: string) => void
  setBusy: (busy: boolean) => void
  resetConversation: () => void
  loadConversation: (messages: SessionMessage[]) => void
  clearToolCalls: () => void
  incrementToolCallCount: () => void
  addLoadedSkill: (name: string) => void
}

export type AgentStore = AgentState & AgentActions

const now = () => Date.now()

// Returns the index of the LAST message with role "assistant" AND isStreaming, or -1.
// CR-01/T-16-13: a notice appended mid-stream (e.g. /skill ack) becomes the array
// tail — streaming mutations must target the streaming message wherever it sits,
// never the array tail.
function lastStreamingIdx(msgs: Message[]): number {
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === "assistant" && msgs[i].isStreaming) return i
  }
  return -1
}

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
  loadedSkills: [] as string[],

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
      const idx = lastStreamingIdx(msgs)
      if (idx !== -1) msgs[idx] = { ...msgs[idx], content: msgs[idx].content + chunk }
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
      const idx = lastStreamingIdx(msgs)
      if (idx !== -1) msgs[idx] = { ...msgs[idx], content, isStreaming: false }
      return { conversation: msgs, status: "idle" }  // IN-01: degenerate ternary removed
    }),

  truncateStreamingMessage: () =>
    set((s) => {
      const msgs = [...s.conversation]
      const idx = lastStreamingIdx(msgs)
      if (idx !== -1) {
        msgs[idx] = { ...msgs[idx], isStreaming: false, truncated: true }
        return { conversation: msgs, status: "idle" }
      }
      return { conversation: msgs }
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

  addLoadedSkill: (name) =>
    set((s) =>
      s.loadedSkills.includes(name)
        ? s                                  // belt-and-suspenders; backend dedups (D-07)
        : { loadedSkills: [...s.loadedSkills, name] }
    ),

  addSkillNotice: (text, tone) =>
    set((s) => ({
      conversation: [
        ...s.conversation,
        { id: nextId(), role: "notice", content: text, timestamp: now(), ...(tone && { tone }) },
      ],
    })),   // NEVER touches status/busy/error — addError is NOT reused (UI-SPEC §6.3)

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
      loadedSkills: [],
    }),

  loadConversation: (messages) =>
    set({
      conversation: messages.map((m) => ({
        id: nextId(),
        role: m.role,
        content: m.content,
        timestamp: now(),
      })),
      toolCalls: [],
      toolCallCount: 0,
      status: "idle",
      error: null,
      loadedSkills: [],
    }),

  clearToolCalls: () => set({ toolCalls: [] }),

  incrementToolCallCount: () =>
    set((s) => ({ toolCallCount: s.toolCallCount + 1 })),
}))
