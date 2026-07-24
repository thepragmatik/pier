# Pi Extensions

Pi's TypeScript extension system lets you install community-maintained packages that
register tools, slash commands, lifecycle hooks, and config flags inside Pi. This guide
covers the extensions most relevant to the Pier + Hermes integration.

For a comprehensive technical evaluation, see the
[Pi Extension Ecosystem Guide](../reference/pi-ecosystem-guide.md).

## Quick Setup

Install all recommended extensions in one command:

```bash
pier setup --essential
```

This installs the 3 **Essential** extensions:

- **pi-mcp-adapter** — MCP gateway (filesystem, GitHub, databases, APIs)
- **pi-subagents** — Parallel/chain subagent delegation
- **pi-web-access** — Web search and content fetching

For all 5 extensions including Optional ones:

```bash
pier setup --all
```

## Extension Tiers

### Essential

Extensions you should install to get the full Pier + Pi experience.

#### pi-mcp-adapter

| | |
|---|---|
| **Package** | `npm:pi-mcp-adapter` |
| **Version** | 2.11.0 |
| **Downloads/mo** | ~157,600 |
| **License** | MIT |

Bridges Pi to the entire [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
ecosystem. Any MCP-compatible server — filesystem, GitHub, databases, APIs — becomes
available as Pi tools.

**Install:**

```bash
pi install npm:pi-mcp-adapter
```

**Tools registered:**

| Tool | Description |
|------|-------------|
| `mcp` | Unified MCP gateway — connect, call, search, describe tools |
| `server_*` | Direct MCP server tools (when `MCP_DIRECT_TOOLS` is set) |

**Key capability for Pier:** Without this extension, Pi can only use bash. With it, Pi
connects to the entire MCP ecosystem. This is the single highest-leverage extension for
Pier integration.

**Quick config** (`~/.pi/mcp-config.json`):

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "<your-token>" }
    }
  }
}
```

[:octicons-link-external-16: GitHub](https://github.com/nicobailon/pi-mcp-adapter)

#### pi-subagents

| | |
|---|---|
| **Package** | `npm:pi-subagents` |
| **Version** | 0.35.1 |
| **Downloads/mo** | ~124,300 |
| **License** | MIT |

Enables parallel and sequential subagent delegation within Pi sessions. Directly mirrors
Hermes's `delegate_task` pattern — Pi can spawn child agents for independent subtasks.

**Install:**

```bash
pi install npm:pi-subagents
```

**Tools registered:**

| Tool | Description |
|------|-------------|
| `subagent` | Delegate tasks to subagents — single, parallel, chain, async, scheduled |
| `wait` | Wait for async subagent results |

**Key capability for Pier:** Multi-agent delegation is a core Hermes pattern. Without
subagents, Pi cannot do parallel file analysis, independent subtask execution, or chained
work. With subagents, a single `pier_delegate` can trigger a full parallel fan-out.

**Example — parallel code review + test writing:**

```
pier_delegate("Review src/auth.py for bugs AND write tests for the fix")
  → Pi spawns 2 subagents in parallel
    ├─ subagent(agent="code-reviewer", task="Review src/auth.py")
    └─ subagent(agent="test-writer", task="Write tests for auth fix")
  → Pi synthesizes results from both subagents
  → Returns unified fix + tests
