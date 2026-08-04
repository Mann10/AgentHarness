---
phase: 14-read-skill-provider-e2e
reviewed: 2026-08-02T12:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - skills/store.py
  - tests/test_skills_store.py
  - skills/provider.py
  - skills/filter.py
  - tests/test_skills_provider.py
  - tool/registry.py
  - tests/test_load_skill.py
  - context/message.py
  - context/context.py
  - harness/runtime.py
  - skills/__init__.py
  - main.py
  - tests/test_cancel_mid_gather.py
  - tests/test_skills_e2e.py
  - agent/core.py
findings:
  critical: 0
  high: 3
  medium: 5
  low: 6
  total: 14
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-08-02T12:00:00Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Phase 14 delivers the `read_skill`/`read_skill_path` async provider, the `SkillStore`
canonicalize-then-contain path-traversal guard (D-10/D-11/D-12), the single shared
`RuntimeAPI.load_skill()` path (D-09), the persist=False skill-body injection (D-08/D-13),
and the cancel-mid-gather rollback fix in `agent/core.py` (D-14).

The **path-traversal guard is sound**: I verified empirically on this win32 platform that
`../`, absolute, and backslash vectors all raise `ValueError`; `Path.resolve()` canonicalizes
symlinks before `is_relative_to()` (which is case-insensitive on WindowsPath — no case-bypass
of containment); absolute-join and symlink-escape vectors are covered by tests. No escape was
found. `yaml.safe_load` is used (no unsafe deserialization), and no hardcoded secrets or
command-injection surfaces exist in the reviewed files.

However, the dedup contract (D-07 exactly-once, ACT-02) is **broken on the primary platform
(win32) by a case-variant bypass**, and a concurrent-read TOCTOU can double-inject the same
body in a single agent turn. The context summarizer writes debug output to stdout via `print()`,
which corrupts the NDJSON RPC protocol when summarization fires in `--rpc` mode. The
cancel-mid-gather rollback is index-based and silently no-ops if summarization shrank the
message list between index capture and rollback — the exact regression D-14 claims to fix.

No Critical findings: the security boundary (skill-dir containment) held up to adversarial
analysis, including NTFS ADS and drive-relative vectors.

## High Issues

### H-01: Case-variant dedup bypass — skill body injected twice on win32 (D-07/ACT-02 violation)

**File:** `harness/runtime.py:188-197`
**Issue:** `load_skill` dedups by comparing the raw caller-provided `name` against the
recorded canonical name: `existing = next((e for e in loaded if e["name"] == name), None)`.
But `SkillStore.lookup()` keys case-insensitively on win32 (`store.py:36-37`), so
`load_skill("DEMO-GREETER")` succeeds even though `"demo-greeter"` is already loaded, and the
case-sensitive `==` misses the record. **Empirically confirmed on this platform**: loading
`demo-greeter` then `DEMO-GREETER` injects the body as a system message twice and appends the
loaded record twice. This breaks the phase's own exactly-once contract (D-07, ACT-02) and
inflates every subsequent LLM call with a duplicate instruction block.
**Fix:** compare against the canonical name after lookup, not the raw input:
```python
existing = next((e for e in loaded if e["name"] == name), None)  # pre-check fast path
info = self._skill_store.lookup(name)          # KeyError → clear error
existing = next((e for e in loaded if e["name"] == info.name), None)
if existing is not None:
    return f"Skill '{info.name}' already loaded"
```
Add a win32 test: load `demo-greeter`, then `DEMO-GREETER`, assert exactly one body and one record.

### H-02: Summarizer `print()` corrupts the NDJSON RPC stdout protocol

**File:** `context/context.py:99-105, 128-136`
**Issue:** `_maybe_summarize` writes `print(...)` debug banners to **stdout**. In `--rpc` mode
(`main.py:284-306`, `backend/rpc/server.py:126-131`) stdout is exclusively the JSON-RPC channel
("All output must be NDJSON on stdout"). When summarization triggers (token usage ≥ 0.75 ×
limit — which the Phase 14 skill bodies make more likely since they add system-message tokens),
raw `--- [CONTEXT] ...` lines interleave with NDJSON responses, breaking the TUI's line-based
parser. The new skill-body feature increases the trigger likelihood, so this pre-existing bug
becomes reachable in normal Phase 14 usage.
**Fix:** route all `print()` in `context.py` through `logger` (stderr) or an injectable
diagnostic sink:
```python
logger.debug("[CONTEXT] Summarization triggered (%d/%d tokens)", self.total_tokens, self.token_limit)
```
Also suppress the per-message preview prints in RPC mode entirely.

### H-03: Concurrent `read_skill` calls bypass dedup (TOCTOU) — double injection in one turn

