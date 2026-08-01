---
phase: 14-read-skill-provider-e2e
created: 2026-08-01
status: complete
tags: [skills, read_skill, provider, traversal, cancel, e2e]
---

# Phase 14: read_skill Provider End-to-End — Research

## Objective

What does the executor need to know to PLAN and IMPLEMENT the backend read path for skills:
`SkillStore` (index + load + traversal-guarded path reads), the `__skills__` tool provider
(`read_skill` + `read_skill_path`), the single shared `RuntimeAPI.load_skill()` load path with
system-role body injection, and the cancel-mid-gather cleanup — Level-2/Level-3 progressive
disclosure, backend-only (TUI indicator is Phase 16, `/skill` command is Phase 15).

## Phase Requirements (MUST address)

| ID | Requirement | Delivered by |
|----|-------------|--------------|
| DISC-03 | Agent loads a skill body on demand via a dedicated `read_skill` tool | provider surface + load path |
| DISC-04 | `read_skill` reads are path-scoped — no traversal outside the skills directory | `SkillStore.read_path` traversal guard |
| DISC-05 | Bundled resources (`references/`, `scripts/`, `assets/`) readable on demand via path-scoped reads | `SkillStore.read_path` |
| ACT-02 | Agent auto-invokes skills when a manifest description matches | model-driven (D-13), dedup (D-07), load path |
| CAP-01 | Skill bodies are markdown that reference bundled files relative to the skill dir | `SkillStore.read_path` relative resolution |
| CAP-03 | `read_skill` always retained in the tool list even when `allowed-tools` filtering is active | `skills/filter.py` retention contract (unit-tested here; enforcement is Phase 17) |

## Key Finding 1 — D-01 supersedes the ARCHITECTURE sketch

The milestone ARCHITECTURE.md Pattern 1 shows a **single** tool `read_skill(name[, path])`.
The locked decision **D-01 overrides this: TWO tools** — `read_skill(name=...)` loads a body,
`read_skill_path(skill=..., path=...)` reads a bundled resource. D-02: both are reserved,
un-namespaced names registered by an async provider named `__skills__`. The LLM sees exactly
`read_skill` / `read_skill_path`. **Plans MUST implement two tools, not one.**

## Key Finding 2 — Provider must be async; LocalToolProvider cannot be reused

- `ToolProvider` protocol (`tool/models.py:7`, `@runtime_checkable`) requires
  `start()`, `shutdown()`, `fetch_tools()`, `call_tool()` — all async.
- `LocalToolProvider` handlers are **sync** `Callable[[dict], str]` (`tool/local_provider.py:15`)
  — skill loading must `await` context injection → **SkillToolProvider is a new async class**
  modeled on `MCPToolProvider` (`tool/mcp_provider.py`): async `fetch_tools()` returns `list[Tool]`,
  async `call_tool(name, arguments)` returns `ToolResult`.
- Registration: `ToolRegistry.add_provider("__skills__", provider, namespace=None)`
  (`tool/registry.py:34-38`) — `namespace=None` keeps the un-prefixed names.
- **Interface-first:** the provider receives injected `load_handler(name)` / `read_path_handler(name, path)`
  async callables (Pattern 3 — load-once-shared-handler). RuntimeAPI provides them (Plan 14-03).
  The provider itself never touches Session/context directly.

## Key Finding 3 — Registry collision handling (D-03) needs an explicit surface

- `_register_tools` (`tool/registry.py:123-142`) **already raises `ValueError`** on a tool-name
  collision (L133-140), with a clear message.
- **GOTCHA:** `ToolRegistry.start()` (`L40-55`) wraps each provider's registration in
  `try/except Exception` and **swallows it, logging only** (L54-55). A collision would therefore be
  silently logged and the `__skills__` tools never registered.
- D-03 requires the collision to be **rejected with a clear error**. Implementation options:
  extend `_register_tools` with a `RESERVED_SKILL_TOOLS = {"read_skill", "read_skill_path"}`
  guard that produces the D-03 error text, and/or have the wiring site (main.py, Plan 14-03)
  assert `read_skill in registry.list_tools()` after `start()` and raise otherwise. Both paths
  must be unit-tested: a provider holding `read_skill` + the `__skills__` provider → clear error.

