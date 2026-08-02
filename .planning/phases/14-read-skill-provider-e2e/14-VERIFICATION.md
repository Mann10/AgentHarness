---
phase: 14-read-skill-provider-e2e
verified: 2026-08-02T13:30:00Z
status: gaps_found
score: 10/11 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Re-loading an already-loaded skill is a no-op returning an 'already loaded' ack — dedup via session.skill_state['loaded'] (D-07); the body loads into context exactly once (ROADMAP SC1, ACT-02)"
    status: failed
    reason: "Dedup compares the raw caller-supplied name case-sensitively against recorded names, while SkillStore.lookup() keys case-insensitively on win32 (os.name == 'nt'). On this primary platform, loading 'demo-greeter' then 'DEMO-GREETER' passes the dedup check, injects the body as a system message TWICE, and appends TWO skill_state records — empirically confirmed against the real stack. The D-07 no-op contract and 'exactly once' guarantee are broken for case variants. (Review H-01, independently confirmed.)"
    artifacts:
      - path: "harness/runtime.py"
        issue: "Line 189: existing = next((e for e in loaded if e['name'] == name), None) — case-sensitive == against a case-insensitive lookup (store.py:36-37). The dedup key and the lookup key are inconsistent."
    missing:
      - "Compare dedup against the canonical name after lookup (info.name), or key the loaded records with the same case-normalized dedupe key SkillStore uses"
      - "Add a win32 test: load_skill('demo-greeter') then load_skill('DEMO-GREETER') asserts exactly one system body and one skill_state record"
  - truth: "ACT-02 auto-invoke holds end-to-end: the model-driven load path injects exactly one system body and dedups on re-load"
    status: failed
    reason: "Same root cause as the D-07 gap (H-01). The mechanism is wired and the same-name path is exactly-once, but the exactly-once contract fails for case-variant re-loads on win32 — the platform the project is developed on. The E2E and load-path tests only exercise identical-string re-loads, so the suite does not catch it."
    artifacts:
      - path: "harness/runtime.py"
        issue: "Lines 188-196: check-then-inject-then-append ordering with a case-sensitive existing check"
    missing:
      - "Case-normalize the dedup comparison (fix H-01) and add the case-variant regression test to test_load_skill.py / test_skills_e2e.py"
human_verification: []
---

# Phase 14: read_skill Provider End-to-End — Verification Report

