---
phase: 14-read-skill-provider-e2e
plan: 04
subsystem: skills
tags: [skills, read_skill, cancel, cancellation, tool_calls, e2e, summarization, jsonl, pytest]

# Dependency graph
requires:
  - phase: 14-read-skill-provider-e2e
    plan: 03
    provides: "RuntimeAPI.load_skill single shared path, add_skill_message injection, make_skill_provider(), real SkillStore wiring — the stack this plan's E2E drives end-to-end"
  - phase: 13-context-plumbing-persist-fix
    provides: "Message.persist flag, system-role summarization exemption, non-serialized skill_state — the plumbing the summarize-survive and JSONL-untouched assertions depend on"
  - phase: 14-read-skill-provider-e2e
    plan: 01
    provides: "SkillStore.read_path traversal-guarded reads — the delegate target read_skill_path E2E exercises (CAP-01)"
provides:
  - "agent/core.py cancel-mid-gather cleanup: except asyncio.CancelledError rolls back the orphaned assistant tool_calls message + partial tool messages and recomputes total_tokens, then re-raises (D-14, ROADMAP criterion 5)"
  - "tests/test_cancel_mid_gather.py — 3-test D-14 regression: cancel during gather leaves provider-valid alternation; next turn streams cleanly; happy path unaffected"
  - "tests/test_skills_e2e.py — 5-test D-15 backend E2E through the REAL stack: load → inject exactly-once → dedup no-op → summarize-survive → JSONL untouched → read_skill_path reference read"
affects: [15-session-behavior, 16-tui-integration, 17-allowed-tools]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Rollback-by-slice: capture msgs_before_gather BEFORE committing the assistant tool_calls message, then del _messages[baseline:] on CancelledError — a turn-scoped atomic rollback that keeps total_tokens consistent via recompute"
    - "E2E-constellation test: real SkillStore + ToolRegistry + SkillToolProvider + RuntimeAPI with only the LLM client stubbed — one file proves the whole Phase 14 backend read path"

key-files:
  created: [tests/test_cancel_mid_gather.py, tests/test_skills_e2e.py]
  modified: [agent/core.py]

key-decisions:
  - "msgs_before_gather captured BEFORE add_assistant_tool_message (plan's sample captured after, which made del [baseline:] a no-op — Rule 1 fix so the rollback slice actually includes the orphaned tool_calls message)"
  - "Cleanup scoped tightly to the gather block (not a broad BaseException catch) so Scheduler's own CancelledError handling at scheduler.py:147 still fires"
  - "E2E runs the real provider stack: SkillToolProvider bound to runtime.load_skill/_read_skill_path registered in a real ToolRegistry before runtime.start() — only the OpenAI client is stubbed"

patterns-established:
  - "Cancel rollback: commit-then-rollback-with-baseline — any async section that commits a message before awaiting a cancellable gather snapshots the message count first and restores it atomically on CancelledError"

requirements-completed: [ACT-02, CAP-01]

# Metrics
duration: 10min
completed: 2026-08-02
---

# Phase 14 Plan 04: Cancel-Mid-Gather Fix + Backend E2E Summary

**Closed the D-14 cancel-mid-gather hole in agent/core.py (except asyncio.CancelledError rolls back the orphaned assistant tool_calls message + partial tool messages with a consistent total_tokens recompute, then re-raises) and proved the full Phase 14 backend read path in Python only: SkillStore → RuntimeAPI.load_skill → system-role injection exactly-once (D-05/D-07) → survive forced summarization (Phase 13 exemption) → persist=False body absent from JSONL (D-13), plus read_skill_path bundled-reference reads through the real provider (CAP-01).**

## Performance

- **Duration:** 10 min
- **Started:** 2026-08-02T12:20:53Z
- **Completed:** 2026-08-02T12:30:51Z
- **Tasks:** 3 (RED + GREEN + E2E)
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- **D-14 closed (ROADMAP criterion 5):** `agent/core.py` gather loop now wraps `asyncio.gather` + the result-append loop in `except asyncio.CancelledError`. On cancel it deletes `_messages[msgs_before_gather:]` (the just-committed assistant tool_calls message plus any partial tool results) and recomputes `context.total_tokens` from the surviving messages, then re-raises so the Scheduler's own CancelledError handling (scheduler.py:147) still fires. `return_exceptions=True` preserved — tool errors never cancel the gather.
- **D-14 regression suite:** `tests/test_cancel_mid_gather.py` (3 tests) — a blocking `asyncio.Event`-gated registry makes `call_tool` hang mid-gather; test 1 cancels the running turn and asserts `to_llm_messages()` has provider-valid alternation (no assistant `tool_calls` without a following `tool` result); test 2 proves the next `run()` streams a clean text response; test 3 guards the happy path (full round-trip still commits both messages).
- **D-15 backend E2E:** `tests/test_skills_e2e.py` (5 tests) drives the REAL stack — `SkillStore` (tmp skills root with `demo-greeter` + `references/guide.md`), a real `ToolRegistry` with `SkillToolProvider` bound to `runtime.load_skill`/`_read_skill_path`, and `RuntimeAPI`; only the OpenAI client is a stub. Proves load → inject (body appears exactly once as a system message), dedup no-op on re-load (ACT-02 exactly-once), summarize-survive under forced tiny-token summarization, JSONL untouched (body absent, user/assistant present), and `read_skill_path` returning the bundled reference (CAP-01).
- Knowledge graph refreshed via `graphify update .` per AGENTS.md.

## TDD Execution

