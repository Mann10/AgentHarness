---
phase: 09-ts-tui-json-rpc
plan: 02
subsystem: rpc
tags: typescript, ink, react, json-rpc, ndjson, esbuild, stdio

requires:
  - phase: 09-ts-tui-json-rpc
    plan: 01
    provides: Python JSON-RPC 2.0 backend adapter (protocol.py, server.py, dispatcher.py, adapter.py)

provides:
  - frontend/ directory with TypeScript + Ink + esbuild toolchain
  - frontend/src/rpc/ module (protocol.ts, transport.ts, client.ts)
  - RPC client that can spawn Python backend, send/receive JSON-RPC messages, and stream event notifications

affects:
  - 09-03 onward (TUI screens, state store, UI components)

tech-stack:
  added:
    - ink 5.2.1 (React for terminal UIs)
    - react 18.3.1
    - esbuild 0.24.x (bundler)
    - tsx 4.x (dev runner)
    - typescript 5.5+
  patterns:
    - JSON-RPC 2.0 client with NDJSON framing over stdio
    - StdioTransport class wrapping child_process.spawn with line buffering
    - RpcClient class with request/notification/event dispatch separation
    - Protocol types matching Python backend's JSON-RPC 2.0 schema

key-files:
  created:
    - frontend/package.json
    - frontend/tsconfig.json (strict, es2022, ESNext modules)
    - frontend/esbuild.config.mjs
    - frontend/.gitignore
    - frontend/src/index.tsx
    - frontend/src/App.tsx
    - frontend/src/rpc/protocol.ts
    - frontend/src/rpc/transport.ts
    - frontend/src/rpc/client.ts
  modified: []

key-decisions:
  - "Ink v5's jsxImportSource must be 'react' not 'ink' because Ink 5.2.1 doesn't export a jsx-runtime module path"
  - "Entry point renamed to .tsx extension because both esbuild and tsc require JSX content in .tsx files"
  - "esbuild config needs jsx: 'automatic', jsxImportSource, and loader: { '.ts': 'tsx' } for JSX handling"
  - "RPC_METHODS array matches 7 methods from D-06: chat, cancel, sessions.{list,switch,create,delete}, ping"
  - "Notification type constants match D-09: turn_started, tool_call, tool_result, token, response_complete, cancelled, error"

requirements-completed:
  - D-05 (NDJSON framing, full flush on every message)
  - D-08 (Event-to-notification mapping)
  - D-10 (frontend/ with React + Ink)
  - D-11 (Custom terminal components on Ink)
  - D-12 (App logic independent of Ink/React)
  - D-13 (frontend/ structure: rpc/, state/, ui/)
  - D-15 (Frontend never imports Python logic)

duration: 5min
completed: 2026-07-27
---

# Phase 9 Plan 2: TypeScript/Ink Frontend Scaffolding + JSON-RPC 2.0 Client Library

**TypeScript project with Ink + esbuild toolchain and layered RPC client module — StdioTransport, RpcClient, and protocol types matching the Python backend's JSON-RPC 2.0 schema**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-27T22:20:38Z
- **Completed:** 2026-07-27T22:25:57Z
- **Tasks:** 2
- **Files created:** 10

## Accomplishments

- **TypeScript + Ink project scaffolded** — `frontend/` with package.json, tsconfig.json (strict mode, es2022), esbuild bundler config, .gitignore
- **Six source files created** — `src/index.tsx` (entry point with Ink render), `src/App.tsx` (placeholder component), `src/rpc/protocol.ts`, `src/rpc/transport.ts`, `src/rpc/client.ts`
- **StdioTransport class** — spawns Python subprocess, reads NDJSON stdout with line buffering, writes to stdin, handles lifecycle (start/send/stop/pid/isRunning)
- **RpcClient class** — JSON-RPC 2.0 request/response dispatch (request() with timeout, notify() fire-and-forget), event notification routing (on()/subscribe pattern), pending request tracking, subprocess lifecycle integration
- **Protocol types** — RPCRequest, RPCResponse, RPCError, RPCNotification, EventPayload interfaces + NOTIFICATION_TYPES and RPC_METHODS constants matching D-06 and D-09

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold TypeScript project with Ink + esbuild toolchain** - `efd185f` (feat)
2. **Task 2: Create RPC protocol types + stdio transport + client** - `cc8b751` (feat)
3. **Chore: Add package-lock.json from npm install** - `c5e41d9` (chore)

**Plan metadata:** Will be committed as part of this session.

## Files Created

