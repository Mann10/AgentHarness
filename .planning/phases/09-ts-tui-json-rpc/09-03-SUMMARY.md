---
phase: 09-ts-tui-json-rpc
plan: 03
subsystem: ui
tags: typescript, ink, react, state-management, tui

requires:
  - phase: 09-ts-tui-json-rpc
    plan: 02
    provides: TypeScript frontend project (Ink, esbuild, toolchain) + RPC client library

provides:
  - Presentation state store with publish-subscribe pattern (store.ts + reducers.ts)
  - MessageCard component with role-based terminal styling (user/assistant/error/system)
  - InputBar with keyboard-driven text entry and Enter submission
  - ConversationScreen — message list + streaming display + input bar
  - App.tsx wiring — RPC client event subscription, state dispatch, lifecycle management

affects:
  - 09-04 onward (feature parity: tool calls, sessions, stats)

tech-stack:
  added:
    - Ink useInput hook for keyboard capture (no external input library)
  patterns:
    - Module-level singleton store with publish-subscribe (no Zustand)
    - Pure-function reducers mapping RPC event notifications to state updates
    - Component → store → RPC client data flow (D-14, D-15)

key-files:
  created:
    - frontend/src/state/store.ts
    - frontend/src/state/reducers.ts
    - frontend/src/ui/components/MessageCard.tsx
    - frontend/src/ui/components/InputBar.tsx
    - frontend/src/ui/screens/ConversationScreen.tsx
  modified:
    - frontend/src/App.tsx

key-decisions:
  - "Used Ink's built-in useInput hook for keyboard capture instead of ink-text-input dependency — keeps dependencies minimal per CONTEXT.md discretion"
  - "MessageCard uses role-based color coding: user (green), assistant (cyan), error (red), system (yellow/dim)"
  - "App.tsx subscribes to all 7 RPC notification types on mount via rpcClient.on(), routes through handleEvent()"
  - "ConversationScreen uses store.subscribe() + useState tick counter for reactive re-rendering"

patterns-established:
  - "Pattern: State store → subscribe → useState tick trigger re-render cycle for Ink components"
  - "Pattern: useInput hook handles all keyboard input in InputBar component"
  - "Pattern: App.tsx lifecycle — createStore → spawn RpcClient → subscribe events → render → cleanup on unmount"

requirements-completed:
  - D-11 (Custom terminal components on Ink)
  - D-12 (App logic independent of Ink/React)
  - D-13 (state/ and ui/ structure)
  - D-14 (State store — presentation state only)
  - D-15 (Frontend never imports Python logic)

duration: 7min
completed: 2026-07-27
---

# Phase 9 Plan 3: Presentation State Store + Conversation UI + Input Wiring

**Core TUI interaction layer — state store with event reducers, role-styled message cards, keyboard-driven input bar, and App.tsx wiring to the RPC client**

## Performance

- **Duration:** 7 min
- **Started:** 2026-07-27T22:30:00Z
- **Completed:** 2026-07-27T22:37:00Z
- **Tasks:** 5
- **Files created:** 5
- **Files modified:** 1

## Accomplishments

- **Presentation state store (store.ts + reducers.ts)** — Module-level singleton Store class with publish-subscribe pattern, typed StoreState (messages, activeToolCalls, isProcessing, streamedContent, sessions, error), and 7 convenience methods (addMessage, appendStreamedContent, finalizeStream, setProcessing, addToolCall, updateToolCall, setError). Pure-function handleEvent() maps all 7 RPC notification types to state updates with zero Ink/React imports (D-12 compliance).

- **MessageCard component** — Renders messages with role-based terminal styling: user (green/You: prefix), assistant (cyan/Assistant: prefix), error (red), system (yellow/dim). Uses Ink Box/Text primitives.

- **InputBar component** — Keyboard-driven text input using Ink's useInput hook. Enter submits non-empty prompts, Backspace deletes chars, disabled state when backend is processing. Bordered box with prompt indicator. No external input library dependency.

- **ConversationScreen** — Main view subscribing to store changes via useEffect + useState tick counter. Renders message history, streaming content (assistant responses in progress), and error states. Empty state prompt for new conversations. Input bar at the bottom.

- **App.tsx wiring** — Creates store singleton, spawns Python backend via RpcClient('python', ['-m', 'agentharness', '--rpc']), subscribes to all 7 notification types routing through handleEvent(), passes store + prompt callback to ConversationScreen. Cleans up subscriptions and stops RPC client on unmount.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create presentation state store** - `ea6249e` (feat)
2. **Task 2: Create MessageCard component** - `d938263` (feat)
3. **Task 3: Create InputBar component** - `90c7faf` (feat)
4. **Task 4: Create ConversationScreen** - `26fbb7d` (feat)
5. **Task 5: Wire App.tsx with RPC client** - `5e0b273` (feat)

