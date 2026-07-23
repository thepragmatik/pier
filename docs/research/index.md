# Research

Phase R research artifacts that informed Pier's architecture and design.

## Research Documents

- **[Pi Architecture Deep-Dive](pi-architecture-deep-dive.md)** — Comprehensive analysis of Pi's
  TypeScript-native architecture, CLI modes, RPC protocol, and extension system.
- **[Hermes Coding-Agent Patterns](hermes-coding-agent-patterns.md)** — Survey of how Hermes
  currently delegates coding tasks to external agents (Codex, Claude Code, OpenCode) and the
  patterns, limitations, and opportunities those integrations reveal.
- **[Competitive Integration Landscape](competitive-integration-landscape.md)** — Analysis of
  competing orchestrator-coding-agent protocols and integration patterns from the broader
  ecosystem (Aider, Cline, Roo Code, Continue, OpenHands).

## How Research Feeds Architecture

Each research document directly informs one or more Architecture Decision Records:

| Research Document | ADR Informed |
|-------------------|--------------|
| Pi Architecture Deep-Dive | [ADR-001](../architecture/adr-001-integration-approach.md) — Three-layer design |
| Hermes Coding-Agent Patterns | [ADR-002](../architecture/adr-002-communication-protocol.md) — RPC protocol choice |
| Competitive Integration Landscape | [ADR-003](../architecture/adr-003-dogfooding-strategy.md) — Dogfooding strategy |

## Research Methodology

Phase R followed a structured research process:

1. **R.1 — Pi Architecture Deep-Dive:** Cloned Pi repo, read source, mapped CLI modes and RPC protocol
2. **R.2 — Hermes Patterns:** Analyzed existing coding-agent skills in Hermes (claude-code, codex, opencode)
3. **R.3 — Competitive Landscape:** Surveyed 6+ orchestrator-coding-agent integrations in the ecosystem
4. **R.4 — Architecture Synthesis:** Produced 3 ADRs + architecture overview + component diagram

The full research process is documented in
[GitHub Issue #6](https://github.com/thepragmatik/pier/issues/6).
