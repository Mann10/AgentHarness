---
phase: 15
slug: session-behavior-skill-command
status: complete
created: 2026-08-02
---

# Phase 15 — Session Behavior & /skill Command: Research

**Question:** What do I need to know to PLAN this phase well?

**Answer in one line:** The `/skill` command, the `skills.load` RPC, and loaded-skill token accounting all plug into four existing, well-tested seams (`_handle_session_cmd`, `RuntimeAPI.load_skill`, the RPC dispatcher pipeline, and `skill_state`) — the phase is additive, not architectural.

---

## 1. The 4-Layer RPC Contract (D-05/D-06/D-08)

The full seam exists and is exercised by `sessions.*` methods. Adding `skills.load` mirrors it exactly:

| Layer | File | What to add |
|-------|------|-------------|
| 1. Protocol | `backend/rpc/protocol.py` | `"skills.load"` in `RPC_METHODS` (line 83-92) + a domain error code constant for skill-not-found |
| 2. Adapter | `backend/rpc/adapter.py` | `handle_skills_load(self, params)` + `dispatcher.register("skills.load", ...)` in `register_all()` |
| 3. TS client | `tui-ink/src/bridge/rpc-client.ts` | `async loadSkill(name: string): Promise<SkillLoadResult>` via existing `request()` |
| 4. TS types | `tui-ink/src/types.ts` | `SkillLoadResult { skill: string; status: "loaded" \| "already_loaded" \| "not_found" }` |

### Critical research finding: structured error codes need a Dispatcher change

`Dispatcher.dispatch()` (dispatcher.py:72-79) catches **all** exceptions and wraps them as `INTERNAL_ERROR` (-32603). Domain error codes (-32602 INVALID_PARAMS, -32001 skill-not-found per D-08) **cannot** flow through today — the RPCError would be swallowed into -32603.

**Design decision:** add an `except RPCError` clause in `Dispatcher.dispatch()` **before** the generic `except Exception` that returns the RPCError's own code/message verbatim. This is additive (existing handlers never raise RPCError, so behavior is unchanged) and enables the D-08 contract. Then `handle_skills_load` raises `RPCError(code=INVALID_PARAMS, ...)` / `RPCError(code=SKILL_NOT_FOUND, ...)`.

### Adapter handler design (no string parsing, no drift)

`RuntimeAPI.load_skill()` returns a human ack string; the RPC needs `{skill, status}`. Do NOT string-parse the ack. Design:

```python
async def handle_skills_load(self, params: dict | None) -> dict:
    if params is None or "name" not in params or not isinstance(params["name"], str) or not params["name"].strip():
        raise RPCError(code=INVALID_PARAMS, message="Missing 'name' in params")     # D-08
    name = params["name"].strip()
    try:
        info = self._runtime.skill_store_lookup(name)   # NEW thin runtime method → SkillInfo | None
    except KeyError:
        raise RPCError(code=SKILL_NOT_FOUND, message=f"Skill '{name}' not found.")  # D-08
    loaded = self._runtime.active_session.skill_state.get("loaded", [])
    if any(e["name"] == info.name for e in loaded):                                  # canonical dedup (H-01)
        return {"skill": info.name, "status": "already_loaded"}                      # D-06
    await self._runtime.load_skill(info.name)                                        # SAME shared path (D-07)
    return {"skill": info.name, "status": "loaded"}
```

- `status` reflects pre-call membership in `skill_state["loaded"]` — deterministic, no ack-string parsing.
- The actual load still goes through `RuntimeAPI.load_skill` — activation cannot drift (D-07).
- `info.name` is the canonical frontmatter name (win32 case-insensitive via `SkillStore._key()`), consistent with the H-01 dedup fix.
- Small TOCTOU note: a concurrent load between the membership check and `load_skill()` is closed by load_skill's own mark-before-inject dedup (H-03) — worst case a cosmetic status race, no double-injection.

### Domain error code constant

Add to `protocol.py` next to the standard codes:
```python
# Domain error codes (D-08)
SKILL_NOT_FOUND = -32001
```
Export via `backend/rpc/__init__.py` alongside the existing protocol exports.

---

## 2. REPL `/skill` Command (D-01/D-02/D-03/D-04/D-07)

Seam: `main.py _handle_session_cmd()` (lines 57-121) — async, returns `True` to signal "handled, don't fall through to chat". Add a `/skill` branch:

```python
if cmd == "/skill":
    name = (parts[1] if len(parts) > 1 else "").strip()
    if not name:
        print("Usage: /skill <name>")                  # D-02 no-arg → usage
        return True
    try:
        ack = await runtime.load_skill(name)           # D-07: REPL calls load_skill directly
        print(ack)                                     # D-01: short ack, body already in context
    except KeyError:
        print(f"Skill '{name}' not found.")            # D-02 distinct error
    return True
```

