# Pier

Integration that lets [Pi](https://github.com/earendil-works/pi) work with a [Hermes orchestrator](https://github.com/nousresearch/hermes-agent).

## Overview

Pier bridges two AI coding-agent ecosystems:

- **Pi** — a TypeScript-based coding agent with a rich CLI, TUI, and extension system
- **Hermes Agent** — a Python-based multi-agent orchestrator with plugin and skill systems

Pier wraps Pi as a Hermes plugin so orchestrator-driven swarms can delegate coding subtasks to Pi's specialist agent loop, with full context handoff and result synthesis.

## Quick Start

```bash
git clone https://github.com/thepragmatik/pier.git
cd pier
make install
make check
```

## Project Structure

| Path | Purpose |
|------|---------|
| `pier/` | Python plugin — registers Pi tools + skills with Hermes |
| `packages/pier-extension/` | TypeScript companion — client-side tool defs + types |
| `tests/` | Python tests (pytest) |
| `docs/architecture/` | Architecture Decision Records |
| `docs/research/` | Background research on Pi and Hermes internals |
