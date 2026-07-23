# Architecture

Pier's architecture is documented through an overview, component diagram, and a set of
Architecture Decision Records (ADRs) that capture why we made the choices we made.

## Architecture Overview

- **[Architecture Overview](overview.md)** — High-level architecture, component diagram, and
  the three-layer integration model (Skill → Plugin → Extension).

## Architecture Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](adr-001-integration-approach.md) | Integration Approach — Three-Layer Architecture | Accepted |
| [ADR-002](adr-002-communication-protocol.md) | Communication Protocol — JSONL RPC over stdio | Accepted |
| [ADR-003](adr-003-dogfooding-strategy.md) | Dogfooding Strategy — Building Pier with Pier | Accepted |

## Architecture Diagram

![Pier Architecture Diagram](pier-architecture.excalidraw)

The full Excalidraw source is available at `pier-architecture.excalidraw` — open it in
[Excalidraw](https://excalidraw.com) to explore interactively.

## Research Foundation

These ADRs were informed by Phase R research:

- [Pi Architecture Deep-Dive](../research/pi-architecture-deep-dive.md)
- [Hermes Coding-Agent Patterns](../research/hermes-coding-agent-patterns.md)
- [Competitive Integration Landscape](../research/competitive-integration-landscape.md)

## How to Contribute

New architectural decisions should be captured as ADRs. See
[Creating a New ADR](../developer-guide/adrs.md#creating-a-new-adr) for the process.
