# Plugins (Layers 2 & 3)

Layers 2 and 3 of Pier are Hermes plugins that unlock Pi's structured RPC protocol and
TypeScript extension system.

## Layer 2: RPC Plugin

The Layer 2 plugin communicates with Pi over its JSONL-based RPC protocol via stdio.
Instead of parsing terminal output, Hermes sends typed commands and receives structured
event streams.

### Architecture

```
Hermes Agent                    Pi Process
┌──────────┐    JSONL/stdio    ┌──────────┐
│  Pier    │ ◄──────────────► │  pi rpc   │
│  Plugin  │                   │           │
└──────────┘                   └──────────┘
```

### Commands

The RPC protocol exposes 20+ commands. Key ones:

| Command | Description |
|---------|-------------|
| `task/run` | Execute a coding task |
| `task/cancel` | Cancel a running task |
| `file/read` | Read a file from the workspace |
| `file/write` | Write a file to the workspace |
| `session/status` | Get current session state |
| `diff/get` | Retrieve the current working diff |

### Events

Pi emits 18 event types that the plugin can subscribe to:

| Event | Description |
|-------|-------------|
| `task.started` | A task began execution |
| `task.progress` | Progress update (percentage + message) |
| `task.completed` | Task finished successfully |
| `task.failed` | Task failed with error |
| `file.changed` | A file was modified |
| `tool.called` | Pi invoked a tool |
| `tool.result` | Tool invocation result |

### Using the Plugin

```python
from pier.plugin import PierPlugin

plugin = PierPlugin()

# Subscribe to events
@plugin.on("task.progress")
def on_progress(event):
    print(f"[{event.percent}%] {event.message}")

# Run a task
result = await plugin.run("Add type hints to all public functions")
print(f"Files changed: {len(result.files)}")
print(f"Diff: {result.diff}")
```

## Layer 3: Extension Bridge

Layer 3 adds an ACP (Agent Communication Protocol) bridge and full TypeScript extension
support. This is the deepest integration tier — Hermes can load and orchestrate Pi
extensions written in TypeScript.

### When to Use Layer 3

- You need custom toolchains that Pi's built-in tools don't cover
- You want to hook into Pi's internal lifecycle (pre-task, post-tool, etc.)
- You're building a long-running agent that needs persistent TypeScript context

### Extension Example

```typescript
// pier-extension.ts
import { PierExtension } from "@earendil-works/pi";

export default class CustomLinter extends PierExtension {
  async onPreToolCall(tool: string, args: Record<string, unknown>) {
    if (tool === "file/write") {
      // Auto-format before writing
      args.content = await this.format(args.content as string);
    }
  }
}
```

```python
# Load it from Hermes
from pier.extension import PierExtensionBridge

bridge = PierExtensionBridge()
bridge.load_extension("./pier-extension.ts")
result = await bridge.run("Refactor with custom linting rules")
```

## Configuration

Plugin configuration lives in your Hermes profile's `config.yaml`:

```yaml
plugins:
  enabled:
    - pier

pier:
  layer: 2              # 1 (skill), 2 (plugin), or 3 (extension)
  pi_path: /usr/local/bin/pi
  rpc_timeout: 600       # Max seconds per RPC call
  event_buffer: 1000     # Max events to buffer before dropping
```

## Next Steps

- [Developer Guide](../developer-guide/index.md) — architecture details and contributing
- [ADR-001: Integration Approach](../architecture/adr-001-integration-approach.md) — why we chose this layered design
- [ADR-002: Communication Protocol](../architecture/adr-002-communication-protocol.md) — RPC protocol design rationale
