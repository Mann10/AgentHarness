import { render } from "ink"
import { App } from "./app.js"
import { RpcClient } from "./bridge/rpc-client.js"

const args = process.argv.slice(2)
let cwd = process.cwd()
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--cwd" && i + 1 < args.length) {
    cwd = args[i + 1]
    i++
  }
}

const client = new RpcClient()

const { waitUntilExit } = render(<App client={client} cwd={cwd} />)

waitUntilExit().catch(() => {
  client.stop()
})
