# ADR-003: Dogfooding Strategy

* **Status:** Accepted
* **Date:** 2026-07-23
* **Author:** hswarm-arch
* **Supersedes:** None
* **Superseded by:** None

## Context

Pier (Hermes↔Pi integration) is being built to replace the current terminal-based coding agent delegation pattern in Hermes (codex, claude-code, opencode skills). The user wants to battle-test Pier in their local Hermes installation — "dogfooding" — to discover real-world issues before broader release.

Dogfooding an orchestrator↔coding-agent integration carries unique risks:
- Pier delegates file writes, shell commands, and git operations to a subprocess. A bug could corrupt the working directory.
- Pi's RPC protocol is a structured channel — protocol desync could leave orphaned processes or inconsistent session state.
- Unlike terminal-based delegation (where output is visible text), RPC events are opaque JSON — debugging a failed task is harder.

The question is: **when is it safe to switch from terminal-mode delegation (claude-code/codex/opencode skills) to Pier, and what is the rollback path?**

## Decision

Pier will be dogfooded **after Layer 2 (RPC Plugin) reaches stable quality**, with the following gating criteria and rollback guarantees.

### Gating Criteria for Dogfooding

| Criterion | Threshold | Verification |
|-----------|-----------|-------------|
| **Task completion rate** | ≥ 95% of terminal-mode baseline | Run 50 identical tasks through both Pier and terminal mode; compare completion rates |
| **Protocol stability** | Zero RPC desyncs in stress test | Run 100 concurrent RPC sessions with rapid abort/steer/compact cycles |
| **Error recovery** | All 6 known failure modes handled | Inject each failure mode (timeout, crash, model error, tool error, auth error, compaction failure) and verify graceful degradation |
| **Cost tracking accuracy** | ±5% of Pi's own cost reporting | Compare `get_session_stats` totals against provider billing for 20 sessions |
| **Session isolation** | No cross-session file corruption | 10 concurrent sessions each writing to different files; verify no collisions |

### Dogfooding Phases

```
Phase 1: Side-by-side (weeks 1-2)
  ├─ Layer 1 (Skill) runs alongside existing coding agent skills
  ├─ Hermes delegates to both: Pier for simple tasks, existing skills for complex ones
  ├─ Output comparison: same task → both agents → compare results
  └─ Gate: ≥ 90% task completion rate on simple tasks

Phase 2: Shadow mode (weeks 3-4)
  ├─ Layer 2 (Plugin) runs in parallel with terminal mode
  ├─ Hermes delegates to both; RPC output is logged but not acted on
  ├─ Protocol desync detection: compare RPC events vs terminal output for same prompts
  └─ Gate: Zero protocol desyncs in 200 sessions

Phase 3: Primary with fallback (weeks 5-8)
  ├─ Layer 2 becomes primary; terminal mode is fallback on failure
  ├─ Layer 3 (Extension) development begins
  ├─ Real user tasks flow through Pier by default
  └─ Gate: < 5% fallback rate, zero data-loss events

Phase 4: Full switch (week 9+)
  ├─ Layer 2 is sole delegation path for Pi-compatible tasks
  ├─ Existing skills (codex, claude-code, opencode) remain available as secondary agents
  ├─ Layer 3 enters its own dogfooding cycle
  └─ Gate: Two weeks with zero fallback triggers
```

### Rollback Path

At any phase, the user can revert to terminal-mode delegation:

1. **Immediate rollback.** Disable the Pier skill/plugin in Hermes config. Existing coding agent skills (codex, claude-code, opencode) are unaffected — they were never removed, just superseded.

2. **Session recovery.** Pi RPC sessions are JSONL files in `~/.pi/agent/sessions/`. If a session was interrupted during dogfooding, it can be resumed with `pi -c` (continue) or `pi -r <session-id>`. Hermes does not depend on Pi session state for its own operation.

3. **Workspace integrity.** Pier operates in git worktrees (ADR-001, Layer 2). If a worktree is corrupted, delete it and create a fresh one. The main repository is never directly modified.

4. **No data migration.** Neither Layer 1 nor Layer 2 modifies Hermes's internal state, session database, or memory. Rollback is a configuration change, not a data migration.

### Success Criteria for Dogfooding Completion

