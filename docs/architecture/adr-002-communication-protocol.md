# ADR-002: RPC as Primary Communication Protocol for Layer 2

* **Status:** Accepted
* **Date:** 2026-07-23
* **Author:** hswarm-arch
* **Supersedes:** None
* **Superseded by:** None

## Context

ADR-001 establishes a three-layer integration architecture for Pier: Skill (terminal subprocess), Plugin (structured protocol), and Extension (ACP bridge). Layer 1 (terminal) is straightforward — it follows the proven pattern from existing Hermes coding agent skills. But Layer 2 needs a communication protocol choice.

The research documents establish four candidate approaches for Hermes↔Pi communication at Layer 2:

| Approach | Mechanism | Structured? | Streaming? | Bidirectional? |
|----------|-----------|:-----------:|:----------:|:--------------:|
| **Terminal subprocess** | `pi -p` / `pi --mode json` | Partial (JSON) | No | No |
| **MCP** | JSON-RPC over stdio/HTTP | Yes | Limited | Tool-only |
| **ACP** | JSON-RPC over stdio/HTTP | Yes | Yes | Yes |
| **Pi RPC** | JSONL over stdin/stdout | Yes | Yes | Yes |

The competitive landscape research (R.3) recommends ACP as the primary protocol for Hermes↔Pi communication. However, ACP has ecosystem dependencies (emerging standard, immature Hermes adapter) that make it better suited for Layer 3 (Extension) than Layer 2 (Plugin).

Pi ships with a **native RPC protocol** (see R.1, Section 3) that provides structured events, streaming, and bidirectional communication — without any external dependency. It is designed specifically for embedding Pi in external applications, which is exactly what Layer 2 does.

## Decision

**Layer 2 will use Pi's native RPC protocol as its primary communication channel**, with terminal JSON mode as a fallback.

```
Primary:   Hermes → JSONL stdin/stdout → Pi --mode rpc
Fallback:  Hermes → stdout JSON parsing → Pi --mode json
```

### Primary Channel: Pi RPC

Pi's RPC protocol operates over **strict LF-delimited JSONL on stdin/stdout**. The Hermes plugin:

1. Spawns `pi --mode rpc --provider <provider> --model <model>`
2. Sends JSON commands on stdin (one per line)
3. Reads JSON events from stdout (one per line, streaming)
4. Maps events to Hermes tool-call lifecycle hooks

Key protocol capabilities the plugin will use:

| Category | Commands | Purpose |
|----------|----------|---------|
| **Prompting** | `prompt`, `steer`, `follow_up`, `abort` | Task delegation and mid-task steering |
| **State** | `get_state`, `get_messages` | Monitoring and context inspection |
| **Model** | `set_model`, `get_available_models` | Provider/model switching |
| **Compaction** | `compact`, `set_auto_compaction` | Context window management |
| **Bash** | `bash`, `abort_bash` | Direct shell execution tracking |
| **Session** | `get_session_stats`, `fork`, `clone` | Cost tracking and session branching |

Key events the plugin will consume:

| Event | Hermes Mapping |
|-------|---------------|
| `agent_start` / `agent_settled` | Task lifecycle boundaries |
| `turn_start` / `turn_end` | Per-turn progress tracking |
| `message_update` (text_delta) | Streaming output display |
| `tool_execution_start/update/end` | Tool call progress bars |
| `bash_execution_update` | Shell output streaming |
| `compaction_start/end` | Context window alerts |
| `auto_retry_start/end` | Transient error visibility |

### Fallback: JSON Mode

If the RPC process fails (Pi version mismatches `--mode rpc`, RPC connection refused), the plugin falls back to `pi --mode json` which outputs JSON Lines events to stdout without the bidirectional command channel.

**Differences from RPC mode:**
- No commands can be sent (prompt is CLI argument, not a `prompt` command)
- No mid-task steering or abort
- No session management (fork, clone, stats)
- Events are still structured JSON, so parsing is identical

### Why not MCP?

MCP is designed for **tool exposure**, not session management. It provides:
- Tool discovery (`tools/list`)
- Tool invocation (`tools/call`)
- Resource access (`resources/read`)

It does **not** provide:
- Session lifecycle (start, fork, clone, compact)
- Streaming conversation events
- Agent-level steering or follow-up
- Provider auth passthrough

MCP is complementary — Pi *should* expose tools via MCP for interoperability with other agents — but it cannot replace Pi's RPC protocol for Layer 2 orchestration.

