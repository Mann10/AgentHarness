# Phase 9: TypeScript TUI + JSON-RPC Adapter — Research

**Date:** 2026-07-27

## 1. Ink (React for Terminal UIs)

### Core Library
- **Library:** `ink` v6.5.1 (vadimdemedes/ink) — 33k stars, 2.1M weekly downloads
- **Pattern:** Custom React renderer targeting terminal stdout (not browser DOM)
- **License:** MIT

### Architecture
- Components render to terminal via Yoga layout engine (Flexbox-based)
- Component tree re-renders on state changes (reactive, like browser React)
- Full React hooks support: `useState`, `useEffect`, `useMemo`, custom hooks

### Core Components
| Component | Purpose |
|-----------|---------|
| `<Box>` | Flexbox container — `flexDirection`, `justifyContent`, `width`, `height`, `padding`, `margin`, `borderStyle` |
| `<Text>` | Styled text — `color`, `backgroundColor`, `bold`, `italic`, `dimColor` |
| `<Static>` | Performance optimization — renders children only once (for logs, history) |
| `<Newline>` | Explicit newline insertion |

### Key Hooks
| Hook | Purpose |
|------|---------|
| `useInput(input, handler)` | Raw keyboard input (stdin) |
| `useFocus({id})` | Focus management between components |
| `useFocusManager()` | Programmatic focus control (focusNext, focusPrevious) |
| `useApp()` | App lifecycle — `exit()` method |
| `useStdoutDimensions()` | Terminal width/height — handle resize |

### Environment & Setup
```
npm install ink react
npm install -D @types/react
npx create-ink-app --typescript  # scaffolding
```

### Anti-Patterns & Pitfalls
- **No `console.log`** — breaks Ink layout. Use stderr or file logging.
- **Limit rendered nodes** — only render what fits on screen. Use windowing.
- **Handle resize** — Use `useStdoutDimensions()` for dynamic layout.
- **Not for simple scripts** — Ink has Node.js startup overhead. Use `prompts`/`inquirer` for one-off questions.

### Ecosystem
- **InkUI** (inkui-lib.vercel.app) — shadcn/ui for terminal UIs, 32+ components, copy-paste ownership
- **ink-testing-library** — Testing utilities for Ink components
- **ink-text-input** — Single-line text input component
- **ink-markdown** — Markdown rendering in terminal
- **React Devtools** — Optional debugging via `DEV=true`

---

## 2. JSON-RPC 2.0 Over Stdio Transport

### Protocol Standard (from MCP specification — industry reference)
- **Wire format:** NDJSON (newline-delimited JSON) — each JSON message on its own line, terminated with `\n`
- **Encoding:** UTF-8
- **Transport:** stdin/stdout pipes between subprocesses

### JSON-RPC 2.0 Message Format

**Request:**
```json
{"jsonrpc":"2.0","id":1,"method":"methodName","params":{"key":"value"}}
```

**Success Response:**
```json
{"jsonrpc":"2.0","id":1,"result":{"data":"value"}}
```

**Error Response:**
```json
{"jsonrpc":"2.0","id":1,"error":{"code":-32000,"message":"Error message","data":{}}}
```

**Notification (no id → no response):**
```json
{"jsonrpc":"2.0","method":"event","params":{"type":"token","requestId":"...","payload":{...}}}
```

### Stdio Transport Rules (MCP standard)
1. Client launches server as subprocess
2. Server reads JSON-RPC messages from stdin; writes to stdout
3. Messages delimited by newlines, MUST NOT contain embedded newlines
4. Server MAY write UTF-8 strings to stderr for logging
5. Server MUST NOT write anything to stdout that isn't a valid JSON-RPC message
6. Client MUST NOT write anything to server's stdin that isn't a valid JSON-RPC message
7. **Must flush after every message** (critical for Python stdio buffering)

### Standard JSON-RPC Error Codes
| Code | Meaning |
|------|---------|
| -32700 | Parse error (invalid JSON) |
| -32600 | Invalid Request |
| -32601 | Method not found |
| -32602 | Invalid params |
| -32603 | Internal error |
| -32000..-32099 | Server error |

### Python Implementation Pattern
```python
import sys, json

# Read
for line in sys.stdin:
    msg = json.loads(line)
    # process

# Write (must flush!)
sys.stdout.write(json.dumps(response) + "\n")
sys.stdout.flush()
```

### Node.js Implementation Pattern
```javascript
import { spawn } from 'child_process';

const proc = spawn('python', ['-m', 'agentharness', '--rpc'], {
  stdio: ['pipe', 'pipe', 'pipe']
});

// Read stdout line-by-line
let buffer = '';
proc.stdout.on('data', (chunk) => {
  buffer += chunk.toString();
  const lines = buffer.split('\n');
  buffer = lines.pop(); // incomplete line
  for (const line of lines) {
    if (line.trim()) handleMessage(JSON.parse(line));
  }
});

// Write to stdin
proc.stdin.write(JSON.stringify(request) + '\n');

// Handle stderr (log only)
proc.stderr.on('data', (chunk) => logger.warn(chunk.toString()));

// Cleanup
proc.on('exit', (code) => cleanup());
```

### Related Libraries (informational — hand-roll per D-05/06)
- `node-stdio-jsonrpc` — TypeScript JSON-RPC stdio client
- `json-rpc-2.0` (npm) — Core JSON-RPC 2.0 implementation
- `json-rpc` (PyPI) — Python JSON-RPC protocol implementation
- **Decision:** Hand-roll per D-05 and D-06 (small surface, no library needed)

