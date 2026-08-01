import { useState, useEffect, useCallback } from "react"
import { Box, Text, useFocus, useFocusManager, useInput, useApp } from "ink"
import { Header } from "./components/header.js"
import { Footer } from "./components/footer.js"
import { SessionPicker } from "./components/session-picker.js"
import { DatePanel } from "./panels/date-panel.js"
import { ConversationPanel } from "./panels/conversation-panel.js"
import { ToolMonitorPanel } from "./panels/tool-monitor-panel.js"
import { useAgentStore } from "./store/agent-store.js"
import { RpcClient } from "./bridge/rpc-client.js"

interface AppProps {
  client: RpcClient
  cwd?: string
}

function FocusablePanel({
  id,
  children,
}: {
  id: string
  children: (focused: boolean) => React.ReactNode
}) {
  const { isFocused } = useFocus({ id })
  return <>{children(isFocused)}</>
}

function InputBar({ client, onOpenPicker }: { client: RpcClient; onOpenPicker: () => void }) {
  const { busy } = useAgentStore()
  const [input, setInput] = useState("")
  const { isFocused } = useFocus({ id: "input", autoFocus: true })

  useInput(
    (char, key) => {
      if (!isFocused) return

      if (key.return) {
        const trimmed = input.trim()
        if (!trimmed) return
        if (trimmed === "/session") {
          onOpenPicker()                                  // D-06: open full-screen overlay
        } else if (trimmed === "/new") {
          // D-11/D-12: immediate fresh start — create, switch active, clear view. No confirm.
          client.createSession().then((id) => {
            const store = useAgentStore.getState()
            store.setActiveSession(id)
            store.resetConversation()
          })
        } else if (trimmed === "/sessions") {
          client.listSessions().then((sessions) => {
            useAgentStore.getState().setSessions(sessions)
          })
        } else {
          client.submitPrompt(trimmed)
        }
        setInput("")
        return
      }

      if (key.backspace || key.delete) {
        setInput((prev) => prev.slice(0, -1))
        return
      }

      if (char && !key.ctrl && !key.meta) {
        setInput((prev) => prev + char)
      }
    },
    { isActive: isFocused },
  )

  return (
    <Box borderStyle="single" borderColor={isFocused ? "green" : "gray"} width="100%">
      <Text bold color="yellow">
        ›{" "}
      </Text>
      <Text color="white">{input}</Text>
      {isFocused && <Text color="green">▊</Text>}
    </Box>
  )
}

export function App({ client, cwd }: AppProps) {
  const { exit } = useApp()
  const { enableFocus, disableFocus } = useFocusManager()
  const { status } = useAgentStore()
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sessions, setSessions] = useState<ReturnType<typeof useAgentStore.getState>["sessions"]>([])
  const [pickerOpen, setPickerOpen] = useState(false)

  useEffect(() => {
    enableFocus()
    return () => disableFocus()
  }, [enableFocus, disableFocus])

  useEffect(() => {
    client
      .start({ cwd })
      .then(() => {
        setConnected(true)
        return client.listSessions()
      })
      .then((sessions) => {
        useAgentStore.getState().setSessions(sessions)
      })
      .catch((err: Error) => {
        setError(err.message)
      })

    return () => {
      client.stop().catch(() => {})
    }
  }, [client])

  useInput((input) => {
    if (pickerOpen) return
    if (input === "q") {
      client.stop().then(() => exit()).catch(() => exit())
    }
  })

  if (error) {
    return (
      <Box flexDirection="column" padding={2}>
        <Text color="red" bold>
          Failed to connect:
        </Text>
        <Text color="red">{error}</Text>
        <Text dimColor>
          Make sure you're in the AgentHarness project root and Python deps are installed.
        </Text>
        <Text dimColor>Press q to quit.</Text>
      </Box>
    )
  }

  if (!connected) {
    return (
      <Box padding={2}>
        <Text color="cyan">Connecting to AgentHarness...</Text>
      </Box>
    )
  }

  if (pickerOpen) {
    return <SessionPicker client={client} onClose={() => setPickerOpen(false)} />
  }

  return (
    <Box flexDirection="column" height="100%">
      <Header />
      <Box flexGrow={1} flexDirection="row">
        <FocusablePanel id="conversation">
          {(focused) => <ConversationPanel focused={focused} />}
        </FocusablePanel>
        <DatePanel />
      </Box>
      <FocusablePanel id="tool-monitor">
        {(focused) => <ToolMonitorPanel focused={focused} />}
      </FocusablePanel>
      <FocusablePanel id="input">
        {(focused) => <InputBar client={client} onOpenPicker={() => setPickerOpen(true)} />}
      </FocusablePanel>
      <Footer />
    </Box>
  )
}