**File:** `harness/runtime.py:188-197` + `agent/core.py:166-171`
**Issue:** The dedup check-then-append in `load_skill` spans an `await`
(`await session.context.add_skill_message(...)`), and the agent executes **all** tool calls of a
turn concurrently via `asyncio.gather(*tasks)` (`agent/core.py:171`). If the LLM emits two
`read_skill` calls for the same skill in one response, both coroutines pass the `existing is
None` check before either appends, then both inject the body → duplicate system message +
duplicate `skill_state["loaded"]` record. There is no lock or atomic mark-and-inject.
**Fix:** mark the record *before* the injection await, or serialize per-name with
`asyncio.Lock`:
```python
if existing is not None:
    return f"Skill '{info.name}' already loaded"
loaded.append({"name": info.name, "dir": str(info.path)})   # mark first (atomic)
await session.context.add_skill_message(info.name, body)    # then inject
```
(Dedup order matters — do the injection after the append so concurrent callers see the record.)

## Medium Issues

### M-01: Cancel-mid-gather rollback can silently no-op (D-14 regression reappears)

**File:** `agent/core.py:152, 185-193`
**Issue:** The rollback deletes by positional index captured *before*
`add_assistant_tool_message(...)`: `del self._context._messages[msgs_before_gather:]`.
But `add_assistant_tool_message` awaits `_maybe_summarize()` (role is "assistant"), which — at
small token limits (the E2E tests use 60) — can **shrink and rewrite `_messages`** (remove old
messages, insert summary at index 0) *after* the index was captured. `del lst[N:]` on a list
shorter than N is a **no-op** (verified on CPython 3.12). Result: the orphaned assistant
`tool_calls` message survives the cancel, the next turn sends dangling `tool_calls` to the
provider, and the exact bug D-14 claims to fix returns. Additionally, cancellation arriving
*inside* `add_assistant_tool_message` (before the `try` at line 170) is not rolled back at all.
**Fix:** track message identity, not position:
```python
orphan = response.tool_calls  # marker: remove this assistant msg + everything after it
try:
    results = await asyncio.gather(*tasks, return_exceptions=True)
    ...
except asyncio.CancelledError:
    # remove the assistant tool_calls message and any partial tool messages by identity
    msgs = self._context._messages
    idx = next((i for i, m in enumerate(msgs) if m.tool_calls), None)
    if idx is not None:
        del msgs[idx:]
    self._context.total_tokens = sum(m.token_count for m in msgs)
    raise
```
Better: move the assistant-tool-message commit *inside* the try (before the gather) so the
rollback always covers it, and give `ConversationContext` a rollback API instead of reaching
into `_messages` from the agent.

### M-02: `read_skill_path` does not enforce the "already-loaded" contract

**File:** `harness/runtime.py:199-203`, `skills/store.py:56-64`
**Issue:** The tool description promises "Read a bundled resource ... **from an already-loaded
skill**", and the schemas limit `path` to "references/, scripts/, assets/". Neither is enforced:
`_read_skill_path` → `store.read_path` checks only index membership (any discovered skill) and
allows any relative path inside the skill directory (e.g., `SKILL.md` itself, or any file).
An LLM can enumerate/read any indexed skill's files — including skills never loaded — without
any `skill_state["loaded"]` check, and there is no guard that the resource is actually a
bundled reference. This is a contract/design gap, not a sandbox escape (containment holds).
**Fix:** check `session.skill_state["loaded"]` for the skill name before reading; optionally
validate the first path segment against `{"references", "scripts", "assets"}`.

### M-03: Multi-worker mode misattributes job results (shared runtime race)

