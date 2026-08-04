# Project Research Summary

**Project:** AgentHarness v1.1 — Skills System (progressive-disclosure SKILL.md loading)
**Domain:** Agent harness / progressive-disclosure skills (discovery → activation → execution pipeline)
**Researched:** 2026-08-01
**Confidence:** HIGH (two LOW/MEDIUM flags — see Confidence Assessment)

## Executive Summary

This milestone adds a Claude Code-style Agent Skills system to an already-working Python 3.12 async agent harness: users drop `SKILL.md` files under `.agentharness/skills/<name>/`, the harness advertises every skill's `name` + `description` as a budgeted manifest in the system prompt (Level-1 disclosure), the full instruction body loads into context only when the agent calls a dedicated `read_skill` tool or the user types `/skill <name>` (Level-2), and bundled `references/`/`scripts/`/`assets/` load on demand via path-scoped reads (Level-3). This mirrors the open agentskills.io standard adopted by Claude Code, Codex, Gemini CLI, and Microsoft Agent Framework. The recommended approach is a layered subsystem, not a fork: a new `skills/` package (pure domain logic) plugged into four existing seams — `session/models.py` (manifest assembly), `context/context.py` (system-role body injection, which is already summarization-exempt at line 88), `tool/registry.py` (a new `__skills__` tool provider, no structural change), and `backend/rpc` + `tui-ink` (a `skills.load` RPC method and a typed `skill_loaded` event for the `/skill` command and indicator).

**Stack decision: exactly ONE new runtime dependency — PyYAML 6.0.3** — plus a small hand-rolled `---` delimiter splitter that delegates parsing to `yaml.safe_load` (safe for untrusted files). Everything else reuses existing machinery: tiktoken-based `count_tokens` for accounting, stdlib `pathlib`/`dataclasses` for discovery and the skill model. No DB, no file watcher, no schema validator, no ruamel.yaml, no python-frontmatter (initially). **Flag for the roadmapper: the four research files disagree on this.** STACK.md, FEATURES.md, and PITFALLS.md all recommend PyYAML (PITFALLS P-07 explicitly warns that hand-rolled YAML splits mis-parse and are a security hazard); only ARCHITECTURE.md argues for a zero-dependency ~40-line hand-rolled parser. The reconciliation: STACK.md's own "frontmatter splitter" pattern (~20 lines, delimiter-only, parsing delegated to `safe_load`) is safe and satisfies both — the roadmapper should lock PyYAML 6.0.3 and the splitter pattern.

