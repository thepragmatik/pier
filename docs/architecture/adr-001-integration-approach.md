# ADR-001: Three-Layer Composable Integration Approach

* **Status:** Accepted
* **Date:** 2026-07-23
* **Author:** hswarm-arch
* **Supersedes:** None
* **Superseded by:** None

## Context

Hermes Agent currently integrates with external coding agents through terminal-based subprocess delegation — the `codex`, `claude-code`, and `opencode` skills all spawn the coding agent as a child process with `pty=true`, monitor it via `process(action="poll")`, and parse unstructured text output. This works but imposes three limitations:

1. **No structured output.** Hermes parses unstructured terminal text for results, error codes, and completion signals.
2. **No bidirectional protocol.** Steering messages mid-task require terminal keystroke injection (`process(action="submit")`).
3. **No typed contract.** Each agent has its own CLI flags, error formats, and output conventions.

Pi (`earendil-works/pi`) offers a richer integration surface: four CLI modes (interactive, print, JSON, RPC), a TypeScript extension system, a structured RPC protocol with 20+ commands and 18 event types, and an Agent Skills-compatible skill system.

The research documents (R.1 Pi deep-dive, R.2 Hermes patterns, R.3 competitive landscape) establish that no protocol standard exists for orchestrator↔coding-agent communication. Current orchestrators (LangGraph, Claude Code session managers, bernstein, h5i) each invent custom subprocess wiring. This is both a validation that the need exists and a sign that a protocol-based approach would be differentiated.

The question is: **what integration architecture lets users adopt Pier at the depth they need, without forcing deep integration before it makes sense?**

## Decision

Pier will adopt a **three-layer composable integration architecture**:

```
Layer 1: Skill       →  Pi as terminal subprocess (print mode)
Layer 2: Plugin      →  Pi via RPC protocol (structured events)
Layer 3: Extension   →  Pi via ACP bridge + TypeScript extensions
```

Each layer is **independently usable** and builds on the one below it. Users choose their integration depth.

### Layer 1: Skill (Terminal Subprocess)

A Hermes skill (`pier`) that delegates to Pi via its `-p` (print) mode:

```
Hermes → terminal(pi -p "<prompt>") → stdout → parsed response
```

**Capabilities:** Basic delegation. Prompt Pi, get text back. Works like the existing `codex`, `claude-code`, and `opencode` skills.

**Who uses it:** Users who just want `pi -p "fix this bug"` without configuring anything else. Everyone evaluating Pier for the first time.

**Implementation:** Follows the proven pattern from R.2 research. Hermes skill YAML frontmatter + markdown body with `terminal()` calls. ~200 lines.

### Layer 2: Plugin (RPC Protocol)

A Hermes plugin that speaks Pi's RPC protocol natively:

```
Hermes → JSONL stdin/stdout → Pi (--mode rpc) → structured events → Hermes
```

**Capabilities:** Structured event parsing (18 event types), streaming progress (token deltas, tool execution updates), cancellation (`abort` command), session management (fork, clone, compact), model/thinking cycling, bash execution tracking, cost monitoring (`get_session_stats`).

**Who uses it:** Users who want rich integration — progress bars on tool execution, cancel mid-task, track token costs per task, fork sessions for parallel exploration.

**Implementation:** Implements the full RPC protocol spec from R.1 (Section 3). JSONL framing with strict LF delimiters. Maps Pi events to Hermes tool-call lifecycle hooks. ~800 lines.

### Layer 3: Extension (ACP Bridge + TypeScript Extensions)

Full ACP (Agent Communication Protocol) bridge between Hermes and Pi, combined with Pi TypeScript extensions for Hermes-specific workflows:

```
Hermes → ACP (JSON-RPC/stdio) → Pi ACP Adapter → Pi TypeScript Extensions
```

**Capabilities:** Session lifecycle over ACP, tool call streaming, resource attachment, Pi extensions that register Hermes-specific tools, cross-provider auth passthrough, workspace management, permission gating.

**Who uses it:** Teams building custom integration pipelines. Projects that need Hermes↔Pi to share authentication, tools, and workspaces seamlessly.

