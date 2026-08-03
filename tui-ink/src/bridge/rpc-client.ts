import { existsSync, createWriteStream } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"
import { spawn, type ChildProcess } from "node:child_process"
import { createInterface, type Interface as ReadlineInterface } from "node:readline"
import { useAgentStore } from "../store/agent-store.js"
import type { EventPayload, SessionMessage, SessionSummary, SkillLoadResult } from "../types.js"

let reqId = 0
const nextReqId = () => ++reqId

function findProjectRoot(start: string): string {
  let dir = start
  for (let i = 0; i < 10; i++) {
    if (existsSync(join(dir, "main.py"))) return dir
    const parent = dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  return start
}

interface RpcClientOptions {
  pythonCmd?: string
  cwd?: string
}

export class RpcClient {
  private proc: ChildProcess | null = null
  private rl: ReadlineInterface | null = null
  private pending = new Map<number, { resolve: (v: unknown) => void; reject: (e: Error) => void }>()
  private buffer = ""
  private _connected = false

  get connected(): boolean {
    return this._connected
  }

  async start(options: RpcClientOptions = {}): Promise<void> {
    const python = options.pythonCmd ?? "python"
    const cwd = findProjectRoot(options.cwd ?? process.cwd())

    this.proc = spawn(python, ["main.py", "--rpc"], {
      cwd,
      stdio: ["pipe", "pipe", "pipe"],
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    })

    // Route Python stderr to a file so debug logs don't corrupt the TUI
    const stderrStream = createWriteStream("tui-ink-rpc.log", { flags: "a" })
    this.proc.stderr!.pipe(stderrStream)

    this.rl = createInterface({ input: this.proc.stdout! })

    this.rl.on("line", (line: string) => {
      const trimmed = line.trim()
      if (!trimmed) return
      try {
        const msg = JSON.parse(trimmed)
        this.handleMessage(msg)
      } catch {
        // skip non-JSON lines (e.g. startup logs piped to stdout despite our intent)
      }
    })

    this.proc.on("exit", (code) => {
      this._connected = false
      for (const { reject } of this.pending.values()) {
        reject(new Error(`RPC process exited with code ${code}`))
      }
      this.pending.clear()
    })

    this.proc.on("error", (err) => {
      this._connected = false
      for (const { reject } of this.pending.values()) {
        reject(err)
      }
      this.pending.clear()
    })

    // Wait for the process to be ready by sending a ping
    await this.request("ping")
    this._connected = true
  }

  async request(method: string, params?: Record<string, unknown>): Promise<unknown> {
    return new Promise((resolve, reject) => {
      const id = nextReqId()
      this.pending.set(id, { resolve, reject })
      const req = { jsonrpc: "2.0", id, method, params: params ?? null }
      this.proc?.stdin?.write(JSON.stringify(req) + "\n")

      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id)
          reject(new Error(`RPC request "${method}" timed out`))
        }
      }, 30_000)
    })
  }

  async submitPrompt(prompt: string): Promise<void> {
    await this.request("chat", { prompt })
  }

  async cancel(): Promise<void> {
    await this.request("cancel")
  }

  async listSessions(): Promise<SessionSummary[]> {
    const result = await this.request("sessions.list")
    return result as SessionSummary[]
  }

  async switchSession(sessionId: string): Promise<boolean> {
    const result = (await this.request("sessions.switch", { session_id: sessionId })) as {
      success: boolean
    }
    return result.success
  }

  async createSession(): Promise<string> {
    const result = (await this.request("sessions.create")) as { session_id: string }
    return result.session_id
  }

  async getActiveSession(): Promise<string | null> {
    const result = (await this.request("sessions.active")) as { session_id: string | null }
    return result.session_id
  }

  async deleteSession(sessionId: string): Promise<boolean> {
    const result = (await this.request("sessions.delete", { session_id: sessionId })) as {
      deleted: boolean
    }
    return result.deleted
  }

  async loadSkill(name: string): Promise<SkillLoadResult> {
    return (await this.request("skills.load", { name })) as SkillLoadResult
  }

  async getSessionHistory(sessionId: string): Promise<SessionMessage[]> {
    const result = (await this.request("sessions.get", { session_id: sessionId })) as
      | { messages: SessionMessage[] }
      | { error: string }
    if ("error" in result) {
      throw new Error(result.error)
    }
    return result.messages
  }

  async ping(): Promise<void> {
    await this.request("ping")
  }

  async stop(): Promise<void> {
    if (this.proc) {
      this.proc.stdin?.end()
      this.proc.kill("SIGTERM")
      this.proc = null
    }
    this.rl?.close()
    this.rl = null
    this._connected = false
  }

  private handleMessage(msg: Record<string, unknown>): void {
    const store = useAgentStore.getState()

    // JSON-RPC response
    if ("id" in msg && msg.id !== undefined && msg.id !== null) {
      const id = Number(msg.id)
      const pending = this.pending.get(id)
      if (!pending) return
      this.pending.delete(id)

      if (msg.error) {
        pending.reject(new Error((msg.error as { message?: string }).message ?? "RPC error"))
      } else {
        pending.resolve(msg.result)
      }
      return
    }

    // JSON-RPC notification (event)
    if (msg.method === "event") {
      const params = msg.params as {
        type: string
        request_id: string
        payload: Record<string, unknown>
      }
      if (!params) return
      this.handleEvent(params)
    }
  }

  private handleEvent(params: {
    type: string
    request_id: string
    payload: Record<string, unknown>
  }): void {
    const store = useAgentStore.getState()
    const { type, payload } = params

    switch (type) {
      case "turn_started": {
        const p = payload as { session_id: string; prompt: string }
        store.setStatus("thinking")
        store.addUserMessage(p.prompt)
        store.clearToolCalls()
        break
      }
      case "tool_call": {
        const p = payload as {
          session_id: string
          tool_name: string
          arguments: Record<string, unknown> | null
          tool_call_id: string
        }
        store.addToolCall(p.tool_name, p.arguments, p.tool_call_id)
        store.setStatus("thinking")
        break
      }
      case "tool_result": {
        const p = payload as {
          session_id: string
          tool_name: string
          result: string
          tool_call_id: string
        }
        store.updateToolResult(p.tool_name, p.result)
        break
      }
      case "token": {
        const p = payload as { session_id: string; chunk: string; request_id: string }
        // Start assistant message on first token
        const state = useAgentStore.getState()
        const lastMsg = state.conversation[state.conversation.length - 1]
        if (!lastMsg || lastMsg.role !== "assistant" || !lastMsg.isStreaming) {
          store.startAssistantMessage()
        }
        store.appendToken(p.chunk)
        break
      }
      case "response_complete": {
        const p = payload as {
          session_id: string
          content: string
          iterations: number
          tool_calls_made: number
          forced: boolean
        }
        const state = useAgentStore.getState()
        const lastMsg = state.conversation[state.conversation.length - 1]
        if (lastMsg && lastMsg.role === "assistant" && lastMsg.isStreaming) {
          store.completeAssistantMessage(p.content)
        } else {
          store.addAssistantMessage(p.content)
        }
        store.setStatus("idle")
        store.setBusy(false)
        break
      }
      case "error": {
        const p = payload as { session_id: string; error: string }
        store.truncateStreamingMessage()
        store.addError(p.error)
        store.setStatus("idle")
        store.setBusy(false)
        break
      }
      case "cancelled": {
        store.truncateStreamingMessage()
        store.addNotice("Cancelled")
        store.setStatus("idle")
        store.setBusy(false)
        break
      }
      case "skill_loaded": {
        // D-07/D-08: chip state ONLY — no notice, no stream message,
        // never touches status/busy (ROADMAP criterion 4). Model-driven loads
        // must not inject into the conversation.
        const p = payload as { skill: string }
        store.addLoadedSkill(p.skill)
        break
      }
    }
  }
}