### Why not ACP for Layer 2?

ACP is the right protocol for **Layer 3** (Extension), where Hermes and Pi share a full session lifecycle with resource attachment and tool streaming. But for Layer 2:

1. **ACP adds a dependency.** Pi RPC is built into Pi. ACP requires an adapter on both sides.
2. **ACP is emerging.** The Hermes ACP adapter exists as a reference implementation but is not production-hardened. Pi does not ship an ACP client.
3. **ACP over-serves Layer 2.** Layer 2 users need structured events + cancellation, not full IDE session management.

Wait for ACP to mature (and for Pi to potentially adopt an ACP server) before promoting it to the Layer 2 protocol.

## Rationale

### Why Pi RPC over terminal JSON mode?

**Structured events ≠ structured interaction.** JSON mode gives structured *output* but not structured *control*. You can't cancel a task mid-execution, fork a session, or query cost statistics. RPC provides all of these.

**Streaming is a first-class protocol feature.** Terminal JSON mode outputs events, but they arrive after the fact. RPC streams `text_delta`, `tool_execution_update`, and `bash_execution_update` in real time — Hermes can display progress bars, not just final results.

**Cancellation is essential for orchestration.** Hermes needs to abort a task when:
- The user sends a mid-task message (steering)
- A timeout fires
- A tool call exceeds safety bounds
- A downstream task depends on upstream results that changed

Without RPC's `abort` command, the plugin can only kill the process — losing session state, cost data, and partial results.

### Why a fallback at all?

Not every Hermes deployment will have Pi installed. The fallback ensures Layer 2 degrades gracefully to JSON mode, which is better than Layer 1 (unstructured text) even without bidirectional control.

## Consequences

### Positive

* **No external dependencies.** Pi RPC works with any Pi installation — no ACP server, no MCP gateway, no network configuration.
* **Full protocol surface from launch.** 20+ commands, 18 event types, streaming, cancellation, session management — all available immediately.
* **Graceful degradation.** JSON mode fallback provides structured output even without RPC.
* **Co-evolution with Pi.** The RPC protocol is Pi's own API. As Pi adds commands/events, the plugin benefits automatically.

### Negative

* **Protocol coupling.** Layer 2 is tightly coupled to Pi's RPC protocol version. Breaking changes in Pi's protocol require plugin updates.
* **JSONL framing complexity.** The protocol uses strict LF delimiters (not Node's `readline`). Hermes's Python implementation must handle this correctly — splitting on `\n` only, not Unicode line separators.
* **No ecosystem portability.** Pi RPC is Pi-specific. If Hermes wants to integrate with another coding agent that doesn't speak Pi RPC, a different Layer 2 plugin is needed.
* **Pi version requirement.** RPC mode must be supported by the installed Pi version. Older versions only have interactive/print modes.

## Alternatives Considered

### A. Terminal-only with `--mode json` (no RPC)

Use JSON mode as the primary channel, skip RPC entirely.

**Rejected.** Loses cancellation, streaming, session management, and model cycling. JSON mode is a good fallback but an impoverished primary protocol.

### B. ACP as Layer 2 primary protocol

Use ACP for Layer 2, reserve Pi RPC for Layer 3.

**Rejected.** ACP is the future of orchestrator↔agent communication, but it's not ready for Layer 2. Pi doesn't ship an ACP server. Hermes's ACP adapter is a reference, not a product. Shipping Layer 2 on ACP in 2026 would mean building the ACP ecosystem ourselves — that's a Layer 3 scope, not Layer 2.

### C. No Layer 2 — skip directly to Layer 3 (ACP)

Build only Layers 1 and 3, skip the middle.

**Rejected.** Layer 3 is the most complex layer (ACP bridge + TypeScript extensions + auth passthrough). It shouldn't be the only structured integration option. Layer 2 provides 80% of the value (structured events, streaming, cancellation) at 40% of the cost.

## References

* [R.1] docs/research/pi-architecture-deep-dive.md, Section 3 — Pi RPC Protocol specification
* [R.2] docs/research/hermes-coding-agent-patterns.md, Pi-Specific Opportunities — RPC as unique differentiator
* [R.3] docs/research/competitive-integration-landscape.md, Section 7-8 — Protocol landscape and ACP recommendation
* [ADR-001] docs/architecture/adr-001-integration-approach.md — Three-layer architecture