**Implementation:** A Hermes-side ACP client (or proxy) that maps Hermes orchestration commands into ACP session operations on Pi. Pi-side TypeScript extensions that register Hermes-native tools (e.g., `hermes_memory_search`, `hermes_skill_call`). ~2000 lines.

## Rationale

### Why three layers instead of one monolithic integration?

1. **Adoption gradient.** Users start at Layer 1 (no config, just install the skill) and upgrade when they need more. Monolithic integration forces everyone to set up RPC/ACP before getting any value.

2. **Independent usefulness.** Layer 1 already delivers value — Pi running tasks that Hermes delegates. It doesn't need Layers 2 or 3 to work.

3. **Progressive investment.** Each layer's cost (implementation, maintenance, documentation) is justified by its own user segment. Layer 3 is expensive (~2000 lines, ACP dependency, Pi extensions) but unnecessary for most users.

4. **Separation of concerns.** Protocol parsing (Layer 2) and orchestration semantics (Layer 3) are different problems. Mixing them creates tight coupling — a protocol change at Layer 2 shouldn't break orchestration logic at Layer 3.

### Why not follow the LangGraph sub-agent node pattern?

LangGraph's "orchestrator graph → delegate node → verify and merge" pattern is the right reference architecture for deterministic orchestration. But it's a **pattern**, not an integration surface. Pier implements this pattern across all three layers — what changes is *how* the delegation node communicates with the coding agent (terminal, RPC, or ACP).

### Why not use MCP as the sole protocol?

MCP (Model Context Protocol) is well-suited for **tool exposure** — Pi can expose its tools as MCP tools, and Hermes can discover them via `tools/mcp_tool.py`. But MCP does not provide:
- Full session lifecycle management (no fork, clone, compact)
- Streaming conversation events
- Steering/follow-up semantics
- Provider auth passthrough

These are essential for orchestrator↔agent communication but outside MCP's scope. MCP is complementary (used alongside ACP in Layer 3), not a replacement.

## Consequences

### Positive

* **Low barrier to entry.** Layer 1 works immediately with no configuration.
* **Upgrade path.** Users move from Layer 1→2→3 as their needs grow, without rebuilding.
* **Testable in isolation.** Each layer can be developed, tested, and dogfooded independently.
* **Aligned with Pi's design.** Pi's CLI already has the print/RPC modes; the layers map directly onto these modes.

### Negative

* **More initial work.** Three integrations instead of one. Each layer needs documentation, tests, and examples.
* **API surface to maintain.** Layer 2 depends on Pi's RPC protocol stability. If the protocol changes, the plugin must be updated.
* **ACP dependency for Layer 3.** The ACP ecosystem is still emerging (JetBrains/Zed). Hermes's ACP adapter exists as a reference but is not yet production-hardened.
* **User confusion risk.** Without clear documentation, users may not understand which layer to use. We need a clear decision tree: "If you want X, use Layer Y."

## Alternatives Considered

### A. Monolithic ACP-only integration

Build one deep integration using ACP and skip the simpler layers.

**Rejected.** Forces every user through the complexity of ACP setup. Most users only need `pi -p "fix this"`, not a full protocol session. Loses the adoption gradient.

### B. Terminal-only (like existing Hermes skills)

Use only Layer 1, mirroring the codex/claude-code/opencode pattern.

**Rejected.** Ignores Pi's unique differentiators — RPC mode, structured events, streaming. Layer 1 alone doesn't justify building a Pier skill; there are already three coding agent skills in Hermes.

### C. RPC as the only surface (skip Layer 1 and 3)

Build only Layer 2.

**Rejected.** Layer 2 requires Pi installation and `--mode rpc` knowledge. Users evaluating Pier need a zero-config entry point (Layer 1). And teams wanting deep orchestration need ACP session lifecycle (Layer 3).

## References

* [R.1] docs/research/pi-architecture-deep-dive.md — Pi architecture, RPC protocol spec, extension system
* [R.2] docs/research/hermes-coding-agent-patterns.md — Hermes skill patterns, gap analysis, Pi opportunities
* [R.3] docs/research/competitive-integration-landscape.md — Protocol landscape, ACP/MCP/A2A analysis
* [Agent Skills standard](https://agentskills.io)
* [ACP specification](https://agentclientprotocol.com/)
* [MCP specification](https://modelcontextprotocol.io/)
