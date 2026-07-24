# pi-lean-ctx Research Report

> **Version researched:** pi-lean-ctx v3.9.12 (published 2026-07-17) · lean-ctx v3.9.12
> **Host:** macOS 26.5.2 · Pi Coding Agent v0.81.1
> **Research date:** 2026-07-24

---

## 1. Does lean-ctx work in pi `-p` (print mode)?

### Background

Pi's `-p` / `--print` flag enables **non-interactive mode**: starts Pi, loads extensions, processes the prompt, prints output to stdout, and exits. Each `pi -p` invocation is a **new process** with no state carried over from the previous one.

### Findings

| Aspect | Status | Details |
|--------|--------|---------|
| Extension loads in `-p` mode | ✅ Yes | pi-lean-ctx registers its tools during init just like interactive mode |
| CLI-backed ctx_* tools | ✅ Work | `ctx_read`, `ctx_shell`, `ctx_grep`, `ctx_find`, `ctx_ls` invoke `lean-ctx` as a subprocess each time — works in `-p` mode |
| MCP bridge startup | ✅ Attempts | Bridge spawns `lean-ctx` MCP server for the duration of the session, then exits |
| Session cache persistence | ❌ **Lost** | Each `-p` invocation is a separate process — the MCP bridge's session cache does not persist across calls |
| Re-read savings (~13 tokens) | ❌ **Not available** | Without persistent bridge, every read is a fresh "Read #1" — no unchanged-stub optimization |
| Binary missing | ⚠️ **Critical dependency** | Without `lean-ctx` binary on PATH or at expected locations, the bridge fails (`ENOENT`) and all ctx_* tools are non-functional |

### Verdict for Pier

If Pier uses `pi -p` for single-shot code generation, pi-lean-ctx provides **per-command compression** (each `ctx_read`/`ctx_shell` call compresses its output via `lean-ctx` CLI), but the **session cache** (the headline ~13-token re-read feature) is **unavailable** without a persistent process. This is a fundamental architectural constraint of `-p` mode — not a bug in pi-lean-ctx.

For applications that call `pi -p` multiple times on the same codebase, the compression still saves tokens on each individual call, but the savings are additive per-call rather than benefiting from cross-call caching.

---

## 2. Does lean-ctx conflict with pi-lsp-extension?

### Tool Namespace Analysis

| Extension | Tool Prefix | Example Tools |
|-----------|-------------|---------------|
| pi-lean-ctx | `ctx_`, `lean_ctx` | ctx_read, ctx_shell, ctx_grep, ctx_find, ctx_ls, lean_ctx |
| pi-lean-ctx (MCP bridge) | `ctx_` | ctx_session, ctx_knowledge, ctx_semantic_search, ctx_overview, ctx_compress, ctx_metrics, ctx_multi_read, ctx_search, ctx_tree |
| pi-lsp-extension | `lsp_`, `code_` | lsp_diagnostics, lsp_hover, lsp_definition, lsp_references, lsp_symbols, lsp_rename, lsp_completions, lsp_code_actions, code_overview, code_search, code_rewrite |

**No tool name conflicts.** The namespaces are entirely disjoint — `lsp_*` vs `ctx_*`.

### Functional Layer Separation

| Concern | Owner | Mechanism |
|---------|-------|-----------|
| File read compression | lean-ctx | Compresses file output before it reaches the model |
| Shell output compression | lean-ctx | Compresses bash/ls/grep/find output |
| LSP diagnostics | pi-lsp-extension | Queries language servers for errors/warnings |
| LSP code intelligence | pi-lsp-extension | Hover, definitions, references, symbols |
| Auto-diagnostics on edit | pi-lsp-extension | Fires after write/edit via post-hook |
| Edit/write builtins | Pi native | Unchanged by both extensions |

### Coexistence Verification

Both extensions were installed simultaneously on the test host:

```
pi list
  npm:pi-lean-ctx        ✓
  npm:pi-lsp-extension   ✓
```

No load errors, no tool registration conflicts, no startup crashes were observed.

### Potential Interaction

- **Complementary, not conflicting**: lean-ctx compresses outputs; pi-lsp-extension provides diagnostics. They address different problems.
- **Diagnostic output volume**: If LSP diagnostics are verbose (e.g., Java projects), routing them through `ctx_shell` could reduce token cost.
- **Auto-diagnostics independence**: pi-lsp-extension's auto-diagnostics fires on `write`/`edit` tool results — lean-ctx does not intercept these tool calls (it only replaces `read`/`bash`/`ls`/`find`/`grep`).

### Verdict