- `load_skill` returns `"Loaded skill {canonical}"` (D-05 ack) or `"Skill '{canonical}' already loaded"` (D-07 no-op ack) — both print as-is (D-01).
- `KeyError` from `SkillStore.lookup()` is the not-found signal (`KeyError(f"Unknown skill '{name}'")`).
- `_handle_session_cmd` already runs in the async REPL loop (`run_repl` line 164) — `await runtime.load_skill(...)` is fine.
- Returns `True` in every branch → never falls through to a chat prompt (ROADMAP criterion 2).
- Case-insensitive matching is handled inside `SkillStore.lookup()` (`_key()` on win32, D-04) — no work needed in main.py.

---

## 3. Loaded-Skill Token Accounting + Cap (D-09..D-12)

### Where tokens are counted

- `llm/base.py` `count_tokens(text)` — tiktoken per `self.config.model`, falls back to `len(text.split())`. Already injected into `Session.create()`/`restore_context()` as `count_tokens=client.count_tokens`.
- `RuntimeAPI` holds `self._client` (line 54) — `self._client.count_tokens(body)` is available at load time.
- Skill bodies are already `Message` objects with `token_count` set (via `context.add_message` → `context.py:30-31`), but that count is **not** cached per-skill and not separately tracked.

### D-09 design: cache per-skill token counts in `skill_state["loaded"]`

Extend the record shape (currently `{"name", "dir"}`) to `{"name": info.name, "dir": str(info.path), "tokens": <int>}`. `skill_state` is non-serialized (Phase 13 pattern) — no JSONL impact. Existing tests assert only `name`/`dir` presence (`test_load_skill.py:128-129`) → additive change, backward compatible.

### D-10/D-12 design: env-var cap, mirroring the Phase 12 manifest pattern

`skills/manifest.py` `manifest_max_chars()` (lines 16-26) is the template: module-level function reading an env var with default + non-numeric fallback. Create the token-cap equivalent:

- New module function (suggest `skills/limits.py` or add to `manifest.py`): `loaded_skill_token_cap(env=None) -> int` reading env var **`LOADED_SKILL_TOKEN_CAP`**, default **8000** (D-12), fallback to default on non-positive/non-numeric.

### D-11 design: refuse on breach, no partial state

In `load_skill()`, after `body = self._skill_store.load(name)` and BEFORE the `loaded.append(...)` mark (mark-before-inject, H-03):

```python
body_tokens = self._client.count_tokens(body)
new_total = sum(e.get("tokens", 0) for e in loaded) + body_tokens
cap = loaded_skill_token_cap()
if new_total > cap:
    raise RuntimeError(
        f"Skill '{info.name}' not loaded — loaded-skill token cap ({cap}) would be exceeded"
    )
loaded.append({"name": info.name, "dir": str(info.path), "tokens": body_tokens})
```

- Check happens **before** the record append → no partial state (D-11).
- The error names the cap (D-11).
- No auto-eviction, no silent drop (D-11 — eviction explicitly rejected in 15-CONTEXT deferred).

### "Chat tokens stay separate" (ROADMAP criterion 3)

- Skill bodies are system-role, `persist=False`, and **exempt from summarization content** (`context.py:91-95` — only non-system messages are summarized). The body itself never triggers chat-token growth.
- `ConversationContext.total_tokens` (summarization trigger) already includes skill-body tokens via `add_message`, but the **cap bounds this contribution** (~8k default) — summarization stays effectively chat-relative with a bounded skill-body floor. No summarization code change required this phase.

---

## 4. CAP-04 Combined-Filter Semantics (D-13/D-14) — locked now, enforced Phase 17

Follow the established **contract-before-enforcement** pattern from Phase 14's `skills/filter.py`:
- `retain_read_skills()` (CAP-03 retention contract) was shipped + unit-tested in Phase 14 with enforcement deferred to Phase 17 (filter.py docstring + tests/test_skills_provider.py:127-143).
- Phase 15 ships the same kind of artifact for CAP-04: a pure function implementing the D-13 intersection + D-14 no-restriction rule, unit-tested, with enforcement wiring deferred to Phase 17.

**Contract (from 15-CONTEXT D-13/D-14):**
- A tool is retained only if it appears in **every** loaded skill's `allowed-tools` (intersection over the restricted skills).
- A loaded skill with **no** `allowed-tools` field imposes no restriction (treated as allowing everything; excluded from the intersection computation).
- `read_skill` / `read_skill_path` always retained (CAP-03 — already covered by `retain_read_skills`).

