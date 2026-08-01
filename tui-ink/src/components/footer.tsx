import { Box, Text } from "ink"

export function Footer() {
  return (
    <Box width="100%" paddingX={1}>
      <Text dimColor>[?] help</Text>
      <Text> </Text>
      <Text dimColor>[/session] sessions</Text>
      <Text> </Text>
      <Text dimColor>[/new] new chat</Text>
      <Text> </Text>
      <Text dimColor>[Tab] panels</Text>
      <Text> </Text>
      <Text dimColor>[q] quit</Text>
    </Box>
  )
}