---

## 3. TypeScript Toolchain Setup (Node.js + Ink project)

### Recommended Stack
| Layer | Tool | Purpose |
|-------|------|---------|
| Runtime | Node.js 18+ (LTS) | Required by Ink |
| Package Manager | npm or pnpm | Dependency management |
| Language | TypeScript 5.x | Type safety |
| Dev Runner | tsx | `tsx --watch src/index.ts` — zero-config TypeScript execution |
| Type Checker | tsc | `tsc --noEmit` — separate type checking (CI/pre-commit) |
| Bundler (prod) | esbuild | `esbuild src/index.ts --platform=node --bundle --outfile=dist/index.js` |
| Test Runner | Vitest | Native TypeScript support, Jest-compatible, fast watch mode |

### tsconfig.json (recommended for Ink app)
```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "target": "es2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "jsx": "react-jsx",
    "jsxImportSource": "ink",
    "noEmit": true,
    "lib": ["es2022"],
    "verbatimModuleSyntax": true
  },
  "include": ["src"]
}
```

### Package.json
```json
{
  "type": "module",
  "scripts": {
    "dev": "tsx --watch src/index.ts",
    "build": "esbuild src/index.ts --platform=node --bundle --outfile=dist/index.js",
    "typecheck": "tsc --noEmit",
    "test": "vitest"
  }
}
```

### Project Structure (per D-13)
```
frontend/
├── package.json
├── tsconfig.json
├── esbuild.config.js (optional)
├── src/
│   ├── index.ts          # Entry point
│   ├── App.tsx           # Root React component
│   ├── rpc/
│   │   ├── client.ts     # JSON-RPC client (request/response/notification dispatch)
│   │   ├── protocol.ts   # TypeScript types for JSON-RPC messages
│   │   └── transport.ts  # Stdio transport (spawn, read/write, lifecycle)
│   ├── state/
│   │   ├── store.ts      # State store (Zustand or useReducer)
│   │   └── reducers.ts   # State reduction logic
│   └── ui/
│       ├── components/   # Reusable components (MessageCard, ToolCallCard, etc.)
│       └── screens/      # Screen-level components (Conversation, SessionPicker, etc.)
```

---

## 4. Subprocess IPC (Node.js spawns Python)

### Architecture Pattern
```
┌───────────────────────────┐     stdin (JSON-RPC)     ┌────────────────────┐
│  TypeScript/Ink TUI       │ ──────────────────────▶  │  Python Backend    │
│  (Node.js parent process) │                          │  (child process)   │
│                           │ ◀────────────────────── │  python -m agenth- │
│                           │  stdout (NDJSON events)  │  arness --rpc      │
└───────────────────────────┘                          └────────────────────┘
                                stderr → captured/logged
```

### Python Side Details
- **Entry point:** `python -m agentharness --rpc` (or `python -m agentharness.rpc.server`)
- **Stdout is JSON-RPC ONLY** — no print(), no logging to stdout
- **Stderr for logging** — Python `logging` module writes to stderr
- **Must flush stdout** after every message: `sys.stdout.flush()` or `print(..., flush=True)`
- **Read loop:** `for line in sys.stdin: msg = json.loads(line)` (blocks until next message)
- **Environment:** `PYTHONUNBUFFERED=1` recommended to prevent stdio buffering issues

### Node.js Side Details
- **Spawn:** `spawn('python', ['-m', 'agentharness', '--rpc'], { stdio: ['pipe', 'pipe', 'pipe'] })`
- **stdin channel:** Write requests as NDJSON lines
- **stdout channel:** Read NDJSON responses + event notifications
- **stderr channel:** Capture and log (or pipe to parent stderr)
- **Line buffering:** Buffer partial reads on stdout, split on `\n`
- **Lifecycle:**
  - On TUI start → spawn Python subprocess
  - On `ping` → verify readiness handshake
  - On TUI exit → send SIGTERM, wait for exit, force kill after timeout

### Key Implementation Details
1. **Python unbuffered:** Use `-u` flag or `PYTHONUNBUFFERED=1` env var
2. **RPC Handshake:** On startup, Python sends a `ping` success (or `server/ready` notification) to confirm readiness
3. **Backpressure:** Node.js may write faster than Python reads — simple NDJSON is self-framing, Python reads one line per message
4. **Error isolation:** Python crash → subprocess exits → TUI detects via `close` event → displays error, offers restart
5. **Windows compatibility:** Use `'python'` command (resolve via PATH) or full path. On Windows, `process.kill()` sends SIGTERM via `taskkill`.

---

## Migration Strategy (per D-21)

```
Phase 9 execution order:
1. RPC adapter + --rpc mode         (backend/rpc/ module)
2. TypeScript client skeleton        (frontend/ — rpc client, verify streaming)
3. Core screens                      (conversation view + input bar)
4. Feature parity                    (tool calls, status panel, sessions, stats)
5. Make TS TUI default (post-Phase 9)
```

---

## Key References

- **Ink:** https://github.com/vadimdemedes/ink (v6.5.1, MIT)
- **MCP stdio transport spec:** https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- **JSON-RPC 2.0 spec:** https://www.jsonrpc.org/specification
- **NDJSON spec:** http://ndjson.org/
- **esbuild docs:** https://esbuild.github.io/
- **tsx runner:** https://github.com/privatenumber/tsx
- **Node.js child_process:** https://nodejs.org/api/child_process.html
- **Node.js + Python IPC patterns:** https://dev.to/besworks/inter-process-communication-between-nodejs-and-python-djf
