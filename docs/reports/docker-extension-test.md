# Docker Extension Compatibility Test

**Date:** 2026-07-24
**Base Image:** `python:3.11-slim`
**Pi Version:** 0.81.1
**Test Environment:** Docker container (clean, no pre-existing state)

## Summary

Verified that `pi-lsp-extension` and `pi-lean-ctx` load together without errors in a clean Docker environment, with all required dependencies and fixes applied.

**Result: PASS** — Both extensions load and register correctly. No "Failed to load extension" errors.

## Prerequisites / Dependencies

| Component | Version | Install Method | Notes |
|-----------|---------|---------------|-------|
| Node.js | 22.23.1 | NodeSource setup_22.x | **Required** — Pi requires Node >= 22 |
| Pi CLI | 0.81.1 | `npm install -g @earendil-works/pi-coding-agent` | |
| pi-lsp-extension | latest (npm) | `pi install npm:pi-lsp-extension` | |
| pi-lean-ctx | latest (npm) | `pi install npm:pi-lean-ctx` | |
| lean-ctx binary | 3.9.12 | `npm install -g lean-ctx-bin` | Required for MCP bridge |
| typescript-language-server | 5.3.0 | `npm install -g typescript-language-server typescript` | Required for TS LSP |
| pi-lean-ctx config | — | Manual (`~/.pi/agent/extensions/pi-lean-ctx/config.json`) | Points binary path |

## Critical Fix Required

### vscode-languageserver-protocol import bug

**File:** `~/.pi/agent/npm/node_modules/pi-lsp-extension/src/lsp-client.ts`

The published package imports from `"vscode-languageserver-protocol/node.js"` but vscode-languageserver-protocol v3.x uses a strict `exports` map that only exposes `"./node"` (no `.js` suffix).

**Fix:**
```bash
sed -i 's|vscode-languageserver-protocol/node\.js|vscode-languageserver-protocol/node|g' \
  ~/.pi/agent/npm/node_modules/pi-lsp-extension/src/lsp-client.ts
```

Without this fix, both extensions fail to load:
```
Error: Failed to load extension: Package subpath './node.js' is not defined by "exports"
```

## lean-ctx MCP Bridge Configuration

The `pi-lean-ctx` extension requires the `lean-ctx` binary on PATH. Install it via `npm install -g lean-ctx-bin` and configure:

```json
{
  "mode": "additive",
  "enableMcp": true,
  "toolProfile": "standard",
  "binary": "/usr/bin/lean-ctx"
}
```

Without this binary, the MCP bridge fails at startup:
```
[lean-ctx MCP bridge] Transport error: spawn lean-ctx ENOENT
```

## Test Results

### Extension Load Test

```
$ pi list
User packages:
  npm:pi-lsp-extension
    /root/.pi/agent/npm/node_modules/pi-lsp-extension
  npm:pi-lean-ctx
    /root/.pi/agent/npm/node_modules/pi-lean-ctx
```

Both extensions appear in `pi list` output.

### No-load-error verification

- `pi -ne -p "echo test"` — No extension load errors (only expected "No API key" message)
- `pi -p "echo test"` — No extension load errors (only expected "No API key" message)
- No "Failed to load extension" messages in any test run

### Test A: LSP Diagnostics (load-only)

LSP extension loads successfully. Full LLM call blocked by missing API key (expected in clean Docker).

### Test B: lean-ctx Compression (load-only)

lean-ctx extension loads successfully. lean-ctx binary responds correctly. Full LLM call blocked by missing API key.

### Test C: Combined Load

Both extensions load simultaneously without conflicts. No inter-extension errors observed.

## Full Docker Setup Script

```bash
# Base: python:3.11-slim
apt-get update -qq && apt-get install -y -qq curl ca-certificates gnupg
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y -qq nodejs

# Pi + extensions
npm install -g @earendil-works/pi-coding-agent --ignore-scripts -q
pi install npm:pi-lsp-extension
pi install npm:pi-lean-ctx

# lean-ctx binary
npm install -g lean-ctx-bin -q

# Configure lean-ctx MCP bridge
mkdir -p ~/.pi/agent/extensions/pi-lean-ctx
cat > ~/.pi/agent/extensions/pi-lean-ctx/config.json << EOF
{
  "mode": "additive",
  "enableMcp": true,
  "toolProfile": "standard",
  "binary": "$(which lean-ctx)"
}
EOF

# Fix vscode-languageserver-protocol import
sed -i 's|vscode-languageserver-protocol/node\.js|vscode-languageserver-protocol/node|g' \
  ~/.pi/agent/npm/node_modules/pi-lsp-extension/src/lsp-client.ts

# TypeScript language server
npm install -g typescript-language-server typescript -q
```

## Issues Found

1. **Node.js version requirement**: Pi 0.81.1 requires Node >= 22. The `python:3.11-slim` image ships Node 20.x by default. Must install Node 22 from NodeSource.
2. **Import path bug**: `pi-lsp-extension` has a hard `.js` suffix on the `vscode-languageserver-protocol` import that conflicts with the library's exports map. Manual fix required until upstream publishes a patched version.
3. **lean-ctx binary not bundled**: `pi-lean-ctx` requires the standalone `lean-ctx-bin` npm package installed globally. The extension does not auto-install this dependency.

## Recommendations

1. **pi-lsp-extension**: Remove `.js` suffix from `vscode-languageserver-protocol/node` import in next release.
2. **pi-lean-ctx**: Consider bundling or auto-downloading the `lean-ctx` binary so it works out of the box.
3. **Documentation**: Add Node 22 requirement to Pi install docs.