**File:** `main.py:244-269`
**Issue:** `worker_count > 1` workers share one `RuntimeAPI`/`Scheduler`. If worker A's job is
still running when worker B submits, B's prompt goes into the scheduler backlog and is drained
*by the scheduler* (not by B's loop). Worker A's `while runtime.is_busy` loop keeps spinning
through B's job, then both workers read `runtime.active_session.context._messages[-1].content`
and call `complete_job` — the final message now belongs to whichever job finished last, so job
results are attributed to the wrong jobs (or empty when a queued job's final message never
materializes in time). The `_messages[-1]` probe is also a private-access/IndexError risk when
the context is empty.
**Fix:** capture results via per-turn event correlation (subscribe `ResponseComplete` and match
`session_id`/prompt), or serialize workers (`worker_count` must be 1 given the shared backlog),
or give each job its own session. At minimum, guard `_messages[-1]` with a length check.

### M-04: Untrusted skill descriptions are injected into every session's system prompt

**File:** `session/models.py:78-79` (dep) + `skills/manifest.py:36-38`
**Issue:** `Session._build_system_prompt` unconditionally appends the skill manifest
(`skill_manifest`) to the system prompt of **every** session, and the manifest is built from
skill frontmatter `description` fields (`build_manifest_text` → `_sanitize_description`), which
only strips control characters/newlines. A malicious or compromised skill (skills are typically
cloned from the internet, e.g. `.agentharness/skills`) can embed
"ignore previous instructions …" in its description — no `read_skill` call is even required to
poison the system prompt. The Phase 14 `read_skill` body injection is by-design
(system-role instruction load), but the manifest auto-injection is a persistent,
no-user-action prompt-injection surface. Skill bodies loaded via `read_skill` are likewise
injected verbatim as system messages with no delimiting marker.
**Fix:** delimit manifest/body content as untrusted data (e.g., a clearly marked
`<untrusted_skill_content>` block with a warning line), cap description length, and consider
requiring explicit user consent before auto-injecting a skill's description into the system
prompt.

### M-05: No size guard on skill-body injection

**File:** `harness/runtime.py:193`, `context/context.py:40-42`
**Issue:** `load_skill` injects the full `SKILL.md` body (`body.strip()`) as a system message
with no length budget or truncation (the `manifest_max_chars` budget applies only to the
manifest). An oversized skill body can exceed `token_limit` by itself; because system-role
messages are exempt from summarization removal (`context.py:91-94`), the body stays forever and
every assistant turn then triggers summarization — which, per H-02, corrupts RPC stdout, and
per M-01, destabilizes the cancel rollback. There is also no validation that `SKILL.md` is
readable at `load()` time beyond the index (discovery already skipped unreadable files, so this
is mostly moot — but a skill file deleted between index and load raises an unhandled
`FileNotFoundError`).
**Fix:** enforce a body budget (e.g., truncate to `manifest_max_chars`-style cap with a marker)
and wrap `read_text` in the same "clear error naming the skill" contract as `lookup`.

## Low Issues

### L-01: `_create_agent` re-runs discovery, bypassing the store index

**File:** `harness/runtime.py:270-277`
**Issue:** `_create_agent` calls `discover_skills(self._skill_store._root)` directly instead of
using the store's already-built index (`SkillStore._skills`), parsing every skill dir on every
agent/session creation. This duplicates work and can drift: `SkillStore` indexes once at
construction (store.py:34), so skills added mid-run appear in the manifest but
`load_skill` raises `KeyError` — confusing inconsistency between two sources of truth. It also
reaches into the private `_root` attribute.
**Fix:** expose `SkillStore.entries()` / reindex-on-demand and use the store's index for the
manifest; rebuild the manifest from the same snapshot `load_skill` resolves against.

### L-02: TOCTOU window in the traversal guard (resolve-then-read)

**File:** `skills/store.py:56-64`
**Issue:** `p.is_relative_to(base)` is checked after `resolve()`, but `p.read_text()` re-opens
the path — a symlink planted inside the skill dir *after* resolve but *before* read escapes the
containment check. Only exploitable with write access to the skill dir (at which point the
attacker owns the sandbox anyway), so Low for this threat model.
**Fix:** open via the resolved path with `os.open(..., O_NOFOLLOW)` and/or re-stat + re-check
containment immediately before read.

### L-03: `SkillToolProvider.call_tool` — unhelpful KeyError and misleading `tool_call_id`

**File:** `skills/provider.py:50-55`
**Issue:** `arguments["name"]` raises `KeyError: 'name'` when the LLM omits a required arg —
surfaced to the model as `Error: 'name'` with no guidance. `ToolResult(tool_call_id=name, ...)`
uses the *tool name* rather than the LLM's call id; the agent ignores it today
(`agent/core.py:179` uses `tc.id`), so this is misleading, not breaking.
**Fix:** use `arguments.get("name")` with a clear validation error, and thread the call id
through if the registry can provide it.

### L-04: `RESERVED_SKILL_TOOLS` duplicated in two modules

**File:** `skills/provider.py:11`, `skills/filter.py:5`
**Issue:** The reserved set is defined twice; a future edit to one will silently desync the
other (only the unit test pins equality). `filter.py` should import from `provider.py` (or a
shared constants module) — the test comment claims "one source of truth", which the code does
not actually implement.

### L-05: Stale documentation / mid-function import / duplicated arg summarizer

**File:** `harness/runtime.py:296-297`, `tool/registry.py:110`, `agent/core.py:226-234`
**Issue:** `_make_summarize_fn` docstring says "Duplicated from main.py … Will replace main.py's
version when integrated" — main.py no longer defines a summarization prompt (stale comment).
`registry.call_tool` imports `time` mid-function (`tool/registry.py:110`). `_summarize_args`
(registry) and `_arg_summary` (agent/core) are identical helpers duplicated across modules.
**Fix:** hoist the import to module top, consolidate the arg-summary helper into one shared
utility, and update/delete the stale docstring.

### L-06: `run_worker` reads private context state with no bounds check

**File:** `main.py:259-260`
**Issue:** `runtime.active_session.context._messages[-1].content` reaches into two private
attributes and `IndexError`s on an empty context (guarded only for `active_session is None`).
Prefer a typed completion signal (e.g., the `ResponseComplete` event payload captured per job)
so worker mode stops depending on message-list internals. Related to M-03's fix.

---

_Reviewed: 2026-08-02T12:00:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