## Files Created/Modified

- `frontend/src/state/store.ts` — Presentation state store with Store class, StoreState interface, Message/ToolCallState/SessionInfo types, and singleton createStore()
- `frontend/src/state/reducers.ts` — Pure-function handleEvent() mapping 7 notification types to store mutations
- `frontend/src/ui/components/MessageCard.tsx` — Role-based message rendering component
- `frontend/src/ui/components/InputBar.tsx` — Keyboard-driven text input with Enter submission
- `frontend/src/ui/screens/ConversationScreen.tsx` — Main conversation view with message list, streaming, error display, and input bar
- `frontend/src/App.tsx` — Root component with RPC client lifecycle, event subscriptions, and UI wiring

## Decisions Made

- Used Ink's built-in `useInput` hook for keyboard capture instead of `ink-text-input` dependency — keeps dependencies minimal per CONTEXT.md discretion
- MessageCard uses role-based color coding: user (green bold prefix), assistant (cyan bold prefix), error (red), system (yellow dim)
- App.tsx subscribes to all 7 RPC notification types on mount via `rpcClient.on()`, routes through `handleEvent()`
- ConversationScreen uses `store.subscribe()` + `useState` tick counter for reactive re-rendering — lightweight pattern without Zustand

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan file truncated — missing tasks 2-5**
- **Found during:** Task 1 execution (plan loading)
- **Issue:** The PLAN.md file is truncated/corrupted (280 lines, ends mid-XML-tag at `<automated>cd frontend && npx tsc --noEmit`). Only Task 1 (state store) was fully defined. Tasks 2-5 for MessageCard, InputBar, ConversationScreen, and App.tsx wiring were absent.
- **Fix:** Reconstructed missing tasks from the plan's `must_haves` section (provides/exports contracts), `must_haves.truths` (behavioral requirements), and `key_links` (wiring patterns). Implemented all 4 missing artifacts matching the specified contracts.
- **Files modified:** `frontend/src/ui/components/MessageCard.tsx`, `frontend/src/ui/components/InputBar.tsx`, `frontend/src/ui/screens/ConversationScreen.tsx`, `frontend/src/App.tsx`
- **Verification:** All 6 source files exist, TypeScript compilation passes (0 errors), esbuild build succeeds, acceptance criteria pass for all 5 tasks, all 5 truth statements verified
- **Committed in:** d938263, 90c7faf, 26fbb7d, 5e0b273 (distinct task commits)

---

**Total deviations:** 1 auto-fixed (Rule 3 - Blocking)
**Impact on plan:** The truncated plan was reconstructed from must_haves contracts with zero speculation — all contracts verified against the plan's own artifact specifications. All 5 truth statements pass. No scope creep.

## Issues Encountered

- Plan file was truncated/truncated — the `<tasks>` section ends mid-verify-tag at line 280. This is a file integrity issue likely from a prior write, not a plan design issue. Missing tasks were reconstructed from the `must_haves` and `key_links` frontmatter sections which were intact.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All core TUI interaction layer components are complete and type-checked
- State store with event reducers handles all 7 notification types
- ConversationScreen with message list + streaming + input bar is wired to the RPC client
- Ready for Plan 09-04: Tool call display, session management screens, stats panel, and feature parity with the existing Python Textual TUI
- `npm run typecheck` and `npm run build` both pass cleanly

## Self-Check: PASSED

- [x] All 6 source files exist on disk
- [x] All 5 commits present in git log (ea6249e, d938263, 90c7faf, 26fbb7d, 5e0b273)
- [x] TypeScript compilation passes (0 errors)
- [x] esbuild build succeeds (dist/index.js produced)
- [x] Store exports createStore, Store, StoreState, Message
- [x] reducers exports handleEvent with no Ink/React imports (D-12)
- [x] Store has all 6 required methods
- [x] MessageCard has role-based styling for user/assistant/error/system
- [x] InputBar uses useInput hook and has onSubmit callback
- [x] ConversationScreen shows messages, streaming, errors
- [x] App.tsx subscribes to RPC events, sends chat requests
- [x] All 5 must_haves truths verified

---

*Phase: 09-ts-tui-json-rpc*
*Completed: 2026-07-27*
