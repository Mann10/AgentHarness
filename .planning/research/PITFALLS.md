# Pitfalls Research

**Domain:** Adding a progressive-disclosure Skills System to an existing agent harness (AgentHarness v1.1 — SKILL.md discovery → activation → execution pipeline)
**Researched:** 2026-08-01
**Confidence:** HIGH (codebase integration facts verified against source); MEDIUM (provider-dependent behavior flagged inline)

## Critical Pitfalls

### P-01: Manifest token-budget overflow (too many skills, over-long descriptions)

**What goes wrong:**
The skill manifest is injected into the system prompt on *every* LLM call (`session/models.py:_build_system_prompt` → `to_llm_messages`). When a project accumulates 50+ skills, or authors write 2,000-character descriptions "just in case," the manifest silently eats the context window and the ~1,500-char budget (D-07) becomes meaningless. The agent gets a wall of noise, stops reading descriptions (lost-in-the-middle), and the "cheap discovery" premise of progressive disclosure collapses — the exact anti-pattern the Anthropic design rationale warns about. On a 4K-token model (the v1.0 default, `config.max_tokens`), a bloated manifest plus AGENTS.md plus base prompt can starve the conversation.

**Why it happens:**
There is no existing mechanism to measure or cap the system prompt — `_build_system_prompt` appends parts blindly (base prompt, AGENTS.md, CWD), and nothing counts their tokens. The budget is a *decision* (D-07) with no enforcement hook. `count_tokens` (`llm/base.py:49`) is tiktoken-based and **model-dependent** — the same manifest measures differently if `config.model` changes, so a token-counted cap is unstable across model switches. Authors are rewarded for verbose descriptions (they fear the skill won't be triggered), so descriptions balloon unless the harness pushes back.

**How to avoid:**
- Enforce the cap in **characters**, not tokens (Claude Code uses ~1,500 chars — a stable, model-independent unit). Measure the *entire assembled system prompt* (base + AGENTS.md + manifest), not just the manifest, and keep the manifest a fixed fraction.
- Implement a deterministic truncation rule: sort skills by name, keep the longest-lived prefix that fits; log which skills were trimmed so authors notice (`[skills] manifest cap hit — dropped: foo, bar`).
- Optionally surface manifest size in the TUI footer/panel so the cost is visible.
- Put the budget constant + assembly in one function with a unit test that asserts "manifest assembly never exceeds X chars for Y skills."

**Warning signs:**
- System prompt grows linearly with `skills/` dir contents; `logger.info("LLM call #%d with %d tool(s)")` in `agent/core.py` shows context bloat indirectly.
- Agent frequently fails to invoke a skill that *is* in the manifest — classic lost-in-the-middle symptom.
- A `[skills]` warning absent from logs after adding skill #N — means no budget enforcement exists.
- Token counts per turn creeping up with no conversation growth.

**Phase to address:** Skill discovery & manifest phase (SKL-02). The cap, truncation rule, and measurement test must ship with manifest assembly, not later — retrofitting a cap after skills exist is politically hard (which skills get cut?).

---

### P-02: `read_skill` tool confusion vs regular tools

**What goes wrong:**
Three distinct confusions, all plausible in this codebase:
1. **Name collision with a real tool/provider** — `read_skill` registers via the local provider (`tool/registry.py:add_provider` + `LocalToolProvider.add_tool`). `_register_tools` **raises `ValueError`** on name collision (`registry.py:133-141`). If an MCP server exposes a tool named `read_skill` (or a namespace produces `read_skill`), the whole registry breaks — not the skill system, the *entire harness*.
2. **Agent confusion** — `read_skill` sits next to `read_file`/`list_dir` (built-ins, `local_provider.py`). The LLM will conflate them: `read_file(path="skills/graphify/SKILL.md")` instead of `read_skill(name="graphify")`. This defeats the session-scoped load bookkeeping (the harness never learns the skill is loaded → no "Skill loaded" state, no `allowed-tools` filtering, no indicator) and also silently bypasses the path sandbox (P-06).
3. **Tool-loop self-exclusion** — `Agent.run` calls `registry.list_tools()` per iteration (`agent/core.py:108`). If `allowed-tools` filtering (P-05) is applied naively, a skill whose `allowed-tools` list doesn't include `read_skill` removes the *only* way to load further skills — deadlock.

**Why it happens:**
The registry is flat-name with namespace prefixes; a new local tool is indistinguishable from MCP tools at the LLM layer. There is no notion of "reserved tool names." And the milestone (D-15) explicitly defers script-as-tool registration, so nobody thinks about the tool name space being shared until a collision bites.

**How to avoid:**
- **Reserve the name:** hard-block any provider/skill from registering `read_skill` (fail with a *clear, actionable* message, not the generic collision ValueError — or namespace it `skill.read` if collisions are plausible).
- Give `read_skill` a distinct, self-describing schema: `name` (string) + optional `path` (relative within skill dir). Description must say "loads a skill's instructions — use the skill name from the manifest, not a filesystem path; do not use read_file for this."
- Enforce the load at the **registry/call layer**, not by trusting the LLM: `read_skill` must update loaded-skill session state as a side effect of a successful call. If the agent used `read_file` instead, no session state changes — and the skill body content it reads still lands in context unmanaged (detectable: body content appears without a load event).
- When a skill is loaded, `allowed-tools` filtering must always keep `read_skill` in the list.

**Warning signs:**
- `ValueError: Tool name collision: 'read_skill'` at startup (`registry.py:137`).
- A skill's instructions appear in the transcript with no `tool_call`/`tool_result` pair naming `read_skill`.
- TUI tool monitor shows `read_file` calls targeting `skills/` paths.
- Agent calls `read_skill(name="skills/graphify/SKILL.md")` (path-as-name).

**Phase to address:** Activation (`read_skill`) phase (SKL-03). Name reservation and the distinct schema ship with the tool itself.

---

### P-03: Skill body injected into the wrong role (breaking summarization exemption)

**What goes wrong:**
D-12 says: loaded skill body = **system-role message**, which survives summarization because `context/context.py:88` excludes `role == "system"` from `_maybe_summarize`. The failure mode is injecting the body as `user` or `assistant`:
- As **user**: it's *not* summarization-exempt — the skill instructions get compacted away mid-session, silently destroying the very instructions that are the point of the feature.
- As **assistant**: it breaks the OpenAI tool-calling **alternation contract** — `context.py:43-49` adds assistant-with-tool_calls, then tool messages must follow. An injected assistant message mid-loop (or between `add_assistant_tool_message` and `add_tool_message`) produces a 400 from the provider. It also *triggers* `_maybe_summarize` (only assistant adds do — `context.py:34`), firing compaction exactly when you don't want it.

**A subtler trap:** even "correct" system-role injection has a provider risk. `to_llm_messages` (`session/models.py:57-61`) puts the session system prompt *first*; a context-injected system message lands **after user/assistant messages**. OpenAI's current chat-completions API tolerates this, but many OpenAI-compatible providers (the harness's whole point — configurable `base_url`) reject or ignore system messages that aren't first. The "no new mechanism" claim in D-12 is only true for *summarization* — not for every backend.

