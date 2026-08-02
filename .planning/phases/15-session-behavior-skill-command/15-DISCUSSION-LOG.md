# Phase 15: Session Behavior & /skill Command - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-02
**Phase:** 15-session-behavior-skill-command
**Areas discussed:** /skill command UX, RPC method & payload, Token accounting & cap, CAP-04 combined-filter semantics

---

## /skill Command UX

| Option | Description | Selected |
|--------|-------------|----------|
| Short ack only | Mirror read_skill's D-05 ack: print `Loaded skill <name>` only. Body already went to context as a system message — echoing duplicates it. | ✓ |
| Ack + one-line hint | Print the ack plus a hint like "Body added to context (system message)". | |
| Echo full body | Print the full skill body to the terminal so the user can read it immediately. | |

**User's choice:** Short ack only
**Notes:** —

---

| Option | Description | Selected |
|--------|-------------|----------|
| Distinct errors + usage | Unknown name → `Skill '<name>' not found.`; no argument → usage line. Never silent no-op or chat fall-through (ROADMAP criterion 2). | ✓ |
| No-arg lists skills | No argument lists available skills (name: description from manifest) so the user can pick one, mirroring /sessions. | |

**User's choice:** Distinct errors + usage
**Notes:** —

---

| Option | Description | Selected |
|--------|-------------|----------|
| Match read_skill dedup | Exactly-once (D-07): second load prints `Skill 'demo-greeter' already loaded` — same dedup ack read_skill returns. | ✓ |
| Reload forces re-inject | User-driven reload re-injects the body even if loaded (different from read_skill dedup). | |

**User's choice:** Match read_skill dedup
**Notes:** One dedup contract, two entry points.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Case-insensitive, same as read_skill | `DEMO-GREETER` loads `demo-greeter` on win32, matching discovery (D-06) and read_skill dedup. | ✓ |
| Case-sensitive always | Match strictly against frontmatter name, case-sensitive on all platforms. | |

**User's choice:** Case-insensitive, same as read_skill
**Notes:** —

---

## RPC Method & Payload

| Option | Description | Selected |
|--------|-------------|----------|
| Single skills.load | One RPC method handles load + already-loaded (returns ack/status). Follows the sessions.* namespacing pattern in protocol.py. | ✓ |
| Load + list now | Separate skills.load and skills.list methods — but listing is a future /skills feature (AUTH-02, v1.2). | |
| Reuse chat method | Reuse the existing chat path with a special /skill payload rather than a new whitelisted method. | |

**User's choice:** Single skills.load
**Notes:** —

---

| Option | Description | Selected |
|--------|-------------|----------|
| Ack + status field | `{ skill: <name>, status: loaded\|already_loaded\|not_found }`. TUI and REPL both render from this — no body echoed. | ✓ |
| Ack + body | Include the full body in the response so a future TUI could display it inline. | |
| Minimal 200-style ack | Empty success response; error responses carry message. | |

**User's choice:** Ack + status field
**Notes:** —

---

| Option | Description | Selected |
|--------|-------------|----------|
| REPL direct, RPC for TUI | REPL calls runtime.load_skill directly (in-process); RPC method exists for TUI/remote clients (Phase 16). Same shared load path = no drift. | ✓ |
| REPL routes through RPC | REPL also sends skills.load through the RPC dispatcher — uniform contract but adds a hop for an in-process call. | |

**User's choice:** REPL direct, RPC for TUI
**Notes:** —

---

| Option | Description | Selected |
|--------|-------------|----------|
| Structured error codes | -32602 INVALID_PARAMS for missing arg, domain code (e.g. -32001) for skill-not-found, plus message. Follows existing RPCError shape. | ✓ |
| Status in result only | Return status: not_found in the result payload; client renders the message. | |

**User's choice:** Structured error codes
**Notes:** —

---

## Token Accounting & Cap

| Option | Description | Selected |
|--------|-------------|----------|
| Count at load, cache | client.count_tokens() on each body at load time, cache per skill in skill_state. Summarization threshold stays chat-relative. | ✓ |
| Recount every turn | Recount loaded skill bodies on every turn — always current but per-turn overhead. | |
| Approximate from chars | Skip real counting; use body char-length/4 as a token estimate. | |

**User's choice:** Count at load, cache
**Notes:** —

---

| Option | Description | Selected |
|--------|-------------|----------|
| Token cap | Token cap on combined loaded-skill bodies, configurable via env var (mirrors SKILL_MANIFEST_MAX_CHARS but tokens, not chars). | ✓ |
| Char cap | Character cap like the manifest budget — consistent with Phase 12 but tokens matter for context window. | |
| No cap | Bound only by existing summarization. (ROADMAP criterion 3 requires a cap.) | |

**User's choice:** Token cap
**Notes:** —

---

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse with error | Refuse with clear error naming the cap. No partial state, no silent drop. | ✓ |
| Evict oldest, auto-load | Drop the oldest loaded skill to make room — automatic but silently evicts state the model may rely on. | |
| Load with warning | Still load (context grows past cap) but log a warning — cap becomes advisory only. | |

**User's choice:** Refuse with error
**Notes:** —

---

| Option | Description | Selected |
|--------|-------------|----------|
| ~8k tokens | Generous for real skill docs (~500-2k tokens each), bounded enough to protect a 200k window. | ✓ |
| ~4k tokens | Tight but very safe for smaller context windows. | |
| ~16k tokens | Allows many/large skills but eats more of a 200k window. | |

**User's choice:** ~8k tokens (default, env-var override)
**Notes:** —

---

## CAP-04 Combined-Filter Semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Intersection | A tool is retained only if in EVERY loaded skill's allowed-tools list. read_skill/read_skill_path always retained (CAP-03). Recommended by ROADMAP. | ✓ |
| Union | A tool is retained if in ANY loaded skill's allowed-tools list — more permissive. | |
| Last-loaded wins | Last-loaded skill's allowed-tools wins — simple but surprising when two skills disagree. | |

**User's choice:** Intersection
**Notes:** Locked now, enforced Phase 17.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Unrestricted = no filter | A skill without allowed-tools imposes NO restriction — intersection over the restricted skills only. | ✓ |
| Any unrestricted cancels filter | Any loaded skill with no allowed-tools → full tool list (all tools pass) — cancels filtering entirely. | |

**User's choice:** Unrestricted = no filter
**Notes:** —

---

## OpenCode's Discretion

- Exact usage-line wording and error string wording
- Exact domain error code integer for skill-not-found (e.g. -32001)
- Env-var name for the loaded-skill token cap
- Per-skill token-count cache record shape in skill_state
- TS-side method naming for skills.load in rpc-client.ts (as long as RPC_METHODS has skills.load)

## Deferred Ideas

- TUI /skill intercept + "Skill loaded" indicator + skill_loaded notification — Phase 16
- allowed-tools enforcement (per-iteration filter projection) — Phase 17
- /skills listing command (AUTH-02, v1.2) — not added to /skill
- Auto-eviction of loaded skills at the cap — rejected; cap breach refuses the load
