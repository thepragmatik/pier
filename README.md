# Pier

[![CI](https://github.com/thepragmatik/pier/actions/workflows/ci.yml/badge.svg)](https://github.com/thepragmatik/pier/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Hermes](https://img.shields.io/badge/hermes-agent-plugin-blueviolet.svg)](https://github.com/nousresearch/hermes-agent)

**Pier** is a Hermes Agent plugin that bridges the [Pi coding agent](https://github.com/earendil-works/pi) with a [Hermes orchestrator](https://github.com/nousresearch/hermes-agent), letting orchestrator-driven swarms delegate coding tasks to Pi's best-in-class agent loop.

## Architecture

```
┌────────────────────┐       ┌──────────────────────┐
│  Hermes Swarm      │       │  Pi Coding Agent      │
│  (orchestrator)    │──────▶│  (specialist)          │
│                    │◀──────│                        │
│  • task routing    │       │  • AI-assisted coding  │
│  • multi-agent     │       │  • CLI + TUI           │
│  • result synthesis│       │  • extension system    │
└────────────────────┘       └──────────────────────┘
          │                            │
          └──────── Pier ──────────────┘
               • plugin (Python)
               • extension (TypeScript)
               • protocol bridge
```

Pier is a **dual-language project**:

- **Python** (`pier/`) — Hermes Agent plugin that registers Pi tools and skills with the orchestrator
- **TypeScript** (`packages/pier-extension/`) — companion npm package for client-side tool definitions and UI extensions

## Quick Start

```bash
# Clone and install
git clone https://github.com/thepragmatik/pier.git
cd pier

# Python
make install          # pip install -e ".[dev]"
make test-py          # pytest

# TypeScript
make install-js       # npm install
make lint-js          # biome check
make test-js          # vitest

# Everything
make check            # lint + test (both languages)
```

## Project Status

Pier is in early development. See the [Architecture Decision Records](docs/architecture/) for design rationale and the [research notes](docs/research/) for background on Pi and Hermes internals.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. Agent contributors should also read [AGENTS.md](AGENTS.md).

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
