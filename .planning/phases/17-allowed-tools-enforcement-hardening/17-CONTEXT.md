# Phase 17: allowed-tools Enforcement & Hardening - Context

**Gathered:** 2026-08-04
**Status:** CANCELLED — phase skipped by user decision; milestone to close without enforcement

> **IMPORTANT:** This phase is **cancelled** by explicit user decision during context
> gathering (2026-08-04). Do NOT plan, research, or execute Phase 17's original scope.
> The allowed-tools enforcement (CAP-02 / CAP-04) is deferred to a future/end milestone.
> See `<deferred>` below for what this means and what already-shipped code stays.

<domain>
## Phase Boundary

Original scope (now cancelled): enforce `allowed-tools` while a skill is loaded — a pure
per-iteration projection of the tool list passed to the LLM at the `list_tools()` boundary
(registry never mutated), `read_skill` always retained (CAP-03), intersection semantics
across multiple loaded skills (CAP-04), dispatch-side rejection in `registry.call_tool`,
and a full milestone E2E verification.

**User decision:** This enforcement is **not wanted now**. It is deferred to the end
milestone. Phase 17 as planned is skipped, and the v1.1 Skills milestone should be closed
without it. No implementation decisions below — the phase is cancelled.

</domain>

<decisions>
## Implementation Decisions

### Phase disposition (cancellation decision)
- **D-01:** Phase 17 is **cancelled**. No allowed-tools enforcement wiring, no dispatch-side
  rejection in `registry.call_tool`, no filter E2E verification script, no hardening pass.
- **D-02:** The already-shipped pure functions stay as-is and un-wired: `skills/filter.py`
  (`retain_read_skills`, `intersect_allowed_tools`) and their unit tests
  (`tests/test_skills_filter.py`, `tests/test_skills_provider.py`) remain — they are valid
  contracts, just not enforced. No rework or deletion.
- **D-03:** CAP-02 (filtering) and CAP-04 (intersection) remain **Pending** requirements,
  deferred to a future/end milestone. They are NOT delivered by v1.1.
- **D-04:** `skill_state["loaded"]` record stays `{name, dir, tokens}` — no `allowed-tools`
  field is added. The Phase 15 D-13/D-14 semantics decision stands as documentation but is
  not implemented now.

### OpenCode's Discretion
- None — the phase is cancelled; there is nothing left to discretion.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone & requirements (the deferral context)
- `.planning/REQUIREMENTS.md` §CAP-02, §CAP-04 — the two requirements deferred out of v1.1;
  still marked Pending until a future milestone re-maps them
- `.planning/MILESTONE-CONTEXT.md` — D-16 (allowed-tools enforcement) is the milestone-level
  intent now deferred; read to understand why the phase existed and what "end milestone"
  means for future scoping
- `.planning/ROADMAP.md` §Phase 17 — the cancelled phase definition (goal, success criteria,
  plan breakdown) for the audit trail

### Prior phase context (locked decisions being deferred, not re-litigated)
- `.planning/phases/15-session-behavior-skill-command/15-CONTEXT.md` — D-13/D-14: intersection
  semantics + no-field-unrestricted, decided in Phase 15 but only to be enforced later
- `.planning/phases/14-read-skill-provider-e2e/14-CONTEXT.md` — D-09: `skill_state["loaded"]`
  record shape the filter would have read
- `.planning/phases/12-skills-discovery-manifest/12-CONTEXT.md` — D-15/D-16: allowed-tools
  parsing + shape validation (shipped, stays)

### Existing contract code (already shipped — reference for the future milestone)
- `skills/filter.py` — `retain_read_skills()` (CAP-03 retention) + `intersect_allowed_tools()`
  (CAP-04 intersection); pure, tested, un-wired. The future enforcement wires these.
- `tests/test_skills_filter.py` — the CAP-04 intersection contract tests (passing)
- `tests/test_skills_provider.py` — the CAP-03 retention contract tests (passing)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (for the future milestone)
- `skills/filter.py` — the two pure filter functions; the enforcement layer only needs to call
  them at the `list_tools()` boundary
- `agent/core.py:108` — `tools = self._registry.list_tools()` — the per-iteration seam where a
  projection would apply
- `tool/registry.py:68` — `list_tools()` returns the full union (local + MCP + `__skills__`
  provider); `call_tool()` (line 85) is where dispatch-side rejection would land
- `harness/runtime.py:179` `load_skill()` — where `skill_state["loaded"]` records are written
  (would gain `allowed_tools` if the future milestone caches it at load time)

### Established Patterns
- Pure-function contract first, wiring later: `skills/filter.py` follows the same
  contract-before-enforcement pattern used in Phases 14/15
- Session-scoped state via `skill_state` (non-serialized, resets on `/new`) — the filter's
  natural data source when it is finally wired

### Integration Points (currently dormant)
- `agent/core.py` `run()` loop — filter projection point (not wired)
- `tool/registry.py` `call_tool()` — rejection point (not wired)
- `skills/filter.py` — the functions to invoke (exist, unused by runtime)

</code_context>

<specifics>
## Specific Ideas

- The user clarified during discussion that tool filtering masks the WHOLE union passed to the
  LLM (MCP + local + skill tools, via `list_tools()`), which confirmed the feature's real
  scope — and then decided that sandboxing isn't needed for the current milestone.
- The milestone should be closed via `/gsd-complete-milestone`; a future/end milestone
  re-scopes CAP-02/CAP-04 when tool sandboxing becomes necessary.

</specifics>

<deferred>
## Deferred Ideas

- **allowed-tools enforcement (CAP-02)** — per-iteration filter projection at the
  `list_tools()` boundary — deferred to end/future milestone. The pure functions in
  `skills/filter.py` are the ready-made implementation.
- **Intersection semantics enforcement (CAP-04)** — multi-skill `allowed-tools` intersection —
  deferred to the same future milestone. Semantics already documented in Phase 15 D-13/D-14.
- **Dispatch-side rejection in `registry.call_tool`** — a call to a filtered-out tool refused
  at the registry — deferred with enforcement.
- **Milestone-wide E2E verification script + hardening pass** (remaining traversal vectors,
  filter edge cases) — the ROADMAP plan 17-03 — not needed now; if a milestone E2E is still
  wanted, it belongs with the milestone close rather than a Phase 17 plan.
- **`allowed-tools` caching in `skill_state["loaded"]`** — rejected for now (D-04); only
  relevant if/when the filter is wired.

---

*Phase: 17-allowed-tools-enforcement-hardening*
*Context gathered: 2026-08-04*
