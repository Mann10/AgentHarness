import { Box, Text } from "ink"

export function Footer() {
  return (
    <Box width="100%" paddingX={1}>
      <Text dimColor>[?] help</Text>
      <Text> </Text>
      <Text dimColor>[q] quit</Text>
      <Text> </Text>
      <Text dimColor>[Tab] panels</Text>
      <Text> </Text>
      <Text dimColor>[/] search</Text>
      <Text> </Text>
      <Text dimColor>[1-3] jump</Text>
    </Box>
  )
}
