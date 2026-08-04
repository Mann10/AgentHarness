# Phase 17: allowed-tools Enforcement & Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-04
**Phase:** 17-allowed-tools-enforcement-hardening
**Areas discussed:** Phase disposition (cancellation decision)

---

## Phase Disposition

The discussion did not follow the standard gray-area interview: the user immediately
challenged whether allowed-tools enforcement is needed at all, which redirected the session
into a scope/roadmap decision before any implementation gray areas (data source, rejection
UX, matching, E2E) were reached.

### Initial gray areas presented (not discussed in depth)
The following were offered for discussion but superseded by the cancellation decision:

| Area | Options presented |
|------|-------------------|
| Filter data source | Cache allowed-tools in `skill_state["loaded"]` at load / Re-query SkillStore per iteration / Passed in from the Agent loop |
| Blocked-call rejection | Raise ValueError like unknown tools / structured ToolResult / name the restricting skill |
| allowed-tools matching | Exact-match / case-insensitive on win32 / warn on unregistered names |
| E2E + hardening scope | Automated pytest script / human TUI checkpoint / traversal-vector hardening coverage |

### User's choice (free-text progression)
1. First response to "which areas to discuss": *"what we are discussing here?? we don't
   need a tool filtering for skills. It's fine as it is"* — challenged the need for the
   feature.
2. Asked to clarify whether this meant keep/drop/trim: *"firstly tell me are we filtering
   the tools from mcp server i.e mcp_servers.json?? and local tools"* — asked what the
   filter actually masks.
3. After confirming the filter masks the whole `list_tools()` union (MCP + local + skill
   tools): selected **"Keep filtering — discuss HOW"**.
4. On the filter data-source question: *"I dont need to enforce skills for now we will
   leave it for the end milestone."* — decided to defer enforcement.
5. On what Phase 17 should deliver: selected **"Skip Phase 17, close milestone"**.

**Final outcome:** Phase 17 cancelled. Enforcement (CAP-02/CAP-04) deferred to a
future/end milestone. v1.1 milestone to be closed without it. Existing pure functions in
`skills/filter.py` stay un-wired.

---

## OpenCode's Discretion

- None — the phase is cancelled and the user made the decisive call on every fork.

## Deferred Ideas

- CAP-02 allowed-tools enforcement (per-iteration filter projection) — end milestone
- CAP-04 intersection semantics enforcement — end milestone
- Dispatch-side rejection in `registry.call_tool` — with enforcement
- Milestone E2E verification script + hardening pass (ROADMAP 17-03) — milestone close scope
- `allowed-tools` caching in `skill_state["loaded"]` — only relevant when the filter is wired
