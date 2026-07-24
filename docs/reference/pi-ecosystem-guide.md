# Pi Extension Ecosystem Guide

> **Last updated:** 2026-07-24
>
> Deep-dive evaluation of the top 5 Pi extensions by monthly npm downloads.
> Tests performed with Pi CLI v0.81.1 on macOS (arm64).

---

## Overview

Pi's extension system installs packages via `pi install npm:<package>` and
loads their TypeScript/JavaScript entry points on session start. Extensions
can register tools, slash commands, lifecycle hooks, and config flags.

All five extensions below installed cleanly with no dependency conflicts.
The install added 264 npm packages total across all extensions (~1.7 MB
unpacked). No peer dependency warnings were emitted.

---

## 1. pi-mcp-adapter — `npm:pi-mcp-adapter`

| Field | Value |
|---|---|
| **Version** | 2.11.0 |
| **Author** | Nico Bailon ([@nicobailon](https://github.com/nicobailon/pi-mcp-adapter)) |
| **License** | MIT |
| **Monthly downloads** | ~157,600 |
| **npm deps** | 8 (MCP SDK, TypeBox, zod, open, recheck, Pi AI/TUI) |
| **Unpacked size** | 1.9 MB |

### Install

```bash
pi install npm:pi-mcp-adapter
```

### Tools Registered

| Tool | Type | Description |
|---|---|---|
| `mcp` | proxy | Unified MCP gateway — connect to MCP servers, call their tools, search/describe tools |
| `server_*` | direct | When `MCP_DIRECT_TOOLS` env var is set, individual MCP server tools are registered as standalone Pi tools with a configurable prefix |

The `mcp` proxy tool accepts these parameters:

| Parameter | Type | Description |
|---|---|---|
| `tool` | string | Tool name to call (e.g. `"xcodebuild_list_sims"`) |
| `args` | string | Arguments as JSON string (e.g. `'{"key": "value"}'`) |
| `connect` | string | Server name to connect (lazy connect + metadata refresh) |
| `describe` | string | Tool name to describe (shows parameters) |
| `search` | string | Search tools by name/description |
| `regex` | boolean | Treat search as regex (default: substring match) |
| `includeSchemas` | boolean | Include parameter schemas in search results |
| `server` | string | Filter to specific server (also disambiguates tool calls) |
| `action` | string | `'ui-messages'`, `'auth-start'`, or `'auth-complete'` |

### Commands

| Command | Description |
|---|---|
| `/mcp` | Show MCP server status and management panel |
| `/mcp tools` | List all available MCP tools |
| `/mcp setup` | Open MCP configuration setup |
| `/mcp reconnect <server>` | Reconnect a specific MCP server |
| `/mcp status` | Show status of all configured servers |
| `/mcp-auth` | Authenticate with an MCP server (OAuth) |

### Config Flags

- `--mcp-config <path>` — Path to MCP config file

### Works in Print Mode (`pi -p`)?

**Yes.** The `mcp` proxy tool is registered at extension load time, before
any session mode is chosen. The tool will work in print mode as long as the
MCP servers are configured in the MCP config file. The `/mcp` slash command
requires a TUI but the tool itself is mode-independent.

### Compatibility with Pier Integration

**Full compatibility.** The MCP adapter uses standard stdio-based MCP
protocol. Pier's RPC and extension bridge layers can interact with MCP
servers through this adapter. Use `pier.extension.PierExtensionBridge` for
TypeScript extensions alongside this adapter.

### Recommended Config

Create `~/.pi/mcp-config.json`:

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
      "env": {
        "GITHUB_TOKEN": "<your-token>"
      }
    }
  },
  "settings": {
    "toolPrefix": "server",
    "disableProxyTool": false
  }
}
```

Set `MCP_DIRECT_TOOLS=github` to expose GitHub's tools as direct Pi tools
(prefixed as `server_*`) instead of going through the proxy.

---

## 2. pi-hermes-memory — `npm:pi-hermes-memory`

| Field | Value |
|---|---|
| **Version** | 0.8.2 |
| **Author** | Chandra Teja ([@chandra447](https://github.com/chandra447/pi-hermes-memory)) |
| **License** | MIT |
| **Monthly downloads** | ~2,000 |
| **npm deps** | 2 (Pi TUI, better-sqlite3) |
| **Unpacked size** | 1.0 MB |
| **Tests** | 693 |

### Relationship to Hermes Agent

**Yes, this is explicitly ported from Nous Research's Hermes Agent.**
The README states "Ported from Hermes agent" and the code maps directly to
Hermes Agent's memory tool (`tools/memory_tool.py`), session search, and
skill management features. Features ported include:

- Memory tool (MEMORY.md + USER.md) — 5,000 char limit
- Session search via SQLite FTS5
- Procedural skills (SKILL.md files)
- Auto-consolidation / rotation
- Correction detection
- Background learning loop
- Secret scanning (API keys, tokens blocked)

### Install

```bash
pi install npm:pi-hermes-memory
```

### Tools Registered

| Tool | Description | Parameters |
|---|---|---|
| `memory` | Save/manage persistent memory across sessions | action (add/replace/remove), target (memory/user/project/failure), content, old_text, category, failure_reason |
| `memory_search` | Search extended memory store (unlimited capacity) | query, project, target (memory/user/failure), category (failure/correction/insight/preference/convention/tool-quirk), limit (max 20) |
| `session_search` | Search Pi session files (two variants: legacy FTS5 or anchor mode) | Markdown-format request with from/to/cwd/limit/all/any/exclude |
| `skill_manage` | Manage procedural skills (SKILL.md files) | action (create/view/patch/update/edit/delete), name, skill_id, description, scope, section, content, when_to_use, procedure_steps, pitfalls, verification_steps |

### Commands

| Command | Description |
|---|---|
| `/memory-insights` | Show what's stored in memory |
| `/memory-skills` | List procedural skills |
| `/memory-consolidate` | Manual consolidation trigger |
| `/memory-interview` | Onboarding interview to pre-fill user profile |
| `/memory-switch-project` | Switch project memory context |
| `/memory-index-sessions` | Index all past Pi sessions into SQLite |
| `/memory-sync-markdown` | Sync Markdown memories to SQLite search index |
| `/learn-memory-tool` | Learn how to use the memory tool |
| `/preview-context` | Preview what memory context Pi will see |

### Works in Print Mode (`pi -p`)?

**Yes.** All tools are registered at extension load time. Memory will
initialize and load from disk on session_start. Tools work in non-interactive
mode. Slash commands require a TUI and won't work in print mode.

### Compatibility with Pier Integration

**Full compatibility.** Pier's Layer 1 (skill subprocess) can invoke Pi
sessions that load this extension. The persistent memory will survive across
multiple Pier-triggered Pi sessions.

### Recommended Config

`~/.pi/agent/pi-hermes-memory/config.json`:

```json
{
  "memoryDir": "",
  "projectsMemoryDir": "projects-memory",
  "memoryCharLimit": 5000,
  "projectCharLimit": 5000,
  "maxMemories": 50,
  "reviewIntervalTurns": 10,
  "reviewIntervalToolCalls": 15,
  "syncedMemoryToSearchLimit": 5000,
  "consolidationTimeoutMs": 30000,
  "sessionSearch": { "variant": "anchors" }
}
```

---

## 3. pi-subagents — `npm:pi-subagents`

| Field | Value |
|---|---|
| **Version** | 0.35.1 |
| **Author** | Nico Bailon ([@nicobailon](https://github.com/nicobailon/pi-subagents)) |
| **License** | MIT |
| **Monthly downloads** | ~124,300 |
| **npm deps** | 2 (jiti, yaml) |
| **Unpacked size** | 2.4 MB |

### Install

```bash
pi install npm:pi-subagents
```

### Tools Registered

| Tool | Description | Modes |
|---|---|---|
| `subagent` | Delegate tasks to subagents with chains and parallel execution | single, parallel (tasks[]), chain (chain[] with previous), async, scheduled |
| `wait` | Wait for async subagent results | configurable timeout, polling |

The `subagent` tool supports these parameters (simplified):

| Parameter | Description |
|---|---|
| `agent` | Agent name to use (single mode) |
| `task` | Task description (single mode) |
| `tasks` | Array of {agent, task} for parallel execution |
| `chain` | Array of {agent, task} for sequential execution |
| `async` | Run in background (default: per config) |
| `output` | Save output to file |
| `cwd` | Working directory override |
| `reads` | Files to read before running |
| `skills` | Skills to make available |
| `turnBudget` | Assistant-turn budget (maxTurns, graceTurns) |
| `toolBudget` | Tool-call budget (soft, hard) |

### Config

`~/.pi/agent/extensions/subagent/config.json`:

```json
{
  "asyncByDefault": false,
  "forceTopLevelAsync": false,
  "maxSubagentDepth": 1,
  "maxSubagentSpawnsPerSession": null,
  "intercomBridge": { "mode": "always", "instructionFile": "./intercom-bridge.md" },
  "worktreeSetupHook": "./scripts/setup-worktree.mjs",
  "completionBatch": { "maxBatchEntries": 10, "flushIntervalMs": 500 },
  "waitTool": { "enabled": true, "waitDelayMs": 2000, "maxWaitMs": 600000 },
  "asyncWidget": true
}
```

### Works in Print Mode (`pi -p`)?

**Yes.** The subagent tool is registered at extension load time. It should
work in print mode for synchronous subagent tasks. Async mode returns
immediately and the `wait` tool can be used to poll results. The `/` slash
commands require a TUI.

### Compatibility with Pier Integration

**Full compatibility.** Subagents can be used within Pier-triggered Pi
sessions. The escape hatch (`SUBAGENT_CHILD_ENV=1`) prevents recursive
subagent spawning. Config controls max depth and spawn limits.

---

## 4. pi-web-access — `npm:pi-web-access`

| Field | Value |
|---|---|
| **Version** | 0.13.0 |
| **Author** | Nico Bailon ([@nicobailon](https://github.com/nicobailon/pi-web-access)) |
| **License** | MIT |
| **Monthly downloads** | ~134,900 |
| **npm deps** | 5 (Readability, linkedom, turndown, unpdf, p-limit) |
| **Unpacked size** | 7.0 MB |

### Install

```bash
pi install npm:pi-web-access
```

### Tools Registered

| Tool | Description | Key Parameters |
|---|---|---|
| `web_search` | Search the web with AI-synthesized answers & source citations | query, queries[], numResults, includeContent, recencyFilter, domainFilter, provider, workflow |
| `fetch_content` | Fetch URL(s) and extract readable markdown. Supports YouTube transcripts, GitHub repos, local video files | url, urls[], forceClone, prompt (for video), timestamp, frames, model |
| `get_search_content` | Retrieve full content from a previous web_search or fetch_content call | responseId, query, queryIndex, url, urlIndex |

### Supported Search Providers

| Provider | Requires |
|---|---|
| OpenAI | Codex subscription or OpenAI API key (OPENAI_API_KEY) |
| Brave | BRAVE_API_KEY |
| Exa | EXA_API_KEY |
| Tavily | TAVILY_API_KEY |
| Perplexity | PERPLEXITY_API_KEY |
| Gemini API | GEMINI_API_KEY |
| Gemini Web | Google account logged into Chrome |
| Parallel | PARALLEL_API_KEY |

Provider auto-select: OpenAI > Exa > Brave > Parallel > Tavily > Perplexity
> Gemini API > Gemini Web. Set `provider: "brave"` to force a specific one.

### Workflow Modes

| Mode | Description |
|---|---|
| `none` | No curator. Returns raw results. Works in print mode. |
| `summary-review` (default) | Opens interactive browser curator for result review. Requires TUI. |
| `auto-summary` | Generates model summary without opening curator. Works headless. |

### Works in Print Mode (`pi -p`)?

**Partially.** `web_search` with `workflow: "none"` or `workflow: "auto-summary"`
works in print mode. `fetch_content` works fully in print mode (no UI needed).
`get_search_content` works fully. The curator/browser UI workflow requires a
TUI session.

### Compatibility with Pier Integration

**Full compatibility.** Web search and fetch work well within Pier's Layer 1
(skill subprocess). For headless operation, set `workflow: "none"` or
`workflow: "auto-summary"` to skip the curator UI.

### Recommended Config

`~/.pi/agent/extensions/web-access/config.json`:

```json
{
  "provider": "auto",
  "workflow": "auto-summary",
  "curatorTimeoutSeconds": 20,
  "ssrf": { "allowRanges": ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"] },
  "shortcuts": { "curate": "ctrl+shift+s", "activity": "ctrl+shift+w" }
}
```

Set `workflow: "none"` in headless/Pier environments.

---

## 5. context-mode — `npm:context-mode`

| Field | Value |
|---|---|
| **Version** | 1.0.169 |
| **Author** | Mert Koseoğlu ([@mksglu](https://github.com/mksglu/context-mode)) |
| **License** | Elastic-2.0 |
| **Monthly downloads** | ~101,800 |
| **npm deps** | 8 (Clack prompts, domino, MCP SDK, better-sqlite3, turndown, zod, picocolors) |
| **Unpacked size** | 4.2 MB |

### Install

```bash
pi install npm:context-mode
```

### Tools Registered (via MCP Bridge)

Context-mode spawns a long-lived MCP server (`server.bundle.mjs`) and
dynamically registers its tools through Pi's `registerTool()` API. Tools
become available on `before_agent_start` (session start).

| Tool | Description |
|---|---|
| `ctx_batch_execute` | Sandbox multi-command execution |
| `ctx_execute` | Sandbox code execution (supports JavaScript/TypeScript) — keeps raw data out of context |
| `ctx_execute_file` | Execute a script file in the sandbox |
| `ctx_index` | Index local file or directory into persistent FTS5 knowledge base |
| `ctx_search` | Search indexed content (BM25 ranking) |
| `ctx_fetch_and_index` | Fetch web pages and index them for search |
| `ctx_stats` | Context savings stats — per-tool breakdown, tokens consumed |
| `ctx_doctor` | Diagnostics — runtimes, hooks, FTS5, registration |
| `ctx_upgrade` | Pull latest version, rebuild, migrate cache |
| `ctx_purge` | Permanently delete all indexed content |
| `ctx_insight` | Opens hosted Insight dashboard for org analytics |

### Commands

| Command | Description |
|---|---|
| `/ctx-stats` | Context savings statistics |
| `/ctx-doctor` | Diagnostics |

### Key Feature: HTTP Routing Block

Context-mode intercepts `bash` tool calls that contain fetch/requests/curl/wget
patterns and blocks them, redirecting the model to use `ctx_execute` or
`ctx_fetch_and_index` instead. This prevents raw HTTP output from flooding
the context window. Safely silent curl/wget with file output is allowed as
an escape hatch when the MCP bridge is unavailable.

### Works in Print Mode (`pi -p`)?

**Yes.** The MCP bridge is started lazily from `before_agent_start`, which
fires for print-mode dispatches. Tools are registered before Pi snapshots
the tool registry for the model call. Safely silent background: guide
routes HTTP-heavy bash commands to ctx_* tools even in print mode.

### Compatibility with Pier Integration

**Full compatibility.** Context-mode works alongside Pier's skill/plugin
integration. The sandboxed execution (`ctx_execute`) complements Pier's
Layer 1 skill subprocess model. Use `ctx_search` for persistent knowledge
crossing both Pier and Pi sessions.

### License Note

Context-mode uses the **Elastic License 2.0 (ELv2)**, which restricts:
- Use as a paid service (SaaS) where context-mode is the primary value
- Circumvention of license key or payment mechanisms

It is free for individual and internal business use.

---

## Cross-Extension Compatibility Matrix

| Extension | pi-mcp-adapter | pi-hermes-memory | pi-subagents | pi-web-access | context-mode |
|---|---|---|---|---|---|
| **pi-mcp-adapter** | — | ✓ No conflict | ✓ No conflict | ✓ No conflict | ✓ Shares MCP server but no tool name collision |
| **pi-hermes-memory** | ✓ | — | ✓ No conflict | ✓ No conflict | ✓ No conflict |
| **pi-subagents** | ✓ | ✓ | — | ✓ No conflict | ✓ No conflict |
| **pi-web-access** | ✓ | ✓ | ✓ | — | ✓ No conflict |
| **context-mode** | ✓ (MCP bridge) | ✓ | ✓ | ✓ | — |

All five extensions were installed simultaneously with no conflicts.
No tool name collisions were detected. Total install added 264 npm packages.

---

## Summary: Which Extensions to Enable

| Use case | Recommended |
|---|---|
| Connecting to MCP servers (DB, API tools) | pi-mcp-adapter |
| Persistent memory & cross-session recall | pi-hermes-memory |
| Parallel/chain agent delegation | pi-subagents |
| Web search & content fetching | pi-web-access |
| Context window optimization | context-mode |
| All-in-one for Pier integration | All five (no conflicts) |

---

## Diagnostic Commands

Check what's installed:

```bash
pi list
```

Check extension-specific status:

```bash
# pi-mcp-adapter
pi -p -e "mcp({})"

# pi-hermes-memory
/ctx-stats         # in interactive mode
# Or check ~/.pi/agent/pi-hermes-memory/ for stored files

# pi-subagents
ls ~/.pi/agent/extensions/subagent/results/

# pi-web-access
# web_search with workflow:"none" returns results without UI

# context-mode
# ctx_doctor tool provides full diagnostics
```