| Metric | Target |
|--------|--------|
| Tasks completed via Pier | ≥ 200 |
| Protocol desync events | 0 |
| Data-loss events (corrupted workspace, lost output) | 0 |
| Rollback events triggered | ≤ 5 (all resolved within Phase 3) |
| User-reported issues requiring code changes | ≤ 3 |
| Time from bug report to fix deployed | ≤ 24 hours |

## Rationale

### Why dogfood after Layer 2, not Layer 1?

Layer 1 (terminal subprocess) is functionally identical to existing Hermes coding agent skills. Dogfooding it would validate that Pi works as a subprocess — something already proven by Pi's own test suite and the R.1 deep-dive.

Layer 2 introduces the novel integration pattern: RPC protocol, structured events, streaming, cancellation, session management. **This is where the unknown risks live.** Dogfooding should focus on what's new, not what's proven.

### Why phased rollout instead of immediate switch?

1. **Failure modes multiply at scale.** A protocol parsing bug that is harmless on 10 sessions might corrupt 100 sessions when deployed. Phased rollout catches scaling issues before they affect real work.

2. **Comparison data is gold.** Running Pier and terminal mode side-by-side on identical tasks generates a controlled dataset for quality comparison. "Is Pier better?" becomes an empirical question, not a subjective one.

3. **Trust develops gradually.** The user needs to see Pier working reliably on simple tasks before trusting it with complex, long-running work. Phased rollout builds this trust incrementally.

### Why keep existing skills available even after full switch?

The existing coding agent skills (codex, claude-code, opencode) serve as **reference implementations** and **escape hatches**:

- **Reference:** When Pier behaves unexpectedly, running the same task through an existing skill isolates whether the issue is Pi-specific or infrastructure-wide.
- **Escape hatch:** If Pi has a regression (e.g., a new Pi release breaks RPC), the existing skills keep Hermes functional while the regression is fixed.
- **Ecosystem diversity:** Different tasks benefit from different agents. Pi may excel at some tasks while Claude Code excels at others. Keeping all skills available lets Hermes route tasks to the best agent.

## Consequences

### Positive

* **Safe experimentation.** Side-by-side and shadow modes let the user observe Pier's behavior without risking real work.
* **Measurable quality gates.** Each phase has clear, quantitative thresholds — no subjective "feels stable enough."
* **Zero-risk rollback.** Disabling Pier does not affect any other Hermes skill or configuration.
* **Benchmark dataset.** Side-by-side comparison generates data for evaluating Pier's quality against terminal-mode delegation.

### Negative

* **Schedule dependency.** Full dogfooding completion takes ~9 weeks, tied to Layer 2 quality. If Layer 2 has implementation delays, dogfooding is delayed.
* **Dual maintenance during transition.** During Phases 1-3, both Pier and terminal-mode delegation paths must be maintained and kept consistent.
* **Comparison overhead.** Running every task twice (Phases 1-2) doubles API costs and wall-clock time during those phases.
* **Pi version coupling.** Dogfooding validates a specific Pi version. Pi releases during dogfooding may require re-validation.

## Alternatives Considered

### A. Immediate switch (no dogfooding)

Build Pier, deploy it, fix bugs as they appear in production.

**Rejected.** Pi's RPC protocol is a new integration surface with no operational history. Bugs found in production could corrupt workspaces, lose task output, or require complex session recovery — risks that dogfooding is designed to catch.

### B. Dogfood after Layer 1 only

Start using Pier as soon as the terminal-mode skill works, iterate from there.

**Rejected.** Layer 1 is essentially a renamed codex/claude-code skill that launches `pi -p` instead of `claude -p`. It doesn't exercise the novel parts of the architecture (RPC, streaming, cancellation). Dogfooding Layer 1 would give a false sense of security about Layer 2.

### C. Dogfood Layer 3 first

Build the full ACP bridge + TypeScript extensions, dogfood the complete system at once.

**Rejected.** Layer 3 is the most complex layer with the most dependencies (ACP ecosystem, Pi extensions). Dogfooding it first means debugging multiple novel systems simultaneously — protocol issues, extension bugs, and orchestration logic all intermixed. Layer-by-layer dogfooding isolates each novel component.

## References

* [ADR-001] docs/architecture/adr-001-integration-approach.md — Three-layer architecture
* [ADR-002] docs/architecture/adr-002-communication-protocol.md — RPC protocol decision
* [R.1] docs/research/pi-architecture-deep-dive.md, Section 3 — RPC protocol specification
* [R.2] docs/research/hermes-coding-agent-patterns.md — Existing skill patterns and error handling
