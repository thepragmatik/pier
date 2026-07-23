---
name: pier
description: "Delegate coding tasks to Pi CLI (pi -p) for one-shot coding, code review, and PR workflows."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Coding-Agent, Pi, Code-Review, Refactoring, Automation]
    related_skills: [claude-code, codex, opencode]
---

# Pier — Hermes Orchestration Guide

Delegate coding tasks to [Pi](https://github.com/earendil-works/pi) (the Pi coding agent CLI) via the Hermes terminal. Pi can read files, write code, run shell commands, and manage git workflows autonomously.

## Prerequisites

- **Install:** `npm install -g @earendil-works/pi-coding-agent`
- **Check:** `pi --version` — confirms Pi is on PATH
- **Verify modes:** `pi --help` — check for `-p` (print), `--mode json`, `--mode rpc`

## Print Mode (`-p`) — Primary Integration Path

Print mode runs a one-shot task, returns the result, and exits. This is the simplest and most reliable integration path.

```
terminal(command="pi -p 'Add error handling to all API calls in src/' --model anthropic/claude-sonnet-4 --max-turns 10", workdir="/path/to/project", timeout=120)
```

**When to use print mode:**
- One-shot coding tasks (fix a bug, add a feature, refactor)
- Code review and analysis
- CI/CD automation and scripting
- Any task where you don't need multi-turn conversation

## RPC Mode (`--mode rpc`) — Multi-Turn Sessions (via Plugin)

For multi-turn interactive sessions, use the Pier **plugin** (Layer 2). The plugin provides `pier_session` for RPC-based bidirectional communication with streaming progress, session resume, and cost tracking.

```
# Available when the pier plugin is loaded:
pier_session(prompt="Refactor the auth module to use JWT", model="anthropic/claude-sonnet-4")
```

See the [Pier Plugin docs](plugins.md) for full RPC session details.

## JSON Mode (`--mode json`) — Structured Output

For structured, machine-parseable results:

```
terminal(command="pi --mode json 'Analyze auth.py for security issues' --model anthropic/claude-sonnet-4", timeout=120)
```

## Basic Usage Patterns

### Quick Code Review
```
terminal(command="cd /path/to/repo && git diff main...feature-branch | pi -p 'Review this diff for bugs, security issues, and style problems.' --model anthropic/claude-sonnet-4", timeout=120)
```

### Bug Fix
```
terminal(command="pi -p 'Fix the type errors in src/handlers.py. Make sure all edge cases are handled.' --model anthropic/claude-sonnet-4", workdir="/project", timeout=180)
```

### Feature Implementation
```
terminal(command="pi -p 'Implement a REST endpoint for user preferences with validation, tests, and OpenAPI docs.' --model anthropic/claude-sonnet-4 --max-turns 15", workdir="/project", timeout=300)
```

### Refactoring
```
terminal(command="pi -p 'Refactor the database layer to use async/await throughout. Update all callers. Keep existing tests passing.' --model anthropic/claude-sonnet-4 --max-turns 10", workdir="/project", timeout=240)
```

## Tool Allowlisting

Pi respects tool allowlists for safety:

```
# Allow read-only + bash (no writes)
terminal(command="pi -p 'Audit all SQL queries for injection vulnerabilities' --tools read,bash --max-turns 5", timeout=120)
```

Common tools: `read`, `bash`, `edit`, `write`, `web_search`, `web_fetch`

## Provider Configuration

Pi auto-detects provider API keys from the environment:

| Provider | Env Variable |
|----------|-------------|
| Anthropic | `ANTHROPIC_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| OpenRouter | `OPENROUTER_API_KEY` |
| Google | `GOOGLE_API_KEY` / `GEMINI_API_KEY` |

Override the default model per-invocation:

```
terminal(command="pi -p 'task' --provider openrouter --model openai/gpt-4o", timeout=120)
```

Or set defaults via environment:

```bash
export PIER_DEFAULT_PROVIDER=anthropic
export PIER_DEFAULT_MODEL=claude-sonnet-4-20250514
```

## Layer Progression

Pier integrates at three layers:

| Layer | Component | Use When |
|-------|-----------|----------|
| **1 — Skill** | This SKILL.md | One-shot tasks, simple delegation |
| **2 — Plugin** | `plugins/pier/` | RPC sessions, streaming, lifecycle |
| **3 — ACP Bridge** | TypeScript extension | Long-running agent, custom protocol |

Start with Layer 1 (print mode). Graduate to Layer 2 (plugin) for richer sessions. Layer 3 is for advanced extension use cases.
