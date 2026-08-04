---
phase: 14-read-skill-provider-e2e
plan: 03
subsystem: skills
tags: [skills, read_skill, load_skill, skill_state, manifest, system-message, persist, pytest]

# Dependency graph
requires:
  - phase: 14-read-skill-provider-e2e
    plan: 01
    provides: "SkillStore with lookup/load/read_path + traversal guard — the delegate target for load_skill and _read_skill_path"
  - phase: 14-read-skill-provider-e2e
    plan: 02
    provides: "SkillToolProvider injected-handler contracts + RESERVED_SKILL_TOOLS + D-03 registry guard — the provider this plan wires into production"
  - phase: 13-context-plumbing-persist-fix
    provides: "Message.persist flag, to_events() filter, non-serialized Session.skill_state, system-role summarization exemption — the plumbing add_skill_message rides on"
  - phase: 12-skills-discovery-manifest
    provides: "discover_skills(), build_manifest_text(), Session.skill_manifest seam — the Phase 12 manifest seam this plan makes live end-to-end"
provides:
  - "Message.skill_name optional field (D-08 tag, from_dict-compatible) + ConversationContext.add_skill_message(name, body): system role, persist=False, tagged"
  - "RuntimeAPI.load_skill(name) single shared load path: dedup (D-07) -> add_skill_message injection (D-08) -> short ack (D-05), writes skill_state['loaded'] name+dir (D-09)"
  - "RuntimeAPI._read_skill_path handler + make_skill_provider() + _create_agent manifest attach — Phase 12 seam live end-to-end"
  - "main.py _build_runtime: SkillStore(.agentharness/skills) + __skills__ registration before runtime.start() in repl/worker/rpc + D-03 read_skill visibility assert"
affects: [14-04-cancel-mid-gather, 15-session-behavior, 16-tui-integration, 17-allowed-tools]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single shared load path: RuntimeAPI.load_skill is the one injection point for both read_skill tool and (Phase 15) /skill command — provider receives it as an injected handler (Pattern 3, D-09)"
    - "Dedup record in non-serialized skill_state['loaded'] as a list of {name, dir} dicts — deterministic no-op re-loads (D-07), read by Phase 17 filtering"

key-files:
  created: [tests/test_load_skill.py]
  modified: [context/message.py, context/context.py, harness/runtime.py, skills/__init__.py, main.py]

key-decisions:
  - "load_skill raises RuntimeError('SkillStore not configured') / RuntimeError('No active session') before any lookup — hard preconditions surface mis-wiring instead of silently no-oping"
  - "Manifest attach guarded by session.skill_manifest is None — once per Session object, idempotent across _create_agent re-runs (create/switch/start)"
  - "Provider construction exposed via RuntimeAPI.make_skill_provider() and shared _build_runtime helper in main.py — all three modes (repl/worker/rpc) register __skills__ before runtime.start() through one code path"
  - "D-03 visibility assert placed after await runtime.start() in each mode — registry.start() swallows per-provider registration errors, the assert turns any swallow into a loud failure"

patterns-established:
  - "Provider-handler binding at the runtime: make_skill_provider() closes over load_skill/_read_skill_path so main.py wires tools with one call and no handler drift"
  - "Non-serialized session-scoped dedup: skill_state['loaded'] list-of-dicts is the single dedup source for load_skill, never touches JSONL"

requirements-completed: [DISC-03, DISC-04, ACT-02, CAP-01]

# Metrics
duration: 4min
completed: 2026-08-01
---

# Phase 14 Plan 03: Load-Skill Runtime + Production Wiring Summary

**`RuntimeAPI.load_skill(name)` single shared load path (dedup via `skill_state["loaded"]` → system-role injection via `add_skill_message` → short ack) with the `Message.skill_name` D-08 tag, plus main.py production wiring that makes the Phase 12 manifest seam live end-to-end — `__skills__` registered before `runtime.start()` in all three modes with a D-03 `read_skill` visibility assert.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-08-01T21:50:39Z
- **Completed:** 2026-08-01T21:53:59Z
- **Tasks:** 3 (RED + GREEN + wiring)
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments

- `Message.skill_name: str | None = None` added as the last dataclass field (D-08 tag); `from_dict` untouched — stored events never carry the key
- `ConversationContext.add_skill_message(name, body)` — `Message(role="system", content=body, persist=False, skill_name=name)` appended via `add_message`: body visible every turn, exempt from summarization (system role, Phase 13), never reaches JSONL (persist=False, D-13)
- `RuntimeAPI.load_skill(name)` — D-09 single shared path: dedup no-op re-load via `skill_state["loaded"]` (D-07), `SkillStore.lookup` frontmatter-name authority (D-04), body injection, `skill_state["loaded"]` records `{"name", "dir"}` (D-09), short-ack return (D-05 — body never duplicated in the tool result)
- `RuntimeAPI._read_skill_path(skill, rel)` delegates to `SkillStore.read_path` (14-01 traversal guard); `make_skill_provider()` binds both handlers into `SkillToolProvider`
- `_create_agent` attaches `session.skill_manifest` from `discover_skills` + `build_manifest_text` once per Session object — Phase 12's seam is now live for every fresh session
- `main.py` `_build_runtime()` shared helper: `SkillStore(Path.cwd() / ".agentharness" / "skills")` + `RuntimeAPI(skill_store=...)` + `registry.add_provider("__skills__", provider)` (namespace=None) registered BEFORE `runtime.start()` in REPL, worker, and RPC modes; D-03 assert after start: `read_skill` must be in `registry.list_tools()`
- `skills/__init__.py` barrel now exports the full skills surface: `SkillStore`, `SkillToolProvider`, `RESERVED_SKILL_TOOLS`, `retain_read_skills`
- `tests/test_load_skill.py` — 8-test suite: skill_name default/from_dict, add_skill_message contract, dedup no-op, skill_state record, JSONL absence (D-13), unknown-name error, manifest attach

