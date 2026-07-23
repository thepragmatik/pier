# Pi Architecture Deep-Dive

> Comprehensive research document on the Pi coding agent's architecture, CLI modes, extension system, RPC protocol, configuration model, and security model.
>
> Repository: https://github.com/earendil-works/pi (monorepo: pi-mono)
> Packages: `pi-ai`, `pi-agent-core`, `pi-coding-agent`, `pi-tui`, `pi-storage-sqlite-node`, `pi-server`
> License: MIT

---

## Table of Contents

1. [Package Architecture (Monorepo Structure, SDK APIs)](#1-package-architecture)
2. [CLI Modes](#2-cli-modes)
3. [RPC Protocol](#3-rpc-protocol)
4. [Extension System](#4-extension-system)
5. [Tool System](#5-tool-system)
6. [Skill System](#6-skill-system)
7. [Configuration Model](#7-configuration-model)
8. [Session Management](#8-session-management)
9. [Authentication](#9-authentication)
10. [Security Model](#10-security-model)

---

## 1. Package Architecture

Pi is a **TypeScript monorepo** (npm workspaces, biome for linting, vitest for testing) hosted as `earendil-works/pi-mono`. It is published as several npm packages under the `@earendil-works` scope.

### Monorepo Layout

```
pi/
├── packages/
│   ├── ai/             # @earendil-works/pi-ai — Unified LLM API, provider abstractions
│   ├── agent/          # @earendil-works/pi-agent-core — Stateful agent loop, tool execution, events
│   ├── coding-agent/   # @earendil-works/pi-coding-agent — Full coding agent: CLI, TUI, RPC, SDK, extensions, skills
│   ├── tui/            # @earendil-works/pi-tui — Terminal UI components
│   ├── storage/        # @earendil-works/pi-storage-sqlite-node — SQLite session backend
│   └── server/         # @earendil-works/pi-server — HTTP server mode
├── AGENTS.md           # Development rules and conventions
├── CONTRIBUTING.md     # Contributor guidelines (auto-close for new contributors)
├── SECURITY.md         # Security policy
└── package.json        # Root workspace config
```

### Layer Architecture

```
pi-ai (providers, models, auth, tools, streaming)
   ↓
pi-agent-core (Agent class, agent loop, tool execution, events)
   ↓
pi-coding-agent (CLI, TUI, RPC, SDK, extensions, skills, sessions, settings)
```

#### @earendil-works/pi-ai

The **LLM abstraction layer**. Key concepts:

- **Provider**: runtime unit owning a model catalog, auth resolution, and streaming behavior. Examples: `anthropicProvider()`, `openaiProvider()`, `openrouterProvider()`.
- **Models collection**: `createModels()` or `builtinModels()` holds providers and routes requests.
- **API implementations**: shared wire protocols — `anthropic-messages`, `openai-responses`, `openai-completions` — reused across providers (xAI, Groq, Cerebras, OpenRouter all share `openai-completions`).
- **Tool definitions**: TypeBox schemas for type-safe tool definitions and automatic argument validation.
- **Auth**: per-provider resolution chain (stored credentials → env vars → OAuth). Supports `CredentialStore` interface for persistent auth.
- **Streaming**: events (`start`, `text_delta`, `thinking_delta`, `toolcall_delta`, `done`, `error`) with both streaming (`stream`) and complete (`complete`) APIs.
- **Browser usage**: tree-shakeable; individual provider factories are subpath imports.

#### @earendil-works/pi-agent-core

The **stateful agent engine**. Key concepts:

- **Agent class**: wraps the agent loop with state management, event subscriptions, and lifecycle.
- **agentLoop / agentLoopContinue**: low-level imperative API for direct control.
- **AgentMessage**: flexible message type supporting custom roles via declaration merging.
- **AgentState**: `systemPrompt`, `model`, `thinkingLevel`, `tools`, `messages`, `isStreaming`, `streamingMessage`, `pendingToolCalls`, `errorMessage`.
- **Event flow**: `agent_start` → `turn_start` → `message_start/end` (user) → `message_start/update/end` (assistant) → `tool_execution_start/update/end` → `turn_end` → `agent_end`.
- **Steering/Follow-up**: queue messages while agent is running (`steer()` during tool execution, `followUp()` after completion).
- **Tool execution**: parallel mode (default) or sequential (per-tool or global).
- **transformContext / convertToLlm**: hooks for pruning, compaction, and custom message conversion.
- **Proxy support**: `streamProxy()` for browser apps routing through a backend.

#### @earendil-works/pi-coding-agent

The **full coding agent** — CLI entry point, TUI, RPC mode, SDK, extension system, skill system, session management, settings. Key exports:

- `createAgentSession()` — main factory for embedding Pi in other apps
- `AgentSession` — session lifecycle, prompting, queueing, tree navigation, compaction
- `AgentSessionRuntime` — session replacement (`newSession`, `switchSession`, `fork`, `clone`, `importFromJsonl`)
- `DefaultResourceLoader` — discovers extensions, skills, prompts, themes, context files
- `SettingsManager` — global + project settings merging
- `SessionManager` — JSONL session persistence with tree structure
- `ModelRuntime` — model discovery, auth resolution, runtime API key overrides
- `defineTool()` — custom tool definition helper
- `resolveCliModel()` / `resolveModelScopeWithDiagnostics()` — CLI model parsing helpers

---

## 2. CLI Modes

Pi runs in four modes, controlled by flags and the `--mode` option.

### Interactive Mode (default)

Full terminal UI with:
- Startup header showing loaded AGENTS.md files, prompt templates, skills, extensions
- Editor with `@` file references, path completion, multi-line (Shift+Enter), external editor (Ctrl+G)
- `/commands` for built-in and extension-registered operations
- Keyboard shortcuts: Ctrl+L (model selector), Ctrl+P/Shift+Ctrl+P (cycle models), Shift+Tab (cycle thinking level), Ctrl+O (collapse/expand tool output), Ctrl+T (collapse/expand thinking), Escape (cancel/abort)
- Message queue: Enter = steering (delivered after current tool calls), Alt+Enter = follow-up (after agent finishes)
- Footer: cwd, session name, token/cache usage, cost, context %, current model

### Print Mode (`-p`, `--print`)

Non-interactive one-shot: prints the assistant response to stdout and exits. Reads piped stdin and merges it into the prompt. Useful for scripting:

```bash
pi -p "Summarize this codebase"
cat README.md | pi -p "Summarize this text"
```

### JSON Mode (`--mode json`)

Non-interactive mode that outputs all agent events as JSON Lines to stdout. Events match the RPC event schema (see Section 3). Used for programmatic consumption where a full protocol is not needed.

### RPC Mode (`--mode rpc`)

Full-duplex JSONL protocol over stdin/stdout for embedding Pi in IDEs, custom UIs, or automated pipelines. See Section 3 for the complete protocol specification.

### CLI Options Reference

**Modes**: `-p`/`--print`, `--mode json`, `--mode rpc`, `--export`

**Model options**: `--provider`, `--model` (supports `provider/id:thinking`), `--api-key`, `--thinking` (off|minimal|low|medium|high|xhigh|max), `--models` (cycling scoped models), `--list-models`

**Session options**: `-c`/`--continue`, `-r`/`--resume`, `--session <path|id>`, `--fork <path|id>`, `--session-dir`, `--no-session` (ephemeral), `--name`/`-n`

**Tool options**: `-t`/`--tools` (allowlist), `-xt`/`--exclude-tools`, `-nbt`/`--no-builtin-tools`, `-nt`/`--no-tools`

**Resource options**: `-e`/`--extension`, `--no-extensions`, `--skill`, `--no-skills`, `--prompt-template`, `--no-prompt-templates`, `--theme`, `--no-themes`, `-nc`/`--no-context-files`

**Other**: `--system-prompt`, `--append-system-prompt`, `--verbose`, `-a`/`--approve`, `-na`/`--no-approve`, `--offline`

**Environment variables**: `PI_CODING_AGENT_DIR`, `PI_CODING_AGENT_SESSION_DIR`, `PI_PACKAGE_DIR`, `PI_OFFLINE`, `PI_SKIP_VERSION_CHECK`, `PI_TELEMETRY`, `PI_CACHE_RETENTION`, `VISUAL`/`EDITOR`. Bash tool sessions receive `PI_SESSION_ID`, `PI_SESSION_FILE`, `PI_PROVIDER`, `PI_MODEL`, `PI_REASONING_LEVEL`.

---

## 3. RPC Protocol

RPC mode provides a complete JSONL-based protocol over stdin/stdout for embedding Pi in external applications. It uses **strict LF (`\n`) delimiters** — clients must split on `\n` only and not use generic line readers (Node's `readline` is NOT protocol-compliant because it splits on Unicode U+2028/U+2029 inside JSON strings).

### Protocol Framing

```
Client → stdin:   JSON command (one line)
Server → stdout:  JSON response (one line) + streaming events
```

All commands support an optional `id` field for request/response correlation.

### Commands

| Category | Command | Description |
|----------|---------|-------------|
| **Prompting** | `prompt` | Send a user prompt (with optional `streamingBehavior`: `steer` or `followUp`) |
| | `steer` | Queue steering message during streaming |
| | `follow_up` | Queue follow-up message after agent finishes |
| | `abort` | Cancel current agent operation |
| | `new_session` | Start fresh session (cancellable by extensions) |
| **State** | `get_state` | Current model, thinking level, streaming/compacting status, session info |
| | `get_messages` | All conversation messages |
| **Model** | `set_model` | Switch to specific model by provider/id |
| | `cycle_model` | Cycle to next available model |
| | `get_available_models` | List all configured models |
| **Thinking** | `set_thinking_level` | Set reasoning level (off|minimal|low|medium|high|xhigh|max) |
| | `cycle_thinking_level` | Cycle through available levels |
| | `get_available_thinking_levels` | List levels supported by current model |
| **Queue** | `set_steering_mode` | `all` or `one-at-a-time` (default) |
| | `set_follow_up_mode` | `all` or `one-at-a-time` (default) |
| **Compaction** | `compact` | Manual context compaction (optional custom instructions) |
| | `set_auto_compaction` | Enable/disable automatic compaction |
| **Retry** | `set_auto_retry` | Enable/disable automatic retry on transient errors |
| | `abort_retry` | Cancel in-progress retry |
| **Bash** | `bash` | Execute shell command (output streams as events, added to next prompt context) |
| | `abort_bash` | Abort running bash command |
| **Session** | `get_session_stats` | Token usage, cost, context window usage |
| | `export_html` | Export session to HTML file |
| | `switch_session` | Load different session file |
| | `fork` | Create fork from specific user message |
| | `clone` | Duplicate active branch to new session |
| | `get_fork_messages` | List user messages available for forking |
| | `get_entries` | All session entries (append-order tree, cursor-based) |
| | `get_tree` | Full session tree structure |
| | `get_last_assistant_text` | Text of last assistant message |
| | `set_session_name` | Set display name |
| **Commands** | `get_commands` | List available extension commands, prompt templates, and skills |

### Events (streamed to stdout)

| Event | Description |
|-------|-------------|
| `agent_start` | Agent begins processing |
| `agent_end` | Low-level run completes (may still retry or compact) |
| `agent_settled` | Fully settled; no retry/compaction/follow-up remains |
| `turn_start` / `turn_end` | One LLM call + tool executions |
| `message_start` / `message_update` / `message_end` | Message lifecycle with streaming deltas |
| `bash_execution_update` | Direct bash command output chunk |
| `tool_execution_start` / `_update` / `_end` | Tool execution lifecycle |
| `queue_update` | Pending steering/follow-up queue changed |
| `compaction_start` / `compaction_end` | Context compaction lifecycle |
| `auto_retry_start` / `auto_retry_end` | Transient error retry lifecycle |
| `summarization_retry_*` | Summarization retry lifecycle |
| `extension_error` | Extension threw an error |

Message update `assistantMessageEvent` delta types: `start`, `text_start`, `text_delta`, `text_end`, `thinking_start`, `thinking_delta`, `thinking_end`, `toolcall_start`, `toolcall_delta`, `toolcall_end`, `done`, `error`.

### Extension UI Protocol

When extensions call `ctx.ui` methods in RPC mode, they translate to an `extension_ui_request` / `extension_ui_response` sub-protocol:

- **Dialog methods** (`select`, `confirm`, `input`, `editor`): emit `extension_ui_request` on stdout, block until client sends `extension_ui_response` with matching `id`. Support optional `timeout`.
- **Fire-and-forget methods** (`notify`, `setStatus`, `setWidget`, `setTitle`): emit request but do not expect response.
- `ctx.mode` is `"rpc"` and `ctx.hasUI` is `true` in RPC mode.

---

## 4. Extension System

Extensions are TypeScript modules that extend Pi with custom tools, commands, event handlers, keyboard shortcuts, and UI components. They are the primary customization mechanism.

### Extension Architecture

```
Extension (TypeScript module)
  └── default export: (pi: ExtensionAPI) => void | Promise<void>
```

Extensions can be:

- **Single file**: `~/.pi/agent/extensions/my-extension.ts`
- **Directory with index.ts**: `extensions/my-extension/index.ts`
- **Package with dependencies**: `extensions/my-extension/package.json` + `node_modules/`
- **Inline factories** via SDK: `DefaultResourceLoader({ extensionFactories: [...] })`
- **Pi packages** shared via npm/git

### ExtensionAPI Methods

| Method | Description |
|--------|-------------|
| `pi.registerTool(tool)` | Register a tool the LLM can call |
| `pi.registerCommand(name, handler)` | Register a `/command` |
| `pi.registerShortcut(keys, handler)` | Register keyboard shortcut |
| `pi.registerFlag(name, handler)` | Register CLI flag |
| `pi.registerProvider(config)` | Register a dynamic LLM provider |
| `pi.registerEntryRenderer(type, renderer)` | Custom entry rendering in TUI |
| `pi.on(event, handler)` | Subscribe to lifecycle events |
| `pi.sendMessage(text)` | Send a message to the agent from extensions |
| `pi.appendEntry(type, data)` | Persist state in session file |
| `pi.events` | Event bus for extension-to-extension communication |

### Event Lifecycle

```
pi starts
  ├─ project_trust (user/global + CLI extensions only)
  ├─ session_start { reason: "startup" }
  └─ resources_discover { reason: "startup" }

prompt sent:
  ├─ input (can intercept/transform/handle)
  ├─ before_agent_start (inject message, modify system prompt)
  ├─ agent_start
  │   └─ [turn loop]
  │       ├─ context (modify messages before LLM call)
  │       ├─ before_provider_headers
  │       ├─ before_provider_request
  │       ├─ after_provider_response
  │       ├─ tool_call (block/modify)
  │       └─ tool_result (modify)
  ├─ agent_end
  └─ agent_settled

Session ops: session_before_switch, session_before_fork, session_before_compact, session_before_tree
             session_shutdown, session_start (re-fired)
Model ops: model_select, thinking_level_select
```

### ExtensionContext (ctx) Capabilities

| API | Description |
|-----|-------------|
| `ctx.ui.select()` | Multi-choice prompt |
| `ctx.ui.confirm()` | Yes/no confirmation |
| `ctx.ui.input()` | Free-form text input |
| `ctx.ui.editor()` | Multi-line editor |
| `ctx.ui.notify()` | Informational notification |
| `ctx.ui.setStatus()` | Footer status text |
| `ctx.ui.setWidget()` | Widget above editor (TUI) |
| `ctx.ui.custom()` | Full TUI custom component (not supported in RPC mode) |
| `ctx.sessionManager` | Access session file, entries, tree |
| `ctx.settingsManager` | Access settings |
| `ctx.getSystemPrompt()` | Current chained system prompt |
| `ctx.getApiKeys(providerId)` | Resolve API keys |
| `ctx.mode` | `"tui"`, `"rpc"`, `"print"`, `"json"`, `"sdk"` |
| `ctx.hasUI` | Whether user interaction methods are available |

### Extension Locations

| Location | Scope |
|----------|-------|
| `~/.pi/agent/extensions/*.ts` | Global |
| `~/.pi/agent/extensions/*/index.ts` | Global (subdirectory) |
| `.pi/extensions/*.ts` | Project-local (after trust) |
| `.pi/extensions/*/index.ts` | Project-local (after trust) |
| `settings.json: extensions[]` | Additional paths |
| CLI `-e` flag | One-shot (repeatedly) |

---

## 5. Tool System

Pi provides a set of built-in tools that the LLM can call, plus the ability to register custom tools via extensions or SDK.

### Built-in Tools

| Tool | Description |
|------|-------------|
| `read` | Read file contents |
| `write` | Write content to file |
| `edit` | Targeted find-and-replace editing (returns unified diff patch) |
| `bash` | Execute shell commands |
| `grep` | Search file contents |
| `find` | Find files by name |
| `ls` | List directory contents |

Default built-ins (when no `--tools` specified): `read`, `bash`, `edit`, `write`.

### Tool Execution

- **Parallel mode** (default): preflight tools sequentially, execute allowed ones concurrently. Emit `tool_execution_end` as soon as each tool is finalized, then toolResult messages in assistant source order.
- **Sequential mode**: execute tool calls one at a time (legacy behavior). Forced when any tool in a batch has `executionMode: "sequential"`.
- **Preflight phase**: `beforeToolCall` hook runs after argument validation; can block execution.
- **Postprocess phase**: `afterToolCall` hook runs after execution; can signal `terminate: true` to skip follow-up LLM call.
- **Error handling**: throw errors (don't return error messages as content). Caught and reported to LLM as `isError: true`.

### Tool Definition (TypeScript)

```typescript
const myTool: AgentTool = {
  name: "my_tool",
  label: "My Tool",
  description: "Does something useful",
  parameters: Type.Object({
    input: Type.String({ description: "Input value" }),
  }),
  executionMode: "sequential", // optional per-tool override
  execute: async (toolCallId, params, signal, onUpdate, ctx) => {
    onUpdate?.({ content: [{ type: "text", text: "Working..." }], details: {} });
    return {
      content: [{ type: "text", text: `Result: ${params.input}` }],
      details: {},
    };
  },
};
```

### Tool Selection

- `--tools <list>`: allowlist specific tools (built-in, extension, and custom)
- `--exclude-tools <list>`: disable specific tools
- `--no-builtin-tools`: disable default built-ins, keep extension/custom tools
- `--no-tools`: disable all tools
- SDK: `tools: ["read", "bash", "my_tool"]`, `excludeTools: ["ask_question"]`, `customTools: [myTool]`

---

## 6. Skill System

Pi implements the [Agent Skills standard](https://agentskills.io) — self-contained capability packages loaded on-demand by the agent.

### Skill Structure

```
my-skill/
├── SKILL.md              # Required: YAML frontmatter + markdown instructions
├── scripts/              # Helper scripts
│   └── process.sh
├── references/           # Detailed docs loaded on-demand
│   └── api-reference.md
└── assets/               # Other supporting files
    └── template.json
```

### SKILL.md Format

```markdown
---
name: my-skill
description: What this skill does and when to use it. Be specific.
---

# My Skill

## Setup
Run once before first use:
```bash
cd /path/to/skill && npm install
```

## Usage
```bash
./scripts/process.sh <input>
```
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Max 64 chars, lowercase a-z/0-9/hyphens |
| `description` | Yes | Max 1024 chars |
| `license` | No | License name |
| `compatibility` | No | Max 500 chars, environment requirements |
| `metadata` | No | Arbitrary key-value mapping |
| `allowed-tools` | No | Pre-approved tools (experimental) |
| `disable-model-invocation` | No | `true` = hidden from system prompt, requires `/skill:name` |

### Skill Discovery

Pi scans these locations at startup:
- Global: `~/.pi/agent/skills/`, `~/.agents/skills/`
- Project (after trust): `.pi/skills/`, `.agents/skills/` (cwd + ancestors up to git root)
- Packages: `skills/` directories or `pi.skills` in package.json
- Settings: `skills` array
- CLI: `--skill <path>` (repeatable, additive even with `--no-skills`)

### Progressive Disclosure

1. At startup, Pi scans skill locations and extracts names + descriptions
2. System prompt includes available skills in XML per the spec
3. When a task matches, the agent uses `read` to load full SKILL.md
4. Skills can also be invoked explicitly via `/skill:name`

### Skill Commands

Skills register as `/skill:name` commands (when `enableSkillCommands: true`):
```
/skill:brave-search           # Load and execute
/skill:pdf-tools extract      # Load with arguments
```

### Cross-Harness Compatibility

Pi can load skills from other agent directories via settings:
```json
{
  "skills": ["~/.claude/skills", "~/.codex/skills"]
}
```

---

## 7. Configuration Model

Pi uses a two-layer JSON settings system with project-over-global merging.

### Settings Files

| Location | Scope | Description |
|----------|-------|-------------|
| `~/.pi/agent/settings.json` | Global | All projects |
| `.pi/settings.json` | Project | Overrides global (merged, not replaced) |

Nested objects are merged (project values override individual keys in global).

### Settings Categories

| Category | Key Settings |
|----------|-------------|
| **Model & Thinking** | `defaultProvider`, `defaultModel`, `defaultThinkingLevel`, `hideThinkingBlock`, `showCacheMissNotices`, `thinkingBudgets` |
| **UI & Display** | `theme`, `externalEditor`, `quietStartup`, `defaultProjectTrust`, `collapseChangelog`, `editorPaddingX`, `outputPad` |
| **Compaction** | `compaction.enabled`, `compaction.reserveTokens` (default 16384), `compaction.keepRecentTokens` (default 20000) |
| **Branch Summary** | `branchSummary.reserveTokens`, `branchSummary.skipPrompt` |
| **Retry** | `retry.enabled` (default true), `retry.maxRetries` (3), `retry.baseDelayMs` (2000), `retry.provider.timeoutMs`, `retry.provider.maxRetries` (0), `retry.provider.maxRetryDelayMs` (60000) |
| **Message Delivery** | `steeringMode` (`all` or `one-at-a-time`), `followUpMode`, `transport` (`sse`, `websocket`, `websocket-cached`, `auto`) |
| **Network** | `httpProxy` |
| **Terminal/Images** | `terminal.showImages`, `images.autoResize`, `images.blockImages` |
| **Shell** | `shellPath`, `shellCommandPrefix`, `npmCommand` |
| **Sessions** | `sessionDir` |
| **Model Cycling** | `enabledModels` (glob patterns) |
| **Resources** | `packages`, `extensions`, `skills`, `prompts`, `themes`, `enableSkillCommands` |
| **Telemetry** | `enableInstallTelemetry` |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `PI_CODING_AGENT_DIR` | Override config directory (default: `~/.pi/agent`) |
| `PI_CODING_AGENT_SESSION_DIR` | Override session storage directory |
| `PI_PACKAGE_DIR` | Override package directory |
| `PI_OFFLINE` | Disable all startup network operations |
| `PI_SKIP_VERSION_CHECK` | Skip update check |
| `PI_TELEMETRY` | Override telemetry and provider attribution headers |
| `PI_CACHE_RETENTION` | `long` for extended prompt cache |

### Custom Provider/Model Configuration

Add custom providers via `~/.pi/agent/models.json` if they speak a supported API format (OpenAI, Anthropic, Google). For custom APIs or OAuth, use extensions.

### Pi Packages

Bundle and share extensions, skills, prompts, and themes via npm or git:

```bash
pi install npm:@foo/pi-tools
pi install git:github.com/user/repo
pi install git:github.com/user/repo@v1  # pinned tag/commit
pi list
pi update --all
```

Package manifest (`package.json`):
```json
{
  "name": "my-pi-package",
  "keywords": ["pi-package"],
  "pi": {
    "extensions": ["./extensions"],
    "skills": ["./skills"],
    "prompts": ["./prompts"],
    "themes": ["./themes"]
  }
}
```

---

## 8. Session Management

Sessions use **JSONL files** with a tree structure (`id`/`parentId` linking), enabling in-place branching without creating new files.

### File Location

```
~/.pi/agent/sessions/--<path>--/<timestamp>_<uuid>.jsonl
```

### Session Versions

- **v1**: Linear entry sequence (legacy, auto-migrated)
- **v2**: Tree structure with id/parentId
- **v3**: Renamed `hookMessage` role to `custom`

### Entry Types

| Entry type | Description | LLM Context? |
|-----------|-------------|:---:|
| `session` | Header (first line) | No |
| `message` | User/assistant/toolResult messages | Yes |
| `model_change` | Model switch mid-session | Metadata only |
| `thinking_level_change` | Thinking level change | Metadata only |
| `compaction` | Context compaction entry | Yes (summary) |
| `branch_summary` | Branch switch summary | Yes |
| `custom` | Extension state persistence | No |
| `custom_message` | Extension-injected context | Yes |
| `label` | User bookmark on entry | No |
| `session_info` | Session display name | No |
| `bash_execution` | Direct bash execution | Converted to user message |

### Message Types (AgentMessage Union)

- `UserMessage` — role: `"user"`, content: text or (text|image)[]
- `AssistantMessage` — role: `"assistant"`, content: (text|thinking|toolCall)[] with `api`, `provider`, `model`, `usage`, `stopReason`
- `ToolResultMessage` — role: `"toolResult"`, `toolCallId`, `toolName`, `isError`
- `BashExecutionMessage` — role: `"bashExecution"`, command, output, exitCode
- `CustomMessage` — role: `"custom"`, customType (extension identifier)
- `BranchSummaryMessage` — role: `"branchSummary"`, summary, fromId
- `CompactionSummaryMessage` — role: `"compactionSummary"`, summary, tokensBefore

### Tree Branching

```
[user] ── [assistant] ── [user] ── [assistant] ─┬─ [user] ← current leaf
                                                │
                                                └─ [branch_summary] ── [user] ← alternate
```

- `/tree` — navigate in-place, select any point to continue from
- `/fork` — create new session file from previous user message
- `/clone` — duplicate active branch to new session
- `--fork <path|id>` — CLI-level forking
- `/compact` — summarize older messages to fit context window
- **Auto-compaction**: triggered on context overflow (recovers and retries) or when approaching limit (proactive)

### Context Building

`buildContextEntries()` walks from current leaf to root, honoring compaction:
1. Collects all entries on the active path
2. If a `CompactionEntry` is on the path, includes its summary and `retainedTail` (materialized AgentMessage[] kept after compaction)
3. Newer compactions act as self-contained checkpoints with `retainedTail`

### SDK Session Management

```typescript
// In-memory (no persistence)
const { session } = await createAgentSession({
  sessionManager: SessionManager.inMemory(),
});

// New persistent session
const { session } = await createAgentSession({
  sessionManager: SessionManager.create(process.cwd()),
});

// Continue most recent
const { session } = await createAgentSession({
  sessionManager: SessionManager.continueRecent(process.cwd()),
});

// Session replacement (for /new, /resume, /fork, /clone, import)
await runtime.newSession();
await runtime.switchSession("/path/to/session.jsonl");
await runtime.fork("entry-id");
```

---

## 9. Authentication

Pi supports authentication through multiple mechanisms, resolved per-provider.

### Auth Resolution Priority

1. **Runtime overrides** (`modelRuntime.setRuntimeApiKey("anthropic", "sk-...")`) — not persisted
2. **Stored credentials** in `~/.pi/agent/auth.json` (API keys or OAuth tokens via `/login`)
3. **Environment variables** (e.g., `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`)
4. **Fallback resolver** (for custom provider keys from `models.json`)

### Provider Auth Methods

**API keys** (majority of providers): resolved from env vars or stored credentials.
**OAuth flows**: Anthropic (subscription), OpenAI (ChatGPT Plus/Pro/Codex), GitHub Copilot, Vertex AI.
**AWS credentials**: Amazon Bedrock (ambient profiles, access keys, ECS roles, web identity tokens).
**Google ADC**: Vertex AI (gcloud Application Default Credentials, service account files).

### CredentialStore

The `CredentialStore` interface governs persistent credential storage:
- `read(providerId)` — read credential
- `list()` — non-secret metadata only
- `modify(providerId, fn)` — serialized read-modify-write (only write path)
- `delete(providerId)` — remove
- OAuth token refresh runs inside `modify` to prevent concurrent double-refresh

### Env Vars for API Keys (Selected Providers)

| Provider | Variable(s) |
|----------|------------|
| Anthropic | `ANTHROPIC_API_KEY` or `ANTHROPIC_OAUTH_TOKEN` |
| OpenAI | `OPENAI_API_KEY` |
| Azure OpenAI | `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_BASE_URL` or `AZURE_OPENAI_RESOURCE_NAME` |
| Google | `GEMINI_API_KEY` |
| Vertex AI | `GOOGLE_CLOUD_API_KEY` or `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` + ADC |
| DeepSeek | `DEEPSEEK_API_KEY` |
| xAI | `XAI_API_KEY` |
| OpenRouter | `OPENROUTER_API_KEY` |
| Amazon Bedrock | Ambient AWS profiles/credentials |
| Hugging Face | `HF_TOKEN` |
| GitHub Copilot | `COPILOT_GITHUB_TOKEN` |

### Interactive Login

In interactive mode, `/login` opens an OAuth flow for subscription-based providers. `/logout` revokes stored credentials.

---

## 10. Security Model

Pi has **no built-in sandbox**. It runs with the full permissions of the user account that starts it.

### Design Tenets

1. **No permission popups**: Pi intentionally does not prompt for every action. Run in a container, or implement permission gates via extensions.
2. **No sandbox**: Real isolation comes from the operating system or containerization. Pi defers to OS-level, VM-level, or container-level boundaries.
3. **Project trust is not a sandbox**: Project trust is only an input-loading guard. It prevents a repo from silently changing Pi's settings or extensions before you approve it. It does not restrict what the model can ask tools to do.

### Project Trust Mechanism

Pi checks for project resources requiring trust:
- `.pi/settings.json`
- `.pi/extensions`, `.pi/skills`, `.pi/prompts`, `.pi/themes`
- `.pi/SYSTEM.md` or `.pi/APPEND_SYSTEM.md`
- `.agents/skills` in cwd or ancestors

**Trust states**: `ask` (default), `always`, `never`. Set via `defaultProjectTrust` in global settings.
**Persistence**: saved decisions in `~/.pi/agent/trust.json`.
**Non-interactive modes**: `ask` and `never` ignore project resources; `always` trusts them. Use `--approve`/`-a` or `--no-approve`/`-na` to override.

### Containerization Recommendation

For untrusted or unattended work, Pi recommends:
- Run Pi inside a container/VM/sandbox
- Route built-in tool execution into a Gondolin micro-VM
- Mount only workspace paths; avoid mounting `~/.pi/agent`
- Pass minimum required API keys or short-lived credentials
- Restrict network access when not needed
- Review diffs before copying results back to trusted systems

### Package Security

Pi packages run with full system access. Extensions execute arbitrary TypeScript; skills instruct the model to perform any action. Users are advised to review source code before installing third-party packages. Package installs run `npm install --omit=dev` by default.

### Risk Vectors

- **Prompt injection** from repository files, comments, docs, context files, or build output is expected local-agent risk
- **Malicious extensions** have full system permissions
- **Malicious skills** can instruct the model to perform destructive actions
- **Model output** is not validated for safety; Pi is a development tool, not a security boundary

### Security Reporting

Security issues should be reported through the repository SECURITY.md policy, not public issues. Expected local-agent behavior and lack of built-in sandbox are outside the security boundary unless demonstrating a real privilege-boundary bypass.

---

## Appendix: Key Integration Points

### SDK Quick Start

```typescript
import { createAgentSession, ModelRuntime, SessionManager } from "@earendil-works/pi-coding-agent";

const modelRuntime = await ModelRuntime.create();
const { session } = await createAgentSession({
  sessionManager: SessionManager.inMemory(),
  modelRuntime,
});

session.subscribe((event) => {
  if (event.type === "message_update" && event.assistantMessageEvent.type === "text_delta") {
    process.stdout.write(event.assistantMessageEvent.delta);
  }
});

await session.prompt("What files are in the current directory?");
```

### RPC Mode Start

```bash
pi --mode rpc --provider anthropic --model claude-sonnet-4-20250514
```

### Extension Template

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "my_tool",
    description: "Does something",
    parameters: Type.Object({ input: Type.String() }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      return { content: [{ type: "text", text: `Done: ${params.input}` }], details: {} };
    },
  });

  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName === "bash" && event.input.command?.includes("rm -rf")) {
      const ok = await ctx.ui.confirm("Dangerous!", "Allow rm -rf?");
      if (!ok) return { block: true, reason: "Blocked" };
    }
  });
}
```

### Skill Template

```markdown
---
name: my-skill
description: Perform specialized task X. Use when user asks about X.
---

# My Skill

## Steps
1. Read the relevant files
2. Process data using ./scripts/process.sh
3. Write output

See [reference](references/guide.md) for options.
```
