# Hermes Coding-Agent Integration Patterns Research

**Date:** 2026-07-23
**Author:** hswarm-rsrch
**Status:** Complete
**Source:** Hermes Agent v0.19.0 skills (codex, claude-code, opencode) in `skills/autonomous-ai-agents/`

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Per-Agent Analysis](#per-agent-analysis)
3. [Common Patterns](#common-patterns)
4. [Distinctive Features Per Agent](#distinctive-features-per-agent)
5. [Pi-Specific Opportunities](#pi-specific-opportunities)
6. [Gap Analysis](#gap-analysis)
7. [Recommendations for Pi](#recommendations-for-pi)

---

## Executive Summary

Three Hermes skills delegate coding tasks to external autonomous coding agents (Codex, Claude Code, OpenCode). Each follows a consistent orchestration pattern — Hermes spawns the coding agent as a subprocess via its `terminal` tool, either in **print/one-shot mode** (non-interactive, exits when done) or **interactive PTY mode** (multi-turn, for iterative work). The skills share ~70% structural DNA but differ in dialog handling, structured output, and permission models. Pi has unique advantages (RPC mode, minimal system prompt, TypeScript-native extensions) that none of the three existing agents fully exploit.

---

## Per-Agent Analysis

### 1. Codex (OpenAI) — `skills/autonomous-ai-agents/codex/skill.md`

**Version:** 1.0.0 | **Install:** `npm i -g @openai/codex` | **Auth:** OAuth or `OPENAI_API_KEY`

**Orchestration approach:** Terminal-based subprocess with `pty=true`.

- **One-shot:** `codex exec '<prompt>'` — runs and exits. Requires a git repo.
- **Flags:** `--full-auto` (sandboxed auto-approve), `--yolo` (no sandbox), `--sandbox danger-full-access` (bypasses bubblewrap for gateway contexts).
- **Background:** `terminal(background=true, pty=true)` — monitor with `process(action="poll")`, send input with `process(action="submit")`.
- **Parallel work:** Git worktrees — `git worktree add -b fix/issue-N /tmp/issue-N main`, then launch Codex in each.
- **PR review:** Clone to temp dir, `gh pr checkout N`, `codex review --base origin/main`.
- **Batch PRs:** `git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'`, then review multiple PRs in parallel.

**Key quirk:** Codex requires a git repo — even for scratch work you must `mktemp -d && git init`.

**Error handling:** Gateway sandbox context failure is explicitly documented — bubblewrap/user-namespace errors require `--sandbox danger-full-access` with process-boundary safety layers.

### 2. Claude Code (Anthropic) — `skills/autonomous-ai-agents/claude-code/skill.md`

**Version:** 2.2.0 | **Install:** `npm i -g @anthropic-ai/claude-code` | **Auth:** OAuth or `ANTHROPIC_API_KEY`

**Most feature-rich skill (745 lines)** with two distinct orchestration modes:

#### Mode 1: Print Mode (`-p`) — Preferred for most tasks
- `claude -p '<prompt>'` — one-shot, exits when done. No PTY needed. No dialog handling.
- Supports structured JSON output (`--output-format json`), JSON schema for extraction (`--json-schema`), streaming (`stream-json`).
- Session continuation: `--resume <id>`, `--continue`, `--fork-session`.
- **Bare mode** (`--bare`): skips hooks, plugins, MCP discovery, CLAUDE.md loading, OAuth. Fastest startup.
- Cost controls: `--max-turns`, `--max-budget-usd`, `--fallback-model`, `--effort`.
- Tool restrictions: `--allowedTools`, `--disallowedTools`, `--permission-mode`.
- **Piped input:** `cat file | claude -p 'analyze'`, `git diff | claude -p 'summarize'`.

#### Mode 2: Interactive PTY via tmux — Multi-turn sessions
- Requires tmux orchestration: `tmux new-session -d`, `tmux send-keys`, `tmux capture-pane`.
- Dialog handling is CRITICAL: workspace trust dialog (Enter = accept), permissions bypass dialog (Down then Enter to select "Yes, I accept").
- Built-in worktree support: `--worktree` creates `.claude/worktrees/<name>`, `--tmux` creates a tmux session for it.
- Slash commands: `/compact`, `/review`, `/plan`, `/agents`, `/mcp`, `/model`.
- Custom subagents: `.claude/agents/*.md` defined with model, tools, and system prompt.

**Error handling:** Budget errors, rate limits (stream events include `system/api_retry`), context degradation above 70%.

**Claude Code-only features not in other skills:**
- Hooks system (8 event types: PreToolUse, PostToolUse, Stop, etc.)
- MCP server integration (stdio/http/sse transports, scoped `-s user|local|project`)
- CLAUDE.md project context files with rules directory
- Auto-memory (`~/.claude/projects/<project>/memory/`)
- Custom slash commands (`.claude/commands/*.md`)
- Skills directory (`.claude/skills/*.md` — auto-invoked by NL matching)
- Agent teams (`--teammate-mode`, `@agent-name` invocation)
- Session cost tracking (`--output-format json` returns `total_cost_usd`, `usage`)
- `/compact` context management

### 3. OpenCode — `skills/autonomous-ai-agents/opencode/skill.md`

**Version:** 1.2.0 | **Install:** `npm i -g opencode-ai@latest` or `brew install anomalyco/tap/opencode`
**Key distinction:** Provider-agnostic (can use OpenRouter, Anthropic, OpenAI, etc.)

**Orchestration approach:**
- **One-shot:** `opencode run '<prompt>'` — no PTY needed. Supports `-f <file>` context files, `--thinking`, `--model provider/model`.
- **Interactive:** TUI in background with `pty=true` — send prompts via `process(action="submit")`.
- **Session management:** `opencode -c` (continue last), `opencode -s <id>` (specific session), `opencode session list`.
- **PR review:** `opencode pr <number>` built-in.
- **Cost tracking:** `opencode stats`, `opencode stats --days 7 --models ...`.
- **Flags:** `--agent <name>`, `--format json`, `--variant <level>` (reasoning effort).

**Key quirk:** `/exit` is NOT a valid command — opens agent selector. Use Ctrl+C or `process(action="kill")`.

**Least complex skill (219 lines)** — simpler than both Codex and Claude Code, reflecting OpenCode's younger ecosystem.

---

## Common Patterns

### 1. Terminal-Based Delegation (Core Architecture)

All three use the same fundamental architecture: Hermes spawns the coding agent as a subprocess via the `terminal` tool. Two modes are universal:

| Mode | Mechanism | PTY Needed? | Use Case |
|------|-----------|-------------|----------|
| **Print / One-Shot** | `codex exec`, `claude -p`, `opencode run` | No (except Codex) | Bounded tasks: fix bug, add feature, review diff |
| **Interactive / TUI** | Background process with pty | Yes | Multi-turn iteration, exploratory coding |

**Hermes handles both identically** — `background=true, pty=true` spawns the process, `process(action="poll")` monitors it, `process(action="submit")` sends input.

### 2. Error Recovery Patterns

| Pattern | Codex | Claude Code | OpenCode |
|---------|-------|-------------|----------|
| **Timeouts** | Implicit via `terminal(timeout=N)` | Implicit + `--max-turns` + `--max-budget-usd` | Implicit via timeout |
| **Retry handling** | `--sandbox danger-full-access` for gateway crashes | `--fallback-model` for overload | Log inspection before kill |
| **Cleanup** | `git worktree remove` | `tmux kill-session` | Ctrl+C / kill |
| **Output verification** | `git diff` review | JSON result with `subtype` field | Session logs |

**Key insight:** None of the three have explicit retry logic in the skill itself — retry is implicit (re-run the terminal command). Claude Code is the only one with structured error reporting in its output format.

### 3. Provider/Model Configuration

| Aspect | Codex | Claude Code | OpenCode |
|--------|-------|-------------|----------|
| **Provider** | OpenAI only (hardcoded) | Anthropic only (hardcoded) | Any (provider-agnostic) |
| **Model selection** | N/A (fixed) | `--model sonnet\|opus\|haiku` | `--model openrouter/anthropic/claude-sonnet-4` |
| **Auth** | OAuth or API key | OAuth, API key, or SSO | `opencode auth login` or env vars |
| **Cost tracking** | None documented | `--output-format json` → `total_cost_usd` | `opencode stats` |

**Pi takeaway:** Pi should be provider-agnostic like OpenCode but also expose cost tracking natively in its RPC responses.

### 4. Working Directory Isolation

All three enforce scope via the `terminal(workdir=...)` parameter. Two patterns emerge:

- **Simple isolation:** Set `workdir` to the project directory. Each agent call is scoped.
- **Git worktree isolation:** For parallel tasks, create separate git worktrees:
  ```bash
  git worktree add -b fix/issue-78 /tmp/issue-78 main
  terminal(command="codex exec 'Fix it'", workdir="/tmp/issue-78")
  ```
  - Codex skill documents this explicitly.
  - Claude Code has built-in `--worktree` flag.
  - OpenCode skill recommends separate workdirs.

**Pi takeaway:** Pi's TypeScript extension system could provide first-class workspace management.

### 5. Git Repository Requirement

Codex **requires** a git repo to run. Claude Code and OpenCode strongly recommend it (for `git diff`, PR review, session tracking). Only Claude Code offers `--bare` mode that strips all project context.

### 6. PR Review Pattern

Common pattern across all three:
```bash
# Clone to temp dir
REVIEW=$(mktemp -d) && git clone <repo> $REVIEW
# Run review
claude -p 'Review this diff' --allowedTools Read
# Or use built-in
opencode pr <number>
```

---

## Distinctive Features Per Agent

| Feature | Codex | Claude Code | OpenCode | Pi Opportunity |
|---------|-------|-------------|----------|----------------|
| **Structured JSON output** | No | Yes (`--output-format json`) | Yes (`--format json`) | Native RPC returns structured objects |
| **Streaming output** | No | Yes (`stream-json`) | No | Native streaming over RPC |
| **Custom subagents** | No | Yes (`.claude/agents/*.md`) | TUI agent switching | Extension-defined subagents |
| **MCP integration** | No | Yes (`claude mcp add`) | No | RPC-based MCP-style tool registration |
| **Hooks system** | No | Yes (8 event types) | No | Extension system covers this better |
| **Project context files** | No | CLAUDE.md + rules dir + auto-memory | No | Minimal system prompt could replace |
| **Cost limits** | No | `--max-budget-usd` | `opencode stats` | Include in RPC response metadata |
| **Session resumption** | No | `--continue`, `--resume`, `--fork-session` | `-c`, `-s` | Stateless RPC — no session to resume |
| **JSON schema extraction** | No | Yes (`--json-schema`) | No | Could be part of RPC protocol |
| **Git worktree built-in** | No | Yes (`--worktree`) | No | Workspace management via extensions |

---

## Pi-Specific Opportunities

### 1. RPC Mode (Unique Differentiator)

**Current state:** All three existing agents use subprocess-based delegation — Hermes talks to them via the terminal tool. This means:
- No structured return value (parsing text output)
- No bidirectional streaming protocol
- No typed request/response contracts
- No native auth integration with Hermes providers

**Pi opportunity:** Pi's RPC mode is a first-class integration pattern that none of the three existing coding agents support. Benefits:
- **Structured responses:** Return typed objects (`{changes: [...], tests_run: N, output: "..."}`) instead of raw text.
- **Streaming:** Real-time token streaming over RPC transport.
- **Bidirectional:** Pi can push progress events, ask questions, and receive structured answers without parsing terminal output.
- **Auth:** Hermes provider auth flows directly through the RPC connection — no separate OAuth dance.

**Architecture recommendation:**
```
┌──────────┐  RPC (JSON/Protobuf)  ┌──────────┐
│  Hermes  │ ◄──────────────────►  │    Pi    │
│  Agent   │                       │  Server  │
└──────────┘                       └──────────┘
     │                                  │
     │ terminal (fallback)              │ subprocess (code)
     ▼                                  ▼
  coding agents                   workspace files
```

Hermes would call Pi via RPC by default, falling back to terminal-based subprocess for users without Pi installed.

### 2. Minimal System Prompt (Lower Token Cost)

**Current state:** Claude Code auto-loads CLAUDE.md (project context), `.claude/rules/*.md` (rules directory), `~/.claude/projects/<project>/memory/` (auto-memory), plugins, MCP configs, and hooks. This means every API call pays for this accumulated context.

Codex requires a git repo with branch context. OpenCode loads project-level configuration.

**Pi opportunity:** Pi's design could default to a **minimal system prompt** — only what is explicitly provided per-request. This would:
- Reduce per-call token costs significantly, especially compared to Claude Code's context-heavy model.
- Make Pi ideal for CI/CD pipelines and automation where low-latency, low-cost calls matter.
- Let users opt into context loading (via extensions) rather than having it always on.
- Enable sub-50-token system prompts for simple operations.

**Benchmark target:** Pi's minimal prompt should target 50–150 tokens vs. Claude Code's 2,000+ token system prompt baseline.

### 3. TypeScript Extension System

**Current state:** Claude Code supports custom slash commands (`.claude/commands/*.md`), skills (`.claude/skills/*.md`), subagents (`.claude/agents/*.md`), and hooks (`.claude/settings.json`). These are all **markdown/JSON files**, not programmatic extensions.

**Pi opportunity:** Pi's TypeScript-native extension system is fundamentally more powerful:
- **TypeScript APIs** for workspace management, file operations, provider configuration.
- **Lifecycle hooks** (before_task, after_task, on_error, on_complete) as TypeScript functions.
- **Custom tools** registered via extension API (analogous to MCP but native, no subprocess overhead).
- **Provider adapters** — TypeScript modules that abstract different LLM providers.
- **Validation middleware** — intercept and validate tool calls, file writes, network access.

**Where extensions improve on Claude Code's approach:**

| Capability | Claude Code | Pi (TypeScript Extensions) |
|------------|-------------|---------------------------|
| Command format | Markdown files | TypeScript functions |
| Hooks | JSON config | Lifecycle callbacks |
| Tool registration | MCP (subprocess) | Native API |
| Type safety | None | Full TypeScript |
| Distribution | Git repos | npm packages |

---

## Gap Analysis

### What Pi Has That No Coding Agent Has

| Gap | Description | Why It Matters |
|-----|-------------|----------------|
| **RPC Protocol** | Bidirectional structured communication channel | No terminal parsing needed; typed in/out; streaming |
| **No MCP dependency** | MCP adds 50ms+ per tool call for subprocess spawn | Pi's native extensions are faster and lighter |
| **No subagents** | Claude Code has subagents but they require `.claude/agents/*.md` with fixed config | Pi extensions replace the need for subagents as a concept |
| **No permissions system** | Claude Code has `--allowedTools` / `--permission-mode`, but they're CLI flags not runtime checks | Pi extensions can implement runtime permission gating |
| **Sessionless** | Claude Code and OpenCode have heavy session management | Stateless = simpler, cheaper for bounded tasks |

### What Pi Should Borrow from Existing Agents

| Feature | Source | Pi Adaptation |
|---------|--------|---------------|
| `--max-turns` cost cap | Claude Code | RPC request metadata field |
| `--max-budget-usd` spend cap | Claude Code | Metadata field + extension hook |
| `--output-format json` structured output | Claude Code / OpenCode | Native RPC response format |
| Piped input (`cat file \| agent`) | Claude Code | RPC file attachment API |
| Session continuation with `--continue` | Claude Code / OpenCode | Optional session IDs in RPC for multi-step workflows |
| Git worktree isolation | Codex / Claude Code | Built-in workspace management extension |
| Provider agnosticism | OpenCode | Extension API for provider adapters |
| PR review command | Codex / OpenCode | Built-in `review` RPC method |
| Structured JSON with schema validation | Claude Code (`--json-schema`) | RPC schema validation natively |

### What Pi Does Not Need to Build

| Feature | Rationale |
|---------|-----------|
| CLAUDE.md auto-loading | Minimal system prompt philosophy — only load what's given |
| Hooks with JSON config | TypeScript lifecycle hooks are strictly better |
| MCP integration | Pi's extension system replaces MCP as concept |
| tmux orchestration | RPC mode doesn't need terminal tricks; fallback terminal mode can work differently |
| Dialog handling (trust prompts) | RPC mode has no interactive prompts; terminal mode borrows from Claude Code's print mode |

---

## Recommendations for Pi

### Tier 1: Must-Have (Launch)

1. **RPC-first architecture** — Make RPC the primary integration mode with terminal fallback. Every capabilitiy should be expressible as a structured RPC request.
2. **Provider-agnostic** — Extensions should abstract providers. Ship with OpenRouter/Ollama adapters; accept community-built ones.
3. **Minimal system prompt** — Default to 50-150 tokens. Never auto-load project context. Users opt in explicitly.
4. **Cost tracking in RPC responses** — Return `total_cost_usd`, `token_usage`, `duration_ms` in every response (like Claude Code's JSON output).
5. **Workspace isolation** — First-class support for per-request workspace directories, ideally git-aware.

### Tier 2: Competitive (v1.1)

1. **Built-in PR review RPC method** — Accept git repo URL + PR number, return structured review.
2. **Streaming RPC** — Token-by-token streaming of both reasoning and output.
3. **JSON schema validation** — Allow users to specify output schemas per request.
4. **Session IDs for multi-step workflows** — Lightweight session tokens (no heavy session persistence).
5. **Max token/budget limits** — Per-request metadata fields with strict enforcement.

### Tier 3: Differentiator (v2.0+)

1. **TypeScript extension SDK** — npm package with typed APIs for workspace, file ops, provider config, lifecycle hooks.
2. **Runtime permission system** — Extension-based permission gates for file writes, network access, tool execution.
3. **Custom tool registration** — Extensions can register new tools that appear in Pi's tool schema, analogous to MCP but native.
4. **Validation middleware** — Extensions can intercept and validate/transform any request or response.
5. **Provider adapter API** — TypeScript interface for implementing custom LLM providers.

---

## Appendix A: Skill Metadata Comparison

```yaml
# Codex
name: codex
description: "Delegate coding to OpenAI Codex CLI (features, PRs)."
version: 1.0.0
tags: [Coding-Agent, Codex, OpenAI, Code-Review, Refactoring]
related_skills: [claude-code, hermes-agent]
platforms: [linux, macos, windows]

# Claude Code
name: claude-code
description: "Delegate coding to Claude Code CLI (features, PRs)."
version: 2.2.0
tags: [Coding-Agent, Claude, Anthropic, Code-Review, Refactoring, PTY, Automation]
related_skills: [codex, hermes-agent, opencode]
platforms: [linux, macos, windows]

# OpenCode
name: opencode
description: "Delegate coding to OpenCode CLI (features, PR review)."
version: 1.2.0
tags: [Coding-Agent, OpenCode, Autonomous, Refactoring, Code-Review]
related_skills: [claude-code, codex, hermes-agent]
platforms: [linux, macos, windows]
```

## Appendix B: Integrated Orchestration Flow (ASCII)

```
┌─────────────────────────────────────────────────────────┐
│                    Hermes Agent                          │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐    │
│  │   Codex     │  │  Claude Code│  │   OpenCode    │    │
│  │  Skill      │  │  Skill      │  │   Skill       │    │
│  └──────┬──────┘  └──────┬──────┘  └───────┬───────┘    │
│         │                │                 │             │
│    ┌────▼────────────────▼─────────────────▼─────┐       │
│    │         terminal() + process() tools        │       │
│    │   (background=true, pty=true, workdir=...)   │       │
│    └────────────────────┬─────────────────────────┘       │
│                         │                                 │
│                    ┌────▼────┐                            │
│                    │  Subprocess (OS)                      │
│                    │ codex / claude / opencode            │
│                    └─────────┘                            │
└─────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   Pi (Future)    │
                    │  ┌────────────┐  │
                    │  │  RPC Mode  │◄─┤──── RPC (JSON/stream)
                    │  └────────────┘  │
                    │  ┌────────────┐  │
                    │  │ Terminal   │◄─┤──── Fallback
                    │  │ Mode       │  │
                    │  └────────────┘  │
                    │  ┌────────────┐  │
                    │  │ TypeScript │  │
                    │  │ Extensions │  │
                    │  └────────────┘  │
                    └──────────────────┘
```