**Why it happens:**
`Message.role` validation accepts `"system"` (`context/message.py:7`), and `add_message` exists, so injection looks trivial — but nothing in the codebase has ever inserted a system message *mid-conversation* before. The summarization exemption creates false confidence about provider acceptance.

**How to avoid:**
- Add a dedicated `add_skill_message(content)` (or explicit `add_system_message`) to `ConversationContext` that records the role as `system` and tags it (e.g. `metadata={"kind": "skill", "name": ...}`) so loaded-skill messages are identifiable and countable.
- **Verify against the actual configured backend** during the activation phase: send a request with a mid-conversation system message; if the provider rejects it, fall back to appending the skill body into the *system block* (a loaded-skills registry the system prompt builder reads) instead of a context message. Design for both paths from day one.
- Never route skill bodies through `add_user_message` / `add_assistant_message`; add a comment at `context.py:88` documenting the exemption *and* the alternation constraint so future editors don't "fix" the role.

**Warning signs:**
- A skill's instructions disappear from the conversation after a summarization pass (compaction printed at `context.py:93-99`).
- HTTP 400 `messages with role 'system' must be first` or `alternating roles` from the provider after a skill loads.
- Summarization fires immediately after a skill loads (assistant-role injection).

**Phase to address:** Activation (`read_skill`) phase for the injection mechanics; a provider-compat check belongs in the session-behavior phase's E2E verification.

---

### P-04: `/skill` command routing (TUI vs backend RPC mismatch)

**What goes wrong:**
Today every slash command is parsed **in the TUI** (`tui-ink/src/app.tsx:41-66`): `/session`, `/new`, `/sessions` are handled client-side; *everything else* falls through to `client.submitPrompt(trimmed)` → `chat` RPC → `RuntimeAPI.submit_prompt` → `Scheduler` → `Agent.run`. So typing `/skill graphify` in the current TUI sends the literal string `/skill graphify` to the LLM as a **user message** — the model may or may not interpret it, no session state changes, no indicator, and behavior differs from the Python REPL (`main.py` handles its own slash set). The classic failure: TUI and REPL each get their own `/skill` implementation and they drift (command parsing, error messages, busy-state handling). A second mismatch: if `/skill` becomes a backend RPC method (`skills.load`), it must be added to the **whitelist + adapter + dispatcher + client** — `protocol.py:83-93` lists 9 methods, `adapter.register_all` registers them, `rpc-client.ts` wraps them, `types.ts` types them. Missing any one layer = `METHOD_NOT_FOUND` (-32601) or a 30-second client timeout (`rpc-client.ts:94-99`) with the input already cleared from the TUI box.

**Why it happens:**
The TUI owns the input loop and the backend owns session state — the skill load state (D-13: session-scoped, lives in the runtime) is backend-side, so a TUI-only `/skill` can't update it. Two processes, two languages, one command. The RPC method surface has grown through 9 methods without a checklist enforcing that all four layers stay in sync.

**How to avoid:**
- **One router, one source of truth:** decide *where* `/skill` is handled and mirror it in the other surface deliberately. Recommended: `skills.load` RPC method (backend owns load state) + thin TUI interceptor that parses `/skill <name>` and calls it; REPL gets the same path. The TUI must NOT fall through `/skill` to `submitPrompt`.
- Treat the RPC surface as a contract: update `protocol.py` `RPC_METHODS`, `adapter.py` (handler + `register_all`), `dispatcher` (automatic), `rpc-client.ts`, and `types.ts` in one change — add a checklist item to the plan.
- Backend handler must be non-blocking and safe while the scheduler is busy (a `/skill` during an active turn should queue or reject clearly, mirroring `Scheduler` backlog semantics — not block the streaming turn).
- `/skill <unknown>` must return a distinguishable error (skill-not-found) — not a generic `INTERNAL_ERROR` that the TUI renders as a system failure.
- Test the round trip: TUI keystroke → JSON-RPC → backend load → notification → indicator.