```

[:octicons-link-external-16: GitHub](https://github.com/nicobailon/pi-subagents)

#### pi-web-access

| | |
|---|---|
| **Package** | `npm:pi-web-access` |
| **Version** | 0.13.0 |
| **Downloads/mo** | ~134,900 |
| **License** | MIT |

Web search and content fetching with multiple provider backends. Headless-compatible
(`workflow: "none"` or `"auto-summary"`). Essential for coding tasks that need current
documentation, API references, or package lookups.

**Install:**

```bash
pi install npm:pi-web-access
```

**Tools registered:**

| Tool | Description |
|------|-------------|
| `web_search` | Search the web with AI-synthesized answers and source citations |
| `fetch_content` | Fetch URL(s) and extract readable markdown (supports YouTube, GitHub, PDFs) |
| `get_search_content` | Retrieve full content from a previous search |

**Key capability for Pier:** Coding tasks frequently need fresh information. Without web
access, Pi is limited to offline reasoning. Set `workflow: "auto-summary"` for headless
Pier environments.

**Headless config** (`~/.pi/agent/extensions/web-access/config.json`):

```json
{
  "provider": "auto",
  "workflow": "auto-summary"
}
```

Supported providers: OpenAI, Brave, Exa, Tavily, Perplexity, Gemini API, Gemini Web.

[:octicons-link-external-16: GitHub](https://github.com/nicobailon/pi-web-access)

---

### Optional

Extensions that add significant value but aren't required for Pier integration.

#### pi-hermes-memory

| | |
|---|---|
| **Package** | `npm:pi-hermes-memory` |
| **Version** | 0.8.2 |
| **Downloads/mo** | ~2,000 |
| **License** | MIT |

Port of Hermes Agent's memory system into Pi. Provides persistent cross-session memory,
session search via SQLite FTS5, procedural skills (SKILL.md), and auto-consolidation.

**Install:**

```bash
pi install npm:pi-hermes-memory
```

**Tools registered:** `memory`, `memory_search`, `session_search`, `skill_manage`

**When to install:** You want Pi sessions triggered by Pier to have persistent memory
that survives across sessions. Not required for Pier itself — Hermes already has its own
memory system. Install if you want Pi to remember things independently of Hermes.

[:octicons-link-external-16: GitHub](https://github.com/chandra447/pi-hermes-memory)

#### context-mode

| | |
|---|---|
| **Package** | `npm:context-mode` |
| **Version** | 1.0.169 |
| **Downloads/mo** | ~101,800 |
| **License** | Elastic-2.0 |

Context window optimization via sandboxed code execution and persistent FTS5 knowledge
base. Reduces token costs by keeping raw data out of the context window.

**Install:**

```bash
pi install npm:context-mode
```

**Tools registered:** `ctx_execute`, `ctx_batch_execute`, `ctx_search`, `ctx_fetch_and_index`,
`ctx_stats`, `ctx_doctor`, and more.

**When to install:** Token budget management is critical for your workflow. The sandboxed
execution model keeps raw command output from flooding Pi's context window.

[:octicons-link-external-16: GitHub](https://github.com/mksglu/context-mode)

---

## Compatibility

All five extensions were tested simultaneously with zero conflicts. They register tools
at extension load time (before session mode is chosen), so all tools work in both print
mode (`pi -p`) and RPC mode (`pi --mode rpc`). Slash commands (`/mcp`, `/memory-*`,
etc.) require a TUI and are unavailable in non-interactive mode.

| Extension | Print Mode | RPC Mode | Pier Compatible |
|-----------|:----------:|:--------:|:---------------:|
| pi-mcp-adapter | ✓ | ✓ | ✓ |
| pi-subagents | ✓ | ✓ | ✓ |
| pi-web-access | ✓ (workflow: none/auto-summary) | ✓ | ✓ |
| pi-hermes-memory | ✓ | ✓ | ✓ |
| context-mode | ✓ | ✓ | ✓ |

## Checking Extension Status

```bash
# List installed extensions
pi list

# Pier's built-in status report
pier status
```

The Pier status report shows each extension's version, load state, and monthly download
count so you know which extensions are active and whether any have errors.

## Next Steps

- [Pi Extension Ecosystem Guide](../reference/pi-ecosystem-guide.md) — Full technical
  evaluation with config examples and cross-extension compatibility matrix
- [Pier Integration Spec §9](../architecture/pier-integration-spec.md#9-pi-extension-ecosystem-integration) —
  Architecture-level design for extension auto-detection, classification, and setup
- [Plugins](plugins.md) — Layer 2 RPC plugin architecture
