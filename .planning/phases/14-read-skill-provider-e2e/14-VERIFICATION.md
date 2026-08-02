---
phase: 14-read-skill-provider-e2e
verified: 2026-08-02T19:00:00Z
status: passed
score: 11/11 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 10/11
  gaps_closed:
    - "Re-loading an already-loaded skill is a no-op returning an 'already loaded' ack — dedup via session.skill_state['loaded'] (D-07); the body loads into context exactly once (ROADMAP SC1, ACT-02) — H-01 fixed: load_skill dedups against canonical info.name post-lookup"
    - "ACT-02 auto-invoke holds end-to-end: the model-driven load path injects exactly one system body and dedups on re-load — same H-01 root cause closed; case-variant re-loads are no-op acks with exactly one body and one skill_state record"
  gaps_remaining: []
  regressions: []
human_verification: []
---

# Phase 14: read_skill Provider End-to-End — Verification Report

**Phase Goal:** Agent can load a skill body on demand via a dedicated `read_skill` tool and read bundled resources through path-scoped reads — Level-2/Level-3 disclosure. Bodies flow through the persist-safe plumbing from Phase 13 as system-role messages.
**Verified:** 2026-08-02T19:00:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (H-01 fixed by plan 14-05)

## Goal Achievement

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | `read_skill(name)` loads the full skill body into context as a system-role message **exactly once**; re-load is a no-op "already loaded" ack; tool result is a short ack, body never duplicated (SC1, D-05, D-07) | ✓ VERIFIED | **H-01 closed.** `harness/runtime.py:191-202`: `lookup()` runs first, dedup compares `e["name"] == info.name` (canonical post-lookup name — consistent with `SkillStore._key()` case-insensitive normalization on win32), no-op ack returns canonical name, `loaded.append` precedes the injection await (mark-before-inject, H-03 hardening). Empirical repro on this win32 machine: `load_skill('demo-greeter')` → `Loaded skill demo-greeter`; `load_skill('DEMO-GREETER')` → `Skill 'demo-greeter' already loaded`; body_count=1; record_count=1. D-05 ack-not-body holds |
| 2   | Agent can read bundled resources (`references/`, `scripts/`, `assets/`) by relative path inside the loaded skill's directory (SC2, DISC-05, CAP-01) | ✓ VERIFIED | `SkillStore.read_path` reads `references/guide.md`; E2E test 5 returns `GUIDE REFERENCE CONTENT` through the real provider + store (unchanged from initial verification, no regression) |
| 3   | Every path-traversal attempt — `../`, `..\`, absolute paths, win32 drive-path tricks, symlink escapes — is rejected with a clear error naming the skill AND the rejected path; reads never escape the skills directory (SC3, DISC-04, D-10/D-11/D-12) | ✓ VERIFIED | `skills/store.py:56-60` canonicalize+contain guard (`(dir/rel).resolve()` + `is_relative_to(base)`); parametrized suite in `tests/test_skills_store.py` (12 pass + 1 symlink skip on non-admin win32) — full suite green (156 passed, 1 skipped) |
| 4   | `read_skill`/`read_skill_path` are reserved, un-namespaced tool names registered by the async `__skills__` provider — LLM sees exactly these two (SC4, D-01/D-02) | ✓ VERIFIED | `skills/provider.py` `fetch_tools()` returns exactly the two un-namespaced schemas; `tests/test_skills_provider.py` asserts names + no prefix — no regression |
| 5   | No provider can shadow or be shadowed on the reserved skill tool names — collision raises a clear error (SC4, D-03) | ✓ VERIFIED | `tool/registry.py:134-140` reserved-name guard before the generic collision branch, raises `ValueError` naming the reserved tool and owner; collision test passes — no regression |
| 6   | The allowed-tools filter always retains `read_skill`/`read_skill_path` (`allowed ∪ {read_skill, read_skill_path}`), unit-tested here (SC4, CAP-03) | ✓ VERIFIED | `skills/filter.py` `retain_read_skills` (None/empty/union cases all tested) — enforcement wiring correctly deferred to Phase 17; no regression |
| 7   | `load_skill` injects via tagged `add_skill_message(name, body)`: system role, `persist=False`, `skill_name` set; body visible every turn and exempt from summarization (D-06/D-08, Phase 13 plumbing) | ✓ VERIFIED | `context/context.py:40-42` builds `Message(role="system", content=body, persist=False, skill_name=name)`; `Message.skill_name` field present (`context/message.py:18`), `from_dict` never reads the key; `_maybe_summarize` exempts system role — no regression |
| 8   | Auto-invoke is model-driven only — no keyword matching, no heuristic pre-loading (D-13) | ✓ VERIFIED | Grep across production `harness/` and `agent/` finds no keyword/heuristic/pre-load matching; the manifest + `read_skill` tool are the only mechanism — no regression |
| 9   | Loaded bodies flow persist-safe: never serialized to JSONL (`persist=False` filter), survive forced summarization (system-role exemption) (D-15) | ✓ VERIFIED | `session/models.py:85` `to_events()` filters `m.persist` (and L114 identity-based save watermark); E2E tests 3-4 pass through the real stack — no regression |
| 10  | Cancelling a turn during the tool-result gather leaves no partial tool messages and no dangling `tool_calls` — next turn streams cleanly (SC5, D-14) | ✓ VERIFIED | `agent/core.py:152,185-191` baseline-captured rollback with `total_tokens` recompute; 3 regression tests pass. **Caveat (unchanged, advisory):** M-01 — rollback is index-based and can silently no-op if summarization shrinks `_messages` between baseline capture and cancel (small token limits); not exercised by tests (token_limit=1000) |
| 11  | Production wiring: main.py builds the manifest from `discover_skills` + `build_manifest_text`, attaches it via `_create_agent`, registers `__skills__` BEFORE `runtime.start()`, and asserts `read_skill` visible after start — Phase 12 seam live end-to-end | ✓ VERIFIED | `main.py _build_runtime()` (L200-224) + D-03 asserts in worker (L292), repl (L338), rpc (L223); `harness/runtime.py` manifest attach in `_create_agent`; `session/models.py` appends `skill_manifest` to the system prompt; `skills/__init__.py` barrel complete — no regression |

**Score:** 11/11 truths verified

### Gap Closure Verification (14-05)

| 14-05 must-have | Status | Evidence |
| --------------- | ------ | -------- |
| Case-variant re-load (`demo-greeter` → `DEMO-GREETER`) is a no-op on win32 — second call returns "already loaded" ack, body exactly once (D-07, SC1, ACT-02) | ✓ VERIFIED | Empirical: `ack2 = "Skill 'demo-greeter' already loaded"`, `body_count=1`. Code: `runtime.py:193` dedups against `info.name` |
| `skill_state['loaded']` holds exactly one record (canonical name + base dir) after the case-variant re-load (D-09) | ✓ VERIFIED | Empirical: `record_count=1`, `records=[{'name': 'demo-greeter', 'dir': ...}]`. Code: `runtime.py:199` appends `{"name": info.name, "dir": str(info.path)}` |
| Regression tests fail pre-fix and pass post-fix; full suite green (156 + 1 skip, 0 regressions) | ✓ VERIFIED | RED commit `c4bfb44` (tests failed pre-fix with 2 bodies/2 records per commit message), GREEN commit `d5ed6a2`; `pytest tests/test_load_skill.py tests/test_skills_e2e.py -q` → 15 passed; full suite → 156 passed, 1 skipped |
| Artifact `harness/runtime.py` contains `e['name'] == info.name` | ✓ VERIFIED | `runtime.py:193` — exactly one match |
| Artifact `tests/test_load_skill.py` contains `test_case_variant_reload_never_double_injects` | ✓ VERIFIED | Line 176 — asserts 1 body (`len([... "Hello body" ...]) == 1`) + 1 record + canonical name |
| Artifact `tests/test_skills_e2e.py` contains `test_case_variant_reload_never_double_injects` | ✓ VERIFIED | Line 200 — same assertions through the real stack |
| Key link: load_skill dedup key = canonical `info.name` from `SkillStore.lookup()` | ✓ WIRED | `runtime.py:191` lookup → `:193` `existing = next((e for e in loaded if e["name"] == info.name), None)` |
| Key link: loaded record append uses canonical `info.name` (same string as dedup key) | ✓ WIRED | `runtime.py:199` `loaded.append({"name": info.name, "dir": str(info.path)})` — same canonical string as the L193 dedup check |

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `skills/store.py` | SkillStore: index, body load, traversal-guarded read_path | ✓ VERIFIED | `class SkillStore` with `lookup`/`load`/`read_path` + `is_relative_to` guard — unchanged |
| `tests/test_skills_store.py` | Traversal suite (posix + win32 vectors) same wave | ✓ VERIFIED | 13 tests; 12 pass + 1 symlink skip (non-admin win32) — unchanged |
| `skills/provider.py` | Async SkillToolProvider (fetch_tools/call_tool) | ✓ VERIFIED | Two reserved schemas, injected-handler dispatch, RESERVED_SKILL_TOOLS — unchanged |
| `skills/filter.py` | `retain_read_skills` pure retention | ✓ VERIFIED | None/union/empty semantics correct — unchanged |
| `tool/registry.py` | Reserved-name collision guard | ✓ VERIFIED | Guard at L134-140 — unchanged |
| `context/message.py` | `Message.skill_name` optional field, from_dict-compatible | ✓ VERIFIED | `skill_name: str | None = None` (L18), last field — unchanged |
| `context/context.py` | `add_skill_message(name, body)` — system, persist=False, tagged | ✓ VERIFIED | L40-42 exactly per contract — unchanged |
| `harness/runtime.py` | `load_skill` single shared path + provider handlers + manifest attach | ✓ VERIFIED | **H-01 fixed**: dedup against canonical `info.name` (L193), lookup-before-dedup (L191), mark-before-inject (L199 before L201), canonical no-op ack (L195); `_read_skill_path` + `make_skill_provider` + manifest attach intact |
| `main.py` | Production wiring: SkillStore + `__skills__` + reserved-name assert | ✓ VERIFIED | `_build_runtime` + 3-mode registration + asserts (L223/292/338) — unchanged |
| `skills/__init__.py` | Barrel exports full skills surface | ✓ VERIFIED | SkillStore, SkillToolProvider, RESERVED_SKILL_TOOLS, retain_read_skills — unchanged |
| `agent/core.py` | Cancel-mid-gather cleanup (CancelledError) | ✓ VERIFIED | Baseline-capture rollback + total_tokens recompute (M-01 caveat) — unchanged |
| `tests/test_cancel_mid_gather.py` | D-14 regression (3 tests) | ✓ VERIFIED | All 3 pass — unchanged |
| `tests/test_skills_e2e.py` | D-15 backend E2E (5 + 1 = 6 tests, real stack) | ✓ VERIFIED | Load/inject, dedup, case-variant regression (new), summarize-survive, JSONL-untouched, read_skill_path — all through real SkillStore+Registry+Provider+RuntimeAPI |
| `tests/test_load_skill.py` | Load-path suite (8 + 1 = 9 tests) | ✓ VERIFIED | skill_name, add_skill_message, dedup, case-variant regression (new), skill_state, JSONL, unknown, manifest — all pass |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `skills/store.py` | `skills/discovery.py` | index built from `discover_skills()`; dedupe-key convention | ✓ WIRED | Case-insensitive key mirrors `_dedupe_key` — unchanged |
| `skills/store.py` | `pathlib.Path.resolve` | canonicalize + `is_relative_to` containment | ✓ WIRED | All vectors rejected — unchanged |
| `skills/provider.py` | `harness/runtime.py` | injected `load_handler`/`read_handler` | ✓ WIRED | `make_skill_provider()` binds `load_skill` + `_read_skill_path` — unchanged |
| `tool/registry.py` | `skills/provider.py` | `add_provider("__skills__", provider, namespace=None)` + RESERVED_SKILL_TOOLS import | ✓ WIRED | No prefix; guard fires on collision — unchanged |
| `context/context.py` | `context/message.py` | `add_skill_message` builds tagged system Message | ✓ WIRED | L40-42 → `add_message` — unchanged |
| `harness/runtime.py` | `skills/store.py` | `load_skill` → `SkillStore.lookup/load`; `_read_skill_path` → `read_path` | ✓ WIRED | **Dedup key now = canonical `info.name` returned by the case-insensitive lookup** — the H-01 key disagreement is resolved |
| `harness/runtime.py` | `session/models.py` | `skill_state["loaded"]` name+dir records | ✓ WIRED | Record written (D-09); **case-variant re-loads no longer double-record** (dedup key == record name == canonical `info.name`) |
| `main.py` | `skills/provider.py` | `_build_runtime` registers `__skills__` before start; assert after | ✓ WIRED | All 3 modes; asserts present — unchanged |
| `agent/core.py` | `context/context.py` | CancelledError rollback of `_messages` + total_tokens | ✓ WIRED | L185-193 (M-01 index-based caveat) — unchanged |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `SkillStore.load` | body | `SKILL.md` via `parse_skill_doc` after frontmatter | Real file content (`# Demo\n\nHello body`) | ✓ FLOWING |
| `SkillStore.read_path` | file content | bundled resource files via guarded resolve+read | Real (`GUIDE REFERENCE CONTENT`) | ✓ FLOWING |
| `RuntimeAPI.load_skill` | system message | SkillStore body → `add_skill_message` | Real body, system role, persist=False | ✓ FLOWING |
| `RuntimeAPI._create_agent` | `session.skill_manifest` | `discover_skills` + `build_manifest_text` (real discovery) | Real manifest text, appended to system prompt | ✓ FLOWING |
| `skill_state["loaded"]` | dedup records | `load_skill` append | Real; **exactly one record per skill including case variants** (H-01 fixed) | ✓ FLOWING |
| E2E JSONL | stored events | `to_events()` persist filter | Skill body absent; user/assistant present | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Traversal vectors rejected with skill+path error | inline script over real `SkillStore` (`../`, `..\`, `/etc/passwd`, `C:\windows\win.ini`, `../../`) | All 5 raise `ValueError` naming both skill and path | ✓ PASS |
| Legitimate in-bounds read succeeds | `read_path("demo-greeter", "references/guide.md")` | `GUIDE REFERENCE CONTENT` | ✓ PASS |
| Unknown skill errors clearly | `store.load("nope")` | `KeyError: "Unknown skill 'nope'"` | ✓ PASS |
| Body loads after frontmatter | `store.load("demo-greeter")` | `'# Demo\n\nHello body'` | ✓ PASS |
| Same-name re-load dedups (D-07) | `load_skill("demo-greeter")` twice | `Loaded skill demo-greeter` + `already loaded`; body once | ✓ PASS |
| **Case-variant re-load dedups (D-07 win32, H-01 regression)** | `load_skill("demo-greeter")` then `load_skill("DEMO-GREETER")` | **`Loaded skill demo-greeter` → `Skill 'demo-greeter' already loaded`; body_count=1; record_count=1** | ✓ PASS (was ✗ FAIL pre-fix) |
| Concurrent same-skill loads (H-03 TOCTOU) | `asyncio.gather(load_skill, load_skill)` | `Loaded` + `already loaded`; body once — record now appended before the injection await (mark-before-inject hardened the window) | ✓ PASS (hardened) |
| Targeted regression files | `python -m pytest tests/test_load_skill.py tests/test_skills_e2e.py -q` | 15 passed (13 prior + 2 new H-01 regression tests) | ✓ PASS |
| Full test suite | `python -m pytest -q` | 156 passed, 1 skipped (11.07s) — matches 14-05 SUMMARY claim | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| DISC-03 | 14-01, 14-02, 14-03, 14-05 | Agent can load a skill body on demand via dedicated `read_skill` tool | ✓ SATISFIED | `read_skill` registered, `load_skill` injects body exactly once incl. case variants (H-01 fixed); E2E tests 1 + case-variant regression |
| DISC-04 | 14-01, 14-03 | `read_skill` reads path-scoped to skills dir — no traversal | ✓ SATISFIED | `read_path` canonicalize+contain; review independently found no escape; all vectors rejected |
| DISC-05 | 14-01 | Bundled resources (`references/`, `scripts/`, `assets/`) readable via path-scoped reads | ✓ SATISFIED | `read_path` + E2E test 5 (references/guide.md) |
| ACT-02 | 14-03, 14-04, 14-05 | Agent auto-invokes skills when manifest description matches task | ✓ SATISFIED | Model-driven only (D-13); manifest + `read_skill` wired; exactly-once holds for identical names AND case variants on win32 (H-01 fixed, empirical) |
| CAP-01 | 14-01, 14-03, 14-04 | Skill bodies are markdown referencing bundled files relative to skill dir | ✓ SATISFIED | `read_skill_path` → guarded `read_path` returns bundled reference |
| CAP-03 | 14-02 | `read_skill` always retained even when allowed-tools filtering active | ✓ SATISFIED | `retain_read_skills` contract unit-tested; enforcement wiring correctly deferred to Phase 17 |

All 6 requirement IDs declared in plan frontmatter (union across 14-01..14-05: DISC-03, DISC-04, DISC-05, ACT-02, CAP-01, CAP-03) are accounted for and match the Phase 14 mapping in REQUIREMENTS.md. No orphaned requirements. With H-01 closed, DISC-03 and ACT-02 are now fully satisfied with no caveat.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `harness/runtime.py` | 193 | Case-sensitive dedup `==` vs case-insensitive lookup | ~~🛑 Blocker~~ **RESOLVED (H-01)** | Dedup now compares canonical `info.name` post-lookup — case-variant re-loads are no-ops (empirically verified) |
| `context/context.py` | 99-105, 112, 133-136 | `print()` debug banners to stdout | ⚠️ Advisory (H-02, deferred) | Corrupts NDJSON RPC stdout when summarization fires — pre-existing (Phase 13), **explicitly deferred with disposition in 14-05 plan, NOT a phase must-have** |
| `harness/runtime.py` | 199-201 | Check-then-await-then-append dedup (TOCTOU) | ℹ️ Hardened (H-03) | `loaded.append` now precedes the injection await — no suspension point remains between mark and inject |
| `agent/core.py` | 152, 190 | Index-based rollback (`del _messages[N:]`) | ⚠️ Advisory (M-01, deferred) | Can no-op if summarization shrank `_messages` (small token limits) — **explicitly deferred in 14-05 plan, NOT a phase must-have** |
| `harness/runtime.py` | 204-208 | `read_skill_path` no loaded-check | ℹ️ Advisory (M-02, deferred) | Contract gap, not sandbox escape — **deferred to Phase 15/17 per 14-REVIEW disposition** |
| `tool/registry.py` | 110 | Mid-function `import time` | ℹ️ Low (L-05) | Style only |
| `skills/provider.py` + `skills/filter.py` | 11 / 5 | `RESERVED_SKILL_TOOLS` defined twice | ℹ️ Low (L-04) | Test pins equality; single source of truth claimed but not implemented |

### Review Findings Disposition (14-REVIEW.md)

| Finding | Verdict | Disposition |
| ------- | ------- | ----------- |
| H-01 Case-variant dedup bypass | **CONFIRMED → FIXED** | Closed by 14-05: canonical-name dedup + 2 regression tests; empirically verified post-fix |
| H-02 Summarizer print() corrupts RPC stdout | Confirmed in code — not a phase must-have | Deferred (14-05 plan disposition): route prints through logger in a hardening pass |
| H-03 Concurrent dedup TOCTOU | Latent → **hardened** | Mark-before-inject folded into the H-01 fix (record appended before injection await) |
| M-01 Cancel rollback can no-op | Plausible edge, not exercised by tests | Deferred (14-05 plan disposition): prefer identity-based removal / rollback API |
| M-02 read_skill_path no loaded-check | Design gap, not sandbox escape | Deferred: Phase 15/17 concern |
| M-03/M-04/M-05, L-01..L-06 | Out of phase scope | Info — track for later phases |

### Deferred Items

None — the two previously-failed truths are now verified (gaps_remaining: []). Advisory findings H-02, M-01, M-02 were explicitly deferred with disposition in the 14-05 plan's `deferred_scope_notes` and are NOT phase must-have truths; per the task scope they do not block this phase. They remain open hardening items for later phases (Phases 15/16/17 goals do not cover them — a hardening note should be filed for H-02/M-01).

### Human Verification Required

None — all checks were programmatic (grep, full pytest run, empirical spot-check of the exact prior H-01 repro on this win32 machine). The phase is backend-only by design (D-15); TUI/indicator work is Phase 16.

### Gaps Summary

**No blocking gaps remain — the phase goal is achieved (11/11 truths verified).**

- The single blocking gap from the initial verification (H-01: D-07/ACT-02 "exactly once" dedup broken for case variants on win32) is closed by plan 14-05. `RuntimeAPI.load_skill` now dedups against the canonical `info.name` returned by the case-insensitive `SkillStore.lookup()` (`harness/runtime.py:193`), the loaded record is appended before the injection await (`:199`), and the no-op ack returns the canonical name (`:195`). The exact prior repro — `load_skill('demo-greeter')` then `load_skill('DEMO-GREETER')` — now returns `Skill 'demo-greeter' already loaded` with exactly one system body and one `skill_state["loaded"]` record, verified empirically on this machine.
- Two regression tests pin the contract (unit in `tests/test_load_skill.py:176`, E2E through the real stack in `tests/test_skills_e2e.py:200`), both RED pre-fix (`c4bfb44`) and GREEN post-fix (`d5ed6a2`). Full suite: 156 passed, 1 skipped, 0 regressions — matching the 14-05 SUMMARY claim exactly.
- All remaining 9 truths were re-checked (existence + wiring + data flow) with no regressions: traversal guard, provider surface, D-03 collision guard, CAP-03 retention, system-role persist=False injection, model-driven auto-invoke, JSONL safety, cancel-mid-gather cleanup, and the Phase 12 manifest seam + `__skills__` production wiring.

**Advisory warnings (non-blocking, deferred with disposition in 14-05 — tracked for a hardening pass):**
- H-02: `context.py` `print()` banners corrupt NDJSON RPC stdout when summarization fires — High production impact in `--rpc` mode, pre-existing (Phase 13), not a phase must-have failure.
- M-01: index-based cancel rollback can no-op under summarization interference at small token limits — D-14 guarantee degrades in that edge; not exercised by tests.
- M-02: `read_skill_path` does not enforce the "already-loaded" contract — design gap, containment holds; Phase 15/17 concern.

---

_Verified: 2026-08-02T19:00:00Z_
_Verifier: OpenCode (gsd-verifier)_
