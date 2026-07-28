import { useState, useEffect } from "react"
import { Text } from "ink"

interface StreamingTextProps {
  text: string
}

export function StreamingText({ text }: StreamingTextProps) {
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const timer = setInterval(() => {
      setVisible((v) => !v)
    }, 500)
    return () => clearInterval(timer)
  }, [])

  return (
    <Text color="white">
      {text}
      {visible ? <Text color="green">▊</Text> : <Text> </Text>}
    </Text>
  )
}