- **RED:** `tests/test_cancel_mid_gather.py` (156 lines) — blocking-registry cancel test. Failed for the correct reason against the pre-fix `agent/core.py`: `AssertionError: assistant tool_calls at index 1 has no following message` — the orphaned tool_calls message was present in `to_llm_messages()`.
- **GREEN:** `agent/core.py` (30 insertions / 14 deletions) — `except asyncio.CancelledError` block around gather + append with baseline-slice rollback and `total_tokens` recompute. All 3 cancel tests pass; full suite green.
- **REFACTOR:** None — implementation is minimal and exactly per the plan's intent.

## task Commits

Each task was committed atomically:

1. **task 1: RED — failing test for cancel-mid-gather** - `b210832` (test)
2. **task 2: GREEN — cancel-mid-gather cleanup in agent/core.py** - `ef23adb` (feat)
3. **task 3: backend E2E — load → inject → summarize-survive → JSONL untouched (D-15)** - `88c1093` (test)

**Plan metadata:** `pending` (docs commit after SUMMARY)

## Files Created/Modified

- `agent/core.py` - `except asyncio.CancelledError` around the gather + result-append section: `del self._context._messages[msgs_before_gather:]` + `total_tokens = sum(m.token_count ...)` then re-raise (D-14)
- `tests/test_cancel_mid_gather.py` - 3-test D-14 regression suite (blocking `asyncio.Event` registry + tool-then-text stub LLM)
- `tests/test_skills_e2e.py` - 5-test D-15 backend E2E through the real SkillStore + ToolRegistry + SkillToolProvider + RuntimeAPI stack

## Decisions Made

- **Baseline before append (Rule 1 fix):** the plan's code sample captured `msgs_before_gather = len(self._context._messages)` AFTER `add_assistant_tool_message`, which put the baseline at the index *following* the orphaned message — `del self._context._messages[msgs_before_gather:]` then removed nothing. Moved the capture BEFORE the append so the rollback slice includes the just-committed assistant tool_calls message, matching the plan's stated intent ("removes the just-added assistant tool_calls message and any partial tool messages").
- **Tight cleanup scope:** the `except asyncio.CancelledError` sits only around the gather block, not a broad BaseException catch, so Scheduler's CancelledError handler (scheduler.py:147) and RuntimeAPI cancel flow are unaffected.
- **Real-stack E2E:** the E2E registers the `__skills__` provider in a real `ToolRegistry` before `runtime.start()` (mirroring main.py's `_build_runtime` wiring) rather than mocking the registry — only the OpenAI client is stubbed, making D-15 a genuine backend-only verification.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Baseline captured after the append made the rollback a no-op**
- **Found during:** task 2 (GREEN — cancel-mid-gather cleanup)
- **Issue:** The plan's action-block sample captured `msgs_before_gather = len(self._context._messages)` immediately after `add_assistant_tool_message`, so the baseline equaled the index *after* the orphaned assistant message. `del self._context._messages[msgs_before_gather:]` then sliced from past-the-end and removed nothing — the dangling tool_calls message survived the cancel (RED tests still failed after the first implementation).
- **Fix:** Moved `msgs_before_gather` capture to BEFORE `await self._context.add_assistant_tool_message(...)`, so the rollback slice starts at the orphaned message itself and removes it plus any partial tool results.
- **Files modified:** agent/core.py
- **Verification:** All 3 cancel tests pass; `python -m pytest -q` → 154 passed, 1 skipped; `grep -n "CancelledError" agent/core.py` present
- **Committed in:** ef23adb (task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for correctness — the plan's literal code sample would not have closed the D-14 hole. The fix matches the plan's documented intent exactly; no scope creep.

## Issues Encountered

- None — the E2E suite's only wrinkle was my own exact-match assertion (`m["content"] == "Hello body"`) when the parsed skill body is `"# Demo\n\nHello body"`; corrected to substring matching before commit (test-only, no production impact).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **D-14 closed:** cancelling a turn during the tool-result gather leaves no partial tool messages and no dangling tool_calls — the next turn's message list is provider-valid (ROADMAP criterion 5), proven by regression tests.
- **D-15 verified backend-only:** load → inject → summarize-survive → JSONL untouched is proven through the real stack in Python; Phase 16 owns the TUI indicator, Phase 15 owns `/skill`.
- **ACT-02 exactly-once** via D-07 dedup and **CAP-01** via `read_skill_path` reference reads are both asserted end-to-end — Phase 17's allowed-tools filtering reads the same `skill_state["loaded"]` record.
- Full suite at 154 passed + 1 skipped (baseline 146 + 3 cancel + 5 E2E), ready for the next phase.
- Phase 14 is the last plan in the wave — **Phase 14 complete, ready for the next step.**

## Self-Check: PASSED

- `agent/core.py` contains `except asyncio.CancelledError`: True
- `tests/test_cancel_mid_gather.py` exists with `def test_cancel_mid_gather`: True
- `tests/test_skills_e2e.py` exists with `def test_e2e_load_skill_injects_body_exactly_once`: True
- Commit `b210832` (RED), `ef23adb` (GREEN), `88c1093` (E2E) present in git log: True
- `python -m pytest tests/test_cancel_mid_gather.py -x` → 3 passed
- `python -m pytest tests/test_skills_e2e.py -x` → 5 passed
- `python -m pytest -q` → 154 passed, 1 skipped
- No unexpected deletions in any commit (verified per-commit)

---

*Phase: 14-read-skill-provider-e2e*
*Completed: 2026-08-02*
