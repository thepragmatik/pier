# API Reference

Pier exposes a Python API across three integration layers. This reference documents the
public interfaces, types, and configuration.

## Layer 1: Skill (Terminal Subprocess)

::: pier.skill

### `pier.run(task: str, *, workdir: str | None = None, timeout: int = 300) -> PierResult`

Execute a coding task via Pi's `run` CLI mode. This is the simplest integration path.

```python
from pier import run

result = run("Add type hints to src/models.py")
print(result.success)    # bool
print(result.summary)    # str — Pi's output summary
print(result.diff)       # str — unified diff of changes
print(result.files)      # list[str] — changed file paths
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `task` | `str` | *required* | The coding task description |
| `workdir` | `str \| None` | `None` | Working directory (defaults to cwd) |
| `timeout` | `int` | `300` | Max execution time in seconds |

**Returns:** `PierResult`

---

## Layer 2: Plugin (RPC Protocol)

::: pier.plugin

### `class PierPlugin`

Async context manager for the RPC protocol bridge. Communicates with Pi over JSONL/stdio.

```python
from pier.plugin import PierPlugin

plugin = PierPlugin()

@plugin.on("task.progress")
def on_progress(event):
    print(f"{event.percent}%: {event.message}")

async with plugin:
    result = await plugin.run("Refactor auth module")
```

#### Methods

##### `run(task: str, *, files: list[str] | None = None) -> PierPluginResult`

Execute a coding task with real-time event streaming.

##### `on(event: str)`

Decorator to register an event handler. Supported events:

- `task.started`, `task.progress`, `task.completed`, `task.failed`
- `file.changed`, `file.created`, `file.deleted`
- `tool.called`, `tool.result`
- `session.status`

##### `cancel()`

Cancel the currently running task.

##### `status() -> PierSessionStatus`

Get the current session state.

---

## Layer 3: Extension (ACP Bridge)

::: pier.extension

### `class PierExtensionBridge`

ACP bridge with TypeScript extension support. The deepest integration tier.

```python
from pier.extension import PierExtensionBridge

bridge = PierExtensionBridge()
bridge.load_extension("./custom-linter.ts")

async with bridge:
    result = await bridge.run("Refactor with custom linting")
```

#### Methods

##### `load_extension(path: str)`

Load a TypeScript extension file. Extensions can hook into Pi's lifecycle events.

##### `run(task: str) -> PierExtensionResult`

Execute a coding task with loaded extensions active.

##### `list_extensions() -> list[ExtensionInfo]`

List all currently loaded extensions.

---

## Shared Types

::: pier.types

### `PierResult`

```python
@dataclass
class PierResult:
    success: bool
    summary: str
    diff: str
    files: list[str]
    exit_code: int
    duration_ms: int
```

### `PierPluginEvent`

```python
@dataclass
class PierPluginEvent:
    type: str           # e.g., "task.progress"
    data: dict          # Event-specific payload
    timestamp: float    # Unix timestamp
```

### `PierSessionStatus`

```python
@dataclass
class PierSessionStatus:
    connected: bool
    task_running: bool
    current_task: str | None
    files_modified: list[str]
    uptime_seconds: int
```

## Configuration

Configuration is read from Hermes profile `config.yaml` under the `pier:` key:

```yaml
pier:
  layer: 2                # Integration layer: 1, 2, or 3
  pi_path: /usr/local/bin/pi
  pi_mode: run            # Pi CLI mode override
  rpc_timeout: 600        # Max seconds per RPC call
  event_buffer: 1000      # Max events to buffer
  log_level: info         # debug, info, warning, error
```