Suggested surface (new pure function in `skills/filter.py`):
```python
def intersect_allowed_tools(allowed_sets: list[set[str]]) -> set[str]:
    """D-13/D-14: intersection over restricted skills only (empty set = unrestricted, skipped)."""
    restricted = [s for s in allowed_sets if s]
    return set.intersection(*restricted) if restricted else set()
```
Plus a doc/contract file (`docs/skills-allowed-tools.md` or a decision record) that Phase 17's planner reads. The docs record must name D-13, D-14, and CAP-03.

---

## 5. Validation Architecture

### Test infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest 7.x + `pytest-asyncio` (`asyncio_mode = auto` in pytest.ini) |
| Config file | `pytest.ini` (testpaths = tests) |
| Quick run | `python -m pytest tests/test_skills_load_rpc.py tests/test_load_skill.py tests/test_skill_command.py -q` |
| Full suite | `python -m pytest -q` |
| Estimated runtime | ~15-30s |

### Established fixtures/patterns to reuse

- **RuntimeAPI with stub LLM + real SkillStore** — `tests/test_load_skill.py:16-64`: `tmp_path` skills root with a `demo-greeter` SKILL.md (frontmatter-name authority), `client.count_tokens = len` stub, `JSONLSessionStore(tempfile.mkdtemp())`, `backlog_maxsize=5`. Real `.agentharness/skills/demo-greeter` also exists with `allowed-tools: [echo]`.
- **RPC adapter unit tests** — `tests/test_rpc_adapter.py`: MagicMock runtime + AsyncMock handlers; `register_all(dispatcher)` registration assertions.
- **REPL command tests** — no existing test for `_handle_session_cmd`; add `tests/test_skill_command.py` calling `main._handle_session_cmd(line, current, runtime, config, client)` with a MagicMock runtime, asserting `return True` + captured stdout (capsys) per branch (success / unknown / no-arg).
- **Dispatcher error-code test** — extend `tests/test_rpc_adapter.py` (or new `tests/test_dispatcher.py`) asserting `dispatch()` returns the RPCError's own code for a handler that raises `RPCError`, and still wraps unknown exceptions as -32603.

### Per-file verification map (draft — finalized in VALIDATION.md)

| File | Tests |
|------|-------|
| `backend/rpc/protocol.py` | `"skills.load"` in RPC_METHODS; `SKILL_NOT_FOUND == -32001` |
| `backend/rpc/dispatcher.py` | RPCError passthrough test |
| `backend/rpc/adapter.py` | handle_skills_load: missing name → -32602; unknown → -32001; loaded / already_loaded statuses; registered |
| `harness/runtime.py` | load_skill token caching + cap refusal (no partial state) + cap env override |
| `main.py` | `/skill` branches: success ack / not-found / usage; never falls through |
| `skills/filter.py` | `intersect_allowed_tools`: intersection, empty-set skip, single restriction |
| `tui-ink/src/types.ts`, `rpc-client.ts` | TS compile (`npm run build` or `tsc --noEmit` in tui-ink) |

### Manual-only verifications

- REPL end-to-end: `python main.py` → `/skill demo-greeter` (twice) → `/skill nosuch` → `/skill` — captured in plan checkpoint.

---

## 6. Key Constraints & Pitfalls (from research)

1. **Do NOT change `RuntimeAPI.load_skill`'s return contract** (str ack) — the read_skill tool provider (`skills/provider.py:51`) and existing tests depend on it. Token accounting must be additive inside the same method.
2. **The cap check must precede the `loaded.append` mark** (H-03 mark-before-inject) or a refused load leaves partial state (violates D-11).
3. **`Dispatcher.dispatch` swallows exception codes** — without the RPCError passthrough clause, D-08 structured codes are impossible.
4. **win32 case-insensitivity** — never compare raw user names for dedup; always use canonical `info.name` from `SkillStore.lookup()` (H-01).
5. **`skill_state` is non-serialized** — new `tokens` field never touches JSONL; do NOT add it to `to_snapshot_meta()`.
6. **REPL must return `True`** from `_handle_session_cmd` for every `/skill` branch — a missed return falls through to a chat prompt (ROADMAP criterion 2).
7. **TS side is contract-only this phase** — the TUI indicator / input-bar intercept / `skill_loaded` notification are Phase 16 (15-CONTEXT deferred). Only types + client wrapper now.
8. **`allowed-tools: ()` (empty tuple) means "no restriction"** (skills/models.py D-15/D-16) — this is the D-14 "imposes no restriction" signal; do not confuse with "allow nothing".

## 7. Artifact Summary (what planning must produce)

- `15-RESEARCH.md` (this file)
- `15-VALIDATION.md` (Nyquist contract)
- PLAN.md files covering: RPC 4-layer (`skills.load`), REPL `/skill`, token accounting + cap, CAP-04 semantics contract