**Key risks, all mitigated by research:** (1) **Manifest budget overflow** — enforce a *character*-based cap (~1,500 chars, Claude Code's precedent), not tiktoken tokens, because `count_tokens` is model-dependent and the budget must be stable across model switches; ship the cap with a truncation rule and trim-warnings in the discovery phase, not later. (2) **D-13 JSONL leak** — the loaded-skill body must persist in-session but never serialize to the JSONL file; this requires a `Message.persist` flag, a `to_events()` filter, and — critically — a matching `mark_saved()` index fix, or event loss/duplication occurs. (3) **Provider acceptance of mid-conversation system messages** — `to_llm_messages()` places injected bodies *after* user/assistant messages; verify against the real configured backend and design the "append to system block" fallback up front. (4) **Path traversal** on `read_skill(path=...)` — resolve + `is_relative_to()` containment, with win32 test vectors, shipped in the same wave as the tool. (5) **Two deadlock-style traps:** the `allowed-tools` filter must *always* retain `read_skill` (union `allowed ∪ {read_skill}`), and the persist/filter design must never mutate registry state (pure per-iteration projection + dispatch-side rejection in `call_tool`).

## Key Findings

### Recommended Stack

**Source: [STACK.md](STACK.md) — HIGH confidence.** One new runtime dependency: **PyYAML 6.0.3** (2025-09-25; cp312 win_amd64 wheels verified on PyPI; `requires-python >=3.8`; independent of all existing deps). Added to `requirements.txt` as `PyYAML>=6.0.3`. All other research files agree it is the only new dep, with ARCHITECTURE.md the lone dissenter on the hand-rolled question (see Executive Summary for the resolution).

**Core technologies:**
- **PyYAML 6.0.3**: parse YAML frontmatter — `yaml.safe_load` (SafeLoader) is safe for untrusted user-authored files; tiny, ubiquitous, production-stable; read-only use makes ruamel's round-trip features dead weight.
- **tiktoken (existing, `llm/base.py:49`)**: `count_tokens()` for manifest accounting — consistency with context accounting for free; but see the P-01 flag: the *cap unit* should be characters, not tokens (model-dependent).
- **Python stdlib (pathlib, dataclasses, 3.12)**: discovery scan via `os.scandir`/`Path.iterdir()` — O(dirs), microseconds at this scale; `Path.is_relative_to` (3.12) for traversal containment.
- **Internal `skills/` package**: `frontmatter.py` splitter (~20 lines, `---` delimiters, delegates to `safe_load`, degrades to `({}, body)` on any error) + inline `isinstance` validation in a `Skill` dataclass.

**Explicitly NOT used:** ruamel.yaml, watchdog/FS watchers (manifest is a fixed session snapshot; `read_skill` resolves by name at call time anyway), SQLite/JSON index (no benefit at this scale), python-frontmatter (until frontmatter variance grows — it just wraps PyYAML, one-line swap later), pydantic/cerberus (2-3 optional fields), any new token library, any change to `context/context.py` (system role already flows through, survives summarization, serializes to JSONL).

### Expected Features

**Source: [FEATURES.md](FEATURES.md) — HIGH confidence.** The open agentskills.io standard (30+ tools) defines the three mandatory progressive-disclosure behaviors; all map to locked decisions D-01..D-16.

**Must have (table stakes):**
- **SKILL.md format, required `name` + `description` frontmatter** — `name` must match the folder (validate + warn on mismatch, don't fail) (D-01..D-03).
- **Manifest of name+description in the system prompt** with a character cap + deterministic trim (D-06, D-07).
- **Description is the routing signal** — says what the skill does *and when to use it*; warn (don't reject) on <~20 chars (D-03).
- **On-demand activation** via a dedicated `read_skill(name=...)` tool with a valid-name enum schema (D-08).
- **Loaded body persists for the session** as a system-role message (D-12).
- **User invocation via `/skill <name>`** slash command + RPC (D-11).
- **Malformed skill never breaks the harness** — skip-with-warning; duplicate names first-wins with deterministic sort (D-04, D-05).
- **Level-3 bundled resources** (`references/`, `scripts/`, `assets/`) loaded on demand via path-scoped reads (D-09, D-10).

**Should have (differentiators — AgentHarness is deliberately *better* than the references here):**
- **System-role summarization exemption = zero-machinery persistence** — beats Claude Code's compaction re-attach subsystem (5k/skill, 25k combined budget, drops older skills). Loaded bodies can't be dropped. Highest-leverage architectural finding.
- **`allowed-tools` as *real enforcement*** (tool-list filter while loaded) — the spec marks it experimental; Claude Code/Codex treat it as a per-turn permission *grant*, most agents ignore it. Filtering is the only coherent interpretation for a harness with no permission-prompt UX (D-16).
- **Path-scoped `read_skill`** — no generic filesystem exposure (vs Claude Code's bash/read).
- **TUI "Skill loaded" transparency indicator** via a typed event (D-14).
- **Session-scoped, never persisted to JSONL** — clean portability semantics (D-13).
- **Per-call manifest rebuild = free live discovery** — a skill written mid-session appears next turn with zero watcher infrastructure.

**Defer (v2+, also in MILESTONE-CONTEXT deferred list):** skill authoring/management UI, marketplace, script-as-tool registration (D-15), user-global skills dir (D-01), skill chaining/nested skills, multiple simultaneously-loaded-skill combined filtering, `/skills` listing command (natural small P2 follow-up).

**Anti-features (explicitly rejected):** keyword/embedding trigger matching (the standard's rationale explicitly rejects it — brittle, doesn't compose), script-as-tool registration, persisting loaded bodies to JSONL, loading all bodies at session start, skill chaining now, authoring UI/marketplace now, user-global dir now, manifest without a cap, `allowed-tools` as permission-grant.

### Architecture Approach

**Source: [ARCHITECTURE.md](ARCHITECTURE.md) — HIGH confidence (all seams verified in source).** A subsystem layered on the existing harness, delivered through existing mechanisms only. New top-level `skills/` package (pure domain, one-way deps, no cycles — never imports `agent/`):

1. **`skills/models.py`** — `SkillInfo`, `SkillState`, `SkillLoadResult` dataclasses; `SkillState` is session-scoped and never serialized (D-13).
2. **`skills/discovery.py`** — one-pass scan + frontmatter parse; skip-and-warn (D-04); normalized first-wins (D-05); budget-trim support (D-07).
3. **`skills/manifest.py`** — pure function formatting entries into a system-prompt section, capped at budget; `None` when no skills.
4. **`skills/store.py`** — `SkillStore`: index, `load(session, name)`, `read_path(name, rel)` with traversal guard; owns the risky I/O.
5. **`skills/provider.py`** — `SkillToolProvider`, an **async** `ToolProvider` registered as `__skills__` (no namespace → tool name stays `read_skill`). `LocalToolProvider` can't be reused — its handlers are sync.
6. **`skills/filter.py`** — pure whitelist-filter of `list_tools()` output; always retains `read_skill`.

**Integration points (touch-points only, no rewrites):**
- `session/models.py` — `skill_manifest`/`skill_state` as **non-serialized Session fields** (set once at `_create_agent()` with an `if session.skill_manifest is None` guard); Skills section appended in `_build_system_prompt()` (rebuilt per call = free live discovery); `persist` filter in `to_events()`.
- `context/context.py` — **NO change**: system role already supported, summarization-exempt (line 88), serializes to JSONL (hence the `persist` flag, see traps).
- `agent/core.py` — a `read_skill` branch in the result loop (inject body as `Message(role="system")` + short ack tool message); one injected `tool_filter` line at the `list_tools()` boundary (line 108).
- `tool/registry.py` — **NO structural change**: `add_provider("__skills__", SkillToolProvider)` slots into the existing provider protocol.
- `backend/rpc/protocol.py` + `adapter.py` + `server.py` — `skills.load` RPC method; `NotificationType.skill_loaded` + `_DOMAIN_TO_NOTIFICATION`/extractor.
- `main.py` + `harness/runtime.py` — wiring (build SkillStore + manifest once, pass to all 4 RuntimeAPI construction sites); `RuntimeAPI.load_skill()` is the **single shared load path** for both model-driven and user-driven activation (Pattern: load-once-shared-handler).
- `tui-ink/` — `app.tsx` `/skill ` intercept (never fall through to `submitPrompt`), `types.ts` event union, `agent-store.ts` notice, `rpc-client.ts`.

**Key patterns:** provider-as-tool (async protocol); session-scoped mutable state on the `Session` object (scope + reset on `/new` come free, vs an anti-pattern runtime dict keyed by session id); load-once-shared-handler (prevents read_skill//skill drift); event-notification fan-out for the TUI indicator.

**The two implementation traps the plan must not miss:**
1. **to_events/D-13 JSONL leak (ARCHITECTURE Anti-Pattern 2):** summarization exemption ≠ serialization exemption — `Session.to_events()` serializes *all* `_context._messages` including system role. Fix: new `Message.persist: bool = True` field; skill bodies created with `persist=False`; `to_events()` filters them. **Critical pairing: `mark_saved()` must count the same filtered set** — it currently counts raw `len(self._context._messages)` while `unpersisted_events()` slices the filtered `to_events()`, so an unfixed `mark_saved()` causes index drift and event loss/duplication on save.
2. **read_skill-never-filtered guardrail (ARCHITECTURE Anti-Pattern 6 / PITFALLS P-02, P-05):** a naive whitelist filter removes `read_skill` itself → the skill can't load references or a second skill — deadlock. The filter must always compute `allowed ∪ {"read_skill"}`.

### Critical Pitfalls

**Source: [PITFALLS.md](PITFALLS.md) — HIGH for codebase facts, MEDIUM for provider/external claims.** Top 5:

1. **P-01 Manifest token-budget overflow** — the manifest is injected on *every* LLM call; unmeasured, it silently eats the window (lost-in-the-middle) and the ~1,500-char cap becomes meaningless. **Avoid:** enforce the cap in *characters* (model-independent), measure the whole assembled system prompt, deterministic truncation (sort by name, first-wins prefix) + log trimmed skills, unit test "manifest never exceeds X chars for N skills." → **Phase 1.**
2. **P-07 Malformed frontmatter crashing discovery** — discovery runs inside system-prompt assembly, which runs on *every* LLM call; one bad file 500s everything. **Avoid:** per-skill try/except with an exception taxonomy (`FrontmatterError`/`YAMLError`/`OSError` → warn + skip, nothing escapes), PyYAML `safe_load` only, sanitize descriptions for manifest embedding (strip newlines/control chars), mtime-invalidated caching, fixture tests (broken YAML, missing name, empty file, non-UTF8, dir without SKILL.md). → **Phase 1.**
3. **P-06 Path traversal on skill-dir reads** — the built-in file tools are *unsandboxed* (CONCERNS.md flag); naive `open(base_dir / path)` exposes `.env`, session JSONL, any file, on win32 with both `/` and `\` plus `C:\`. **Avoid:** canonicalize + contain — `p = (base_dir / rel).resolve(); if not p.is_relative_to(base_dir.resolve()): raise ValueError`; reject non-relative args; test `../`, `..\`, absolute, symlink-to-outside, case tricks. Ship tests with the tool, not in "hardening." → **Phase 3.**
4. **P-03 Wrong-role injection (breaks the summarization exemption)** — injecting as `user` gets compacted away; as `assistant` breaks the OpenAI alternation contract (400) and *triggers* `_maybe_summarize`. **Avoid:** dedicated `add_skill_message()` recording `role="system"` + `metadata={"kind":"skill","name":...}`; verify the real backend accepts mid-conversation system messages; design the append-to-system-block fallback from day one. → **Phase 3** (mechanics) + **Phase 4** (provider-compat E2E).
5. **P-05 allowed-tools filtering that persists past the loaded window** — mutating registry state removes tools forever (no unload path exists) and `call_tool` doesn't check the filter (bypass); combined semantics across multiple loaded skills are undefined. **Avoid:** pure per-iteration projection (registry untouched), dispatch-side rejection in `call_tool`, combined-filter semantics decided up front (intersection = safest), filter state tied to the same object as load state. **The filter design must be decided before the activation phase ships.** → **Phase 4** (design) + **Phase 6** (implementation).

**Also critical (mapped below):** P-02 (read_skill name collision/confusion), P-04 (/skill TUI-vs-RPC routing), P-08 (name collisions incl. folder-vs-frontmatter + win32 case), P-09 (loaded-context accumulation, no unload path), P-10 (streaming/cancel — dangling tool_calls mid-gather → 400; typed event needed, no token/tool_result smuggling), P-11 (skill tokens inflate `total_tokens` → chat summarized sooner; threshold must be chat-relative).

## Implications for Roadmap

Six phases, ordered by dependency (pure → integrated) and by risk (the persist fix lands *before* any real skill body can flow through `to_events()`). This follows the ARCHITECTURE.md build order, re-grouped per the synthesizer's direction (allowed-tools implementation last, design first). Phase boundaries below are suggestions; the roadmapper assigns numbers.

### Phase 1: Skills discovery & manifest (SKL-01/SKL-02)
**Rationale:** Pure domain, zero integration risk — fastest feedback, no harness risk. The manifest-in-prompt is the cheapest user-visible win (SKL-02) and ships before any tool exists. The cap/truncation/warnings must land with assembly — retrofitting a cap after skills exist is politically hard.
**Delivers:** `skills/models.py` + `skills/discovery.py` + `skills/frontmatter.py` + `skills/manifest.py` + unit tests; PyYAML 6.0.3 added to requirements.txt; `# Available Skills` section in `_build_system_prompt()` from a precomputed manifest string on `Session`; skip-and-warn (D-04); normalized first-wins (D-05); char-cap + deterministic trim + trim-warnings (D-07).
**Addresses:** table-stakes features D-01..D-07.
**Avoids:** P-01 (char cap + whole-prompt measurement test), P-07 (per-skill try/except, fixtures, sanitized descriptions, mtime cache), P-08 (folder-vs-frontmatter name validation, reserved names `read_skill`/slash-command collisions).

### Phase 2: Context plumbing — the persist fix (D-12/D-13 foundation)
**Rationale:** This is the highest-risk change in the milestone (it touches session serialization). It must come second — *before* the read_skill provider makes real skill bodies flow — so the JSONL exclusion is proven before any body is ever written.
**Delivers:** `Message.persist: bool = True` field; `to_events()`/`mark_saved()` filter **with the index-drift fix as a paired change** (Anti-Pattern 2); `Session.skill_manifest`/`skill_state` non-serialized fields; summarization-exemption documented at `context.py:88` (a comment, not a code change).
**Addresses:** D-12 (persist for session) + D-13 (not persisted to JSONL) — the two decisions that collide with existing code.
**Avoids:** the to_events/D-13 JSONL-leak trap; P-09/P-11 accounting groundwork (token accounting can begin here or in Phase 4).

### Phase 3: read_skill provider end-to-end (SKL-03)
**Rationale:** The store's side effects (load/read) depend on the Phase 2 plumbing; the tool's end-to-end path proves the whole backend loop before any frontend work. Per P-05, the filter *design decision* is made here even though enforcement lands in Phase 6.
**Delivers:** `skills/store.py` (load + path-scoped `read_path` with traversal guard); `skills/provider.py` (async `SkillToolProvider`); reserved-name registration; `RuntimeAPI.load_skill()` as the single shared load path; system-role body injection via tagged `add_skill_message()`; short confirmation as the tool result (body is *not* duplicated in the tool result — Anti-Pattern 1); `SkillLoadedEvent` through the event pipeline; the cancel-mid-gather alternation fix.
**Addresses:** D-08, D-09, D-10 (activation + Level-3), D-12 (injection).
**Avoids:** P-02 (reserved name, distinct schema), P-03 (correct role + metadata tag; verify real backend, design fallback), P-06 (traversal test suite incl. win32 vectors — same wave as the tool), P-10 (cancel hole closed + tested).

### Phase 4: Session behavior & /skill command (SKL-04/SKL-05)
**Rationale:** Loaded-skill state now exists (Phase 2/3); this phase makes it *accounted* and *user-invocable*. The `/skill` RPC is the first cross-boundary feature, so the four-layer RPC contract checklist ships here.
**Delivers:** `skills.load` RPC method across **all four layers** in one change (`protocol.py` RPC_METHODS, `adapter.py` handler + `register_all`, `rpc-client.ts`, `types.ts`); REPL parity in `main.py` (`/skill` branch in `_handle_session_cmd`); separate `loaded_skill_tokens` accounting so the summarization threshold is chat-relative (P-11); a loaded-skill token cap (P-09); combined-filter semantics *decided and documented* (P-05); non-blocking `/skill` handler vs the streaming turn.
**Addresses:** D-11 (slash command), D-16 design decisions, P-09/P-11 (accounting).
**Avoids:** P-04 (single RPC source of truth; `/skill` never falls through to `submitPrompt`; distinguishable skill-not-found error), P-05 (semantics + state coherence decided before enforcement ships), P-03 (provider-compat E2E against the real `base_url`).

### Phase 5: TUI integration (D-14)
**Rationale:** Every backend path is proven by Phase 4; the TUI work is presentation over proven events. The typed event (not inference) drives the indicator.
**Delivers:** `NotificationType.skill_loaded` across all five touchpoints (harness event → server mapping + extractor → protocol → `handleEvent` case → store); InputBar `/skill ` intercept (mirroring `/session`/`/new`, never forwarded as a chat prompt); "Skill loaded: <name>" notice via the existing `addNotice` pattern; optional footer chip (D-14 discretion); optional P2 `/skills` listing command.
**Addresses:** D-14 (indicator transparency), D-11 (TUI half of the command).
**Avoids:** P-10 (no token/tool_result smuggling — a fake tool card or streamed text chunk polluting the assistant message), P-04 (round-trip test: keystroke → JSON-RPC → load → notification → indicator).

### Phase 6: allowed-tools enforcement & hardening (D-16)
**Rationale:** Enforcement is a thin, well-understood layer once the filter semantics (Phase 4) and load state (Phases 2-3) exist. Keeping it last lets every other path prove itself unfiltered first, and gives the guardrails a dedicated hardening pass.
**Delivers:** `skills/filter.py` pure per-iteration projection applied at `agent/core.py:108`; **`read_skill` always retained (`allowed ∪ {"read_skill"}`)**; dispatch-side rejection in `registry.call_tool`; `switch_session()`/`/new` reset semantics; full E2E verification script (author a skill, confirm manifest, `/skill` force-load, system-role injection, JSONL untouched, filter active, indicator).
**Addresses:** D-16 (tool filtering).
**Avoids:** P-05 (mutation leakage, `call_tool` bypass, undefined combined semantics), the read_skill-never-filtered deadlock trap, P-06 remaining vectors in the E2E.

### Phase Ordering Rationale

- **Dependency-driven:** pure domain (Phase 1) → session serialization (Phase 2, needed by every body-injection path) → store+tool (Phase 3) → state semantics + RPC (Phase 4) → presentation (Phase 5) → enforcement (Phase 6).
- **Risk-first placement:** the `persist`/`mark_saved()` pairing is the riskiest change and sits at Phase 2, not last, so JSONL exclusion is proven before any real body exists (ARCHITECTURE.md ordering rationale).
- **Design-before-implementation for D-16:** P-05 requires the pure-filter design decision *before* the activation phase ships (the load/unload state object is shared) — Phase 4 locks semantics, Phase 6 implements.
- **Both activation paths share one loader from day one** (Pattern 3) so model-driven and user-driven loads cannot drift (FEATURES.md dependency note).
- **No new machinery anywhere:** this ordering never requires a file watcher, a DB, or a schema validator — every phase reuses an existing seam.

### Research Flags

Phases likely needing research during planning:
- **Phase 3:** provider tolerance of mid-conversation system messages — verify against the *actual configured* backend (local proxy default at `localhost:20128`; ARCHITECTURE marks this LOW confidence). Also confirm the endpoint accepts multiple system messages (the injected body lands after user/assistant messages).
- **Phase 4:** combined `allowed-tools` semantics across multiple loaded skills (union/intersection/error) — the milestone defers full composition but the agent can load two skills in one turn; a decision is required, not more research (P-05).

Phases with standard patterns (skip research-phase — well-documented ecosystem + verified seams):
- **Phase 1:** agentskills.io standard + Claude Code docs fully cover frontmatter/manifest shape; codebase seams verified in source.
- **Phase 2:** purely internal serialization mechanics, fully specified by ARCHITECTURE.md + PITFALLS.md.
- **Phase 5:** existing Phase-9 JSON-RPC/event pipeline pattern in-repo is the template; no external research needed.
- **Phase 6:** filter + traversal guard are well-understood patterns; test-vector design is the only work.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | PyPI-verified PyYAML 6.0.3; integration points read directly from source; one flagged disagreement (ARCHITECTURE.md hand-rolled vs majority PyYAML) resolved to PyYAML + delimiter splitter |
| Features | HIGH | agentskills.io spec + Claude Code official docs + Anthropic engineering blog + cross-agent comparison matrix; all mapped to D-01..D-16 |
| Architecture | HIGH | Every seam (models.py, context.py:88, core.py:108, registry.py, RPC, TUI) verified in source; LOW sub-flag on multi-system-message provider tolerance |
| Pitfalls | HIGH | Codebase integration facts verified in source; MEDIUM sub-flag on provider-dependent behavior and external ecosystem claims |

**Overall confidence:** HIGH

### Gaps to Address

- **PyYAML vs hand-rolled parser (open):** 3 of 4 files recommend PyYAML; ARCHITECTURE.md argues for zero-dep hand-rolled. Roadmapper should lock PyYAML 6.0.3 + STACK.md's delimiter-splitter pattern (the safe middle ground). Do NOT adopt a full hand-rolled YAML parser (P-07).
- **Manifest budget unit (open):** STACK.md proposes `SKILL_MANIFEST_MAX_TOKENS = 800` (token-based); P-01 + FEATURES explicitly recommend *characters* (~1,500, Claude Code precedent) because tiktoken counting is model-dependent. Recommend char-based; exact constant is OpenCode discretion (D-07).
- **Unload path (open):** D-13 has no unload (only `/new`); P-09 recommends a minimal `/skill --unload` or unload affordance so "persists for session" doesn't become a liability in long sessions. Decide scope in the roadmap.
- **Combined allowed-tools semantics (open):** undefined across multiple loaded skills; ARCHITECTURE's v1.1 default is "any loaded skill without allowed-tools ⇒ no filtering" (simple, safe); intersection is the safest enforcement semantics. Decide and document in Phase 4.
- **Multi-system-message provider tolerance (LOW confidence):** must be verified against the real backend in Phase 3, with the append-to-system-block fallback pre-designed (P-03).
- **Manifest rebuild timing / frontmatter caching (deferred, OpenCode discretion):** P-07 warns against per-call rescanning — Phase 1 should include mtime-invalidated caching even though "rebuild timing" is a deferred idea.
- **Pre-existing cancel-hole (dangling tool_calls mid-gather, P-10 #3):** pre-dates this milestone but skills make it likelier; fold the fix into Phase 3 with a test.

## Sources

### Primary (HIGH confidence)
- [PyPI: PyYAML 6.0.3](https://pypi.org/project/PyYAML/6.0.3/) — version, cp312 wheels, requires-python (STACK).
- [Agentskills.io open standard (specification + client-implementation guide)](https://agentskills.io/specification) — three-tier disclosure, name/description requirements, dedicated-tool activation, `allowed-tools` experimental status (FEATURES).
- [Claude Code official docs — Extend Claude with skills](https://code.claude.com/docs/en/skills) — 1,536-char listing cap, session persistence of loaded content, `allowed-tools` as per-turn grant, compaction re-attach (FEATURES/PITFALLS).
- [Anthropic engineering blog — "Equipping agents for the real world with Agent Skills" (2025-10-16)](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) — progressive-disclosure design rationale (FEATURES/PITFALLS).
- [Anthropic platform docs — Agent Skills overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) — three-level disclosure, security guidance (FEATURES).
- **AgentHarness codebase (read in full):** `agent/core.py`, `tool/registry.py`, `tool/local_provider.py`, `tool/models.py`, `context/context.py`, `context/message.py`, `session/models.py`, `session/store.py`, `harness/runtime.py`, `harness/scheduler.py`, `harness/events.py`, `backend/rpc/{protocol,server,dispatcher,adapter}.py`, `main.py`, `config.py`, `requirements.txt`, `tui-ink/src/*`, `tests/test_rpc_adapter.py` (ARCHITECTURE/PITFALLS).
- `.planning/MILESTONE-CONTEXT.md` — decisions D-01..D-16 (authoritative for all locked decisions).

### Secondary (MEDIUM confidence)
- [Microsoft Agent Framework skills docs (2026-07)](https://learn.microsoft.com/en-us/agent-framework/agents/skills) — `load_skill`/`read_skill_resource` naming, `allowed-tools` experimental, SKILL.md <500 lines guidance — corroborates tool-name distinctness and manifest-in-system-prompt failure modes (FEATURES/PITFALLS).
- [Codex CLI implementation deep-dive (zenn, 2026-01)](https://zenn.dev/takiko/articles/codex-cli-agent-skills-implementation) — `render_skills_section` manifest shape, per-turn injection (FEATURES).
- [Cross-agent portability analyses (MCP.Directory 2026-05, Codex KB 2026-05)](https://mcp.directory/blog/cross-agent-skills-cursor-codex-cline-antigravity-gemini-mastra-portability) — adoption matrix, `.agents/` path stabilization (FEATURES).
- [python-frontmatter 1.3.0 docs](https://python-frontmatter.readthedocs.io/) — `frontmatter.parse()` behavior, YAMLHandler safe-mode default (STACK).
- [Context7: /yaml/pyyaml, /pycontribs/ruamel-yaml](https://github.com/yaml/pyyaml) — `safe_load` API; ruamel deprecated top-level load (STACK).

### Tertiary (LOW confidence)
- **Multi-system-message tolerance of the configured OpenAI-compatible endpoint** (local proxy default at `localhost:20128`) — needs a live verification in Phase 3; design the system-block fallback regardless (ARCHITECTURE/PITFALLS P-03).
- **Exact Claude Code manifest budget constant** — OpenCode discretion per D-07; ~1,500 chars is the documented precedent.

---
*Research completed: 2026-08-01*
*Ready for roadmap: yes*
