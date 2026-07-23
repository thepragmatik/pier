# Pier

**Hermes Agent ↔ Pi Coding-Agent Integration**

Pier is a composable bridge that lets [Hermes Agent](https://github.com/NousResearch/hermes-agent) delegate
coding tasks to [Pi](https://github.com/earendil-works/pi) — a TypeScript-native coding agent with a structured
RPC protocol, extension system, and Agent Skills compatibility.

## Why Pier?

Hermes currently talks to coding agents (Codex, Claude Code, OpenCode) through terminal subprocesses —
unstructured text, one-shot commands, and ad-hoc error handling. Pi offers a richer surface:

- **Structured RPC** — JSONL-based protocol with 20+ commands and 18 event types
- **TypeScript Extensions** — hook into every phase of the coding lifecycle
- **Agent Skills Compatible** — Pi speaks the same skill format as Hermes
- **Four CLI Modes** — from embedded subprocess to full remote agent

Pier gives Hermes access to all of these through a layered architecture that lets you adopt
integration depth incrementally.

## Quick Start

```bash
# Install Pier
pip install pier

# Or clone and install from source
git clone https://github.com/thepragmatik/pier.git
cd pier
pip install -e .
```

```python
from pier import PierAgent

agent = PierAgent()
result = agent.run("Add type hints to src/models.py")
```

## Layers of Integration

Pier is built in three layers. Start with Layer 1 (the skill) and adopt deeper layers as your
workflow demands more structure:

| Layer | What it is | When to use |
|-------|-----------|-------------|
| **Layer 1 — Skill** | Terminal subprocess wrapper (like existing coding-agent skills) | Quick adoption, simple delegations |
| **Layer 2 — Plugin** | Structured RPC bridge over JSONL/stdio | Real-time event streaming, typed responses |
| **Layer 3 — Extension** | Full ACP bridge with TypeScript extensions | Custom toolchains, deep Pi customization |

[:octicons-arrow-right-24: Read the User Guide](user-guide/index.md) to get started.

## Project Status

Pier is under active development as part of the Hermes Swarm mission.
See the [Blog](blog/index.md) for iteration changelogs and the
[Architecture](architecture/index.md) section for design decisions (ADRs).