**Warning signs:**
- `Method not found: skills.load` in `tui-ink-rpc.log` (server.py routes stderr there) while the TUI shows a silent timeout.
- The agent, unprompted, starts answering "/skill foo" as a conversation topic (fall-through symptom).
- TUI shows the skill loaded but the Python REPL doesn't, or vice versa.
- Input clears from the TUI box but no response/indicator appears (30s timeout hit).

**Phase to address:** Session behavior & `/skill` command phase (SKL-04). The RPC-contract checklist ships with the command.

---

### P-05: `allowed-tools` filtering that persists past the skill's loaded window

**What goes wrong:**
D-16: while a skill with `allowed-tools` is loaded, the tool list passed to the LLM is filtered to that allowlist — "restrictions last as long as the skill is loaded." Two failure modes:
1. **Filtering mutates registry state instead of shaping the per-iteration list.** `Agent.run` calls `registry.list_tools()` fresh each iteration (`agent/core.py:108`) — the filter belongs *on that returned list*, keyed on loaded-skill state. If instead the implementation removes tools from `_provider_tools`/`_tool_map` (`registry.py`'s only mutable structures), the tools stay gone forever — no unload path exists (D-13 has no unload; `/new` or session close only). Worse, `registry.call_tool` (`registry.py:84`) does **not** check the filter: the LLM could still invoke a filtered-out tool by name, silently bypassing the sandbox while the manifest says it's restricted.
2. **Filter semantics are undefined across multiple loaded skills.** The milestone defers "multiple simultaneous loaded skills + combined tool filtering" — but the agent can call `read_skill` twice in one turn. With skill A allow-listing `[read_file]` and skill B allow-listing `[bash]`, the union/intersection/error answer is unspecified → either tools leak through or the agent randomly loses tools.

**Why it happens:**
`list_tools()` is a pure accessor over `_provider_tools` — the natural-looking implementation is to mutate it, because there's no separate "effective tool list" concept. And `call_tool` was built pre-sandbox (CONCERNS.md already flags zero input validation), so enforcement-on-dispatch was never a concern.

**How to avoid:**
- **Filter as pure function:** `registry.list_tools()` stays untouched; the *effective* tool list is computed per iteration: `base_list − filtered` where filtering is derived from current loaded-skill state (session-scoped). Never mutate `_provider_tools`/`_tool_map`.
- Enforce the allowlist in **both** places: the list passed to the LLM AND `call_tool` (reject `ValueError: tool 'X' restricted by loaded skill 'Y'`) — defense in depth; the LLM is not the only caller.
- Define combined-filter semantics up front: intersection (safest), or load-conflict error. Document it in the phase plan; test it.
- Tie filter state to the same object as load state so unload (session switch, `/new`, and any future `/unload`) atomically clears it.
- Add a `loaded_skills()` accessor on the session/runtime so the TUI and tests can observe filter state.

**Warning signs:**
- After loading a skill and then a new `/new`, previously-seen tools are missing (mutation leakage).
- Tool call succeeds despite the tool being filtered (LLM still finds it via `call_tool`).
- Behavior differs between "skill loaded then unloaded" vs. "never loaded."
- Two loaded skills → agent visibly confused about which tools it has.

**Phase to address:** Session behavior phase (SKL-05, D-16). The pure-filter design must be decided *before* the activation phase ships, because the load/unload state object is shared.

---

### P-06: Path traversal on skill-dir reads

**What goes wrong:**
D-08/D-10 scope `read_skill` reads to `skills/` — "no generic filesystem exposure." The codebase precedent is bad: built-in `read_file`/`write_file`/`list_dir` (`tool/local_provider.py:54-84`) accept **arbitrary paths with zero sandboxing** — CONCERNS.md flags this explicitly. If `read_skill`'s sibling-path argument is resolved naively (`skills/<name>/<path>`), the agent can pass `../../config.py`, `..\..\.env`, or an absolute path and read any file the process can read — including `.agentharness/` session JSONL and `.env` (API keys, per CONCERNS.md). The LLM is the caller; prompt-injection in *skill content* (a skill body telling the agent to exfiltrate) turns this into an easy exploit. On Windows (this repo's platform) both `/` and `\` separators and drive-relative paths (`C:\...`) must be handled.

**Why it happens:**
The existing file tools established the "no validation" norm; the milestone's "path-scoped" requirement is a *statement of intent*, not an existing helper. Nobody reuses what doesn't exist. `Path.resolve()`-without-check is the classic implementation.

**How to avoid:**
- **Canonicalize and check containment:** resolve the requested path and the skill base dir (`Path.resolve()` — this also defeats symlink escapes), then require `resolved.is_relative_to(skill_base)` (Python 3.12 — the project floor) or `os.path.commonpath` equality check. Reject `..` segments, absolute paths, and any traversal before resolution.
- Reject path arguments that aren't relative; build the path only inside the loader, never from the raw argument.
- Only expose files *under the specific skill's* directory (not the whole `skills/` tree) — a skill reading another skill's files is usually wrong and is the first step toward escape.
- Unit tests: `../`, `..\`, absolute path, symlink-to-outside, `.env` path, unicode-normalization tricks (NFC/NFD on macOS-style names), case-insensitive escapes on Windows.
- Note the *other* exposure: `read_file`/`list_dir` remain unsandboxed — document that `read_skill`'s sandbox is per-tool, and flag built-in hardening as a separate backlog item (do not silently widen the sandbox scope of the milestone).

**Warning signs:**
- `read_skill` arguments containing `..`, absolute paths, or `C:` drives.
- Skill tool result content that doesn't look like markdown instructions (e.g., JSONL session data, `.env` content).
- Agent reading `.agentharness/skills/<other-skill>/` from inside skill A.

**Phase to address:** Activation (`read_skill`) phase (SKL-03). Security tests for traversal must be in the same wave as the tool, not in "hardening" later.

---

### P-07: Malformed frontmatter crashing discovery

**What goes wrong:**
D-04: malformed skill → log warning + skip; "a broken skill never breaks the harness." The trap: discovery runs as part of **system-prompt assembly, which runs on every single LLM call** (`to_llm_messages` → `_build_system_prompt`). If discovery raises instead of per-skill try/except, one bad YAML file 500s *every* request in the harness — chat, summarization, everything. Failure modes beyond YAML syntax: missing required `name`/`description` (D-03), wrong types (name is a dict), non-UTF-8 bytes / BOM, empty file, a directory that looks like a skill but has no `SKILL.md`, unreadable file (permissions), a `description` containing newlines or control chars that corrupt the manifest formatting (breaking *all* other skills' entries in the same prompt).

**Why it happens:**
The existing precedent (`_build_system_prompt` reads AGENTS.md with zero error handling — CONCERNS.md "Fragile Areas") normalizes unguarded file reads in the hot path. Discovery with a for-loop and no per-item isolation is a natural first draft. Also: no frontmatter parser exists in the codebase, so a homegrown regex/YAML split is likely — and naive `split("---")` mis-parses `---` inside the body.

**How to avoid:**
- **Per-skill try/except with an explicit exception taxonomy:** `FrontmatterError` (missing/invalid fields → warn + skip, per D-04), `YAMLError` (warn + skip), `OSError` (warn + skip). No exception may escape the discovery function — add a test with a fixture set containing: no frontmatter, broken YAML, empty file, non-UTF8, missing `name`, directory without SKILL.md.
- Parse with a real YAML parser (PyYAML) — `safe_load` only; never eval. Validate `name` matches `^[a-z0-9][a-z0-9-]*$` kebab-case (per the agent-skills spec) and `description` is a non-empty string.
- **Sanitize the description** for manifest embedding: strip newlines/control chars or quote it, so one bad skill can't corrupt the manifest block for everyone.
- Cache discovery with mtime invalidation (the AGENTS.md-per-turn re-read is already flagged fragile; don't compound it with a per-turn skill scan of N files). Invalidate on the skills dir mtime or per-file mtime.
- Discovery result must be *total*: warn-count and a `skills_available` count in logs; if all skills fail to parse, the harness must still work (empty manifest).

**Warning signs:**
- Harness completely non-responsive after adding a skill (every call 500s — the silent-killer signature of discovery-in-hot-path).
- `YAMLError` traceback in logs (escaped from discovery).
- Manifest showing a skill entry whose description spans multiple lines / breaks the block formatting.
- `skills_available: N` log line missing or zero when `skills/` clearly has files.

**Phase to address:** Skill discovery & manifest phase (SKL-01). The parse-and-skip contract plus the fixture tests ship with discovery; the caching design belongs to the same phase (or the manifest phase, with a shared discovery module).

---

### P-08: Skill name collisions

**What goes wrong:**
D-05: duplicate names → first-wins (deterministic sort) + warning. Real collision sources in this repo:
1. **Folder-name vs frontmatter-name mismatch** — D-02 says `name` = folder name, but D-03 requires frontmatter `name`. If they disagree (folder `code-review`, frontmatter `name: code_review`), you get two effective names for one skill: the folder scan path and the manifest `name` diverge, so `read_skill` by manifest name fails while the folder listing shows a different name.
2. **Case-insensitive filesystem** — this repo runs on win32. `Foo` and `foo` folders can't coexist on NTFS, so sort order varies, and a *later* skill with a same-name-different-case frontmatter `name` collides silently with an existing entry.
3. **Name collision with the tool namespace** — a skill named `read_skill` collides with the loader tool (P-02); a skill named `session` or `new` collides with slash commands; a skill named like an MCP tool confuses the agent (manifest says "use `graphify`" but `graphify` is also a tool name).
4. **Shadowing across discovery runs** — a skill added later with the same name as an existing one shadows it (D-05 first-wins), and the user has no idea which body the agent is loading.

**Why it happens:**
The registry precedent *raises* on collision (`registry.py:133-141` — an MCP-oriented hard-fail policy), while skills need *soft* first-wins (D-05) — two different policies in one codebase invites copy-paste of the wrong one. And "name = folder name" (D-02) vs "frontmatter name required" (D-03) creates two sources of truth from day one.

**How to avoid:**
- **Single source of truth:** validate at discovery that frontmatter `name` equals the folder name; on mismatch, warn + skip (or resolve to folder name with a loud warning — pick one, D-04's skip policy suggests warn+skip).
- Normalize names at discovery (lowercase, strip) for the collision check so case-insensitive filesystems and `Foo`/`foo` frontmatter don't silently pass.
- Reserve names: block skills named `read_skill` and any existing tool/slash-command name at discovery (warn + skip, never crash).
- Deterministic sort must be by *normalized* name so first-wins is reproducible across platforms/OSes.
- Log shadowing loudly and specifically (`[skills] 'foo' (folder B) shadowed by 'foo' (folder A) — first-wins`). Make the TUI `/skill foo` load ambiguous-name failures visible, not silent.

**Warning signs:**
- `[skills] shadowed` warnings appearing after a git pull adds a skill (team members create same-named skills).
- Loading `/skill foo` yields instructions that match a *different* skill's folder contents.
- `read_skill(name="x")` fails while the manifest lists `x` (frontmatter/folder mismatch).

**Phase to address:** Skill discovery & manifest phase (SKL-01). Name validation and reservation rules ship with the parser.

---

### P-09: Loaded skill context accumulating and crowding the window

**What goes wrong:**
A loaded skill body persists as a system message **for the whole session** (D-12/D-13 — no unload path, `/new` or session close only). Because system messages are summarization-exempt (`context.py:88`), loaded bodies are **never compacted**. The agent can load 4-5 skills in a long session (each body often 500+ lines — the agent-skills spec suggests keeping SKILL.md under 500 lines), and the window fills with stale instructions for tasks long finished. Worse, this interacts with P-11: every loaded body inflates `total_tokens`, pushing *chat* messages into summarization faster. "Persists for session" is the feature; unbounded persistence with no accounting is the bug.

**Why it happens:**
The milestone models Claude Code's "persists for session" without the observation that Claude Code also *assumes* load is infrequent and session length is bounded. The exemption in `_maybe_summarize` (line 88) is a *blanket* system-message exemption — it can't distinguish "conversation summary" system messages (essential, must survive) from "stale skill body" system messages (debatable). No per-message metadata exists (`Message` has no `kind` field), so nothing can tell them apart.

**How to avoid:**
- **Account for loaded skills explicitly:** track `loaded_skill_tokens` on the session/runtime; the context token budget must treat system-role skill bodies as *consumed* context (they are — the provider counts them), even though summarization skips them. Gate new loads: refuse (or warn) when loaded-skill tokens exceed a cap (e.g., 25-30% of `max_tokens`).
- Tag skill messages with `metadata={"kind": "skill", "name": ...}` (extend `Message` with an optional metadata field — backward-compatible since `from_dict` defaults) so loaded bodies are identifiable, countable, and removable.
- Provide a real unload path even if minimal: `/skill` with no arg or `/skill --unload <name>` (cheap — just filter the tagged messages out of context). Even if D-13 keeps session-scoping, an unload command turns "persists for session" from a liability into a feature.
- Optionally: allow summarization to *condense* stale skill bodies (include skill-tagged messages in a separate "skill summary" pass) instead of the blanket exemption — flag as a future-milestone enhancement, not v1.1.

**Warning signs:**
- Token usage per turn stays high even after the task that loaded a skill is long finished.
- Summarization fires repeatedly on chat messages while skill bodies sit untouched (P-11's symptom).
- `total_tokens` grows by ~skill-body-size every time `read_skill` is called.
- Model behavior degrades in long sessions after multiple loads ("forgetting" the actual conversation).

**Phase to address:** Session behavior phase (SKL-05) — the accounting and tagging mechanism must be designed alongside D-12 injection, not after; an unload command can be a later phase of the same milestone.

---

### P-10: Interaction with token-streaming events

**What goes wrong:**
The streaming pipeline has a strict event contract (`harness/events.py`, `server.py:51-123` `_DOMAIN_TO_NOTIFICATION`/`_PAYLOAD_EXTRACTORS`, `rpc-client.ts:195-278` `handleEvent`). Loading a skill crosses this boundary in several breakable ways:
1. **The "Skill loaded" indicator (D-14) has no event type.** Every notification the TUI renders maps to a typed case in `handleEvent` (`turn_started`, `tool_call`, `tool_result`, `token`, `response_complete`, `cancelled`, `error`). If the skill-loaded state is emitted as a generic `tool_result` or smuggled into `token`, the TUI misrenders it (a fake tool card, or a streamed "Skill loaded: X" text chunk that pollutes the assistant message and gets persisted/truncated wrong). The correct path is a new `NotificationType.skill_loaded` + `_DOMAIN_TO_NOTIFICATION` entry + `_PAYLOAD_EXTRACTORS` entry + `handleEvent` case + `types.ts` — five touchpoints, exactly like P-04's four-layer contract.
2. **Tool-call turns stream no tokens** (`agent/core.py:90-93`, `openai_client.py:137-175`): a `read_skill` iteration emits `ToolCallEvent`/`ToolResultEvent` but zero `TokenProduced`. Users see the tool card flash and then silence — the indicator (or lack of one) is the only feedback. If the loaded body is large, the *next* turn's first tokens come after a long pause with the UI looking dead.
3. **Cancel mid-load leaves dangling tool_calls.** `Agent.run` adds the assistant-with-tool_calls message (`context.py:148`) *before* `asyncio.gather` executes tools. On cancel, `gather` is aborted, the tool result is never added, and context now holds an assistant message with `tool_calls` and no matching `tool` response — the next `to_llm_messages()` sends a broken alternation sequence to the provider → 400. Pre-existing, but skills make it likelier (loads happen at the start of tool loops).
4. **Streaming turns that follow a load** must reflect the new context — they do automatically (`to_llm_messages` is called per iteration), but the *manifest* itself is also rebuilt per call, so any drift between "loaded body" state and "manifest" state mid-turn is visible to the model.

**Why it happens:**
The event system was designed for 7 fixed event types; every new user-visible state added since shipped without a new type (the tool monitor reused `tool_call`/`tool_result`). The streaming loop and the context are synchronized only at call boundaries — mid-loop mutations (cancel) leave them inconsistent.

**How to avoid:**
- **Emit a typed `SkillLoadedEvent`** through the full pipeline (harness event → server mapping → notification → `handleEvent` case → store flag → indicator render). No free-riding on `token`/`tool_result`. Treat this as the same contract-discipline as P-04.
- Design the indicator from the event, not from inference: the TUI must never guess "a skill loaded" from tool names — it should react to the event.
- **Close the cancel hole:** in `Agent.run`, when a turn is cancelled mid-gather, drop the dangling assistant-tool_calls message from context (or replace with an explicit "cancelled" tool result) so alternation stays valid. Unit-test: cancel during a `read_skill` call → next turn's message list is provider-valid.
- Reuse `TurnStarted` semantics for loading feedback: emit `TurnStarted`-like or status transitions so the TUI shows "thinking/loading" during the read_skill iteration.
- During the activation phase, run an E2E: load a skill mid-turn while streaming a long response, cancel, then send another prompt — assert no 400 and no duplicated/mangled assistant messages.

**Warning signs:**
- TUI conversation panel renders "Skill loaded: X" as an assistant message (token-event smuggling).
- After pressing cancel during a `read_skill` call, the next prompt fails with a provider alternation/validation error.
- Tool monitor card for `read_skill` shows but no indicator chip and no status change.
- A skill-load indicator that disappears on session restore (event lost because it was never typed/persisted — by design D-13, but the indicator must not imply persistence).

**Phase to address:** TUI integration phase (D-14) for the typed event; the cancel-hole fix belongs to the activation phase's streaming interaction (with a test in the hardening phase).

---

### P-11 (bonus): Skill body token accounting distorts the summarization threshold

**What goes wrong:**
`ConversationContext.add_message` adds *every* message's tokens to `total_tokens` (`context.py:33`), including system messages; `_maybe_summarize` triggers at `total_tokens >= token_limit * 0.75` (`context.py:78`) but only summarizes non-system messages. So each loaded skill body pushes `total_tokens` up without being eligible for compaction — the conversation hits the summarization threshold **sooner and more often**, each pass compacting *chat* context aggressively to make room for skill bodies the model already has in the system block. Net effect: loading a 1,500-token skill on a 4K-window model instantly burns ~37% of the budget, and the user's actual conversation gets summarized away around it.

**Why it happens:**
The token accounting was written when system messages were either the (non-counted) prompt or the summary message inserted at index 0. No code path previously added arbitrary system messages mid-conversation, so "system tokens count toward the threshold" was never a design question. D-12's "no new mechanism" framing skipped the accounting interaction.

**How to avoid:**
- Track system-role skill tokens **separately** (`loaded_skill_tokens` on the context or runtime) and have `_maybe_summarize` evaluate the threshold against *non-system* tokens: `chat_tokens = total_tokens − system_tokens`. This keeps chat-summarization behavior stable regardless of how many skills are loaded.
- Alternatively, decide consciously: skill bodies *should* consume budget (they do at the provider) — then gate loads by P-09's cap so the distortion is bounded and visible. Don't leave it implicit.
- Add a unit test: with a loaded skill body, summarize threshold fires on chat-message growth at the *same* chat volume as without the skill.

**Warning signs:**
- `[CONTEXT] Summarization triggered` immediately after `read_skill` loads a body, with `total_tokens` inflated mostly by the skill.
- Chat history visibly compacted right after a skill load (P-09's symptom, root-caused here).
- `total_tokens`/`token_limit` ratio jumping at load time with no conversation growth.

**Phase to address:** Session behavior phase (SKL-05). The accounting change ships with injection (D-12), not as a follow-up fix.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Re-read `skills/` dir + parse all frontmatter on every LLM call (no cache) | Zero cache invalidation logic | N-file scan + N YAML parses per iteration in the hottest loop; compounds with AGENTS.md-per-turn re-read | Never — cache with mtime invalidation; the discovery module is a natural single home for both |
| Manifest budget measured in tiktoken tokens | "Token-aware" | Budget shifts when `config.model` changes; tests become model-dependent | Use chars (stable, per D-07's ~1,500-char precedent); tokens only as a secondary log metric |
| `read_skill` name + sibling-path args resolved with string concatenation | Two lines of code | Path traversal (P-06) on win32; symlink escapes | Never — `Path.resolve()` + `is_relative_to` containment check |
| `allowed-tools` implemented by mutating `_provider_tools` | Filter "just works" at `list_tools` | Permanent tool loss after unload; bypassable via `call_tool` (P-05) | Never — pure per-iteration filter + dispatch-side enforcement |
| Reusing `tool_result` events to signal "skill loaded" | No new event plumbing | TUI misrenders; no session state; P-10 | Only as a stopgap *before* the TUI phase ships the typed event; never in the shipped milestone |
| Injecting skill body as `user` message "because it's just instructions" | Avoids system-message-position concern | Summarized away; breaks alternation; P-03 | Never |
| Skipping the RPC-contract checklist (`protocol.py` + adapter + client + types) | Faster first iteration | `METHOD_NOT_FOUND` or 30s timeouts on `/skill`; REPL/TUI drift (P-04) | Never once the method exists; add the checklist to the plan |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| OpenAI-compatible backend (configurable `base_url`) | Assuming mid-conversation system messages are accepted everywhere | Verify with the actual configured backend during the activation phase; design the fallback (append to system block) up front (P-03) |
| Tool registry (`tool/registry.py`) | Registering `read_skill` as a plain local tool with no reserved-name check | Reserve/namespace the name; treat `_register_tools` collision as a *recoverable* warning for skills (D-05) but keep hard-fail for MCP tools (P-02, P-08) |
| JSON-RPC event stream (`server.py` → `rpc-client.ts`) | Adding the skill-loaded indicator without touching all 5 touchpoints | New `NotificationType` + server mapping + extractor + `handleEvent` case + `types.ts` in one change (P-10) |
| Summarization (`context/context.py:_maybe_summarize`) | Relying on the line-88 exemption without checking token accounting | Separate skill-token accounting so the threshold stays chat-relative (P-11) |
| Scheduler backlog (`harness/scheduler.py`) | `/skill` RPC blocking while a turn streams | Non-blocking handler; queue or reject with a clear status, mirroring backlog semantics (P-04) |
| Session JSONL store | Persisting loaded skills to disk "to be safe" | Explicitly exclude (D-13); otherwise restored sessions carry stale bodies with no load events (P-09/P-10) |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Manifest grows unbounded (no cap) | System prompt bloat; skill triggers degrade; lost-in-the-middle | Char-based cap + truncation + trim warnings (P-01) | ~20-30 skills on a 4K-window model; earlier with long descriptions |
| Un-cached discovery scan per call | Latency per LLM call rises with `skills/` size | mtime-invalidated cache | 50+ skill folders; YAML parse cost dominates |
| Loaded skill bodies accumulate with no cap/unload | Window crowds; chat summarized around them | Token cap on loads + unload path + skill-token accounting (P-09, P-11) | 3-5 loaded skills in one long session |
| Multiple loaded skills with intersecting `allowed-tools` | Undefined tool visibility; agent confusion | Defined combined-filter semantics (intersection) + tests (P-05) | First turn where the agent loads 2 skills |
| Large `read_skill` result echoed to the TUI tool monitor in full | TUI memory/render spikes; long pauses with no feedback | Truncate `ToolResultEvent` content previews (the 100-char preview pattern in `registry.py:114` already exists — reuse it for read_skill) | Skills with 500+ line bodies |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| `read_skill` path arg resolved without containment check | Read `.env`, session JSONL, any file (P-06) | `resolve()` + `is_relative_to(skill_base)`; reject non-relative args; unit-test traversal vectors incl. win32 `\`, `C:\`, symlinks |
| `allowed-tools` enforced only on the LLM-visible tool list | Bypass via `registry.call_tool` direct invocation (P-05) | Dispatch-side rejection in `call_tool` |
| Unsandboxed `read_file`/`list_dir` treated as "covered by read_skill's sandbox" | False sense of containment; skill bodies can still direct the agent to read arbitrary paths via the built-ins | Document the per-tool boundary; flag built-in hardening as backlog (CONCERNS.md already lists it) |
| Frontmatter parsed with `eval`/`ast.literal_eval` or hand-rolled split | Arbitrary code execution / mis-parse (P-07) | PyYAML `safe_load` only |
| Prompt injection via skill *content* (a skill body instructing exfiltration) | Skill bodies become attack vectors | Treat skills as code: review gate for shared/imported skills (future milestone); at minimum, load indicators (D-14) make behavior attribution visible |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| `/skill <name>` silently falls through to the LLM as a chat message | User thinks it loaded; agent hallucinates a response (P-04) | Intercept in the TUI; clear "Skill loaded / not found" feedback |
| No load indicator | Agent behavior changes (tool restrictions, new instructions) with no visible cause — "why did it stop using X?" (D-14) | Typed `SkillLoadedEvent` → visible chip/status line; also surface *unloads* |
| Skill loads during a silent tool-call turn with no progress feedback | Long pause after the tool card; user thinks it hung (P-10) | Status transition ("loading skill…") during the read_skill iteration |
| Manifest cap silently drops skills | Agent never triggers skills the user authored — "my skill isn't working" (P-01) | Log trimmed skills; optional `/skills` listing shows what's *in* the manifest vs. on disk |
| Duplicate-name shadowing invisible | `/skill foo` loads the wrong body (P-08) | Loud shadow warnings; ambiguous-name error on `/skill` |
| Loaded skills with no way to unload except `/new` | Users restart sessions to "unload" skills | Minimal `/skill --unload` or an unload affordance (P-09) |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Manifest:** Cap enforced in *characters* and measured against the whole system prompt — not just "manifest inserted" — verify the trim-warning fires in logs
- [ ] **read_skill:** Name reserved against providers/tools; traversal tests (`../`, `..\`, absolute, symlink) in the same wave — not deferred to hardening
- [ ] **Skill body injection:** `Message` tagged `metadata.kind="skill"`; skill-token accounting separate from chat tokens; provider accepts mid-conversation system messages (tested against the real `base_url`)
- [ ] **/skill:** Present in ALL of `protocol.py` RPC_METHODS, `adapter.py` handler + `register_all`, `rpc-client.ts`, `types.ts`; TUI intercepts (no fall-through to `submitPrompt`); REPL mirrors TUI
- [ ] **allowed-tools:** Filter is a pure per-iteration projection (registry state untouched); `call_tool` rejects restricted tools; combined-filter semantics defined and tested
- [ ] **Indicator:** Real `SkillLoadedEvent` through the full pipeline — grep `handleEvent` for the new case; no reuse of `token`/`tool_result`
- [ ] **Cancel safety:** Cancel mid-`read_skill` leaves provider-valid alternation (no dangling tool_calls); tested
- [ ] **Discovery:** Per-skill try/except with fixtures (broken YAML, missing name, empty file, non-UTF8); discovery never raises; cached with mtime invalidation
- [ ] **Collisions:** Frontmatter `name` validated against folder name; case-normalized first-wins; shadow warnings visible
- [ ] **Unload/accounting:** Loaded-skill token cap exists; summarization threshold is chat-relative (P-11 test passes); an unload path exists even if minimal

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| P-01 Manifest overflow | LOW | Raise the cap constant / trim descriptions; the truncation log tells you which skills to fix |
| P-02 read_skill name collision | MEDIUM | Rename the colliding skill/tool; until fixed, registry won't start — clear error message needed at registration |
| P-03 Wrong-role injection | MEDIUM | Remove the mistyped message from context (`_messages` filter by tag); re-inject as system; verify provider acceptance |
| P-04 /skill routing mismatch | MEDIUM | Fix the four-layer RPC contract; TUI fall-through is recoverable by restarting the RPC child process (`client.stop()` re-spawns via `findProjectRoot`) |
| P-05 Filter persistence | HIGH | If registry mutated: rebuild `_provider_tools` from `fetch_tools()` re-registration (restart providers) — `Agent.start`/`RuntimeAPI.start` cycle; session switch doesn't help |
| P-06 Traversal | HIGH (security) | Restrict the skill dir to read-only expectations; rotate any leaked `.env`/API key; the skill dir is repo-versioned, so `git diff` shows if skill content itself was tampered |
| P-07 Malformed frontmatter | LOW | Fix the offending SKILL.md; the harness keeps running (D-04 contract) — the warning names the file |
| P-08 Name collisions | LOW | Rename/remove the shadowed skill folder; first-wins order is deterministic so it's reproducible |
| P-09/P-11 Context crowding | MEDIUM | `/new` or session switch clears loaded bodies (D-13); with tagging, a mid-session filter of `kind=skill` messages restores the window without losing the conversation |
| P-10 Streaming/cancel | MEDIUM | Drop the dangling assistant tool_calls message before the next call (a helper on context); restart the turn |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls. Phase names below follow the milestone's natural decomposition (discovery → activation → session behavior → TUI → hardening); the roadmap assigns numbers.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| P-01 Manifest token-budget overflow | Skill discovery & manifest (SKL-02) | Unit: manifest assembly ≤ cap for N skills; log shows trim warning |
| P-02 read_skill tool confusion | Activation / read_skill (SKL-03) | Reserved-name registration test; E2E agent loads by manifest name |
| P-03 Wrong-role injection | Activation / read_skill (SKL-03) + provider-compat check in session behavior | Body survives compaction; no 400; alternation valid |
| P-04 /skill routing (TUI vs RPC) | Session behavior & /skill (SKL-04) | RPC-contract checklist; TUI keystroke → RPC → notification round trip |
| P-05 allowed-tools persistence | Session behavior (SKL-05, D-16) — filter design precedes activation | Filter survives unload; `call_tool` rejects; combined-filter test |
| P-06 Path traversal | Activation / read_skill (SKL-03) | Traversal test suite (win32 + posix vectors) |
| P-07 Malformed frontmatter | Skill discovery (SKL-01) | Fixture-based discovery tests; no-raise guarantee |
| P-08 Skill name collisions | Skill discovery (SKL-01) | Normalized first-wins test; folder/frontmatter mismatch test |
| P-09 Loaded context accumulation | Session behavior (SKL-05) | Token cap on loads; unload path; long-session E2E |
| P-10 Token-streaming interaction | TUI integration (D-14) + cancel-hole fix in activation | Typed event E2E; cancel-mid-load then next prompt is 400-free |
| P-11 Skill token accounting vs summarization | Session behavior (SKL-05) | Threshold-fires-at-same-chat-volume test with/without loaded skill |

## Sources

- **Codebase (verified by reading source, HIGH confidence):** `session/models.py` (`_build_system_prompt`, `to_llm_messages`), `context/context.py` (`_maybe_summarize` line 88, token accounting lines 29-55, 75-121), `context/message.py` (role validation), `agent/core.py` (`run` tool loop, `_stream_llm_call`, gather/cancel), `tool/registry.py` (`list_tools`, `call_tool`, `_register_tools` collision raise), `tool/local_provider.py` (unsandboxed built-ins), `harness/runtime.py`/`scheduler.py` (submit_prompt path, backlog), `backend/rpc/protocol.py` (RPC_METHODS), `backend/rpc/adapter.py`, `backend/rpc/server.py` (`_DOMAIN_TO_NOTIFICATION`, `_PAYLOAD_EXTRACTORS`), `tui-ink/src/app.tsx` (slash-command parsing lines 41-66), `tui-ink/src/bridge/rpc-client.ts` (`handleEvent`, 30s timeout), `llm/base.py`/`llm/openai_client.py` (tiktoken `count_tokens`, stream_chat tool-call behavior)
- `.planning/MILESTONE-CONTEXT.md` — D-01..D-16 decisions the pitfalls must not violate; canonical refs for the Claude Code model
- `.planning/PROJECT.md` — SKL-01..05 requirements, phase scope
- `.planning/ROADMAP.md` — v1.1 has no phases yet; mapping table above proposes them
- `.planning/codebase/CONCERNS.md` — pre-existing: unsandboxed built-in file tools, unguarded AGENTS.md read in hot path, zero test coverage
- **Agent Skills spec / Claude Code model (MEDIUM confidence, external):** https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview (three-level progressive disclosure, metadata always in system prompt); https://code.claude.com/docs/en/skills (session persistence of loaded content, allowed-tools); https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills (design rationale — the noise/cost argument underpinning P-01); https://learn.microsoft.com/en-us/agent-framework/agents/skills (independent implementation: `load_skill`/`read_skill_resource` naming, allowed-tools experimental status, SKILL.md < 500 lines guidance, custom system prompt injection) — corroborates the tool-name-distinctness and manifest-in-system-prompt failure modes

**Confidence notes:** All codebase integration claims (file/line behavior) are verified against the source above (HIGH). The provider-dependent claim (mid-conversation system messages) is MEDIUM — the harness targets configurable OpenAI-compatible backends, and acceptance varies; the activation phase must verify against the real backend. External skill-ecosystem behavior is MEDIUM (official Anthropic docs + Microsoft Agent Framework docs + community guides, 2026).

---
*Pitfalls research for: AgentHarness v1.1 Skills System (progressive disclosure added to an existing agent harness)*
*Researched: 2026-08-01*
