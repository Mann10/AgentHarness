---
phase: 15-session-behavior-skill-command
plan: 02
subsystem: api
tags: [repl, skills, slash-command, python, tdd]

# Dependency graph
requires:
  - phase: 14-read-skill-provider-e2e
    provides: RuntimeAPI.load_skill shared path (D-07), SkillStore.lookup KeyError contract, skill_state["loaded"] exactly-once dedup (H-01)
provides:
  - /skill slash command in main._handle_session_cmd (success / not-found / usage / already-loaded branches)
  - tests/test_skill_command.py — 6 tests covering all four branches + win32 case-variant + fall-through regression
affects: [15-03, 16-tui-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "REPL slash-command branch: return True on every handled path so the line never falls through to a chat prompt"
    - "MagicMock runtime + AsyncMock load_skill for REPL command unit tests (D-07 direct-call seam)"

key-files:
  created:
    - tests/test_skill_command.py
  modified:
    - main.py

key-decisions:
  - "/skill branch calls runtime.load_skill() directly (D-07) — REPL is in-process with RuntimeAPI, no RPC involved"
  - "Name passed raw to load_skill — win32 case-insensitivity handled inside SkillStore.lookup (D-04), no main.py normalization"
  - "No except RuntimeError catch this plan — D-11 cap-refusal RuntimeError is introduced by Plan 15-03, which wires the catch"

patterns-established:
  - "REPL command tests: call main._handle_session_cmd(line, current, runtime, config, client) with AsyncMock load_skill + capsys"

requirements-completed: [ACT-01]

# Metrics
duration: 7min
completed: 2026-08-02
---

# Phase 15 Plan 02: REPL /skill Command — Summary

**`/skill <name>` branch in `main._handle_session_cmd` — user-driven skill activation through the exact same `RuntimeAPI.load_skill()` shared path as `read_skill` (D-07), with distinct not-found/usage errors (D-02), short-ack success output (D-01), exactly-once already-loaded dedup (D-03), and every branch returning `True` so the line never falls through to a chat prompt**

## Performance

- **Duration:** 7 min
- **Started:** 2026-08-02T16:05:03Z
- **Completed:** 2026-08-02T16:12:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `/skill <name>` on a known skill prints the short ack (`Loaded skill demo-greeter`) and returns True (D-01, D-07)
- `/skill <unknown>` prints the distinct error `Skill '<name>' not found.` and returns True (D-02)
- `/skill` with no argument prints `Usage: /skill <name>` and returns True — never a silent no-op or fall-through to chat (D-02)
- Already-loaded re-load prints the dedup ack (`Skill '<name>' already loaded`) — exactly-once via the shared load_skill dedup (D-03, H-01); body never re-injected
- Name passed raw to load_skill — win32 case-insensitive matching handled inside SkillStore.lookup (D-04)
- Fall-through preserved for unknown commands (returns False)
- 6 new tests, TDD RED→GREEN; full suite green: 171 passed, 1 skipped

## task Commits

Each task was committed atomically:

1. **task 1: Wave 0 — create tests/test_skill_command.py (RED scaffold)** - `683c828` (test)
2. **task 2: Implement the /skill branch in _handle_session_cmd (GREEN)** - `3507f07` (feat)

## Files Created/Modified
- `tests/test_skill_command.py` - 6 tests: success ack + True, unknown → distinct error + True, no-arg → usage + True, already-loaded ack + True, win32 case-variant passes raw name (D-04), unknown command falls through to False
- `main.py` - `/skill` branch in `_handle_session_cmd` (after `/title`, before `return False`): parses trimmed name, no-arg → usage, `await runtime.load_skill(name)` → prints ack, `except KeyError` → distinct not-found message, returns True in all paths

## Decisions Made
- **REPL calls `load_skill()` directly (D-07):** The REPL is in-process with RuntimeAPI, so the `/skill` branch awaits `runtime.load_skill(name)` directly — the exact same shared path as the model-driven `read_skill` tool. Activation cannot drift between user-driven and model-driven loads.
- **Raw name passed through (D-04):** main.py does not lowercase/normalize the skill name — `SkillStore.lookup()` handles win32 case-insensitivity via its `_key()` (and the H-01 canonical-name dedup handles case-variant re-loads). Test verifies `load_skill` receives the raw trimmed arg.
- **No `except RuntimeError` this plan:** The D-11 cap-refusal RuntimeError is introduced by Plan 15-03, which also wires the `except RuntimeError` catch in this branch (prints `str(exc)`, returns True). Per the pre-15-03 load_skill contract, `KeyError` is the only expected exception here — pre-15-03 RuntimeErrors (no session/store) remain programmer errors that surface.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- **Console display of em-dashes in test docstrings:** The PowerShell console rendered `—` as `�` in pytest output. Verified the file is valid UTF-8 (em-dash bytes present, no replacement chars) — display-only artifact, not a file defect.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 15-03 (loaded-skill token accounting + cap) wires the `except RuntimeError` catch into this `/skill` branch for the D-11 cap-refusal message — the branch already returns True on every path, so a cap refusal will surface as a printed error rather than a traceback (run_repl at main.py:164 and main()'s finally have no try/except around this call).
- Threat dispositions T-15-06/T-15-07/T-15-08 all mitigated: every branch returns True (malformed commands can't become chat prompts), name only reaches traversal-guarded `SkillStore.lookup()` (never file paths/shell), and exactly-once dedup makes repeat loads no-ops.

---

*Phase: 15-session-behavior-skill-command*
*Completed: 2026-08-02*

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED | `683c828` test(15-02): add failing tests for /skill command | ✓ |
| GREEN | `3507f07` feat(15-02): implement /skill command in REPL | ✓ |

## Self-Check: PASSED

- FOUND: tests/test_skill_command.py
- FOUND: .planning/phases/15-session-behavior-skill-command/15-02-SUMMARY.md
- FOUND commit: 683c828 (test, RED gate)
- FOUND commit: 3507f07 (feat, GREEN gate)
