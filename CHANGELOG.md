# Changelog

All notable changes to Pier are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] Alpha — 2026-07-24

Initial release of **Pier** — a Hermes Agent integration for the [Pi coding agent](https://github.com/earendil-works/pi).
Pier enables orchestrator-driven Hermes swarms to delegate coding tasks to Pi's best-in-class agent loop
through a three-layer composable architecture:

- **Layer 1: Hermes Skill** — Delegate coding tasks via `pi -p` (print mode, zero configuration)
- **Layer 2: Python Plugin** — 4 gated tools for Pi interaction with RPC/JSON/print mode support
- **Layer 3: Pi Extension** — TypeScript companion for client-side tool definitions and UI

### Research & Architecture

- Competitive integration landscape research covering LangChain, Open Interpreter, Claude Code MCP,
  and Hermes ACP patterns; protocol comparison (MCP vs ACP vs A2A vs ANP) with recommendation for
  ACP session management + MCP tool exposure (#1)
- Three Architecture Decision Records: integration approach (three-layer), communication protocol
  (JSONL RPC over stdio), and dogfooding strategy (building Pier with Pier) (#5)
- Pi extension ecosystem integration spec with auto-detection, compatibility guarantees, essential-vs-optional
  classification, and one-command `pier setup` design (#17)
- MkDocs Material documentation site with GitHub Pages deployment, 7 nav sections, and search (#5)

### Core Infrastructure

- Dual-language project scaffold: Python (setuptools, ruff, pytest) + TypeScript (tsc, biome, vitest) (#7)
- CI pipeline: ruff check + format, pytest matrix (3.11–3.13), npm lint + typecheck, mkdocs build --strict (#7)
- AGENTS.md coding rules for AI agents, CONTRIBUTING.md, MIT-licensed (#7)
- README with architecture diagram, quick start, and project status (#7)

### Layer 2: Hermes Plugin

Four gated tools registered with the Hermes orchestrator:

| Tool | Description | Mode |
|------|-------------|------|
| `pier_install_check` | Verify Pi CLI availability and supported modes | — |
| `pier_delegate` | One-shot coding task delegation | Print (`pi -p`) |
| `pier_session` | Multi-turn session with graceful fallback | RPC → JSON → Print |
| `pier_status` | Pi installation and provider configuration | — |

- `PiRPCClient`: async JSONL-framed RPC client with event dispatch, request correlation, and graceful degradation (#8)
- `PiRPCEventParser`: typed dataclasses for all 18 Pi RPC event types (#8)
- Plugin manifest (`plugin.yaml`) and `register()` entry point for Hermes plugin discovery (#12)

### Layer 1: Hermes Skill

- `skills/pier/SKILL.md` — orchestration guide for Pi print-mode delegation covering modes,
  provider config, usage patterns, and layer progression to plugin + extension (#12)

### Layer 3: Pi Extension Ecosystem

- Deep-dive evaluation of top 5 Pi extensions: pi-mcp-adapter (157.6K/mo), pi-subagents (124.3K/mo),
  pi-web-access (134.9K/mo), context-mode (101.8K/mo), pi-hermes-memory (~2K/mo) (#15)
- Comprehensive ecosystem reference guide with tool registration, config, and print/RPC compatibility matrix (#15)
- Pi Extension Setup guide: pi-lsp-extension + language servers, pi-lean-ctx with config examples,
  recommended settings, verification commands, and troubleshooting (#18)

### Testing & Validation

- **163 tests** passing: 100 plugin tests, 36 RPC client tests, 46 event parser tests (#10, #13)
- Layer 2 integration test: plugin installed in Hermes profile, all 4 tools functional,
  `pier_delegate` live coding task completed in 21.37s (#9)
- Layer 3 integration test: RPC bridge verified — prompt→response lifecycle, abort, get_state
  all passing on Pi v0.81.1 (#14)
- Dogfooding battle-test: 5/5 real-world coding scenarios (bug fix, feature, code review, refactoring,
  multi-file module) completed with zero failures, 66/66 generated tests passing (#11)
- Docker dogfooding: clean-slate container test with DeepSeek V4 Flash, 163 tests passing,
  smoke test + 3 scenarios all passing (#16)

### Documentation

- Install guide: step-by-step skill + plugin setup, prerequisites, verification (#12)
- User guide: getting started, skills, plugins, Pi extensions (#5, #12, #17)
- Pi Extension Setup guide with LSP and lean-ctx configuration (#18)
- Architecture overview with Excalidraw component diagram (#5)
- Reference: Python API reference, Pi ecosystem guide (#5, #15)
- Research: Pi architecture deep-dive, Hermes coding patterns (#1, #5)
- Reports: 3 integration tests, 3 dogfooding reports (#9, #11, #14, #16)

### Prerequisites

| Requirement | Minimum Version | Notes |
|-------------|----------------|-------|
| Hermes Agent | ≥ 0.18 | Python ≥ 3.11 required |
| Pi coding agent | v0.81.1 | Print mode always available; RPC mode optional |
| pi-lsp-extension | latest | Recommended for IDE support |
| pi-lean-ctx | latest | Recommended for context optimization |

[0.1.0]: https://github.com/thepragmatik/pier/releases/tag/v0.1.0