- `frontend/package.json` — TypeScript + Ink project manifest with esbuild, tsx, TypeScript dev dependencies
- `frontend/tsconfig.json` — TypeScript compiler config with strict mode, es2022 target, ESNext modules, react-jsx with react jsxImportSource
- `frontend/esbuild.config.mjs` — esbuild bundler config bundling src/index.tsx → dist/index.js
- `frontend/.gitignore` — ignores node_modules/, dist/, *.log
- `frontend/src/index.tsx` — Ink render entry point
- `frontend/src/App.tsx` — Minimal placeholder app with AgentHarness TUI title
- `frontend/src/rpc/protocol.ts` — JSON-RPC 2.0 type definitions and constants
- `frontend/src/rpc/transport.ts` — StdioTransport class for Python subprocess IPC
- `frontend/src/rpc/client.ts` — RpcClient with request/response, notification routing, event dispatch
- `frontend/package-lock.json` — Lockfile from npm install

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] esbuild JSX parsing fails without JSX loader config**
- **Found during:** Task 1 (build verification)
- **Issue:** esbuild failed with `Expected ">" but found "/"` on JSX content in src/index.ts — default esbuild config doesn't handle JSX
- **Fix:** Added `loader: { '.ts': 'tsx' }`, `jsx: 'automatic'`, and `jsxImportSource: 'react'` to esbuild config
- **Files modified:** `frontend/esbuild.config.mjs`
- **Verification:** Build succeeds, dist/index.js produced
- **Committed in:** efd185f (task 1 commit)

**2. [Rule 1 - Bug] .ts extension with JSX content causes TypeScript compilation error**
- **Found during:** Task 1 (typecheck verification)
- **Issue:** Both tsc and esbuild require JSX-containing files to have `.tsx` extension. `src/index.ts` with `<App />` JSX content produced `'>' expected` error
- **Fix:** Renamed to `src/index.tsx` and updated esbuild entryPoints to match
- **Files modified:** `frontend/src/index.ts` → renamed to `frontend/src/index.tsx`, `frontend/esbuild.config.mjs`
- **Verification:** npm run typecheck passes
- **Committed in:** efd185f (task 1 commit)

**3. [Rule 1 - Bug] Ink 5.2.1 doesn't export jsx-runtime, causing JSX type errors**
- **Found during:** Task 1 (typecheck verification)
- **Issue:** tsconfig had `jsxImportSource: "ink"` but Ink 5.2.1 doesn't export a jsx-runtime module path. TypeScript error: `This JSX tag requires the module path 'ink/jsx-runtime' to exist`
- **Fix:** Changed jsxImportSource from `"ink"` to `"react"` in both tsconfig.json and esbuild config. React 18.3.1 provides jsx-runtime.js
- **Files modified:** `frontend/tsconfig.json`, `frontend/esbuild.config.mjs`
- **Verification:** npm run typecheck passes cleanly
- **Committed in:** efd185f (task 1 commit)

**4. [Rule 1 - Bug] response.id type mismatch in client.ts pending map**
- **Found during:** Task 2 (typecheck verification)
- **Issue:** RPCResponse.id is typed as `number | string | null` but the _pending Map expects `number | string` keys, causing TS2345 errors
- **Fix:** Added `if (response.id == null) return;` guard before Map operations
- **Files modified:** `frontend/src/rpc/client.ts`
- **Verification:** npm run typecheck passes cleanly
- **Committed in:** cc8b751 (task 2 commit)

---

**Total deviations:** 4 auto-fixed (all Rule 1 - Bug)
**Impact on plan:** All fixes were necessary for the toolchain to work correctly. No scope creep.

## Issues Encountered

- The plan's tsconfig `jsxImportSource: "ink"` was incompatible with Ink 5.2.1 which doesn't provide a jsx-runtime path. Switched to `react` which is the correct approach for Ink v5 (Ink uses React internally as its renderer).
- The plan specified `src/index.ts` but JSX content requires `.tsx` extension for both esbuild and TypeScript. Renamed and updated references.

## Known Stubs

- `frontend/src/App.tsx` — Placeholder component with hardcoded "Waiting for backend connection..." text. No RPC client wired yet. This is intentional — App will be connected to the state store and RPC client in subsequent plans (09-03+).

## Threat Flags

None — all RPC types and transport are typed contracts with no network exposure (local stdio only).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- TypeScript toolchain is fully operational: `npm run dev`, `npm run build`, `npm run typecheck` all work
- RPC client library is complete and type-checked: StdioTransport spawns Python, RpcClient dispatches requests/routes events
- Ready for Plan 09-03: State store + UI components connected to RPC client
- All three npm scripts pass verification

## Self-Check: PASSED

- [x] SUMMARY.md exists and is readable
- [x] All 3 commits present in git log (efd185f, cc8b751, c5e41d9)
- [x] All source files exist (index.tsx, App.tsx, protocol.ts, transport.ts, client.ts)
- [x] Build output dist/index.js exists
- [x] `npm run typecheck` passes
- [x] `npm run build` succeeds

---

*Phase: 09-ts-tui-json-rpc*
*Completed: 2026-07-27*