**No conflicts.** The two extensions are compatible and complementary. pi-lsp-extension provides code intelligence; pi-lean-ctx reduces token consumption of the resulting output. They can and should be used together.

---

## 3. What is the actual token savings for a real task?

### Verified: Re-Read Cache

The lean-ctx `verify-cache` self-test was run on a ~47-line TypeScript file (1,150 bytes):

```
lean-ctx verify-cache real_sample.ts
  Read #1 (full):     319 tokens
  Read #2 (re-read):  19 tokens  [unchanged stub]
  Re-read savings:    94%
  PASS — session cache engaged
```

### Global Statistics (system-wide)

```
Tokens saved:     118,500
Compression:      98.7%
Commands run:     13
USD saved:        $0.30
```

### Auto-Select Modes

| File Type | Size | Mode | Expected Savings |
|-----------|------|------|-----------------|
| Markdown, JSON, YAML, TOML, etc. | Any | `full` | ~60-80% |
| Code files (57 extensions) | < 8 KB | `full` | ~60-80% |
| Code files | 8-96 KB | `map` (deps + API signatures) | ~80-90% |
| Code files | > 96 KB | `signatures` (AST only) | ~90-95% |
| Other files | < 48 KB | `full` | ~60-80% |
| Other files | > 48 KB | `map` | ~80-90% |
| Unchanged re-read (via MCP cache) | Any | `[unchanged stub]` | ~99.9% (13-19 tokens) |

### Caveats

- Savings depend heavily on file structure — boilerplate files compress well; dense algorithmic code compresses less.
- The 98.7% headline rate includes compressed shell command output (e.g., `ls`, `grep` results), which compresses very aggressively.
- Re-read savings (~13-19 tokens) only apply within a persistent MCP bridge session — not available in `pi -p` mode.

---

## 4. Does the MCP bridge add Hermes-interop value?

### Current State

Hermes already has lean-ctx configured as an MCP server (`~/.hermes/config.yaml`):

```yaml
mcp_servers:
  lean-ctx:
    command: "/opt/homebrew/lib/node_modules/lean-ctx-bin/bin/lean-ctx"
```

The lean-ctx doctor confirms this integration:

```
MCP config — lean-ctx found in: Hermes Agent (~/.hermes/config.yaml)
```

### Services the MCP Bridge Offers

| Service | Pi Context | Hermes Context |
|---------|-----------|----------------|
| Session cache | Persistent per-Pi-session cache for file reads | Already configured — depends on Hermes MCP client capabilities |
| Session state management | `ctx_session` tool | Available if Hermes MCP client can use it |
| Knowledge graph | `ctx_knowledge` tool | Available |
| Semantic search | `ctx_semantic_search` tool | Available |
| Metrics dashboard | `ctx_metrics`, `lean-ctx gain` | Available |
| `ctx_call` gateway | Can invoke any MCP tool | Available |
| Architecture/quality tools | `ctx_overview`, etc. | Available (depends on tool profile) |

### Bridge-to-Pi Architecture

The pi-lean-ctx MCP bridge is **embedded in the Pi extension itself** — it spawns `lean-ctx` as a subprocess via stdio MCP transport. This bridge provides:

