import { Box, Text } from "ink"
import type { Message } from "../types.js"
import { StreamingText } from "./streaming-text.js"

const NOTICE_OK = "✓"                    // green, bold — success tone (09-UI-SPEC §6)
const NOTICE_ERR = "✗"                   // red, bold — error tone (09-UI-SPEC §6)

const CARD_LABELS: Record<Message["role"], string> = {
  user: "You",
  assistant: "Assistant",
  notice: "Notice",
  error: "Error",
}

const CARD_BORDER: Record<Message["role"], "yellow" | "green" | "gray" | "red"> = {
  user: "yellow",       // $secondary — user identity (09/11-UI-SPEC)
  assistant: "green",   // $primary — assistant identity
  notice: "gray",       // dim/neutral treatment (locked)
  error: "red",         // $error
}

const CARD_TINT: Record<Message["role"], string> = {
  user: "#332a00",      // dark muted yellow-brown (locked D-04)
  assistant: "#002a1f", // dark muted green (locked D-04)
  notice: "#2a2a2a",    // neutral dark gray (locked D-04)
  error: "#2a2a2a",     // neutral dark gray (locked D-04)
}

function supportsTruecolor(): boolean {
  if (process.env.COLORTERM === "truecolor") return true
  try {
    const s = process.stdout as unknown as { hasColors?: (count?: number) => boolean }
    return s.hasColors?.(2 ** 24) ?? false
  } catch {
    return false
  }
}

const HAS_TRUECOLOR = supportsTruecolor()   // evaluated once at module load

interface MessageProps {
  message: Message
}

function renderLabel(role: Message["role"]) {
  switch (role) {
    case "user":
      return (
        <Text bold color="yellow">
          {CARD_LABELS[role]}
        </Text>
      )
    case "assistant":
      return (
        <Text bold color="green">
          {CARD_LABELS[role]}
        </Text>
      )
    case "notice":
      return <Text dimColor>{CARD_LABELS[role]}</Text>
    case "error":
      return (
        <Text bold color="red">
          {CARD_LABELS[role]}
        </Text>
      )
  }
  return null
}

function renderContent(message: Message) {
  if (message.role === "user") {
    return <Text color="white">{message.content}</Text>
  }

  if (message.role === "assistant") {
    return (
      <Box>
        <Text bold color="green">
          {message.isStreaming ? "▸" : " "}{" "}
        </Text>
        {message.isStreaming ? (
          <StreamingText text={message.content} />
        ) : (
          <Text color="white">{message.content}</Text>
        )}
        {message.truncated && (
          <Text color="yellow" dimColor italic>
            {" "}(truncated)
          </Text>
        )}
      </Box>
    )
  }

  if (message.role === "notice") {
    if (message.tone === "success") {
      return (
        <Text color="green" bold>
          {NOTICE_OK} {message.content}
        </Text>
      )
    }
    if (message.tone === "error") {
      return (
        <Text color="red" bold>
          {NOTICE_ERR} {message.content}
        </Text>
      )
    }
    return (
      <Text dimColor italic>
        {message.content}
      </Text>
    )
  }

  if (message.role === "error") {
    return (
      <Text color="red" bold>
        ✗ {message.content}
      </Text>
    )
  }

  return null
}

export function MessageCard({ message }: MessageProps) {
  return (
    <Box
      flexDirection="column"
      borderStyle="single"
      borderColor={CARD_BORDER[message.role]}
      backgroundColor={HAS_TRUECOLOR ? CARD_TINT[message.role] : undefined}
      paddingX={1}
    >
      <Box>{renderLabel(message.role)}</Box>
      <Box>{renderContent(message)}</Box>
    </Box>
  )
}
