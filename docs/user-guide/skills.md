# Skills (Layer 1)

Layer 1 of Pier is a Hermes skill that wraps Pi as a terminal subprocess. It mirrors the
existing coding-agent skills (Codex, Claude Code, OpenCode) but targets Pi specifically.

## How It Works

The Pier skill:

1. Accepts a coding task from Hermes
2. Invokes Pi in the appropriate CLI mode (`pi run`)
3. Captures stdout/stderr and exit code
4. Returns structured results to Hermes

This is the simplest integration path — no custom protocol, no plugin required. It works
exactly like the existing `claude-code` or `codex` skills.

## Installing the Skill

```bash
# From the Pier repo
mkdir -p ~/.hermes/skills/pier/
cp skills/pier-skill/SKILL.md ~/.hermes/skills/pier/

# Or install via Hermes plugin manager (future)
hermes skills install pier
```

## Using the Skill

In any Hermes session, reference the skill:

```
@pier Fix the type errors in src/handlers.py
```

The skill configuration in `SKILL.md` defines which Pi CLI mode to use, timeout, and
working directory conventions.

## Skill Configuration

```yaml
# ~/.hermes/skills/pier/SKILL.md frontmatter
tools:
  terminal: true
  file: true
environment:
  PI_MODE: run          # Pi CLI mode: run | chat | rpc | agent
  PI_TIMEOUT: 300       # Max seconds per delegation
  PI_WORKDIR: "${HERMES_WORKDIR}"
```

## Pi CLI Modes

| Mode | Command | Use Case |
|------|---------|----------|
| `run` | `pi run "<task>"` | One-shot task, returns diff + summary |
| `chat` | `pi chat` | Interactive coding session |
| `rpc` | `pi rpc` | JSONL RPC protocol (use Layer 2 instead) |
| `agent` | `pi agent` | Long-running agent with session persistence |

For most Layer 1 usage, `run` mode is the right choice — it's a single command that
completes and returns.

## Next Steps

Ready for deeper integration? Move to [Plugins](plugins.md) for Layer 2 (RPC protocol) and
Layer 3 (ACP bridge + TypeScript extensions).
