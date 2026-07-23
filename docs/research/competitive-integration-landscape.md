# Competitive Integration Landscape: Orchestrator ↔ Coding Agent Communication

> **Date:** 2026-07-23
> **Author:** hswarm-rsrch
> **Purpose:** Survey how major orchestrators, frameworks, and tooling integrate with CLI coding agents — and whether a protocol standard exists for orchestrator↔coding-agent communication.

---

## Table of Contents

1. [LangChain / LangGraph — Codex Integration & Tool-Calling](#1-langchain-langgraph)
2. [Open Interpreter — Plugin System & Tool Registration](#2-open-interpreter)
3. [Claude Code MCP — Tool Exposure via MCP](#3-claude-code-mcp)
4. [ACP Protocol — Hermes ACP Adapter Analysis](#4-acp-protocol)
5. [Protocol Landscape: MCP vs ACP vs A2A vs ANP](#5-protocol-landscape)
6. [awesome-cli-coding-agents: Orchestration Ecosystem Map](#6-awesome-cli-coding-agents-orchestration-ecosystem)
7. [Key Question: Is There a Protocol Standard?](#7-key-question)
8. [Findings & Recommendations](#8-findings-recommendations)

---

## 1. LangChain / LangGraph

### Overview

LangChain and LangGraph form the most mature Python-native agent orchestration ecosystem. LangChain provides the abstraction layer (tool wrappers, retrievers, model interfaces), while LangGraph provides the graph-based orchestration engine with state management, persistence, human-in-the-loop, and checkpointing.

### Codex Integration

LangGraph's integration with OpenAI Codex CLI follows a **hybrid orchestration pattern**:

- **LangGraph owns orchestration** — state machine, routing, persistence, checkpoints, and deterministic control flow.
- **Codex CLI is called as a bounded node** within the graph — when ordinary Python tool-calling isn't enough, the graph dispatches to a Codex-backed sub-agent.
- The adapter library `langgraph-codex` (PyPI) provides this bridge: a small library wrapping a LangGraph node that starts a Codex conversation, passes context, and captures results.

**Key pattern:** Orchestrator as deterministic graph → delegate to coding agent for open-ended sub-tasks → verify and merge result.

### Tool-Calling Patterns

LangChain provides 100+ pre-built tool wrappers. Any Python callable can be registered as a tool via `@tool` decorator or `Tool` class. LangGraph extends this with:

- **Structured tool output** — tools declare schemas via Pydantic.
- **Parallel tool execution** — graph nodes can fan-out tool calls.
- **Human-in-the-loop** — approval gates before tool execution.
- **Sub-agent delegation** — a graph node can spawn a full agent loop with its own toolset.

### Deep Agents Code

LangChain's own terminal coding agent, **Deep Agents Code** (`deepagents-code` on PyPI), is built on the LangGraph ecosystem. It features an interactive TUI, file operations, shell access, subagents, headless mode, and human-in-the-loop approvals with any tool-calling LLM. It represents the **convergent pattern**: an orchestrator framework that ships its own CLI coding agent using that same framework.

### Relevance to Pier/Hermes

LangGraph's sub-agent node pattern is directly analogous to how Pier would orchestrate Pi: a LangGraph-style deterministic graph that delegates open-ended coding work to a CLI coding agent (Pi), then verifies and merges results.

---

## 2. Open Interpreter

### Overview

Open Interpreter is a mature (66.9K stars) terminal-native coding agent that executes Python code, shell commands, and file operations on the user's machine. It is built on top of OpenAI Codex and remains provider-agnostic.

### Architecture

Open Interpreter uses a **modular tool system** based on:

1. **Tool definitions** (`Tool` class) — each tool declares a name, description, parameters (JSON Schema), and an async `run()` implementation.
2. **Tool registry** — tools are discovered and registered at startup from a known set of built-in tools.
3. **Permissions system** — a callback-based approval layer gates tool execution (allow/deny/always-allow).
4. **Sandboxing** — optional Docker-based execution isolation.

The tool system supports:
- **Built-in tools** — shell, Python execution, file read/write, web search, computer vision.
- **Custom tools** — users can define new tools by subclassing the Tool class.
- **Plugin architecture** — community-contributed tool sets (e.g., "Computer Use" QA skills).
- **Parallel tool execution** — multiple tools can run concurrently with result aggregation.

### Tool Registration Pattern

```python
class MyTool(Tool):
    name = "my_tool"
    description = "Does something"
    parameters = {
        "type": "object",
        "properties": {"arg1": {"type": "string"}}
    }
    
    async def run(self, arg1: str):
        return f"Result: {arg1}"
```

Registration happens at startup via scanning installed packages or explicit registration calls. Open Interpreter's design is intentionally **simple and framework-agnostic** — every tool is just an async Python function with a JSON Schema.

### Orchestrator Integration Pattern

Open Interpreter itself **is** the coding agent — it is not designed to be orchestrated from the outside. Integration happens at the Python API level:

```python
from interpreter import interpreter
result = interpreter.computer.run("python", "print('hello')")
```

This means orchestrators that want to use Open Interpreter either:
- Call it as a Python library (embedding)
- Run it as a subprocess and pipe I/O
- Use its HTTP API (community additions)

### Relevance to Pier/Hermes

Open Interpreter's tool registration model is a reference for how Pi could expose its capabilities (file edit, shell, code execution) via a structured tool schema that an orchestrator like Hermes can discover and call.

---

## 3. Claude Code MCP

### Overview

Claude Code is Anthropic's CLI coding agent that deeply integrates the **Model Context Protocol (MCP)** — an open standard that Anthropic created for connecting AI assistants to tools, data sources, and services.

### How Claude Code Exposes Tools via MCP

Claude Code acts as both an **MCP client** and, conceptually, an **MCP-consuming agent**:

1. **MCP server discovery** — Claude Code reads MCP server configurations from `~/.claude/settings.json` or project-local `.mcp.json`.
2. **Tool acquisition** — on startup, Claude Code connects to each configured MCP server via stdio, HTTP, or SSE transport, and acquires the server's advertised tools.
3. **Unified tool space** — tools from all MCP servers are merged into the agent's available tool set alongside its built-in tools (file editing, shell, search, etc.).
4. **Human-in-the-loop** — Claude Code surfaces a permission dialog before executing MCP tools (the user must approve).

### MCP Tool Exposure Format

MCP servers advertise tools via JSON-RPC with a standardized schema:

```json
{
  "name": "tool-name",
  "description": "What the tool does",
  "inputSchema": {
    "type": "object",
    "properties": {
      "param1": {"type": "string", "description": "..."}
    },
    "required": ["param1"]
  }
}
```

Tool results are returned as structured content blocks (text, image, embedded resource).

### Claude Code as a Target for External Orchestration

Claude Code itself **does not expose an orchestrator-facing protocol** — it is designed as a single-session interactive agent. However, the ecosystem has innovated around this:

- **Claude Code MCP servers** that wrap Claude Code itself (e.g., providing a "delegate to Claude Code" tool for other agents).
- **tmux-based session managers** (`claude-squad`, `claude-flow`, etc.) that run multiple Claude Code sessions in parallel and pipe work between them.

### MCP as the Dominant Tool Protocol

MCP has become the de facto standard for **agent-to-tool** communication, supported by:

| Client | Tool Acquisition |
|--------|-----------------|
| Claude Desktop | MCP servers from settings.json |
| Claude Code CLI | MCP servers from settings.json / .mcp.json |
| Cursor | MCP servers via built-in config |
| Zed Editor | MCP via ACP bridge |
| VS Code via GitHub Copilot | MCP (upcoming) |
| OpenCode | MCP support |
| Hermes Agent | MCP via `tools/mcp_tool.py` |
| Goose | MCP native |
| Pi / oh-my-pi | MCP support |
| Waveloom | MCP auto-discovery |

### Relevance to Pier/Hermes

MCP is the natural protocol for **tool exposure**. If Pi exposes its capabilities (file edit, shell, code execution) as MCP tools, any MCP-compatible orchestrator (including Hermes) can discover and call them. This is the cleanest path to orchestrator↔agent tool integration.

---

## 4. ACP Protocol

### Overview

The **Agent Client Protocol (ACP)** is an emerging open standard that standardizes communication between **code editors / IDEs** and **coding agents**. It was created jointly by **JetBrains and Zed** and is positioned as the IDE-to-agent counterpart of MCP (which is agent-to-tool).

### ACP's Two Meanings

> **Important distinction:** ACP appears in two related but distinct contexts:

1. **Agent Client Protocol (ACP)** — JetBrains/Zed protocol for IDE↔coding-agent communication (agentclientprotocol.com).
2. **Agent Communication Protocol (ACP)** — IBM's protocol for agent-to-agent interoperability (agentcommunicationprotocol.dev).

In the Hermes ecosystem, **ACP** refers to the JetBrains/Zed **Agent Client Protocol**.

### ACP Architecture

ACP defines a JSON-RPC-based protocol with:

- **Session management** — create, load, resume, fork, list sessions.
- **Prompt execution** — send a prompt to the agent, receive streaming responses (text + tool calls + thoughts).
- **Tool call streaming** — structured `ToolCallStart`, `ToolCallProgress`, `ToolCallComplete` events.
- **Resource attachment** — agents can attach files, images, and structured data alongside messages.
- **Slash commands** — `help`, `model`, `tools`, `reset`, `compress`, etc.
- **Authentication** — terminal auth flow for provider setup.
- **Model configuration** — switch models mid-session.
- **Plan display** — structured plan/todo updates.

### ACP Adopters

| Actor | ACP Support |
|-------|------------|
| **Zed Editor** | Native ACP client — lists ACP agents in its Agent Registry |
| **JetBrains IDEs** | ACP integration via official plugin |
| **Hermes Agent** | Full ACP server (`hermes acp` via `acp_adapter/`) |
| **Gemini CLI** | ACP server support |
| **Kimi CLI** | ACP IDE integration |
| **LangChain Deep Agents** | ACP integration (`langchain-deepagents[acp]`) |
| **ACP Agent Registry** | Discoverable agent installation (`acp registry install <agent>`) |

### Hermes ACP Adapter Deep Dive

The Hermes ACP adapter (`/Users/rath/.hermes/hermes-agent/acp_adapter/`) implements a full ACP server. Key components:

- **`server.py`** (2207 lines) — The main ACP agent class (`HermesACPAgent`) with session lifecycle, prompt processing, tool streaming, and resource handling. Maps Hermes tools to ACP `ToolKind` taxonomy.
- **`session.py`** (659 lines) — Thread-safe `SessionManager` that creates, persists, restores, forks, and lists ACP sessions. Sessions are backed by the shared `SessionDB` (`~/.hermes/state.db`) for crash recovery and persistence.
- **`tools.py`** (1347 lines) — Maps Hermes tool names to ACP `ToolKind` values (read, edit, search, execute, fetch, think, other). Provides polished tool-call streaming with human-readable titles.
- **`entry.py`** (271 lines) — CLI entry point with `--check`, `--setup`, `--setup-browser` flags.
- **`auth.py`** — Terminal auth flow for provider setup.
- **`permissions.py`** — Approval callback for tool execution.
- **`events.py`** — Streaming event builders for plan updates, thinking, tool progress.
- **`provenance.py`** — Session provenance tracking.

**Notable:** The adapter includes an inline MCP-discovery call at startup (`discover_mcp_tools()`) — Hermes's ACP server also discovers and registers MCP tools, making it a **convergence point** for both protocols.

### ACP Tool Exposure Flow (Hermes)

1. Editor (Zed/JetBrains) connects to `hermes acp` via stdio.
2. ACP `initialize` exchange establishes capabilities.
3. ACP `new_session` creates a Hermes `AIAgent` instance.
4. ACP `prompt` sends user input as structured content blocks.
5. `HermesACPAgent` processes the prompt through Hermes's agent loop.
6. Tool calls stream back as `ToolCallStart` / `ToolCallProgress` / `ToolCallComplete` events.
7. Editor renders tool progress and final response in the IDE.

### Relevance to Pier/Hermes

ACP is the protocol for **IDE→coding-agent** integration. For Pier (which is a Pi↔Hermes bridge), ACP provides:
- A ready-made session management lifecycle.
- Standardized tool-call streaming that works with any ACP-compatible editor.
- A proven reference implementation in Hermes's own `acp_adapter`.

---

## 5. Protocol Landscape

### The Four Major Protocols

| Protocol | Full Name | Creator | Domain | Scope |
|----------|-----------|---------|--------|-------|
| **MCP** | Model Context Protocol | Anthropic | Agent ↔ Tools | How agents discover and call tools/data sources |
| **ACP** | Agent Client Protocol | JetBrains + Zed | IDE ↔ Agent | How code editors communicate with coding agents |
| **A2A** | Agent-to-Agent | Google | Agent ↔ Agent | How agents discover and delegate to other agents |
| **ACP (IBM)** | Agent Communication Protocol | IBM | Agent ↔ Agent | Interoperability between multi-agent systems |
| **ANP** | Agent Network Protocol | Community | Agent ↔ Network | Decentralized agent discovery and routing |

### Protocol Comparison

| Aspect | MCP | ACP (JetBrains/Zed) | A2A | ACP (IBM) |
|--------|-----|---------------------|-----|-----------|
| **Transport** | stdio, HTTP, SSE | stdio (JSON-RPC) | HTTP (REST) | HTTP |
| **Session model** | Stateless (per-request) | Stateful (create/resume/fork) | Task-based (card create/update) | Stateful |
| **Streaming** | SSE | JSON-RPC streaming | Webhook | SSE |
| **Auth** | OAuth 2.1, API keys | Terminal setup flow | OAuth 2.0 | OAuth |
| **Maturity** | High (production, 2024+) | Medium (emerging, 2025+) | Medium (Google-backed) | Low (early 2026) |
| **Adoption** | Wide — Cursor, VS Code, Claude, many agents | Growing — Zed, JetBrains, Gemini CLI, Hermes | Google ecosystem | IBM ecosystem |
| **Tool format** | JSON Schema tools | MCP-like tool schema | Capability-based | Proprietary |
| **IDEs** | Via MCP clients | Native | — | — |
| **CLI agents** | As MCP consumers | As ACP servers | — | — |

### Protocol Stack for an Orchestrator↔Agent Integration

The emerging **layered protocol stack** looks like:

```
┌──────────────────────────────────────────┐
│         A2A / ACP (IBM)                  │
│    Agent-to-Agent orchestration          │
├──────────────────────────────────────────┤
│         ACP (JetBrains/Zed)             │
│    IDE ↔ Coding Agent communication      │
├──────────────────────────────────────────┤
│         MCP (Anthropic)                 │
│    Agent ↔ Tools / Data Sources          │
└──────────────────────────────────────────┘
```

For the **Pier** use case (Hermes ↔ Pi), the relevant layers are:
- **MCP** — Pi exposes its tools (file editing, shell, code execution) as MCP servers.
- **ACP** — A Hermes orchestrator communicates with Pi's coding agent session via ACP.
- **A2A** — For agent-to-agent delegation patterns (Hermes delegates tasks to Pi).

---

## 6. awesome-cli-coding-agents: Orchestration Ecosystem

The [awesome-cli-coding-agents](https://github.com/bradAGI/awesome-cli-coding-agents) list (90+ entries, 2026-07-20) reveals a rapidly maturing orchestration ecosystem:

### Session Managers & Parallel Runners

These tools run multiple coding agent sessions side-by-side:

- **vibe-kanban** (27.5K⭐) — Kanban UI for administering AI coding agents.
- **cmux** (24.8K⭐) — Platform for running multiple coding agents in parallel.
- **Superset** (12.5K⭐) — Terminal built for coding agents; orchestrates parallel sessions.
- **Claude Squad** (8.1K⭐) — tmux-based harness for multiple Claude Code sessions.
- **Emdash** (5.2K⭐) — Concurrent multi-agent orchestration.
- **Crystal** (3.1K⭐) — Parallel Codex + Claude Code sessions in git worktrees.
- **agent-of-empires** (2.8K⭐) — TUI/web UI manager for 6+ coding agents via tmux + worktrees.

### Orchestrators & Autonomous Loops

Dedicated orchestrators that manage coding agent lifecycles:

- **claude-flow** (65.2K⭐) — Multi-agent swarms with coordinated workflows.
- **gastown** (17.1K⭐) — Multi-agent orchestration with persistent work tracking.
- **ralph-orchestrator** (3.1K⭐) — Hat-based loop-until-done execution.
- **AgentsMesh** (2.3K⭐) — Remote AI workstations with Kanban + MR/PR integration.
- **zeroshot** (1.7K⭐) — Planner/implementer/validator loop in isolated environments.
- **Bernstein** (707⭐) — Deterministic Python orchestrator for parallel coding agents.
- **Hephaestus** (951⭐) — Open Agent OS with A2A Hub routing and memory/security gates.
- **h5i** (475⭐) — Peer-review loop: agents code, peer-review, tests verify.
- **OMK** (125⭐) — Provider-neutral CLI control plane for coding agents.
- **kodo** (118⭐) — Multi-agent coding orchestrator with independent architect/tester verification.
- **ORCH** (96⭐) — CLI orchestrator with typed task queue and state machine.

### Agent Infrastructure

Supporting infrastructure for orchestrator↔agent integration:

- **claude-code-router** (35.9K⭐) — Route Claude Code to alternative providers.
- **hcom** (392⭐) — Shared messaging bus for multiple CLI agents to observe and message each other.
- **amux** (304⭐) — Agent multiplexer with kanban board, REST API, and watchdog.
- **AgentBox** (281⭐) — VM isolation for coding agents with checkpointing.
- **handoff** (74⭐) — Delegate tasks to DeepSeek from Claude Code/Codex sessions.
- **construct** (3⭐) — Terminal-native fleet TUI with agent-to-agent orchestration.
- **PATAPIM** — Terminal IDE with multi-agent grid and MCP browser.

### Key Observation

**Every major orchestrator wraps CLI coding agents via subprocess + tmux worktrees.** There is no dominant SDK or protocol for orchestrators to programmatically control coding agents — they all resort to:
1. Starting a new terminal session (tmux pane).
2. Injecting a prompt.
3. Capturing stdout.
4. Parsing structured output (if any).
5. Managing session lifecycle via PID polling.

This is the gap that Pier (and similar protocol-based approaches) aim to fill.

---

## 7. Key Question

> **Is there a protocol standard for orchestrator ↔ coding-agent communication?**

### Answer: Not Yet a Single Standard, But Convergence Is Happening

| Layer | Protocol | Status |
|-------|----------|--------|
| IDE ↔ Agent | **ACP** (JetBrains/Zed) | Emerging standard, multi-IDE support |
| Agent ↔ Tools | **MCP** (Anthropic) | De facto standard, widest adoption |
| Agent ↔ Agent | **A2A** (Google), ACP (IBM), ANP | Fragmented, no clear winner |
| **Orchestrator ↔ Coding Agent** | **None (gap)** | No standard exists |

The **orchestrator↔coding-agent** gap is the missing layer:

- **LangGraph** uses a proprietary Python API (`invoke()` on a graph).
- **Claude Code session managers** use tmux + text injection.
- **Orchestrators** (ralph, zeroshot, Bernstein, h5i) each invent their own subprocess wiring.
- **AgentBox** uses Docker + API.
- **hcom** uses a shared message bus.

### The Closest Candidates

1. **ACP** — The most natural fit for orchestrator↔agent, because it already provides session lifecycle, prompt execution, and tool streaming. The gap is that ACP is designed for **IDE clients**, not **orchestrator clients**. An orchestrator using ACP would be acting as a "headless IDE" — which works but adds unnecessary IDE-centric semantics.

2. **MCP as a wrapper** — An orchestrator could connect to an agent's MCP server, but MCP is designed for tool exposure, not full agent session management (no session lifecycle, no streaming conversation, no forking).

3. **Custom protocols** — Every orchestrator currently rolls its own. This is the status quo.

### Recommendation for Pier

Pier should implement **ACP as the primary integration protocol** for Hermes ↔ Pi communication, because:

- ACP already has Hermes's full server-side implementation as a reference.
- ACP supports everything Pier needs: session management, prompt streaming, tool call events, and resource attachment.
- A growing ecosystem of editors and agents already supports ACP.
- Pier can act as a light ACP **proxy/bridge** — translating Hermes orchestration commands into ACP session operations on Pi.

Complement with **MCP for tool exposure** — if Pi exposes its capabilities as MCP tools, any MCP-compatible agent (including Hermes via `tools/mcp_tool.py`) can discover and invoke them directly.

---

## 8. Findings & Recommendations

### Finding 1: No Single Protocol Standard Exists — But ACP Is the Best Fit

The orchestrator↔coding-agent integration layer is still a greenfield. ACP (JetBrains/Zed) is the most promising candidate because it already provides session lifecycle, prompt/response streaming, tool call events, and multi-editor support.

### Finding 2: MCP Is the De Facto Standard for Tool Exposure

Any coding agent (including Pi) should expose its capabilities as MCP tools. This guarantees compatibility with the widest range of clients: Claude Code, Cursor, Zed, VS Code (upcoming), Hermes, Goose, OpenCode, and many more.

### Finding 3: The Ecosystem Is Fragmenting on Agent-to-Agent Orchestration

A2A (Google), ACP (IBM), and ANP are all competing in the agent-to-agent space. For Pier's scope, A2A is worth monitoring (Google ecosystem weight), but the more immediate integration pattern is orchestrator-as-ACP-client.

### Finding 4: Current Orchestrators All Invent Custom Wiring

Every orchestrator in the awesome list (claude-flow, gastown, ralph, zeroshot, Bernstein, h5i, ORCH, kodo) invents its own subprocess+tmux wiring. None use a standard protocol. This is both a validation that the need exists and a sign that a protocol-based approach (like Pier) would be differentiated.

### Finding 5: LangGraph's Sub-Agent Node Pattern Is the Reference Architecture

For Pier's deterministic orchestration layer, LangGraph's pattern of "orchestrator graph → delegate node to coding agent → verify and merge" is the proven reference architecture.

### Recommended Architecture for Pier

```
┌──────────────────┐         ACP (JSON-RPC/stdio)        ┌──────────────────┐
│   Hermes Agent   │ ──────────────────────────────────► │   Pi Agent       │
│  (Orchestrator)  │ ◄────────────────────────────────── │  (Coding Agent)  │
│                  │   Session mgmt + streaming + tools  │                  │
└──────────────────┘                                     └──────────────────┘
         │                                                       │
         │ MCP tools                                             │ MCP tools
         ▼                                                       ▼
┌──────────────────┐                                     ┌──────────────────┐
│  MCP Servers     │                                     │  File, Shell,    │
│  (external)      │                                     │  Code Exec tools │
└──────────────────┘                                     └──────────────────┘
```

1. **ACP** for orchestrator↔agent session management (Hermes ↔ Pi).
2. **MCP** for tool exposure (Pi exposes its capabilities to any MCP client).
3. **Git worktrees** for isolation (proven pattern from the ecosystem).

---

## References

- LangGraph: https://github.com/langchain-ai/langgraph
- Open Interpreter: https://github.com/openinterpreter/open-interpreter
- Claude Code MCP: https://code.claude.com/docs/en/mcp
- MCP Specification: https://modelcontextprotocol.io/
- ACP (JetBrains/Zed): https://agentclientprotocol.com/
- ACP for LangChain: https://docs.langchain.com/oss/python/deepagents/acp
- ACP (IBM): https://agentcommunicationprotocol.dev/
- A2A (Google): https://github.com/google/A2A
- Hermes ACP Adapter: `acp_adapter/` in hermes-agent repo
- awesome-cli-coding-agents: https://github.com/bradAGI/awesome-cli-coding-agents
- Zylos AI Protocol Comparison: https://zylos.ai/research/2026-02-15-agent-to-agent-communication-protocols/
