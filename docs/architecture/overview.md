# Pier Architecture Overview

> **Pier:** Hermes Agent ↔ Pi coding-agent integration. A three-layer composable bridge that lets Hermes delegate coding tasks to Pi at the depth you need.

## What Is Pier?

Pier connects [Hermes Agent](https://github.com/NousResearch/hermes-agent) (an autonomous AI agent framework) to [Pi](https://github.com/earendil-works/pi) (a TypeScript-native coding agent with RPC protocol and extension system).

Hermes currently delegates coding work to external agents (Codex, Claude Code, OpenCode) via terminal subprocesses. This works but limits integration to unstructured text parsing, one-shot commands, and ad-hoc error handling.

Pi offers a richer integration surface — four CLI modes, a structured RPC protocol with 20+ commands and 18 event types, TypeScript extensions, and an Agent Skills-compatible skill system. Pier takes advantage of all of these through a layered architecture that lets users adopt integration depth incrementally.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Hermes Agent                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      Pier Integration                     │   │
│  │                                                           │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────┐  │   │
│  │  │  Layer 3        │  │  Layer 2        │  │ Layer 1  │  │   │
│  │  │  Extension      │  │  Plugin         │  │ Skill    │  │   │
│  │  │                 │  │                 │  │          │  │   │
│  │  │  ACP Bridge +   │  │  RPC Protocol   │  │ Terminal │  │   │
│  │  │  TypeScript     │◄─┤  (JSONL/stdio)  │◄─┤ Sub-     │  │   │
│  │  │  Extensions     │  │                 │  │ process  │  │   │
│  │  └────────┬────────┘  └────────┬────────┘  └─────┬────┘  │   │
│  │           │                    │                  │       │   │
│  └───────────┼────────────────────┼──────────────────┼───────┘   │
│              │                    │                  │           │
└──────────────┼────────────────────┼──────────────────┼───────────┘
               │                    │                  │
               ▼                    ▼                  ▼
        ┌──────────────────────────────────────────────────┐
        │                    Pi Agent                       │
        │                                                   │
        │  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
        │  │  ACP     │  │  RPC     │  │  Print Mode   │   │
        │  │  Server  │  │  Mode    │  │  (-p / --mode │   │
        │  │          │  │          │  │   json)       │   │
        │  └──────────┘  └──────────┘  └───────────────┘   │
        │                                                   │
        │  ┌──────────────────────────────────────────┐     │
        │  │        TypeScript Extension System        │     │
        │  │  tools | commands | hooks | providers     │     │
        │  └──────────────────────────────────────────┘     │
        │                                                   │
        │  ┌──────────────────────────────────────────┐     │
        │  │        Agent Skills System                │     │
        │  │  SKILL.md | scripts | references          │     │
        │  └──────────────────────────────────────────┘     │
        └──────────────────────────────────────────────────┘
```

### Layer 1: Skill (Terminal Subprocess)

The entry point. A Hermes skill that delegates to Pi via its print mode (`pi -p`).

```
Hermes → terminal("pi -p '<prompt>'") → stdout → parsed response
```

- **Install:** One Hermes skill file (~200 lines)
- **Protocol:** Unstructured text output (or `--mode json` for JSON Lines)
- **Who uses it:** Everyone evaluating Pier. Users who just need basic delegation.
- **When to upgrade:** When you need progress streaming, task cancellation, or cost tracking.

### Layer 2: Plugin (RPC Protocol)

Structured integration via Pi's native RPC protocol.

```
Hermes → JSONL stdin/stdout → Pi --mode rpc → structured events → Hermes
```

- **Install:** Hermes plugin (~800 lines) + Pi installation
- **Protocol:** JSONL-framed commands and events, streaming, bidirectional
- **Key capabilities:** Progress streaming, task cancellation, session forking, cost tracking, model cycling
- **Who uses it:** Users who want rich integration without ACP complexity.
- **When to upgrade:** When you need cross-agent auth passthrough or custom TypeScript extensions.

### Layer 3: Extension (ACP Bridge + TypeScript Extensions)

Deep integration via ACP protocol and Pi TypeScript extensions.

```
Hermes → ACP (JSON-RPC/stdio) → Pi ACP Adapter → Pi TypeScript Extensions
```

- **Install:** Hermes ACP client + Pi ACP adapter + Pi TypeScript extension package
- **Protocol:** ACP (Agent Communication Protocol) with resource attachment and tool streaming
- **Key capabilities:** Full session lifecycle, Hermes-native tools in Pi, cross-provider auth, workspace management
- **Who uses it:** Teams building custom integration pipelines.

## Communication Flow

### Task Delegation (Layer 2 example)

```
Hermes                      Pi (RPC mode)
  │                              │
  │  {"type":"prompt",           │
  │   "text":"Fix the bug in     │
  │   src/parser.ts",            │
  │   "id":"req-1"}              │
  │─────────────────────────────►│
  │                              │  Agent starts processing
  │  {"type":"agent_start",      │
  │   "id":"req-1"}              │
  │◄─────────────────────────────│
  │                              │
  │  {"type":"turn_start",       │
  │   "id":"req-1"}              │
  │◄─────────────────────────────│
  │                              │  LLM generates tool calls
  │  {"type":"tool_execution_    │
  │   start","tool":"read",      │
  │   "id":"req-1"}              │
  │◄─────────────────────────────│
  │                              │  Tool executes
  │  {"type":"tool_execution_    │
  │   end","tool":"read",        │
  │   "id":"req-1"}              │
  │◄─────────────────────────────│
  │                              │
  │  {"type":"message_update",   │
  │   "delta":"Fixed the bug",   │
  │   "id":"req-1"}              │
  │◄─────────────────────────────│
  │                              │
  │  {"type":"agent_settled",    │
  │   "id":"req-1"}              │
  │◄─────────────────────────────│
  │                              │
  │  {"type":"get_session_stats",│
  │   "id":"req-2"}              │
  │─────────────────────────────►│
  │  {"type":"session_stats",    │
  │   "tokens":15234,            │
  │   "cost_usd":0.23,           │
  │   "id":"req-2"}              │
  │◄─────────────────────────────│
```

### Mid-Task Cancellation

```
Hermes                      Pi (RPC mode)
  │                              │
  │  (task running...)           │
  │                              │  Tool executing
  │  {"type":"abort",            │
  │   "id":"req-3"}              │
  │─────────────────────────────►│
  │                              │  Cancels current operation
  │  {"type":"agent_settled",    │
  │   "reason":"aborted",        │
  │   "id":"req-3"}              │
  │◄─────────────────────────────│
```

### Session Forking (parallel exploration)

```
Hermes                      Pi (RPC mode)
  │                              │
  │  {"type":"fork",             │
  │   "entryId":"msg-42",        │
  │   "id":"req-4"}              │
  │─────────────────────────────►│
  │  {"type":"fork_created",     │
  │   "sessionId":"sess-xyz",    │
  │   "id":"req-4"}              │
  │◄─────────────────────────────│
  │                              │
  │  {"type":"prompt",           │
  │   "text":"Try approach B",   │  (runs in forked session)
  │   "id":"req-5"}              │
  │─────────────────────────────►│
```

## Key Design Decisions

| Decision | ADR | Summary |
|----------|-----|---------|
| Three-layer composable architecture | [ADR-001](adr-001-integration-approach.md) | Skill → Plugin → Extension, each independently usable |
| Pi RPC as Layer 2 primary protocol | [ADR-002](adr-002-communication-protocol.md) | JSONL-framed protocol with JSON mode fallback |
| Phased dogfooding after Layer 2 stable | [ADR-003](adr-003-dogfooding-strategy.md) | Side-by-side → shadow → primary → full switch over 9 weeks |

## Relationship to Existing Hermes Skills

Pier does not replace the existing coding agent skills — it adds a new one. The existing skills (codex, claude-code, opencode) remain available:

| Skill | Agent | Protocol | Status with Pier |
|-------|-------|----------|------------------|
| `codex` | OpenAI Codex | Terminal subprocess | Unchanged |
| `claude-code` | Anthropic Claude Code | Terminal subprocess | Unchanged |
| `opencode` | OpenCode | Terminal subprocess | Unchanged |
| `pier` | Pi | Terminal → RPC → ACP | New, layered |

This preserves the ecosystem diversity noted in R.2: different tasks benefit from different agents, and keeping all skills available lets Hermes route tasks to the best agent for each job.

## Dogfooding Status

Pier is currently in development. Dogfooding will follow the phased rollout defined in [ADR-003](adr-003-dogfooding-strategy.md):

| Phase | Timeline | Description |
|-------|----------|-------------|
| Phase 1 | Weeks 1-2 | Layer 1 side-by-side with existing skills |
| Phase 2 | Weeks 3-4 | Layer 2 shadow mode |
| Phase 3 | Weeks 5-8 | Layer 2 primary with fallback |
| Phase 4 | Week 9+ | Full switch |

## Research Foundation

Pier's architecture is grounded in three research documents:

- **[R.1] Pi Architecture Deep-Dive** (`docs/research/pi-architecture-deep-dive.md`): 795-line analysis of Pi's monorepo structure, CLI modes, RPC protocol (20 commands, 18 event types), extension system (15+ lifecycle hooks), tool system (7 built-in tools), skill system (Agent Skills standard), configuration model (two-layer JSON merge), session management (JSONL tree with branching), authentication (4-tier resolution), and security model (no sandbox, containerization recommended).

- **[R.2] Hermes Coding-Agent Patterns** (`docs/research/hermes-coding-agent-patterns.md`): 383-line analysis of three existing Hermes coding-agent skills (codex, claude-code, opencode), identifying common patterns (terminal delegation, error recovery, workdir isolation), distinguishing features (Claude Code's hooks/agents/skills, OpenCode's provider agnosticism), Pi-specific opportunities (RPC mode as unique differentiator, minimal system prompt, TypeScript extensions), and three-tier recommendations.

- **[R.3] Competitive Integration Landscape** (`docs/research/competitive-integration-landscape.md`): 460-line survey of orchestrator↔coding-agent integration patterns across LangChain/LangGraph, Open Interpreter, Claude Code MCP, and the ACP/MCP/A2A/ANP protocol landscape. Key finding: no protocol standard exists for orchestrator↔coding-agent communication — ACP is the best fit for Layer 3, and MCP for tool exposure.

## Diagram

The architecture diagram is available as:
- Excalidraw: `docs/architecture/pier-architecture.excalidraw` (open at [excalidraw.com](https://excalidraw.com))
