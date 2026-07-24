# Pi Extension Setup

> **Last updated:** 2026-07-24
>
> Step-by-step guide for installing and configuring Pi extensions.
> Covers LSP diagnostics (`pi-lsp-extension`) and context trimming (`pi-lean-ctx`).

---

## Overview

Pi's extension system installs packages via `pi install npm:<package>` and
loads their TypeScript/JavaScript entry points on session start. Extensions
can register tools, slash commands, lifecycle hooks, and config flags.

This guide walks through installing two core extensions:

| Extension | Purpose | Package |
|-----------|---|--------|
| pi-lsp-extension | Language Server Protocol diagnostics — lint and type-check without leaving Pi | `npm:pi-lsp-extension` |
| pi-lean-ctx | Intelligent context trimming — strip noise from large prompts | `npm:pi-lean-ctx` |

---

## Prerequisites

- **Pi CLI** installed and on PATH ([Install Pi](https://github.com/thepragmatik/pier))
- **Node.js** ≥ 18 (Pi's runtime)
- **npm** (bundled with Node.js)

Verify Pi is ready:

```bash
pi --version
# Expected: pi 0.81.1 or later
```

---

## 1. Install pi-lsp-extension

`pi-lsp-extension` integrates Language Server Protocol diagnostics into Pi
sessions. It registers a `lsp_diagnostics` tool that runs diagnostics against
project files using installed language servers, giving the model real-time
feedback on type errors, lint violations, and code quality issues.

### Install the extension

```bash
pi install npm:pi-lsp-extension
```

This adds the `lsp_diagnostics` tool to Pi's tool registry. The extension
loads on every session start.

### Install language servers

The LSP extension requires at least one language server to be useful. Install
the servers that match your project's languages:

**TypeScript/JavaScript — `typescript-language-server`**

```bash
npm install -g typescript-language-server typescript
```

The `typescript` package provides `tsserver`, which typescript-language-server
wraps.

**Python — `pyright`**

```bash
npm install -g pyright
```

Validate the servers are discoverable:

```bash
typescript-language-server --version
pyright --version
```

### Configuration

Create `~/.pi/agent/extensions/lsp/config.json`:

```json
{
  "servers": {
    "typescript": {
      "command": "typescript-language-server",
      "args": ["--stdio"],
      "fileTypes": ["ts", "tsx", "js", "jsx"]
    },
    "pyright": {
      "command": "pyright-langserver",
      "args": ["--stdio"],
      "fileTypes": ["py", "pyi"]
    }
  }
}
```

The extension auto-selects the correct server based on the file extension.

---

## 2. Install pi-lean-ctx

`pi-lean-ctx` trims context that does not contribute to the current task,
reducing token usage and keeping the model focused on what matters. It
registers a `lean` tool that can be invoked explicitly or configured to
run automatically on each turn.

### Install the extension

```bash
pi install npm:pi-lean-ctx
```

This registers the `lean` tool — no additional language dependencies required.

### Configuration

Create `~/.pi/agent/extensions/lean-ctx/config.json`:

```json
{
  "autoTrim": true,
  "trimThreshold": 0.85,
  "preserveToolOutputs": true,
  "preserveRecentTurns": 3
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `autoTrim` | `true` | Automatically trim context before each model call |
| `trimThreshold` | `0.85` | Fraction of context window above which trimming triggers |
| `preserveToolOutputs` | `true` | Never trim tool call results |
| `preserveRecentTurns` | `3` | Keep the most recent N turns intact |

---

## 3. Recommended Pi Settings

Pi reads global preferences from `~/.pi/settings.json`. The following values
are recommended for extension-heavy workflows:

```json
{
  "maxTurns": 150,
  "defaultThinkingLevel": "medium",
  "extensionTimeoutMs": 30000,
  "logLevel": "warn"
}
```

| Setting | Value | Rationale |
|---------|-------|-----------|
| `maxTurns` | `150` | Gives the model enough runway for multi-file refactors with LSP-guided iterations |
| `defaultThinkingLevel` | `"medium"` | Balanced token budget — enough reasoning for diagnostics triage without excessive overhead |
| `extensionTimeoutMs` | `30000` | 30-second startup window for language servers (pyright cold start ~5–8s) |
| `logLevel` | `"warn"` | Suppress info/debug noise from extensions in headless mode |

!!! tip "Per-project overrides"
    Copy `~/.pi/settings.json` into any project root as `.pi/settings.json`
    to override these defaults per-repo. Pi picks the nearest `.pi/settings.json`
    walking up from the current working directory.

---

## 4. Verify Installation

List installed extensions:

```bash
pi list
```

Expected output (extension section):

```
Extensions (2 loaded):
  • pi-lsp-extension    npm:pi-lsp-extension    tools: lsp_diagnostics
  • pi-lean-ctx         npm:pi-lean-ctx          tools: lean
```

If an extension is missing, re-run the install command. If it appears but
shows `(error)` next to its name, check the logs:

```bash
pi logs --level debug 2>&1 | grep -i "extension"
```

---

## 5. Test LSP Diagnostics

Verify that `lsp_diagnostics` can analyze Python files in your project:

```bash
pi -p "run lsp_diagnostics on tests/test_plugin.py"
```

Expected behavior:

- Pi invokes `lsp_diagnostics` with the file path `tests/test_plugin.py`
- The extension launches `pyright-langserver`, runs diagnostics, and returns a
  report with any type errors, unused imports, or style issues
- Pi renders the diagnostics results in its response

If pyright is not found, make sure it was installed globally (`npm install -g pyright`)
and that `pyright-langserver` is on PATH.

### Troubleshooting LSP startup

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `lsp_diagnostics` returns empty | Wrong working directory | `cd` to project root before running |
| `Command not found: pyright-langserver` | pyright not on PATH | `npm install -g pyright` or add `~/.npm-global/bin` to PATH |
| `Timeout waiting for server` | pyright cold start | Increase `extensionTimeoutMs` in settings.json |

---

## 6. Test Lean Context

Verify that `lean` can read and summarize a file:

```bash
pi -p "read tests/test_plugin.py and summarize its purpose"
```

Expected behavior:

- Pi reads the file (via its built-in file tool or `read` command)
- If auto-trim is enabled, `pi-lean-ctx` trims any context window bloat before
  the model responds
- Pi returns a concise summary of the test file (e.g., "Unit tests for the Pier
  plugin covering tool registration, install checks, delegation, and helper
  functions")

To confirm the lean tool is active, check the session metadata:

```bash
pi -p "what tools are available in this session?"
```

The response should list `lean` among the registered tools.

---

## All-In-One Verification

Run this short script to confirm both extensions work end-to-end:

```bash
# 1. Check extensions are registered
pi list | grep -E "pi-lsp-extension|pi-lean-ctx" && echo "✓ Extensions loaded"

# 2. LSP diagnostics on a Python test file
pi -p "run lsp_diagnostics on tests/test_plugin.py" && echo "✓ LSP works"

# 3. Lean context summarization
pi -p "read tests/test_plugin.py and summarize" && echo "✓ Lean context works"

echo ""
echo "All checks passed. Pi extensions are ready."
```

---

## Next Steps

- **[Plugins](plugins.md)** — Learn about Pier's Layer 2 and Layer 3 integration
- **[Getting Started](getting-started.md)** — Your first Pier delegation
- **[Pi Extension Ecosystem Guide](../reference/pi-ecosystem-guide.md)** — Deep-dive evaluations of other Pi extensions