## Key Finding 4 — Traversal guard (D-10/D-11/D-12) — win32 is the platform

Project floor is Python 3.12 → `Path.is_relative_to` is available.

Guard algorithm (from milestone PITFALLS P-06):
```python
base = skill_dir.resolve()            # canonicalizes, resolves symlinks/junctions
p = (skill_dir / rel_path).resolve()  # canonicalize AFTER join — defeats ../ and symlink escapes
if not p.is_relative_to(base):
    raise ValueError(f"Path '{rel_path}' escapes skill '{name}'")
```
- **D-10:** reads only inside a **loaded** skill's directory; unloaded skills and anything outside are rejected.
- **D-11:** symlinks canonicalized (`resolve()`); a symlink resolving outside the skill dir is rejected.
- **D-12:** rejection returns a **clear error naming the skill and the rejected path** — never a silent empty result.
- **win32 test vectors (MUST ship in the same wave as the tool):** `../`, `..\`, absolute paths
  (`C:\...`, `/...`), drive-relative (`C:foo`), and symlink/junction-to-outside. Both `/` and `\`
  separators. `Path.resolve()` on Windows normalizes drive-letter case and resolves junctions.
- Also reject non-relative (absolute) inputs BEFORE joining (reject `os.path.isabs(rel)` /
  `Path(rel).is_absolute()` and `rel.parts[0]` in `("..",)` style checks — though the resolve
  + is_relative_to check is the authoritative gate).

## Key Finding 5 — Body injection mechanics (D-05/D-06/D-07/D-08)

- **D-08:** new `context/context.py` method `add_skill_message(name, body)`:
  builds `Message(role="system", content=body, persist=False, skill_name=name)` and appends via
  `add_message`. Requires a `skill_name: str | None = None` field on `Message`
  (`context/message.py`) — `from_dict` must default it to None (stored events never carry the key).
- **D-05:** the tool result is a **short ack** (e.g. `Loaded skill <name>`); the body flows ONLY
  as the system-role message — never duplicated in the tool result.
- **D-06:** body appended at the END of conversation messages (after prior user/assistant turns) —
  `add_message` already appends; visible every turn via `to_llm_messages()`.
- **Summarization exemption:** `ConversationContext._maybe_summarize()` (context.py:87-91) already
  excludes `role == "system"` messages — a loaded body survives summarization for the session (ACT-03/ACT-04).
- **D-07 dedup:** re-loading an already-loaded skill is a no-op returning an "already loaded" ack.
  Dedup is deterministic via `session.skill_state["loaded"]` (D-09): a deduped list of loaded names
  + each skill's base dir. Exact dict layout is OpenCode's discretion (list of names+dirs is required).
- **D-09:** `load_skill()` writes `skill_state["loaded"]`. `skill_state` is already a
  non-serialized `Session` field (`session/models.py:47`) — never reaches JSONL.

## Key Finding 6 — Cancel-mid-gather (D-14) — the hole and the fix

Current gather path in `agent/core.py` (`Agent.run`, L148-177):
1. L148: `await self._context.add_assistant_tool_message(content, tool_calls)` — assistant tool_calls message **committed first**
2. L160-164: `tasks = [...]; results = await asyncio.gather(*tasks, return_exceptions=True)` — cancel lands HERE
3. L166-177: tool result messages appended per call

If a cancel lands during step 2, the assistant tool_calls message is already in context but no
`tool` result messages follow → **next turn has dangling `tool_calls` with no matching tool
results** → provider rejects the message sequence (400-style error). Note `except Exception`
(L202) does NOT catch `asyncio.CancelledError` (it is a BaseException) — cleanup must be explicit.

Fix (OpenCode's discretion on exact approach, but MUST leave no partial messages / no dangling
tool_calls): catch `asyncio.CancelledError` around the gather + result-append block, remove the
just-added assistant tool_calls message (and any partial tool messages from this iteration) from
`context._messages`, restore `total_tokens`, then re-raise. Regression test: cancel during a slow
tool call → next `run()` streams cleanly; `to_llm_messages()` has no assistant message with
`tool_calls` lacking following `tool` messages. Scheduler cancel path: `Scheduler.cancel()` →
`_run_turn` task `.cancel()` (harness/scheduler.py:95-110, 147-148).

## Key Finding 7 — Phase 12 delivered the seam, NOT production wiring

`main.py` and `harness/runtime.py` currently contain **zero** skills wiring (verified by grep).
Phase 12-04-SUMMARY explicitly defers: "Phase 14 can wire the production construction sites
(`main.py`/`harness/runtime.py`): build the manifest from `discover_skills()` + `build_manifest_text()`
and set `session.skill_manifest` before agent runs." Since this phase is "End-to-End", wiring is IN SCOPE:
- `RuntimeAPI._create_agent()` (runtime.py:213-235) is the single choke point: attach
  `session.skill_manifest = build_manifest_text(discover_skills(root))` when `None` (once per Session object).
- Skills root: `Path.cwd() / ".agentharness" / "skills"` (matches `session/store.py:35` base_dir pattern).
- `RuntimeAPI` gains `async def load_skill(name) -> str` (the D-09 single shared path) consumed by
  the provider's injected handler.
- `main.py` (L301-303 area): after `registry.add_provider("__builtin__", ...)`, register
  `registry.add_provider("__skills__", skill_provider)`; assert `read_skill` present after `start()`.

## Reusable Assets (verified on disk)

| Asset | Location | Use |
|-------|----------|-----|
| `discover_skills(root)` / `parse_skill_entry()` | `skills/discovery.py` | `SkillStore` index + name lookup (D-04 case-insensitive on win32 via `_dedupe_key`) |
| `SkillInfo(name, description, path, allowed_tools)` | `skills/models.py` | carries `path` = skill dir — the base dir `read_skill_path` needs |
| `build_manifest_text(entries, max_chars)` | `skills/manifest.py` | production manifest wiring |
| `ToolProvider` protocol | `tool/models.py` | async contract for SkillToolProvider |
| `Tool`, `ToolResult` | `tool/models.py` | fetch_tools / call_tool return types |
| `ToolRegistry.add_provider/list_tools/call_tool` | `tool/registry.py` | `__skills__` registration + LLM-facing list |
| `Message.persist` (Phase 13) | `context/message.py` | `persist=False` for skill bodies (exists) |
| `Session.skill_manifest` + seam | `session/models.py` | manifest section in `_build_system_prompt` (exists) |
| `Session.skill_state` non-serialized dict | `session/models.py:47` | `skill_state["loaded"]` (D-09) |
| `_maybe_summarize` system exemption | `context/context.py:87-91` | body survives summarization (exists) |
| `JSONLSessionStore` persist filter | `session/models.py:84-85` `to_events()` | `persist=False` bodies never reach JSONL (exists) |

## Existing Test Patterns

- pytest 8.x + `pytest-asyncio`, `asyncio_mode = auto`, `testpaths = tests` (pytest.ini)
- Fixtures: `tempfile.mkdtemp()` for store dirs; `tmp_path` for skill dirs
- New files: `tests/test_skills_store.py`, `tests/test_skills_provider.py`, `tests/test_load_skill.py`,
  `tests/test_cancel_mid_gather.py` (each plan owns its own — no shared file across plans in Wave 1)
- Traversal tests create real files: `.agentharness`-style tmp skill dirs with `SKILL.md`, `references/*.md`
- E2E pattern (D-15, from test_persist.py + test_skills_integration.py): create Session →
  `add_skill_message` → `to_llm_messages` shows body → `store.save` → assert JSONL untouched →
  `store.load` + `restore_context` → body absent from restored events

## Validation Architecture

- **Framework:** pytest 8.x + pytest-asyncio (auto mode) — no new dependencies (stdlib pathlib/dataclasses only)
- **Config file:** `pytest.ini` (existing: `asyncio_mode = auto`, `testpaths = tests`)
- **Quick run command:** `python -m pytest tests/test_skills_store.py tests/test_skills_provider.py tests/test_load_skill.py tests/test_cancel_mid_gather.py -x` (per-plan: `python -m pytest tests/test_<plan file>.py -x`)
- **Full suite command:** `python -m pytest -q` (currently 103 tests; phase target ≈ 103 + 25-35 new)
- **Estimated runtime:** ~30-60s
- **Wave sampling:** after every task commit → the plan's own test file; after every wave → full suite
- **Key automated gates:**
  - Traversal suite: `../`, `..\`, absolute, `C:`, symlink/junction-outside → all raise `ValueError` naming skill + path
  - D-03: registering a provider that collides with `read_skill` → clear `ValueError`
  - CAP-03: `filter_tools(allowed, available)` retains `read_skill`/`read_skill_path` unconditionally
  - D-07: second `load_skill(same)` → no duplicate system message, "already loaded" ack
  - D-14: cancel mid-gather → `to_llm_messages()` valid alternation on next turn
  - D-15: `persist=False` body never in JSONL; survives restore; survives summarization
- **Manual-only verifications:** none — all phase behaviors have automated verification (D-15)

## Threat Model Notes (security_enforcement: enabled, ASVS L1, block on high)

Trust boundaries in scope:
1. **LLM → tool input** (`read_skill`/`read_skill_path` arguments are model-generated, hence untrusted)
2. **Skill directory → context** (skill bodies are project-local but user-editable — prompt-injection surface)
3. **Session memory → JSONL** (persist=False must hold; already guarded by Phase 13)

STRIDE register per plan:
- **T-14-01 (Spoofing/Tampering)** — tool-name collision on reserved `read_skill`/`read_skill_path` (D-03) → mitigate: reserved-name guard in `_register_tools` + wiring assert
- **T-14-02 (Information Disclosure, HIGH)** — path traversal via `read_skill_path` (D-10/11/12) → mitigate: `resolve()` + `is_relative_to` containment; win32 vectors; clear error naming skill + path
- **T-14-03 (Spoofing)** — `read_skill(name)` shadowing an unloaded skill or a skill whose folder differs from frontmatter name (D-04) → mitigate: discovery-index lookup, frontmatter-name authority, win32 case-insensitive match
- **T-14-04 (Integrity)** — dangling `tool_calls` after cancel mid-gather (D-14) → mitigate: explicit CancelledError cleanup + regression test
- **T-14-05 (Information Disclosure)** — skill body duplicated in tool result → mitigate: short ack only (D-05)
- **T-14-06 (Tampering)** — symlink/junction inside skill dir escaping to filesystem (D-11) → mitigate: canonicalize + containment, tested with real junction on win32 where possible

## Risks & Mitigations

1. **win32-specific behaviors** — `Path.resolve()` semantics, junction points, case-insensitivity.
   Mitigation: unit tests encode both `/` and `\` vectors; don't assume posix behavior.
2. **Registry `start()` swallowing collisions** — D-03 silent failure if only relying on existing code.
   Mitigation: explicit reserved-name guard + wiring assert (Key Finding 3).
3. **Provider-caller drift** — two tools + injected handlers. Mitigation: interface-first contracts
   defined in Plan 14-02, implemented in 14-03 (single `load_skill` path, Pattern 3).
4. **Cancel cleanup regressing normal flow** — mitigation: cleanup only on `CancelledError`, keep
   `return_exceptions=True` gather behavior; regression test covers normal path unaffected.
5. **Context budget** — traversal suite is broad but each vector is a small parametrized test.

## Out of Scope (deferred — do NOT plan)

- TUI "Skill loaded" indicator (Phase 16), `/skill` command + RPC (Phase 15),
  allowed-tools enforcement + intersection semantics (Phase 17 — only the retention *contract* unit test here),
  script-as-tool registration (D-15), user-global skills dir (D-01), skill chaining (future milestone)
