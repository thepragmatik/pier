# Pier Installation Guide

Install the Pier skill and plugin in your local Hermes installation.

## Prerequisites

- Hermes Agent installed and configured
- A Hermes profile (e.g., `hswarm-orch`)

## Skill Installation

```bash
# Copy the skill to your profile
PROFILE=hswarm-orch  # change to your profile name
mkdir -p ~/.hermes/profiles/$PROFILE/skills/software-development/pier/
cp skills/pier/SKILL.md ~/.hermes/profiles/$PROFILE/skills/software-development/pier/SKILL.md

# Verify (requires gateway restart to pick up new skills)
hermes skills list | grep pier
```

## Plugin Installation

```bash
# Link the plugin into the Hermes plugins directory
ln -sf $(pwd)/plugins/pier ~/.hermes/plugins/pier

# Also link into your profile
ln -sf ~/.hermes/plugins/pier ~/.hermes/profiles/$PROFILE/plugins/pier

# Add to plugins.enabled in config.yaml
# Edit ~/.hermes/profiles/$PROFILE/config.yaml:
plugins:
  enabled:
    - pier

# Verify (requires gateway restart)
hermes plugins list | grep pier
hermes tools list | grep pier
```

## Gateway Restart

After installing the skill and plugin, restart the gateway to pick up changes:

```bash
hermes gateway restart
```

## Verification

```bash
# Check that pier_install_check tool is available
hermes chat -q "Check if Pi is installed" --quiet
# Should trigger the pier_install_check tool
```

## Plugin Tools

The Pier plugin registers these tools:

| Tool | Description |
|------|-------------|
| `pier_install_check` | Check if Pi CLI is installed and what modes it supports |
| `pier_delegate` | Delegate a one-shot coding task via `pi -p` |
| `pier_session` | Start/resume a multi-turn Pi session via RPC mode |
| `pier_status` | Report Pi installation and provider config status |
| `pier_install` | Install Pi CLI via npm |

All tools gate on Pi availability — they only appear when `pi` is on PATH.

## Skill (Layer 1)

The Pier skill provides orchestration patterns for using Pi's print mode (`pi -p`)
directly from Hermes — no plugin required. Use the skill for one-shot coding tasks.

## Plugin (Layer 2)

The Pier plugin provides structured tool interfaces for Pi delegation with:
- Print-mode delegation (`pier_delegate`)
- RPC session management (`pier_session`) 
- Installation management (`pier_install`, `pier_install_check`)
- Status reporting (`pier_status`)