## TDD Execution

- **RED:** `tests/test_load_skill.py` (8 tests) failed with `AttributeError: 'Message' object has no attribute 'skill_name'` — the correct RED reason (skill_name/add_skill_message/load_skill all absent).
- **GREEN:** added `skill_name` field, `add_skill_message`, `load_skill`, `_read_skill_path`, `make_skill_provider`, manifest attach, barrel exports. All 8 load-path tests pass; full suite 146 passed, 1 skipped (baseline 138 + 1 skipped → +8).
- **REFACTOR:** None — implementations are minimal and exactly per the plan's action blocks.

## task Commits

Each task was committed atomically:

1. **task 1: RED — tests for skill_name + add_skill_message + load_skill** - `daa59e2` (test)
2. **task 2: GREEN — implement skill_name, add_skill_message, RuntimeAPI.load_skill** - `c13f8be` (feat)
3. **task 3: production wiring in main.py** - `ab228e8` (feat)

**Plan metadata:** `pending` (docs commit after SUMMARY)

## Files Created/Modified

- `context/message.py` - `skill_name: str | None = None` last field (D-08 tag); from_dict untouched
- `context/context.py` - `add_skill_message(name, body)`: system role, persist=False, skill_name tag
- `harness/runtime.py` - `skill_store` ctor param; manifest attach in `_create_agent`; `load_skill` (dedup → inject → ack); `_read_skill_path` handler; `make_skill_provider()`
- `skills/__init__.py` - Barrel exports `SkillStore`, `SkillToolProvider`, `RESERVED_SKILL_TOOLS`, `retain_read_skills`
- `main.py` - `_build_runtime()` shared helper + `__skills__` registration before start + D-03 assert in all three modes
- `tests/test_load_skill.py` - 8-test load-path suite (created)

## Decisions Made

- **Hard preconditions in load_skill:** raising `RuntimeError` when SkillStore is not configured or no session is active surfaces mis-wiring immediately — no silent no-op.
- **Manifest attach idempotence:** guarded on `session.skill_manifest is None`, so re-running `_create_agent` (start/create/switch) never re-attaches for the same Session object.
- **One wiring helper for three modes:** `_build_runtime` centralizes SkillStore + provider registration so REPL/worker/RPC can't drift; `make_skill_provider()` prevents handler-binding drift.
- **D-03 assert after start:** registry.start() swallows per-provider errors (14-02 left swallow semantics intact); the post-start assert turns a swallowed `__skills__` registration into a loud failure (T-14-01 second leg).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Two transient editor errors during Task 3 (main.py edits removing a `_handle_session_cmd` body line and a `_resolve_session` call) were caught and reverted immediately via `git diff` verification before commit — no net change, main.py committed clean with exactly the plan's 32-line wiring diff.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The single shared `load_skill` path is live and tested: `read_skill` tool (via injected handler), the future `/skill` command (Phase 15), and Phase 17's allowed-tools filtering all read `skill_state["loaded"]`.
- Phase 16's TUI indicator has its seam: `skill_name` tag on loaded-body system messages (D-08).
- Cancel-mid-gather (14-04) is the next wave plan — the load path is independent of the agent gather path, no interference.
- Full suite at 146 passed + 1 skipped, ready for the next plan in the wave.

## Self-Check: PASSED

- `context/message.py` contains `skill_name: str | None = None`: True
- `context/context.py` contains `add_skill_message`: True
- `harness/runtime.py` contains `load_skill`, `_read_skill_path`, `make_skill_provider`, manifest attach in `_create_agent`: True
- `skills/__init__.py` exports SkillStore/SkillToolProvider/RESERVED_SKILL_TOOLS/retain_read_skills: True
- `main.py` contains `_build_runtime` + `__skills__` registration + D-03 assert in all three modes: True
- `tests/test_load_skill.py` exists with 8 tests: True
- Commit `daa59e2` (RED), `c13f8be` (GREEN), `ab228e8` (wiring) present in git log: True
- `python -m pytest tests/test_load_skill.py -x` → 8 passed
- `python -m pytest -q` → 146 passed, 1 skipped
- `python -c "import main"` → imports cleanly
- Real-registry smoke: `read_skill` + `read_skill_path` visible after start, manifest attached for fresh session, real skills indexed (demo-greeter, frontend-design)

---

*Phase: 14-read-skill-provider-e2e*
*Completed: 2026-08-01*
