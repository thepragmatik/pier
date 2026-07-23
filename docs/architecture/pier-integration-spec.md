# Pier Integration Specification — PIER-ARCH-001

* **Document ID:** PIER-ARCH-001
* **Status:** Draft
* **Date:** 2026-07-23
* **Author:** hswarm-arch
* **Scope:** Comprehensive specification for the Hermes Agent ↔ Pi integration

---

## Table of Contents

1. [Overview](#1-overview)
2. [Layer 1: Hermes Skill](#2-layer-1-hermes-skill)
3. [Layer 2: Python Plugin](#3-layer-2-python-plugin)
4. [Layer 3: Pi TypeScript Extension](#4-layer-3-pi-typescript-extension)
5. [Protocol Specification](#5-protocol-specification)
6. [Testing Strategy](#6-testing-strategy)
7. [Security](#7-security)
8. [Dogfooding Acceptance Criteria](#8-dogfooding-acceptance-criteria)

---

## 1. Overview

### 1.1 Problem Statement

Hermes Agent currently delegates coding tasks to external coding agents (Codex, Claude Code, OpenCode) via terminal subprocesses. This works for basic delegation but imposes three structural limitations:

1. **No structured output.** Hermes parses unstructured terminal text for results, error codes, and completion signals. Each agent has its own output format, requiring per-agent parsing logic.
2. **No bidirectional protocol.** Steering messages mid-task require terminal keystroke injection (`process(action="submit")`). There is no programmatic way to cancel, query state, or fork sessions.
3. **No typed contract.** Each agent has its own CLI flags, error formats, and output conventions. Adding a new coding agent means writing a new set of text parsers and error handlers.

Pi (`earendil-works/pi`) offers a richer integration surface: four CLI modes (interactive, print, JSON, RPC), a TypeScript extension system, a structured RPC protocol with 20+ commands and 18 event types, and an Agent Skills-compatible skill system. Pier bridges this richness back to Hermes through a layered architecture.

### 1.2 Solution: Three-Layer Composable Integration

Pier connects Hermes Agent to Pi through three independently usable integration layers. Users choose the depth of integration that matches their needs, and can upgrade progressively without rebuilding.

```
Layer 1: Skill       →  Pi as terminal subprocess (print mode)       ~200 lines
Layer 2: Plugin      →  Pi via RPC protocol (structured events)      ~800 lines
Layer 3: Extension   →  Pi via ACP bridge + TypeScript extensions    ~2000 lines
```

Each layer is **independently useful** and builds on the one below it.

* **Layer 1 (Skill):** Zero-config entry point. Hermes delegates to Pi via `pi -p "<prompt>"`. Works like existing `codex`, `claude-code`, and `opencode` skills. For users evaluating Pier or needing simple one-shot delegation.
* **Layer 2 (Plugin):** Structured integration via Pi's native RPC protocol (JSONL over stdin/stdout). Provides streaming progress, task cancellation, session forking, cost tracking, model cycling, and bash execution tracking. For users who want rich integration without ACP complexity.
* **Layer 3 (Extension):** Deep integration via ACP (Agent Client Protocol) bridge and Pi TypeScript extensions. Full session lifecycle, Hermes-native tools in Pi, cross-provider auth passthrough, workspace management. For teams building custom integration pipelines.

### 1.3 Design Principles

| Principle | Description |
|-----------|-------------|
| **Adoption gradient** | Users start at Layer 1 (no config) and upgrade when they need more. Monolithic integration forces everyone to set up RPC/ACP before getting any value. |
| **Independent usefulness** | Each layer delivers value on its own. Layer 1 delegates tasks. Layer 2 adds structured events. Layer 3 adds cross-agent tooling. No layer requires the next to function. |
| **Separation of concerns** | Protocol parsing (Layer 2) and orchestration semantics (Layer 3) are different problems. A protocol change at Layer 2 must not break orchestration logic at Layer 3. |
| **Protocol-first** | Layers 2 and 3 use structured, versioned, typed protocols — not ad-hoc text parsing. Every integration surface has a machine-readable contract. |
| **Graceful degradation** | When a richer protocol is unavailable, fall back to the next simpler layer. If Pi RPC fails, fall back to JSON mode. If JSON mode fails, fall back to print mode. The user's task still executes. |
| **Ecosystem diversity** | Pier adds Pi as a new coding agent option; it does not replace existing skills (codex, claude-code, opencode). Different tasks benefit from different agents. |
| **Containerization as security boundary** | Pier does not implement its own sandbox. It follows Pi's security model: OS-level, VM-level, or container-level boundaries for untrusted work. |

### 1.4 Integration Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Hermes Agent                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      Pier Integration                     │   │
│  │                                                           │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────┐  │   │
│  │  │  Layer 3        │  │  Layer 2        │  │ Layer 1  │  │   │
│  │  │  Extension      │  │  Plugin         │  │ Skill    │  │   │
│  │  │                 │  │                 │  │          │  │   │
│  │  │  ACP Bridge +   │  │  RPC Protocol   │  │ Terminal │  │   │
│  │  │  TypeScript     │◄─┤  (JSONL/stdio)  │◄─┤ Sub-     │  │   │
│  │  │  Extensions     │  │                 │  │ process  │  │   │
│  │  └────────┬────────┘  └────────┬────────┘  └─────┬────┘  │   │
│  │           │                    │                  │       │   │
│  └───────────┼────────────────────┼──────────────────┼───────┘   │
│              │                    │                  │           │
└──────────────┼────────────────────┼──────────────────┼───────────┘
               │                    │                  │
               ▼                    ▼                  ▼
        ┌──────────────────────────────────────────────────┐
        │                    Pi Agent                       │
        │                                                   │
        │  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
        │  │  ACP     │  │  RPC     │  │  Print Mode   │   │
        │  │  Server  │  │  Mode    │  │  (-p / --mode │   │
        │  │          │  │          │  │   json)       │   │
        │  └──────────┘  └──────────┘  └───────────────┘   │
        │                                                   │
        │  ┌──────────────────────────────────────────┐     │
        │  │        TypeScript Extension System        │     │
        │  │  tools | commands | hooks | providers     │     │
        │  └──────────────────────────────────────────┘     │
        │                                                   │
        │  ┌──────────────────────────────────────────┐     │
        │  │        Agent Skills System                │     │
        │  │  SKILL.md | scripts | references          │     │
        │  └──────────────────────────────────────────┘     │
        └──────────────────────────────────────────────────┘
```

### 1.5 Related Documents

| Document | Purpose |
|----------|---------|
| [ADR-001](adr-001-integration-approach.md) | Three-layer architecture decision |
| [ADR-002](adr-002-communication-protocol.md) | RPC as primary protocol for Layer 2 |
| [ADR-003](adr-003-dogfooding-strategy.md) | Phased dogfooding after Layer 2 stable |
| [R.1] ../research/pi-architecture-deep-dive.md | Pi architecture, RPC protocol spec, extension system |
| [R.2] ../research/hermes-coding-agent-patterns.md | Hermes skill patterns, gap analysis, Pi opportunities |
| [R.3] ../research/competitive-integration-landscape.md | Protocol landscape, ACP/MCP/A2A analysis |

---

## 2. Layer 1: Hermes Skill

### 2.1 Purpose

Layer 1 is the zero-config entry point. A Hermes skill (`pier`) that delegates coding tasks to Pi via its print mode (`-p`). Installs as a single SKILL.md file in `~/.hermes/skills/autonomous-ai-agents/pier/`.

### 2.2 Skill Structure

```
~/.hermes/skills/autonomous-ai-agents/pier/
├── SKILL.md              # Skill definition + delegation patterns
└── scripts/
    └── pier_wrapper.sh   # Optional: Pi version check, auth setup
```

### 2.3 SKILL.md Specification

The skill follows the same pattern as existing `codex`, `claude-code`, and `opencode` skills:

```yaml
---
name: pier
description: "Delegate coding to Pi CLI (features, PRs, refactoring)."
version: 1.0.0
tags: [Coding-Agent, Pi, Autonomous, Code-Review, Refactoring]
related_skills: [claude-code, codex, opencode, hermes-agent]
platforms: [linux, macos]
---

# Pi Coding Agent Skill

## Prerequisites
- Pi installed: `npm install -g @earendil-works/pi-coding-agent`
- Provider configured (see [Configuration](#configuration))

## Quick Start
Delegate a bounded task to Pi in one-shot mode:
terminal(command="pi -p '<prompt>'", workdir="/path/to/project", timeout=300)
```

### 2.4 Delegation Patterns

#### Pattern 1: One-Shot (Print Mode)

The primary pattern. Non-interactive, exits when done. No PTY needed.

```
Hermes → terminal(pi -p "<prompt>", workdir=<project>) → stdout → parsed response
```

**Use cases:** Fix a bug, add a feature, review a diff, generate tests.

**Flags:**
- `--provider <provider>` — specify LLM provider (anthropic, openai, openrouter)
- `--model <provider/model>` — specify model
- `--thinking <level>` — reasoning level (off|minimal|low|medium|high|xhigh|max)
- `--tools <list>` — allowlist specific tools (e.g., `read,bash,edit,write`)
- `--no-approve` — require user approval for destructive operations

#### Pattern 2: Piped Input

```
Hermes → terminal("cat <file> | pi -p '<prompt>'", workdir=<project>) → stdout
```

**Use cases:** Summarize a file, analyze git diff, process build output.

#### Pattern 3: Git Worktree Isolation

```
Hermes → git worktree add -b fix/issue-N /tmp/issue-N main
Hermes → terminal("pi -p 'Fix issue #N'", workdir="/tmp/issue-N")
Hermes → git diff → review changes → merge
```

Follows the same git worktree isolation pattern documented in the `codex` and `claude-code` skills.

#### Pattern 4: PR Review

```
Hermes → terminal("gh pr checkout N", workdir=<repo>)
Hermes → terminal("pi -p 'Review this PR for correctness, security, and style'", workdir=<repo>)
```

### 2.5 Error Handling

| Error | Detection | Recovery |
|-------|-----------|----------|
| Pi not installed | `pi: command not found` in stderr | Report to user: "Install Pi via `npm install -g @earendil-works/pi-coding-agent`" |
| Provider auth failure | `Authentication error` in output | Report missing API key env var |
| Timeout | `terminal(timeout=N)` expires | Re-run with higher timeout or simpler prompt |
| Model error | `Model returned an error` in output | Retry up to 2 times; report if persistent |
| Pi version too old | `--mode rpc not supported` | Report: "Update Pi: `npm update -g @earendil-works/pi-coding-agent`" |

### 2.6 Output Parsing

By default, `pi -p` outputs the assistant response as plain text. For structured output, the skill recommends `--mode json` which outputs JSON Lines events matching the RPC event schema (see Section 5). Parsing logic:

1. **Success:** Non-empty stdout, zero exit code → return output as result.
2. **Empty output:** Zero exit code, empty stdout → task completed with no printable output.
3. **Error:** Non-zero exit code → parse stderr for error message and category.

### 2.7 Relationship to Other Skill Layers

Layer 1 does NOT require Pi RPC mode or ACP. It is fully self-contained. Users upgrade to Layer 2 when they need structured events and session management.

---

## 3. Layer 2: Python Plugin

### 3.1 Purpose

Layer 2 is a Hermes plugin that speaks Pi's RPC protocol natively, providing structured event parsing, streaming progress, task cancellation, session management, and cost tracking.

### 3.2 Plugin Architecture

```
hermes-agent/
└── plugins/
    └── pier/
        ├── __init__.py          # Plugin registration, toolset definition
        ├── rpc_client.py        # JSONL-framed RPC protocol client
        ├── event_parser.py      # Maps Pi RPC events to Hermes tool-call hooks
        ├── session_manager.py   # Session lifecycle (create, fork, clone, compact)
        ├── tool_bridge.py       # Maps Pi tools to Hermes tool schema
        └── config.py            # Provider/model configuration
```

### 3.3 Tool Registration

The plugin registers itself with Hermes's tool registry, exposing a `pier_delegate` tool that appears in Hermes's available tool set:

```python
from tools.registry import registry

registry.register(
    name="pier_delegate",
    toolset="pier",
    schema={
        "name": "pier_delegate",
        "description": "Delegate a coding task to Pi via structured RPC protocol.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The coding task to delegate to Pi"
                },
                "workdir": {
                    "type": "string",
                    "description": "Working directory for the task"
                },
                "model": {
                    "type": "string",
                    "description": "Provider/model override (e.g., 'anthropic/claude-sonnet-4')"
                },
                "thinking": {
                    "type": "string",
                    "enum": ["off", "minimal", "low", "medium", "high", "xhigh", "max"],
                    "description": "Reasoning level"
                },
                "allowed_tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tool allowlist (e.g., ['read', 'bash', 'edit', 'write'])"
                },
                "max_turns": {
                    "type": "integer",
                    "description": "Maximum LLM turns"
                },
                "session_id": {
                    "type": "string",
                    "description": "Resume or fork an existing Pi session"
                }
            },
            "required": ["prompt", "workdir"]
        }
    },
    handler=pier_delegate_handler,
    check_fn=check_pier_requirements,
    requires_env=["PI_INSTALLED"],
)
```

Additional tools registered by the plugin:

| Tool | Purpose |
|------|---------|
| `pier_delegate` | Primary delegation via RPC protocol |
| `pier_abort` | Cancel a running Pi task |
| `pier_fork_session` | Fork Pi session from a message checkpoint |
| `pier_session_stats` | Query token usage, cost, and context window |
| `pier_set_model` | Switch provider/model mid-session |
| `pier_steer` | Send a steering message to a running task |

### 3.4 RPC Bridge Implementation

The RPC client (`rpc_client.py`) implements the JSONL-framed protocol over stdin/stdout:

```python
class PiRpcClient:
    """JSONL-framed RPC client for Pi --mode rpc."""

    def __init__(self, provider: str, model: str):
        self.process = None
        self.provider = provider
        self.model = model
        self._pending_requests: dict[str, Future] = {}
        self._event_handlers: list[Callable] = []

    async def start(self) -> None:
        """Spawn `pi --mode rpc --provider <p> --model <m>` subprocess."""
        self.process = await asyncio.create_subprocess_exec(
            "pi", "--mode", "rpc",
            "--provider", self.provider,
            "--model", self.model,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read_events())

    async def send_command(self, command: dict) -> dict:
        """Send a JSON command on stdin, return response."""
        request_id = command.get("id", str(uuid4()))
        command["id"] = request_id
        payload = json.dumps(command, ensure_ascii=False) + "\n"
        self.process.stdin.write(payload.encode("utf-8"))
        await self.process.stdin.drain()
        future = Future()
        self._pending_requests[request_id] = future
        return await future

    async def _read_events(self) -> None:
        """Read JSON events from stdout, dispatch to handlers."""
        while True:
            line = await self.process.stdout.readline()
            if not line:
                break
            event = json.loads(line.decode("utf-8"))
            # Resolve pending requests by matching event.id
            if event.get("id") in self._pending_requests:
                self._pending_requests[event["id"]].set_result(event)
            # Notify streaming event handlers
            for handler in self._event_handlers:
                await handler(event)

    def on_event(self, handler: Callable) -> None:
        """Register a streaming event handler."""
        self._event_handlers.append(handler)

    async def stop(self) -> None:
        """Terminate the Pi subprocess."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
```

**Key implementation constraints:**

1. **Strict LF (`\n`) delimiters only.** Must split on `\n` — NOT on Unicode line separators (U+2028, U+2029). Python's `readline()` uses `\n` by default and is safe. Node's `readline` module is NOT safe (splits on Unicode separators inside JSON strings).

2. **Non-blocking event dispatch.** All streaming events (text deltas, tool updates, bash output) dispatch to async callbacks. The main command loop must not block on event processing.

3. **Process lifecycle.** The Pi subprocess is spawned once and reused for multiple commands within a session. Commands are multiplexed over the single stdin/stdout channel.

4. **Request/response correlation.** Every command includes an `id` field. Events with a matching `id` are responses. Events without an `id` (or with a different `id`) are streaming events for the current or concurrent operations.

### 3.5 Event Mapping to Hermes Hooks

The event parser (`event_parser.py`) maps Pi RPC events to Hermes-internal lifecycle hooks:

| Pi Event | Hermes Mapping |
|----------|---------------|
| `agent_start` | Task started notification |
| `agent_settled` | Task completed (success, error, or aborted) |
| `turn_start` / `turn_end` | Per-turn progress counter update |
| `message_update` (text_delta) | Streaming output appended to result |
| `message_update` (thinking_delta) | Reasoning block (collapsed by default) |
| `message_update` (toolcall_start/delta/end) | Tool call announced with name |
| `tool_execution_start` | Tool execution progress bar |
| `tool_execution_update` | Tool progress update |
| `tool_execution_end` | Tool result summary |
| `bash_execution_update` | Shell output streaming |
| `compaction_start` / `compaction_end` | Context window alert |
| `auto_retry_start` / `auto_retry_end` | Transient error notification |
| `extension_error` | Extension failure alert |

### 3.6 Session Lifecycle Management

The session manager (`session_manager.py`) provides:

| Operation | RPC Command | Description |
|-----------|------------|-------------|
| **New session** | `new_session` | Start fresh session |
| **Prompt** | `prompt` | Send user prompt |
| **Steer** | `steer` | Queue steering message during execution |
| **Follow-up** | `follow_up` | Queue message for after agent settles |
| **Abort** | `abort` | Cancel current operation |
| **Fork** | `fork` | Create session fork from message checkpoint |
| **Clone** | `clone` | Duplicate active branch to new session |
| **Compact** | `compact` | Manual context compaction |
| **Get state** | `get_state` | Current model, thinking level, status |
| **Get stats** | `get_session_stats` | Token usage, cost, context window |
| **Set model** | `set_model` | Switch provider/model |
| **Cycle model** | `cycle_model` | Cycle to next configured model |
| **Set thinking** | `set_thinking_level` | Change reasoning level |
| **Export** | `export_html` | Export session to HTML |

**Session isolation:** Pi sessions are JSONL files in `~/.pi/agent/sessions/`. Hermes does not depend on Pi session state for its own operation. A corrupted Pi session can be deleted without affecting Hermes.

**Auto-compaction:** Pi automatically compacts context when approaching the model's context window limit. The plugin surfaces compaction events to Hermes so the user is aware of context eviction. Manual compaction can be triggered via `pier_delegate` with compact instructions.

### 3.7 Tool Bridge

The tool bridge (`tool_bridge.py`) maps Pi's built-in tools to Hermes tool schemas for discoverability:

| Pi Tool | Hermes Equivalent | Notes |
|---------|-------------------|-------|
| `read` | `read_file` | File reading |
| `write` | `write_file` | File writing |
| `edit` | `patch` | Targeted find-and-replace with unified diff |
| `bash` | `terminal` | Shell command execution |
| `grep` | `search_files` | File content search |
| `find` | `search_files (target='files')` | File name search |
| `ls` | `search_files (target='files')` | Directory listing |

This mapping enables Hermes to understand what Pi can do without needing to parse Pi's tool definitions. If Pi registers custom tools via extensions, the tool bridge discovers them via `get_commands` RPC call.

### 3.8 Configuration

Plugin configuration via `config.yaml` or environment variables:

```yaml
# ~/.hermes/config.yaml
pier:
  # Default provider/model for Pi delegation
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"

  # RPC protocol settings
  rpc:
    connect_timeout_seconds: 30
    command_timeout_seconds: 600
    graceful_shutdown_seconds: 10

  # Session settings
  session:
    session_dir: "~/.pi/agent/sessions"
    auto_compact_threshold: 0.8  # Context window % to trigger compaction

  # Tool restrictions
  tools:
    default_allowlist: ["read", "bash", "edit", "write"]
    disallowed: []

  # Security
  security:
    containerize: false
    container_image: "pi-agent:latest"
    mount_workspace_only: true
    restrict_network: false
```

Environment variables:
- `PIER_PROVIDER` — default LLM provider
- `PIER_MODEL` — default model
- `PIER_RPC_TIMEOUT` — override command timeout
- `PIER_CONTAINER_IMAGE` — container image for sandboxed execution

### 3.9 Graceful Degradation

If Pi RPC mode is unavailable (Pi not installed, `--mode rpc` unsupported, version mismatch), the plugin falls back to JSON mode:

| Mode | Command | Capabilities |
|------|---------|-------------|
| **Primary: RPC** | `pi --mode rpc --provider X --model Y` | Full bidirectional protocol |
| **Fallback: JSON** | `pi --mode json "prompt" --provider X --model Y` | Structured events, no commands |
| **Last resort: Print** | `pi -p "prompt" --provider X --model Y` | Unstructured text output |

JSON mode provides structured events (same schema as RPC) but no commands — no steering, abort, fork, or session management. Print mode provides only the final assistant text.

---

## 4. Layer 3: Pi TypeScript Extension

### 4.1 Purpose

Layer 3 provides the deepest integration: a full ACP (Agent Client Protocol) bridge between Hermes and Pi, combined with Pi TypeScript extensions that register Hermes-specific tools and lifecycle hooks inside Pi.

**Status:** Future (post-Phase 4 dogfooding). Layer 3 is scoped but not scheduled for immediate implementation.

### 4.2 ACP Bridge Architecture

```
Hermes (ACP Client) ──── ACP (JSON-RPC/stdio) ──── Pi ACP Adapter ──── Pi Agent
                                                                     │
                                                            Pi TypeScript Extensions
                                                            (hermes-memory, hermes-skill, ...)
```

Hermes's ACP client (built on the existing `acp_adapter/` reference implementation) communicates with a Pi-side ACP adapter. The adapter maps ACP session operations into Pi's internal session API:

| ACP Operation | Pi Mapping |
|---------------|-----------|
| `new_session` | `SessionManager.create()` |
| `prompt` | `session.prompt(text)` |
| `resume` | `SessionManager.continueRecent()` |
| `fork` | `session.fork(entryId)` |
| `list_sessions` | `SessionManager.list()` |
| Tool streaming | `session.subscribe(event → ACP ToolKind events)` |

### 4.3 Pi TypeScript Extensions for Hermes

Pi extensions that register Hermes-specific capabilities inside Pi's agent loop:

#### Extension: `hermes-memory`

```typescript
// ~/.pi/agent/extensions/hermes-memory/index.ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "hermes_memory_search",
    label: "Search Hermes Memory",
    description: "Search Hermes Agent's persistent memory for relevant context.",
    parameters: Type.Object({
      query: Type.String({ description: "Natural-language memory query" }),
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      // Call Hermes memory API via ACP resource
      const results = await fetchHermesMemory(params.query);
      return {
        content: [{ type: "text", text: JSON.stringify(results) }],
        details: {},
      };
    },
  });
}
```

#### Extension: `hermes-skill`

```typescript
// ~/.pi/agent/extensions/hermes-skill/index.ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "hermes_skill_call",
    label: "Call Hermes Skill",
    description: "Invoke a Hermes skill from within Pi.",
    parameters: Type.Object({
      skill_name: Type.String({ description: "Name of the Hermes skill" }),
      args: Type.Optional(Type.Record(Type.String(), Type.Unknown())),
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      // Call Hermes skill API via ACP resource
      const result = await callHermesSkill(params.skill_name, params.args);
      return {
        content: [{ type: "text", text: JSON.stringify(result) }],
        details: {},
      };
    },
  });
}
```

#### Extension: `hermes-workspace`

Provides workspace management that aligns Pi's session filesystem with Hermes's git worktree isolation pattern:

```typescript
pi.on("session_start", async (event, ctx) => {
  if (ctx.mode === "rpc") {
    // Align workspace with Hermes-provided workdir
    const workdir = process.env.PIER_WORKDIR;
    if (workdir) {
      process.chdir(workdir);
    }
  }
});
```

### 4.4 Cross-Provider Auth Passthrough

Layer 3 enables Hermes's credential pools to be passed through to Pi sessions. When Hermes delegates to Pi:

1. Hermes resolves the user's provider credentials from its own pool.
2. Hermes passes the resolved credentials as ACP session metadata.
3. The Pi ACP adapter injects them as runtime overrides: `modelRuntime.setRuntimeApiKey(provider, key)`.
4. Pi uses the passed credentials for all LLM calls in that session.

This eliminates the need for users to configure credentials separately in Pi — one Hermes OAuth login covers both agents.

### 4.5 Permission Gating via Extensions

Pi extensions can implement runtime permission gates that block or modify tool calls:

```typescript
pi.on("tool_call", async (event, ctx) => {
  if (event.toolName === "bash") {
    // Block commands matching dangerous patterns
    const blocked = ["rm -rf /", "dd if=", "mkfs."];
    if (blocked.some(p => event.input.command?.includes(p))) {
      return { block: true, reason: "Blocked by Hermes safety policy" };
    }
  }

  if (event.toolName === "write") {
    // Restrict writes to workspace directory
    const workdir = process.env.PIER_WORKDIR || process.cwd();
    if (!event.input.filePath?.startsWith(workdir)) {
      const ok = await ctx.ui.confirm(
        "Outside workspace",
        `Write to ${event.input.filePath} is outside workspace. Allow?`
      );
      if (!ok) return { block: true, reason: "Outside workspace" };
    }
  }
});
```

---

## 5. Protocol Specification

### 5.1 Pi RPC Protocol Overview

Pi's RPC protocol operates over **strict LF-delimited JSONL on stdin/stdout**.

```
Client (Hermes) → stdin:   JSON command (one line, terminated by \n)
Server (Pi)     → stdout:  JSON events (one per line, streaming)
```

### 5.2 JSONL Framing Contract

**Rule 1:** Lines are delimited by ASCII `\n` (0x0A) only. Clients MUST NOT split on Unicode line separators (U+2028, U+2029).

**Rule 2:** Each line is a complete, valid JSON object. No multi-line JSON. No partial lines.

**Rule 3:** Commands include an optional `id` field for request/response correlation. Events with a matching `id` are command responses. Events without an `id` (or with a different `id`) are streaming events.

**Rule 4:** Stderr is for diagnostic output only — not structured protocol data.

### 5.3 Command Reference

#### Prompting

```json
{"type": "prompt", "id": "req-1", "text": "Fix the bug in src/parser.ts"}
```

```json
{"type": "steer", "id": "req-2", "text": "Use immutable data structures instead"}
```

```json
{"type": "follow_up", "id": "req-3", "text": "Also add error handling for edge cases"}
```

```json
{"type": "abort", "id": "req-4"}
```

```json
{"type": "new_session", "id": "req-5"}
```

#### State Queries

```json
{"type": "get_state", "id": "req-6"}
```
```json
// Response:
{"type": "state", "id": "req-6", "model": "claude-sonnet-4", "thinkingLevel": "high",
 "isStreaming": false, "isCompacting": false, "sessionInfo": {...}}
```

```json
{"type": "get_messages", "id": "req-7"}
```

#### Model Management

```json
{"type": "set_model", "id": "req-8", "provider": "openai", "model": "gpt-5"}
{"type": "cycle_model", "id": "req-9"}
{"type": "get_available_models", "id": "req-10"}
```

#### Thinking Level

```json
{"type": "set_thinking_level", "id": "req-11", "level": "high"}
{"type": "cycle_thinking_level", "id": "req-12"}
```

#### Compaction

```json
{"type": "compact", "id": "req-13", "instructions": "Preserve the API schema discussion"}
{"type": "set_auto_compaction", "id": "req-14", "enabled": true}
```

#### Bash

```json
{"type": "bash", "id": "req-15", "command": "npm test"}
{"type": "abort_bash", "id": "req-16"}
```

#### Session Management

```json
{"type": "get_session_stats", "id": "req-17"}
```
```json
// Response:
{"type": "session_stats", "id": "req-17", "tokens": {"input": 8234, "output": 1520, "total": 9754},
 "cost": {"usd": 0.18, "currency": "USD"}, "contextWindow": {"used": 8234, "total": 200000,
 "percent": 4.1}}
```

```json
{"type": "fork", "id": "req-18", "entryId": "msg-42"}
{"type": "clone", "id": "req-19"}
{"type": "get_fork_messages", "id": "req-20"}
{"type": "get_entries", "id": "req-21", "cursor": null, "limit": 50}
{"type": "get_tree", "id": "req-22"}
{"type": "switch_session", "id": "req-23", "path": "/path/to/session.jsonl"}
{"type": "export_html", "id": "req-24"}
```

### 5.4 Event Reference

Events are streamed to stdout and do NOT carry a request `id` unless they are a direct command response.

| Event | Payload | Trigger |
|-------|---------|---------|
| `agent_start` | `{}` | Agent begins processing |
| `agent_end` | `{}` | Low-level run completes |
| `agent_settled` | `{"reason": "completed"|"aborted"|"error"}` | Fully settled |
| `turn_start` | `{}` | New LLM turn begins |
| `turn_end` | `{"stopReason": "..."}` | LLM turn ends |
| `message_start` | `{"role": "assistant"}` | Assistant message begins |
| `message_update` | `{"assistantMessageEvent": {"type": "text_delta", "delta": "..."}}` | Streaming content |
| `message_end` | `{"role": "assistant"}` | Assistant message complete |
| `tool_execution_start` | `{"toolCallId": "...", "toolName": "read", "toolInput": {...}}` | Tool begins |
| `tool_execution_update` | `{"toolCallId": "...", "content": [...]}` | Tool progress |
| `tool_execution_end` | `{"toolCallId": "...", "output": {...}, "isError": false}` | Tool complete |
| `bash_execution_update` | `{"processId": "...", "output": "..."}` | Bash output chunk |
| `queue_update` | `{"steering": [...], "followUp": [...]}` | Queue changed |
| `compaction_start` | `{}` | Context compaction begins |
| `compaction_end` | `{}` | Context compaction ends |
| `auto_retry_start` | `{"attempt": 1, "reason": "rate_limit"}` | Retry begins |
| `auto_retry_end` | `{"attempt": 1, "outcome": "success"}` | Retry complete |

**Assistant message event delta types:**

| Delta Type | Description |
|------------|-------------|
| `start` | Message stream begins |
| `text_start` | Text block begins |
| `text_delta` | Text content increment |
| `text_end` | Text block complete |
| `thinking_start` | Thinking block begins |
| `thinking_delta` | Thinking content increment |
| `thinking_end` | Thinking block complete |
| `toolcall_start` | Tool call object begins |
| `toolcall_delta` | Tool call JSON increment |
| `toolcall_end` | Tool call object complete |
| `done` | Message complete |
| `error` | Message error |

### 5.5 Extension UI Sub-Protocol

When Pi extensions call `ctx.ui` methods in RPC mode, they emit an `extension_ui_request` / `extension_ui_response` sub-protocol:

```json
// Pi → Hermes (blocking, expects response)
{"type": "extension_ui_request", "id": "ui-1", "method": "confirm",
 "title": "Dangerous operation", "message": "This will modify 15 files. Continue?"}

// Hermes → Pi (response)
{"type": "extension_ui_response", "id": "ui-1", "result": true}
```

**Dialog methods (blocking):**
- `select(options, title?)` → selected index
- `confirm(title?, message?)` → boolean
- `input(title?, message?, defaultValue?)` → string
- `editor(title?, message?, defaultValue?)` → string

**Fire-and-forget methods (no response expected):**
- `notify(title?, message?)`
- `setStatus(text?)`
- `setWidget(component?)` (TUI only)
- `setTitle(title?)`

The Hermes Layer 2 plugin must implement handlers for all dialog methods. The user sees these as Hermes-level confirmations, not as Pi terminal prompts.

### 5.6 Error Handling Protocol

Pi reports errors through three channels:

1. **Command response with error:**
```json
{"type": "error", "id": "req-X", "error": "Session not found", "code": "SESSION_NOT_FOUND"}
```

2. **Agent settled with error reason:**
```json
{"type": "agent_settled", "id": "req-X", "reason": "error", "error": "Model returned an error"}
```

3. **Stderr diagnostics** (for infrastructure issues, not structured protocol errors).

### 5.7 Hermes Tool-Call Mapping

The Layer 2 plugin maps Pi's tool calls to Hermes tool-call primitives for the user to see:

```
Pi RPC event                     Hermes user-visible output
─────────────────────────────────────────────────────────
tool_execution_start(read)  →   pi: reading src/parser.ts...
tool_execution_end(read)    →   pi: read src/parser.ts (2,340 bytes)
tool_execution_start(bash)  →   pi: running `npm test -- --grep "parser"`
bash_execution_update       →   pi: [bash output streamed line by line]
tool_execution_end(bash)    →   pi: bash exited with code 0
tool_execution_start(write) →   pi: writing src/parser.ts...
tool_execution_end(write)   →   pi: wrote src/parser.ts (1,892 bytes)
tool_execution_start(edit)  →   pi: editing src/parser.ts (2 replacements)
tool_execution_end(edit)    →   pi: edit applied (unified diff summary)
```

### 5.8 Session Data Flow (End-to-End)

```
Hermes                                          Pi (RPC mode)
  │                                                │
  │  1. Start: pi --mode rpc --provider X          │
  │────────────────────────────────────────────────►│
  │                                                │
  │  2. Delegate: {"type":"prompt",                 │
  │     "text":"Fix the bug in src/parser.ts",     │
  │     "id":"req-1"}                              │
  │────────────────────────────────────────────────►│
  │                                                │  Agent loop starts
  │  {"type":"agent_start"}                        │
  │◄────────────────────────────────────────────────│
  │  {"type":"turn_start"}                         │
  │◄────────────────────────────────────────────────│
  │  {"type":"message_update",                     │  Streaming text
  │   "assistantMessageEvent":                     │
  │   {"type":"text_delta","delta":"I'll fix..."}} │
  │◄────────────────────────────────────────────────│
  │  {"type":"tool_execution_start",               │  Tool: read
  │   "toolName":"read",                           │
  │   "toolInput":{"filePath":"src/parser.ts"}}    │
  │◄────────────────────────────────────────────────│
  │  {"type":"tool_execution_end",                 │
  │   "toolName":"read","output":{...}}            │
  │◄────────────────────────────────────────────────│
  │  {"type":"message_update",                     │  Streaming fix
  │   "assistantMessageEvent":                     │
  │   {"type":"text_delta","delta":"\n\nFixed:"}}  │
  │◄────────────────────────────────────────────────│
  │  {"type":"turn_end"}                           │
  │◄────────────────────────────────────────────────│
  │  {"type":"agent_settled","reason":"completed"} │
  │◄────────────────────────────────────────────────│
  │                                                │
  │  3. Stats: {"type":"get_session_stats",         │
  │     "id":"req-2"}                              │
  │────────────────────────────────────────────────►│
  │  {"type":"session_stats","id":"req-2",         │
  │   "tokens":{"total":5234},"cost":{"usd":0.09}}  │
  │◄────────────────────────────────────────────────│
```

---

## 6. Testing Strategy

### 6.1 Test Pyramid

```
        ┌──────────────┐
        │  Acceptance  │  5-10 tests: End-to-end task delegation
        ├──────────────┤
        │ Integration  │  20-30 tests: Layer interactions, protocol
        ├──────────────┤
        │    Unit      │  50-80 tests: Parsers, mappers, lifecycle
        └──────────────┘
```

### 6.2 Unit Tests

**Scope:** Individual Python modules in the Layer 2 plugin.

| Module | Test Count | Key Cases |
|--------|-----------|-----------|
| `rpc_client.py` | 15-20 | JSONL framing (LF-only), request/response correlation, event dispatch ordering, process lifecycle (start/stop/restart), graceful shutdown |
| `event_parser.py` | 15-20 | Parse every event type (18 types), malformed JSON, missing fields, Unicode text in deltas, extension_error events |
| `session_manager.py` | 10-15 | Command serialization, ID assignment, concurrent command queuing, timeout handling |
| `tool_bridge.py` | 5-10 | Tool name mapping, argument transformation, custom tool discovery |
| `config.py` | 5-10 | Env var resolution, default values, validation |

**Example unit tests:**

```python
# tests/plugins/pier/test_rpc_client.py

def test_jsonl_framing_lf_only():
    """Pi RPC splits on LF, not Unicode line separators."""
    client = PiRpcClient("anthropic", "claude-sonnet-4")
    # U+2028 LINE SEPARATOR inside a JSON string value
    json_with_unicode = (
        '{"type":"message_update","delta":"line1\\u2028line2"}\n'
    )
    parsed = client._parse_line(json_with_unicode.encode())
    assert parsed["delta"] == "line1\u2028line2"  # Unicode preserved, not split

def test_request_response_correlation():
    """Commands with matching id resolve to responses."""
    client = PiRpcClient("anthropic", "claude-sonnet-4")
    future = Future()
    client._pending_requests["req-1"] = future
    # Simulate receiving a response event
    client._dispatch_event({"type": "agent_settled", "id": "req-1", "reason": "completed"})
    result = future.result(timeout=1)
    assert result["type"] == "agent_settled"
    assert result["reason"] == "completed"

def test_unmatched_event_does_not_resolve():
    """Events without matching request ID do not resolve pending requests."""
    client = PiRpcClient("anthropic", "claude-sonnet-4")
    future = Future()
    client._pending_requests["req-1"] = future
    # Simulate a streaming event with no id
    client._dispatch_event({"type": "message_update", "delta": "Hello"})
    assert not future.done()
```

### 6.3 Integration Tests

**Scope:** Interactions between Layer 2 components, and between Layer 2 and a real Pi installation.

| Category | Test Count | Key Cases |
|----------|-----------|-----------|
| RPC client ↔ real Pi | 8-10 | Spawn Pi in RPC mode, send `prompt`, receive `agent_settled`, verify session stats. Test with multiple providers (anthropic, openai, openrouter). |
| JSON fallback | 3-5 | Kill Pi RPC process, verify graceful fallback to `pi --mode json`. Verify event parsing is identical. |
| Print fallback | 2-3 | Kill Pi entirely, verify fallback to `pi -p`. |
| Session forking | 3-5 | Fork session, verify separate continuation paths produce different outputs. |
| Abort mid-task | 3-5 | Start long-running task, send `abort`, verify `agent_settled(reason="aborted")`. |
| Model cycling | 2-3 | `set_model` during task, verify model change in `get_state`. |
| Compaction | 2-3 | Fill context window, trigger auto-compaction, verify `compaction_start/end` events. |

**Example integration test:**

```python
# tests/plugins/pier/test_rpc_integration.py

@pytest.mark.integration
@pytest.mark.requires_pi
async def test_prompt_and_settle():
    """Full prompt→response lifecycle via real Pi RPC."""
    client = PiRpcClient("anthropic", "claude-sonnet-4-20250514")
    await client.start()

    settle_event = None
    async def on_settle(event):
        nonlocal settle_event
        if event["type"] == "agent_settled":
            settle_event = event

    client.on_event(on_settle)
    response = await client.send_command({
        "type": "prompt",
        "text": "What is 2+2? Answer in one word.",
    })

    await asyncio.sleep(10)  # Wait for agent to process
    assert settle_event is not None
    assert settle_event["reason"] == "completed"
    await client.stop()
```

### 6.4 Acceptance Tests

**Scope:** End-to-end tasks delegated through Pier that exercise the full Hermes↔Pi integration.

| Test | Task | Success Criteria |
|------|------|-----------------|
| Simple delegation | "Create hello.py that prints 'Hello, Pier!'" | File created, runs successfully |
| Bug fix | "Fix the off-by-one error in src/utils.py line 42" | Bug fixed, existing tests pass |
| Multi-file refactor | "Extract the authentication logic from app.py into auth.py" | Refactored, imports updated, tests pass |
| Code review | "Review PR #7 for security issues" | Structured review returned with findings |
| Test generation | "Write unit tests for the Parser class" | Tests added, 100% line coverage |
| Shell task | "Run `make build` and fix any compilation errors" | Build succeeds after fixes |
| Parallel sessions | Fork from message, run two approaches, compare | Both forks complete, comparison generated |
| Abort recovery | Start long task, abort mid-execution, verify session is intact | Session resumable after abort |

### 6.5 Test Fixtures

**Mock Pi Server (`tests/plugins/pier/fixtures/mock_pi_server.py`):**

A Python script that speaks the Pi RPC protocol and returns canned responses. Used for unit tests that don't need a real Pi installation.

```python
# Mock server reads JSONL commands from stdin, writes canned events to stdout
# Supports: prompt, get_state, get_session_stats, abort
# Returns: agent_start, turn_start, message_update (text_delta), agent_settled
```

**Test Sessions (`tests/plugins/pier/fixtures/sessions/`):**

Pre-built Pi session JSONL files for testing session management operations (fork, clone, get_entries, get_tree).

### 6.6 CI Configuration

```yaml
# .github/workflows/pier-tests.yml
name: Pier Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - uses: actions/setup-node@v4
        with: { node-version: "22" }
      - run: npm install -g @earendil-works/pi-coding-agent
      - run: pip install pytest pytest-asyncio pytest-cov
      - run: pytest tests/plugins/pier/ -v --cov=plugins/pier --cov-report=term

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff
      - run: ruff check plugins/pier/

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install mypy
      - run: mypy plugins/pier/ --strict
```

### 6.7 Test Isolation

- **Unit tests:** No external dependencies. Mock the Pi subprocess. Run in any environment.
- **Integration tests:** Require Pi installed (`@pytest.mark.requires_pi`). Skip in environments without Pi.
- **Acceptance tests:** Require Pi + LLM provider credentials (`@pytest.mark.requires_pi`, `@pytest.mark.requires_provider`). Run on CI with test credentials.

---

## 7. Security

### 7.1 Security Model Overview

Pier inherits Pi's security model: **no built-in sandbox**. Pi runs with the full permissions of the user account that starts it. Pier adds defense-in-depth at the Hermes integration layer.

### 7.2 Layered Security Architecture

```
┌─────────────────────────────────────────────┐
│ Hermes Security Layer                        │
│ ├─ Tool approval gating (Hermes-level)      │
│ ├─ Workdir isolation (git worktrees)        │
│ └─ Credential pool isolation               │
├─────────────────────────────────────────────┤
│ Pier Security Layer                          │
│ ├─ Tool allowlisting (pier_delegate tools)  │
│ ├─ Extension permission gating (Layer 3)    │
│ └─ Auto-compaction safety bounds            │
├─────────────────────────────────────────────┤
│ Pi Security Layer                            │
│ ├─ Project trust mechanism                  │
│ ├─ Extension isolation (no sandbox)         │
│ └─ Session file isolation                   │
├─────────────────────────────────────────────┤
│ OS / Container Security Layer               │
│ ├─ Docker/podman containerization           │
│ ├─ Gondolin micro-VM                       │
│ ├─ Mount namespace isolation                │
│ └─ Network namespace isolation              │
└─────────────────────────────────────────────┘
```

### 7.3 Tool Permission Model

#### Layer 1 (Skill)

Tools are controlled by Hermes's command approval system (`approvals.mode`):
- `smart` (default): auto-approve low-risk, prompt for destructive
- `manual`: always prompt
- `off`/`--yolo`: bypass all approvals

#### Layer 2 (Plugin)

Pi tool allowlisting via `pier_delegate(allowed_tools=[...])`:

| Pi Tool | Risk Level | Default |
|---------|-----------|---------|
| `read` | Low | Allowed |
| `grep` | Low | Allowed |
| `find` | Low | Allowed |
| `ls` | Low | Allowed |
| `write` | Medium | Allowed (gated by workdir) |
| `edit` | Medium | Allowed (gated by workdir) |
| `bash` | High | Allowed (Hermes approval gating) |
| Extension tools | Variable | Depends on extension |

#### Layer 3 (Extension)

Runtime permission gating via Pi TypeScript extensions. See Section 4.5 for extension permission patterns.

### 7.4 Credential Isolation

| Concern | Mechanism |
|---------|-----------|
| **Pi should not see Hermes credentials** | Pi receives credentials only for the provider it needs, passed via env var or RPC runtime override. Hermes's credential pool is never exposed in full. |
| **Pi's own credentials** | Managed by Pi's auth system (`~/.pi/agent/auth.json`). Hermes does not read or modify Pi's credential store. |
| **Cross-provider auth (Layer 3)** | Hermes resolves credentials from its pool, passes per-session key as ACP metadata. Pi session is ephemeral — key is forgotten when session ends. |
| **Credential in logs** | Secret redaction (`security.redact_secrets: true`) strips credentials from Hermes logs and session transcripts. |
| **Pi session files** | JSONL files in `~/.pi/agent/sessions/` may contain tool output. Do not run Pi with sensitive credentials in environments where session files are shared. |

### 7.5 Containerization

For untrusted or unattended work, Pi (and by extension Pier) should run inside a container.

**Docker-based isolation:**

```bash
# Build a Pier-aware Pi container
docker build -t pi-agent:latest -f- . <<'EOF'
FROM node:22-slim
RUN npm install -g @earendil-works/pi-coding-agent
WORKDIR /workspace
ENTRYPOINT ["pi", "--mode", "rpc"]
EOF

# Run Pi via Pier in container
docker run --rm \
  -v $(pwd):/workspace:rw \
  -e ANTHROPIC_API_KEY \
  -e PIER_WORKDIR=/workspace \
  pi-agent:latest \
  --provider anthropic --model claude-sonnet-4
```

**Containerization recommendations:**

| Concern | Recommendation |
|---------|---------------|
| **Filesystem access** | Mount only workspace paths. Do NOT mount `~/.pi/agent` or `~/.hermes`. |
| **Network access** | Restrict when not needed (`--network none`). Allow only provider API endpoints when needed. |
| **Credentials** | Pass minimum required API keys. Prefer short-lived credentials. |
| **Resource limits** | Set memory/CPU limits (`--memory 4g --cpus 2`). Prevent runaway resource consumption. |
| **Result extraction** | Review diffs before copying results back to trusted systems. Use `git diff` to inspect changes. |
| **Package installation** | Pre-install dependencies; do not run `npm install` inside containerized sessions unless explicitly allowed. |

### 7.6 Workspace Isolation

Pier uses git worktrees for parallel task isolation, following the proven pattern from the `codex` and `claude-code` skills:

```bash
# Create isolated worktree for a Pier task
git worktree add -b pier/fix-issue-42 /tmp/pier-issue-42 main

# Pier operates in the worktree
pier_delegate(prompt="Fix issue #42", workdir="/tmp/pier-issue-42")

# Inspect changes
cd /tmp/pier-issue-42 && git diff

# Merge if good, discard worktree if bad
git worktree remove /tmp/pier-issue-42
```

**Isolation guarantees:**

- **File isolation:** Each worktree is a separate git checkout. Changes in one do not affect others.
- **Git safety:** Worktree branches are regular git branches. Changes are reviewable via `git diff` before merging.
- **Cleanup:** `git worktree remove` deletes the worktree directory. No lingering files.
- **Parallelism:** Multiple Pier tasks can run concurrently in separate worktrees without conflict.

### 7.7 Extension Security (Layer 3)

Pi extensions execute arbitrary TypeScript with full system permissions. Mitigations:

1. **Extension review:** All extensions should be reviewed before installation. Third-party extensions from npm/git should have their source code audited.
2. **Trust on first use:** Pi's project trust mechanism requires user approval before loading project-local extensions for the first time.
3. **CI verification:** Pier extensions used in CI/CD should be pinned to specific git commits or npm versions.
4. **Container boundary:** In high-security environments, run Pier with extensions inside a container with minimal permissions.

### 7.8 Threat Model

| Threat | Likelihood | Impact | Mitigation |
|--------|-----------|--------|------------|
| Pi modifies files outside workspace | Medium | High | Containerization, workdir isolation, extension permission gating |
| Pi exfiltrates credentials | Low | Critical | Container network isolation, credential scoping per session |
| Pi session file leaks secrets in tool output | Medium | High | Secret redaction, session file access control |
| Malicious Pi extension | Low | Critical | Extension review, containerization, CI pinning |
| Prompt injection via workspace files | Medium | Medium | Containerization, workspace file review |
| Protocol desync causes orphaned processes | Medium | Medium | Process lifecycle management, heartbeat monitoring, graceful shutdown |
| Pi runs excessive LLM calls (cost spike) | Medium | Medium | `max_turns` limit, cost tracking, budget alerts |

---

## 8. Dogfooding Acceptance Criteria

### 8.1 Dogfooding Phases

Dogfooding follows the phased rollout defined in [ADR-003](adr-003-dogfooding-strategy.md):

| Phase | Timeline | Description | Primary Metric |
|-------|----------|-------------|---------------|
| **Phase 1: Side-by-side** | Weeks 1-2 | Layer 1 runs alongside existing coding agent skills. Same tasks delegated to both. | ≥ 90% task completion rate |
| **Phase 2: Shadow mode** | Weeks 3-4 | Layer 2 runs in parallel with terminal mode. RPC output logged, not acted on. | Zero protocol desyncs in 200 sessions |
| **Phase 3: Primary with fallback** | Weeks 5-8 | Layer 2 becomes primary; terminal mode is fallback. Real user tasks flow through Pier. | < 5% fallback rate, zero data-loss |
| **Phase 4: Full switch** | Week 9+ | Layer 2 is sole delegation path for Pi-compatible tasks. Layer 3 development begins. | Two weeks with zero fallback triggers |

### 8.2 Quantitative Gates for Graduation

Each phase has objective, measurable gates. No subjective "feels stable enough."

#### Phase 1 Gates

| Gate | Threshold | Measurement |
|------|-----------|-------------|
| Task completion rate | ≥ 90% of terminal-mode baseline | Run 50 identical tasks through Pier (Layer 1) and terminal mode (claude-code); compare completion rates |
| Task success rate | ≥ 85% | Tasks that produce correct, working output (not just non-error completion) |
| Mean time to completion | ≤ 150% of terminal mode | Pier should not be dramatically slower |
| Error recovery | 3/3 basic errors handled | Pi not installed, auth failure, timeout → graceful messaging to user |

**Phase 1 dogfooding tasks (50 tasks minimum):**

| Category | Count | Example |
|----------|-------|---------|
| File creation | 10 | "Create a Python module for user authentication" |
| Bug fixes | 10 | "Fix the TypeError in utils.py line 47" |
| Code review | 10 | "Review the last commit for security issues" |
| Refactoring | 10 | "Extract the helper functions into a utils/ directory" |
| Test generation | 10 | "Write unit tests for the Calculator class" |

#### Phase 2 Gates

| Gate | Threshold | Measurement |
|------|-----------|-------------|
| Protocol desyncs | 0 in 200 sessions | Compare RPC events vs terminal output for same prompts; verify no event mismatch |
| Streaming correctness | ≥ 99% event delivery | Verify every `text_delta` and `tool_execution_*` event arrives in order, no drops |
| Cancellation reliability | 100% success (50/50) | Abort 50 long-running tasks; verify all terminate within 5 seconds |
| Session stats accuracy | ±5% of Pi's own reporting | Compare `get_session_stats` totals against Pi's internal cost tracking |

**Phase 2 shadow-mode tasks (200 sessions minimum):**

All tasks run through BOTH RPC and terminal mode. RPC events are compared against terminal output for consistency. Any divergence is a failure.

#### Phase 3 Gates

| Gate | Threshold | Measurement |
|------|-----------|-------------|
| Fallback rate | < 5% | Percentage of Pier tasks that fall back to terminal mode |
| Data-loss events | 0 | Corrupted workspace, lost output, orphaned processes |
| User-reported issues requiring code changes | ≤ 3 | Tracked in GitHub issues |
| Time from bug report to fix | ≤ 24 hours | From issue filed to fix merged |

#### Phase 4 Gates

| Gate | Threshold | Measurement |
|------|-----------|-------------|
| Zero fallback weeks | 2 consecutive | No Pier task falls back to terminal mode for 2 weeks |
| Task completion rate (production) | ≥ 95% | Over all real user tasks in the period |
| Protocol desyncs (production) | 0 | Over all real user sessions in the period |

### 8.3 Overall Dogfooding Success Criteria

| Metric | Target |
|--------|--------|
| Tasks completed via Pier (all phases) | ≥ 200 |
| Protocol desync events (all phases) | 0 |
| Data-loss events (corrupted workspace, lost output) | 0 |
| Rollback events triggered | ≤ 5 (all resolved within Phase 3) |
| User-reported issues requiring code changes | ≤ 3 |
| Time from bug report to fix deployed | ≤ 24 hours |

### 8.4 Rollback Path

At any phase, the user can revert to terminal-mode delegation:

1. **Immediate rollback.** Disable the Pier skill/plugin in Hermes config. Existing coding agent skills (codex, claude-code, opencode) are unaffected — they were never removed, just superseded.
2. **Session recovery.** Pi RPC sessions are JSONL files in `~/.pi/agent/sessions/`. Interrupted sessions can be resumed with `pi -c` (continue) or `pi -r <session-id>`. Hermes does not depend on Pi session state for its own operation.
3. **Workspace integrity.** Pier operates in git worktrees. If a worktree is corrupted, delete it and create a fresh one. The main repository is never directly modified.
4. **No data migration.** Neither Layer 1 nor Layer 2 modifies Hermes's internal state, session database, or memory. Rollback is a configuration change, not a data migration.

### 8.5 Benchmark Dataset Construction

The 50-task dataset used in Phase 1 is constructed as follows:

1. **Task sources:** Real tasks from existing Hermes coding sessions. 25 tasks that succeeded with terminal mode, 25 tasks that initially failed and needed retry.
2. **Task variety:** File creation, bug fixes, code review, refactoring, test generation. Mix of Python, TypeScript, and shell tasks.
3. **Task complexity:** Simple (1-2 file changes), medium (3-5 files), complex (multi-file refactor with test updates).
4. **Task storage:** Dataset committed as `tests/plugins/pier/fixtures/dogfooding_tasks.json`.

### 8.6 Reporting

Each dogfooding phase produces a report:

```json
{
  "phase": "phase_1",
  "start_date": "2026-08-01",
  "end_date": "2026-08-14",
  "metrics": {
    "tasks_run": 50,
    "tasks_completed": 47,
    "completion_rate": 0.94,
    "mean_completion_time_seconds": 45.2,
    "errors_encountered": {
      "pi_not_installed": 0,
      "auth_failure": 1,
      "timeout": 2
    }
  },
  "comparison_to_baseline": {
    "baseline_completion_rate": 0.96,
    "delta": -0.02,
    "verdict": "WITHIN_TOLERANCE"
  },
  "issues_filed": ["#12: Timeout on long-running shell tasks"],
  "passed_gates": true,
  "proceed_to_next_phase": true
}
```

---

## Appendix A: Implementation Roadmap

| Milestone | Layer | Deliverables | Dependencies |
|-----------|-------|-------------|--------------|
| M1: Skill spec | Layer 1 | SKILL.md, delegation patterns, error handling | Pi installed |
| M2: Skill implementation | Layer 1 | Working pier skill in Hermes | M1 complete |
| M3: RPC client | Layer 2 | `rpc_client.py` with JSONL framing, process lifecycle | Pi with `--mode rpc` |
| M4: Event parser | Layer 2 | `event_parser.py` mapping all 18 event types | M3 complete |
| M5: Session manager | Layer 2 | `session_manager.py` with fork/clone/compact/abort | M3 complete |
| M6: Tool bridge | Layer 2 | `tool_bridge.py` with tool mapping and discovery | M4 complete |
| M7: Plugin integration | Layer 2 | Full plugin registration, config, fallback chain | M3-M6 complete |
| M8: Integration tests | Layer 2 | Test suite against real Pi installation | M7 complete |
| M9: Dogfooding | Layer 1+2 | Phased rollout per ADR-003 | M2, M8 complete |
| M10: ACP bridge (future) | Layer 3 | ACP client for Hermes ↔ Pi ACP adapter | M9 complete, ACP spec stable |

## Appendix B: Glossary

| Term | Definition |
|------|-----------|
| **ACP** | Agent Client Protocol (JetBrains/Zed) — IDE↔coding-agent communication |
| **Agent Skills** | A standard for self-contained capability packages (SKILL.md + scripts + references) |
| **JSONL** | JSON Lines — one JSON object per line, `\n` delimited |
| **MCP** | Model Context Protocol (Anthropic) — agent↔tool communication |
| **Pier** | The Hermes↔Pi integration itself (this project) |
| **Pi** | The coding agent from `earendil-works/pi` |
| **Pi RPC** | Pi's native JSONL-based command/event protocol over stdin/stdout |
| **RPC** | Remote Procedure Call — in this context, Pi's JSONL protocol |
