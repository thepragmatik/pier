# Architecture

Pier is a three-layer composable bridge between Hermes Agent and Pi. Each layer builds
on the one below it, letting users adopt integration depth incrementally.

## High-Level Architecture

For the full architecture overview, see the [Architecture Overview](../architecture/overview.md)
with detailed component diagrams.

## Three Layers

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
└──────────────┼────────────────────┼──────────────────┼───────────┘
               │                    │                  │
               ▼                    ▼                  ▼
         ┌──────────┐        ┌──────────┐       ┌──────────┐
         │  ACP     │        │  RPC     │       │  Print   │
         │  Server  │        │  Mode    │       │  Mode    │
         └──────────┘        └──────────┘       └──────────┘
```

### Layer 1: Skill (Terminal Subprocess)

- Wraps Pi in a terminal subprocess, exactly like existing coding-agent skills
- Hermes invokes `pi -p "<task>"`, captures stdout/stderr, parses the result
- No custom protocol — works out of the box with any Hermes install
- Best for: quick adoption, simple one-shot delegations

### Layer 2: Plugin (RPC Protocol)

- Communicates with Pi over its JSONL-based RPC protocol via stdio
- Hermes sends typed commands (`task/run`, `file/read`, etc.) and receives structured events
- Real-time event streaming: progress updates, file changes, tool calls
- Best for: structured workflows, event-driven integrations, streaming output

### Layer 3: Extension (ACP Bridge)

- Adds ACP (Agent Communication Protocol) bridge on top of RPC
- Hermes can load TypeScript extensions that hook into Pi's lifecycle
- Full bidirectional communication with typed messages
- Best for: custom toolchains, deep Pi customization, long-running agents

## Key Design Decisions

See the ADRs for detailed rationale:

- [ADR-001: Integration Approach](../architecture/adr-001-integration-approach.md) — why three layers
- [ADR-002: Communication Protocol](../architecture/adr-002-communication-protocol.md) — why JSONL/stdio
- [ADR-003: Dogfooding Strategy](../architecture/adr-003-dogfooding-strategy.md) — how we validate Pier with Pier