**Phase Goal:** Agent can load a skill body on demand via a dedicated `read_skill` tool and read bundled resources through path-scoped reads — Level-2/Level-3 disclosure. Bodies flow through the persist-safe plumbing from Phase 13 as system-role messages.
**Verified:** 2026-08-02T13:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | `read_skill(name)` loads the full skill body into context as a system-role message **exactly once**; re-load is a no-op "already loaded" ack; tool result is a short ack, body never duplicated (SC1, D-05, D-07) | ✗ FAILED | `load_skill` + `add_skill_message` + short-ack path all exist and work for identical-string re-loads; **but** case-variant re-load on win32 (`demo-greeter` → `DEMO-GREETER`) double-injects the body and double-appends the skill_state record — empirically reproduced (H-01). D-05 ack-not-body holds; D-07 exactly-once does not |
| 2   | Agent can read bundled resources (`references/`, `scripts/`, `assets/`) by relative path inside the loaded skill's directory (SC2, DISC-05, CAP-01) | ✓ VERIFIED | `SkillStore.read_path` reads `references/guide.md`; E2E test 5 returns `GUIDE REFERENCE CONTENT` through the real provider + store |
| 3   | Every path-traversal attempt — `../`, `..\`, absolute paths, win32 drive-path tricks, symlink escapes — is rejected with a clear error naming the skill AND the rejected path; reads never escape the skills directory (SC3, DISC-04, D-10/D-11/D-12) | ✓ VERIFIED | `read_path` canonicalize+contain guard (`(dir/rel).resolve()` + `is_relative_to(base)`); 5 vectors empirically rejected with skill+path-naming `ValueError`; parametrized suite in `tests/test_skills_store.py` (13 tests, 12 pass + 1 symlink skip permitted on non-admin win32) shipped in the same wave |
| 4   | `read_skill`/`read_skill_path` are reserved, un-namespaced tool names registered by the async `__skills__` provider — LLM sees exactly these two (SC4, D-01/D-02) | ✓ VERIFIED | `skills/provider.py` `fetch_tools()` returns exactly the two un-namespaced schemas; `tests/test_skills_provider.py` asserts names + no prefix |
| 5   | No provider can shadow or be shadowed on the reserved skill tool names — collision raises a clear error (SC4, D-03) | ✓ VERIFIED | `tool/registry.py:134-140` reserved-name guard before the generic collision branch, raises `ValueError` naming the reserved tool and owner; collision test passes |
| 6   | The allowed-tools filter always retains `read_skill`/`read_skill_path` (`allowed ∪ {read_skill, read_skill_path}`), unit-tested here (SC4, CAP-03) | ✓ VERIFIED | `skills/filter.py` `retain_read_skills` (None/empty/union cases all tested, 4 tests) — enforcement wiring correctly deferred to Phase 17 |
| 7   | `load_skill` injects via tagged `add_skill_message(name, body)`: system role, `persist=False`, `skill_name` set; body visible every turn and exempt from summarization (D-06/D-08, Phase 13 plumbing) | ✓ VERIFIED | `context/context.py:40-42` builds `Message(role="system", content=body, persist=False, skill_name=name)`; `Message.skill_name` field present, `from_dict` never reads the key; `_maybe_summarize` exempts system role |
| 8   | Auto-invoke is model-driven only — no keyword matching, no heuristic pre-loading (D-13) | ✓ VERIFIED | grep across production `*.py` finds no keyword/heuristic/pre-load matching; the manifest + `read_skill` tool are the only mechanism |
| 9   | Loaded bodies flow persist-safe: never serialized to JSONL (`persist=False` filter), survive forced summarization (system-role exemption) (D-15) | ✓ VERIFIED | `session/models.py:85` `to_events()` filters `m.persist`; E2E tests 3-4 pass through the real stack (body survives tiny-limit summarization; absent from JSONL file) |
| 10  | Cancelling a turn during the tool-result gather leaves no partial tool messages and no dangling `tool_calls` — next turn streams cleanly (SC5, D-14) | ✓ VERIFIED | `agent/core.py:152-193` baseline-captured rollback with `total_tokens` recompute; 3 regression tests pass (cancel, next-turn streams, happy path). **Caveat:** M-01 — rollback is index-based and can silently no-op if summarization shrinks `_messages` between baseline capture and cancel (small token limits); not exercised by the tests (token_limit=1000) |
| 11  | Production wiring: main.py builds the manifest from `discover_skills` + `build_manifest_text`, attaches it via `_create_agent`, registers `__skills__` BEFORE `runtime.start()`, and asserts `read_skill` visible after start — Phase 12 seam live end-to-end | ✓ VERIFIED | `main.py _build_runtime()` (L195-212) + D-03 asserts in worker (L223), rpc (L292), repl (L338); `harness/runtime.py` manifest attach in `_create_agent` (L270-277); `session/models.py:78-79` appends `skill_manifest` to the system prompt; `skills/__init__.py` barrel complete |

**Score:** 10/11 truths verified

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `skills/store.py` | SkillStore: index, body load, traversal-guarded read_path | ✓ VERIFIED | 64 lines, real implementation; `class SkillStore` with `lookup`/`load`/`read_path` + `is_relative_to` guard (D-12) |
| `tests/test_skills_store.py` | Traversal suite (posix + win32 vectors) same wave | ✓ VERIFIED | 13 tests: index/load/read_path + parametrized 5-vector traversal checklist + symlink escape (skipped on non-admin win32) |
| `skills/provider.py` | Async SkillToolProvider (fetch_tools/call_tool) | ✓ VERIFIED | Two reserved schemas, injected-handler dispatch, unknown-name ValueError, RESERVED_SKILL_TOOLS |
| `skills/filter.py` | `retain_read_skills` pure retention | ✓ VERIFIED | None/union/empty semantics correct; CAP-03 contract |
| `tool/registry.py` | Reserved-name collision guard | ✓ VERIFIED | Guard at L134-140, raises on shadowing |
| `context/message.py` | `Message.skill_name` optional field, from_dict-compatible | ✓ VERIFIED | Last dataclass field, default None; from_dict never reads the key |
| `context/context.py` | `add_skill_message(name, body)` — system, persist=False, tagged | ✓ VERIFIED | L40-42 exactly per contract |
| `harness/runtime.py` | `load_skill` single shared path + provider handlers + manifest attach | ✓ VERIFIED | `load_skill`/`_read_skill_path`/`make_skill_provider`/manifest attach all present; **H-01 defect in dedup comparison** |
| `main.py` | Production wiring: SkillStore + `__skills__` + reserved-name assert | ✓ VERIFIED | `_build_runtime` + 3-mode registration + asserts |
| `skills/__init__.py` | Barrel exports full skills surface | ✓ VERIFIED | SkillStore, SkillToolProvider, RESERVED_SKILL_TOOLS, retain_read_skills, etc. |
| `agent/core.py` | Cancel-mid-gather cleanup (CancelledError) | ✓ VERIFIED | Baseline-capture rollback + total_tokens recompute (M-01 caveat) |
| `tests/test_cancel_mid_gather.py` | D-14 regression (3 tests) | ✓ VERIFIED | Blocking registry + tool-then-text stub LLM; all 3 pass |
| `tests/test_skills_e2e.py` | D-15 backend E2E (5 tests, real stack) | ✓ VERIFIED | Load/inject, dedup, summarize-survive, JSONL-untouched, read_skill_path — all through real SkillStore+Registry+Provider+RuntimeAPI |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `skills/store.py` | `skills/discovery.py` | index built from `discover_skills()`; dedupe-key convention | ✓ WIRED | L41 `for info in discover_skills(self._root)`; case-insensitive key mirrors `_dedupe_key` |
| `skills/store.py` | `pathlib.Path.resolve` | canonicalize + `is_relative_to` containment | ✓ WIRED | L58-60; all vectors rejected empirically |
| `skills/provider.py` | `harness/runtime.py` | injected `load_handler`/`read_handler` | ✓ WIRED | `make_skill_provider()` binds `load_skill` + `_read_skill_path` |
| `tool/registry.py` | `skills/provider.py` | `add_provider("__skills__", provider, namespace=None)` + RESERVED_SKILL_TOOLS import | ✓ WIRED | No prefix (D-02); guard fires on collision |
| `context/context.py` | `context/message.py` | `add_skill_message` builds tagged system Message | ✓ WIRED | L40-42 → `add_message` |
| `harness/runtime.py` | `skills/store.py` | `load_skill` → `SkillStore.lookup/load`; `_read_skill_path` → `read_path` | ✓ WIRED | L192-193, L203 |
| `harness/runtime.py` | `session/models.py` | `skill_state["loaded"]` name+dir records | ⚠️ WIRED (H-01) | Record written (D-09) but dedup comparison is case-sensitive against a case-insensitive lookup — case-variant re-loads double-record |
| `main.py` | `skills/provider.py` | `_build_runtime` registers `__skills__` before start; assert after | ✓ WIRED | All 3 modes; asserts present |
| `agent/core.py` | `context/context.py` | CancelledError rollback of `_messages` + total_tokens | ✓ WIRED | L185-193 (M-01 index-based caveat) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `SkillStore.load` | body | `SKILL.md` via `parse_skill_doc` after frontmatter | Real file content (`# Demo\n\nHello body`) | ✓ FLOWING |
| `SkillStore.read_path` | file content | bundled resource files via guarded resolve+read | Real (`GUIDE REFERENCE CONTENT`) | ✓ FLOWING |
| `RuntimeAPI.load_skill` | system message | SkillStore body → `add_skill_message` | Real body, system role, persist=False | ✓ FLOWING |
| `RuntimeAPI._create_agent` | `session.skill_manifest` | `discover_skills` + `build_manifest_text` (real discovery) | Real manifest text, appended to system prompt | ✓ FLOWING |
| `skill_state["loaded"]` | dedup records | `load_skill` append | Real but **case-variant duplicate records** (H-01) | ⚠️ PARTIAL |
| E2E JSONL | stored events | `to_events()` persist filter | Skill body absent; user/assistant present | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Traversal vectors rejected with skill+path error | inline script over real `SkillStore` (`../`, `..\`, `/etc/passwd`, `C:\windows\win.ini`, `../../`) | All 5 raise `ValueError` naming both skill and path | ✓ PASS |
| Legitimate in-bounds read succeeds | `read_path("demo-greeter", "references/guide.md")` | `GUIDE REFERENCE CONTENT` | ✓ PASS |
| Unknown skill errors clearly | `store.load("nope")` | `KeyError: "Unknown skill 'nope'"` | ✓ PASS |
| Body loads after frontmatter | `store.load("demo-greeter")` | `'# Demo\n\nHello body'` | ✓ PASS |
| Same-name re-load dedups (D-07) | `load_skill("demo-greeter")` twice | `Loaded skill demo-greeter` + `already loaded`; body once | ✓ PASS |
| **Case-variant re-load dedups (D-07 win32)** | `load_skill("demo-greeter")` then `load_skill("DEMO-GREETER")` | **Both return `Loaded skill`; body injected twice; 2 records** | ✗ FAIL (H-01) |
| Concurrent same-skill loads (H-03 TOCTOU) | `asyncio.gather(load_skill, load_skill)` | `Loaded` + `already loaded`; body once — **not exploitable today** (no suspension point between check and append) | ✓ PASS (latent) |
| Full test suite | `python -m pytest -q` | 154 passed, 1 skipped (11.0s) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| DISC-03 | 14-01, 14-02, 14-03 | Agent can load a skill body on demand via dedicated `read_skill` tool | ✓ SATISFIED | `read_skill` registered, `load_skill` injects body; E2E test 1. Caveat: exactly-once fails for case variants (H-01) |
| DISC-04 | 14-01, 14-03 | `read_skill` reads path-scoped to skills dir — no traversal | ✓ SATISFIED | `read_path` canonicalize+contain; review independently found no escape; all vectors rejected |
| DISC-05 | 14-01 | Bundled resources (`references/`, `scripts/`, `assets/`) readable via path-scoped reads | ✓ SATISFIED | `read_path` + E2E test 5 (references/guide.md) |
| ACT-02 | 14-03, 14-04 | Agent auto-invokes skills when manifest description matches task | ✓ SATISFIED (caveat) | Model-driven only (D-13); manifest + `read_skill` wired; exactly-once holds for identical names but **broken for case variants on win32 (H-01)** |
| CAP-01 | 14-01, 14-03, 14-04 | Skill bodies are markdown referencing bundled files relative to skill dir | ✓ SATISFIED | `read_skill_path` → guarded `read_path` returns bundled reference |
| CAP-03 | 14-02 | `read_skill` always retained even when allowed-tools filtering active | ✓ SATISFIED | `retain_read_skills` contract unit-tested; enforcement wiring correctly deferred to Phase 17 |

All 6 requirement IDs declared in plan frontmatter (union: DISC-03, DISC-04, DISC-05, ACT-02, CAP-01, CAP-03) are accounted for and match the Phase 14 mapping in REQUIREMENTS.md. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `harness/runtime.py` | 189 | Case-sensitive dedup `==` vs case-insensitive lookup | 🛑 Blocker (H-01) | Violates D-07/ACT-02 "exactly once" on win32 — body injected twice for case variants (empirically confirmed) |
| `context/context.py` | 99-105, 112, 133-136 | `print()` debug banners to stdout | ⚠️ High (H-02) | Corrupts NDJSON RPC stdout when summarization fires (≥0.75× limit); skill bodies raise token pressure, making it reachable in normal Phase 14 usage. Pre-existing (Phase 13), not a phase must-have failure |
| `harness/runtime.py` | 189-196 | Check-then-await-then-append dedup (TOCTOU) | ⚠️ Latent (H-03) | Not exploitable today — no suspension point between check and append (empirically verified under `asyncio.gather`). Any future await in `add_skill_message`/`count_tokens` reopens the race; mark-before-inject is a cheap hardening |
| `agent/core.py` | 152, 190 | Index-based rollback (`del _messages[N:]`) | ⚠️ Medium (M-01) | Silently no-ops if summarization shrank `_messages` between baseline capture and cancel (small token limits) — the D-14 guarantee degrades in that edge; tests use token_limit=1000 so they don't exercise it |
| `tool/registry.py` | 110 | Mid-function `import time` | ℹ️ Low (L-05) | Style only |
| `skills/provider.py` + `skills/filter.py` | 11 / 5 | `RESERVED_SKILL_TOOLS` defined twice | ℹ️ Low (L-04) | Test pins equality; single source of truth claimed but not implemented |

### Review Findings Disposition (14-REVIEW.md)

| Finding | Verdict | Disposition |
| ------- | ------- | ----------- |
| H-01 Case-variant dedup bypass | **CONFIRMED** — reproduced empirically on win32; breaks must-have truth #1/#2 | Actionable gap; fix in `load_skill` dedup comparison + add regression test |
| H-02 Summarizer print() corrupts RPC stdout | **CONFIRMED in code** — not a phase must-have failure, but High production impact; pre-existing, amplified by skill bodies | Warning — route prints through logger/diagnostic sink (context.py) |
| H-03 Concurrent dedup TOCTOU | **NOT currently exploitable** — empirically verified dedup holds under concurrent gather (no suspension point between check and append) | Warning (latent) — mark-before-append hardening recommended |
| M-01 Cancel rollback can no-op | **Plausible** — index-based rollback fragile under summarization shrink; not exercised by tests | Warning — prefer identity-based removal / rollback API |
| M-02 read_skill_path no loaded-check | Design gap, not sandbox escape — containment holds | Info — Phase 15/17 concern |
| M-03/M-04/M-05, L-01..L-06 | Out of phase scope (worker race, prompt-injection hardening, size guards, etc.) | Info — track for later phases |

### Deferred Items

None — no gap found is explicitly addressed by a later phase's goal or success criteria (Phases 15/16/17 cover `/skill`, TUI indicator, and allowed-tools enforcement; none address dedup case-variant hardening, RPC stdout hygiene, or cancel-rollback identity).

### Human Verification Required

None — all checks were programmatic; the phase is backend-only by design (D-15) and the TUI/indicator work is Phase 16.

### Gaps Summary

**1 failed truth blocks full goal achievement — the D-07/ACT-02 "exactly once" dedup contract is broken for case variants on the primary win32 platform (review H-01, independently reproduced).**

- `RuntimeAPI.load_skill` dedups by comparing the raw caller name (`e["name"] == name`, `harness/runtime.py:189`) while `SkillStore.lookup` keys case-insensitively on win32 (`store.py:36-37`). Loading `demo-greeter` then `DEMO-GREETER` returns two `Loaded skill` acks, injects the body as a system message twice, and appends two `skill_state["loaded"]` records. This violates ROADMAP SC1 ("exactly once"), D-07 (no-op re-load), and ACT-02 (exactly-once auto-invoke) — and inflates every subsequent LLM call with a duplicate instruction block.
- The fix is small and localized: compare dedup against the canonical `info.name` after lookup (or key records with SkillStore's case-normalized dedupe key), plus a win32 case-variant regression test in `test_load_skill.py`/`test_skills_e2e.py`.
- The remaining 10 must-haves are verified: SkillStore index/load/guard, bundled-resource reads (CAP-01), traversal rejection with clear errors (DISC-04), reserved un-namespaced tools + collision guard + filter retention (D-01/D-02/D-03/CAP-03), system-role persist=False injection with summarization survival and JSONL exclusion (D-08/D-13/D-15), model-driven auto-invoke (D-13), cancel-mid-gather closure (D-14), and the Phase 12 manifest seam + `__skills__` production wiring (main.py, all 3 modes).

**Warnings (non-blocking for the phase goal, should be tracked):**
- H-02: `context.py` `print()` banners corrupt NDJSON RPC stdout when summarization fires — High production impact in `--rpc` mode, pre-existing but reachable with skill-body token pressure.
- H-03: latent TOCTOU in dedup — not exploitable today, cheap to harden (mark-before-inject).
- M-01: index-based cancel rollback can no-op under summarization interference at small token limits — D-14 guarantee degrades in that edge.

---

_Verified: 2026-08-02T13:30:00Z_
_Verifier: OpenCode (gsd-verifier)_