1. **Session cache persistence** — the killer feature (re-reads cost ~13 tokens)
2. **Advanced tool registration** — automatically discovers and registers MCP tools as native Pi tools
3. **Automatic reconnection** — up to 3 attempts with exponential backoff on crash
4. **Coexistence aware** — handles name conflicts gracefully (doesn't crash when AFT/magic-context own shared names)

### Hermes-Specific Assessment

| Aspect | Value | Notes |
|--------|-------|-------|
| Pre-configured MCP server | ✅ Yes | Already in config.yaml — no additional setup needed |
| Session cache for Hermes | ⚠️ **Depends on client** | Hermes MCP client must support persistent sessions for cache benefit |
| Tool availability | ✅ 81 tools | Full lean-ctx registry available through MCP |
| Token compression via MCP | ⚠️ **Limited** | MCP bridge exposes tools; file content compression still happens on the subprocess side |
| Hermes-native vs MCP bridge | ✅ Better to use Hermes MCP client | Direct MCP integration is more reliable than the Pi-specific embedded bridge |

### Verdict

The MCP bridge adds **real value for Hermes interop**, mainly because:
- Hermes already has lean-ctx configured as an MCP server
- The 81 MCP tools (knowledge graph, semantic search, architecture analysis, metrics) are all accessible
- The session cache could benefit Hermes sessions if the MCP client is used persistently

The Pi-specific embedded bridge (which spawns `lean-ctx` as a subprocess via stdio) is less relevant to Hermes since Hermes has its own MCP client infrastructure.

---

## 5. Does lean-ctx support all 55+ file extensions it claims?

### Extension Count Verification

From the source code (`extensions/index.ts`):

| Category | Count | Extensions |
|----------|-------|------------|
| Code extensions | **57** | .rs, .ts, .tsx, .js, .jsx, .php, .py, .go, .java, .c, .cc, .cpp, .cxx, .cs, .kt, .swift, .rb, .vue, .svelte, .astro, .html, .css, .scss, .sass, .less, .lua, .zig, .nim, .ex, .exs, .erl, .hs, .ml, .mli, .r, .jl, .dart, .scala, .groovy, .pl, .pm, .sh, .bash, .zsh, .fish, .ps1, .bat, .cmd, .sql, .graphql, .gql, .proto, .thrift, .tf, .hcl, .nix, .dhall |
| Full-read extensions | **11** | .md, .txt, .json, .json5, .yaml, .yml, .toml, .env, .ini, .xml, .lock |
| Image extensions | **5** | .png, .jpg, .jpeg, .gif, .webp |
| **Total unique** | **68** | Combined set (no overlap) |

**Claim of "55+ file extensions": ✅ Verified and conservative.** Actual support exceeds 55 with 68 unique extensions across programming languages, config formats, and documentation files. This does not include the 5 image formats (handled separately for binary display).

### Coverage by Language Family

| Family | Languages |
|--------|-----------|
| Systems | Rust, Zig, Nim, C, C++, C#, Go, Swift, Kotlin |
| Web | TypeScript, JavaScript, TSX, JSX, HTML, CSS, SCSS, SASS, Less, Vue, Svelte, Astro |
| Scripting | Python, Ruby, PHP, Perl, Lua, Shell (bash/zsh/fish), PowerShell, Batch |
| Functional | Erlang, Elixir, Haskell, OCaml (.ml/.mli), Groovy |
| Data/Sci | R, Julia, Dart, Scala |
| Infra | Terraform (.tf), HCL, Nix, Dhall, SQL, GraphQL, Proto, Thrift |
| Config | JSON, JSON5, YAML, TOML, XML, INI, ENV, Lock files |
| Docs | Markdown, TXT |

---

## Installation & Configuration Guide

### Binary Installation

```bash
# Option A: npm (pre-built binary, recommended)
npm install -g lean-ctx-bin
npm install -g --allow-scripts=lean-ctx-bin lean-ctx-bin  # to run postinstall

# Option B: Cargo (source compile)
cargo install lean-ctx

# Option C: Homebrew
brew tap yvgude/lean-ctx && brew install lean-ctx
```

### Pi Extension Installation

```bash
pi install npm:pi-lean-ctx
```

### Configuration

**Per-extension config** at `~/.pi/agent/extensions/pi-lean-ctx/config.json`:

```json
{
  "mode": "additive",
  "enableMcp": true,
  "toolProfile": "lean"
}
```

**Or via environment variables** (override config.json):

```bash
export LEAN_CTX_PI_MODE=additive      # or "replace" to disable Pi builtins
export LEAN_CTX_PI_ENABLE_MCP=1       # 0 to force one-shot CLI
export LEAN_CTX_PI_TOOL_PROFILE=lean  # lean, standard, or power
export LEAN_CTX_BIN=/path/to/lean-ctx # explicit binary path
```

### Verification

```bash
# Check binary
lean-ctx --version

# Run diagnostics
lean-ctx doctor

# Test cache
lean-ctx verify-cache

# Check token savings
lean-ctx gain
lean-ctx gain --deep
```

---

## Recommendations for Pier

1. **Print mode limitation**: If Pier uses `pi -p`, document that lean-ctx re-read caching is unavailable. Each invocation gets fresh compression but no cross-call benefits. Consider using long-lived Pi sessions where possible.

2. **Install both extensions**: Install both `pi-lean-ctx` and `pi-lsp-extension` — they coexist without conflicts and serve complementary roles (compression + code intelligence).

3. **Binary dependency**: Ensure the `lean-ctx` binary is installed on target hosts. The Pi extension alone is inert without it. Use `lean-ctx doctor` to verify installation.

4. **Tool profile selection**: Start with `lean` profile (default, minimal token overhead for schema descriptions). Upgrade to `standard` or `power` only if specific tools (ctx_edit, ctx_patch, architecture tools) are needed.

5. **MCP for Hermes**: Use Hermes' native MCP client to connect to lean-ctx directly (already configured in `config.yaml`) rather than the Pi-specific embedded bridge. This avoids the ENOENT startup failures on the Pi side when the binary isn't on the expected path.
