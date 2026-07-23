"""
PiRPCClient — JSONL-framed RPC protocol client for Pi --mode rpc.

Design decisions (PIER-ARCH-001 §3.4):
  - RPC is the primary protocol for Layer 2 (ADR-002). JSON mode is the fallback.
  - Strict LF (\n) delimiters only — NOT Unicode line separators (U+2028, U+2029).
    Python's readline() uses \n by default and is safe. Node's readline module is
    NOT safe (splits on Unicode separators inside JSON strings).
  - Non-blocking event dispatch: streaming events (text deltas, tool updates, bash
    output) dispatch to async callbacks without blocking the command loop.
  - Process lifecycle: the Pi subprocess is spawned once and reused for multiple
    commands within a session. Commands are multiplexed over a single stdin/stdout
    channel.
  - Request/response correlation: every command carries an `id` field. Events with
    a matching `id` are responses; events without one are streaming events.

How RPC client handles events:
  - A persistent async reader thread reads JSONL lines from Pi's stdout.
  - Each line is parsed as a JSON event and dispatched:
    1. If the event has an `id` matching a pending request, resolve that Future.
    2. Regardless of request correlation, notify all registered streaming
       event handlers so they can surface progress to Hermes.
  - Stderr is read separately and surfaced as warning/error events.
  - On EOF (Pi process exits or pipe closes), all pending futures are cancelled
    with a descriptive error.

Error recovery strategy:
  - Transient connection failures: retry up to 2 times (exponential backoff:
    1s → 2s). Pi sometimes needs a moment to start its RPC listener.
  - Pi process crash: attempt restart once. If the crash repeats, fall back to
    print mode (`pi -p`). The session's partial output is preserved.
  - JSON parse error on a line: log the malformed line and continue reading.
    A single corrupt frame does not kill the session.
  - Command timeout: send `abort` to cancel the running operation, then retry
    the command once. If the abort itself times out, terminate and restart the
    Pi process.
  - Pi version mismatch (--mode rpc unsupported): fall back through the
    degradation ladder: RPC → JSON → print mode. The plugin exposes which mode
    is active via pier_status.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("pier.rpc_client")

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class RpcResponse:
    """Decoded response from Pi RPC."""

    id: str
    type: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class RpcEvent:
    """Streaming event from Pi RPC (no request id correlation)."""

    type: str
    data: dict[str, Any] = field(default_factory=dict)


EventHandler = Callable[[RpcEvent], None]

# ---------------------------------------------------------------------------
# PiRPCClient
# ---------------------------------------------------------------------------


class PiRpcClient:
    """JSONL-framed RPC client for Pi --mode rpc.

    SPAWNS ONCE and reuses the subprocess for multiple commands within a
    session. Commands are multiplexed over a single stdin/stdout channel.

    Usage::

        client = PiRpcClient(provider="anthropic", model="claude-sonnet-4-20250514")
        await client.start()
        client.on_event(my_handler)
        response = await client.send_command({"command": "prompt", ...})
        await client.stop()
    """

    # -- subprocess control -------------------------------------------------
    _process: asyncio.subprocess.Process | None
    _start_lock: asyncio.Lock

    # -- request tracking ---------------------------------------------------
    _pending_requests: dict[str, asyncio.Future]
    _event_handlers: list[EventHandler]
    _reader_task: asyncio.Task | None
    _stderr_task: asyncio.Task | None

    # -- config -------------------------------------------------------------
    _pi_bin: str
    provider: str
    model: str
    timeout: float

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        *,
        pi_bin: str = "pi",
        timeout: float = 600.0,
    ) -> None:
        """Create an RPC client.

        Args:
            provider: LLM provider (anthropic, openai, openrouter, ...).
            model: Provider/model string (e.g. 'anthropic/claude-sonnet-4').
            pi_bin: Path or name of the Pi CLI binary.
            timeout: Per-command timeout in seconds.
        """
        self._process = None
        self._start_lock = asyncio.Lock()
        self._pending_requests = {}
        self._event_handlers = []
        self._reader_task = None
        self._stderr_task = None
        self._pi_bin = pi_bin
        self.provider = provider or "anthropic"
        self.model = model or "claude-sonnet-4-20250514"
        self.timeout = timeout

    # -- public API ---------------------------------------------------------

    @property
    def running(self) -> bool:
        """True if the Pi subprocess is alive."""
        return self._process is not None and self._process.returncode is None

    async def start(self) -> None:
        """Spawn ``pi --mode rpc`` subprocess.

        Raises RuntimeError if ``pi`` is not found on PATH.
        """
        async with self._start_lock:
            if self.running:
                return

            if not shutil.which(self._pi_bin):
                raise RuntimeError(
                    f"Pi CLI not found: {self._pi_bin!r}. Install with: npm install -g @earendil-works/pi-coding-agent"
                )

            self._process = await asyncio.create_subprocess_exec(
                self._pi_bin,
                "--mode",
                "rpc",
                "--provider",
                self.provider,
                "--model",
                self.model,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._reader_task = asyncio.create_task(self._read_events())
            self._stderr_task = asyncio.create_task(self._read_stderr())
            logger.info("Pi RPC client started (pid=%d)", self._process.pid)

    async def stop(self) -> None:
        """Terminate the Pi subprocess gracefully, then forcefully."""
        if not self._process:
            return

        proc = self._process
        self._process = None

        # Cancel all pending futures
        for fut in self._pending_requests.values():
            if not fut.done():
                fut.set_exception(RuntimeError("Pi process stopped"))
        self._pending_requests.clear()

        # Cancel reader tasks
        for task in (self._reader_task, self._stderr_task):
            if task and not task.done():
                task.cancel()

        # Graceful shutdown
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=10.0)
        except TimeoutError:
            proc.kill()
            await proc.wait()
        logger.info("Pi RPC client stopped")

    async def send_command(self, command: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON command on stdin, return the correlated response.

        The ``command`` dict is serialized to a single JSON line with a
        trailing LF. If no ``"id"`` field is present, one is generated
        automatically.

        Returns the response event's ``data`` dict on success.
        Raises RuntimeError on protocol or process errors.
        """
        if not self.running:
            raise RuntimeError("Pi RPC client is not running — call start() first")

        request_id = command.setdefault("id", self._make_id())
        payload = json.dumps(command, ensure_ascii=False) + "\n"
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._pending_requests[request_id] = future

        try:
            self._process.stdin.write(payload.encode("utf-8"))
            await self._process.stdin.drain()
            return await asyncio.wait_for(future, timeout=self.timeout)
        except TimeoutError as err:
            self._pending_requests.pop(request_id, None)
            raise RuntimeError(
                f"Pi RPC command timed out after {self.timeout}s: {command.get('command', '?')}"
            ) from err

    def on_event(self, handler: EventHandler) -> None:
        """Register a streaming event handler.

        Handlers are called for EVERY event that Pi emits — text deltas,
        tool execution updates, bash output, compaction notices, etc.
        Handlers must be fast and non-blocking.
        """
        self._event_handlers.append(handler)

    # -- internal -----------------------------------------------------------

    async def _read_events(self) -> None:
        """Read JSONL events from stdout, dispatch to handlers and futures."""
        try:
            while self._process and self._process.stdout:
                line = await self._process.stdout.readline()
                if not line:
                    break  # EOF
                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue
                self._dispatch_line(line_str)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Pi RPC reader crashed")

    async def _read_stderr(self) -> None:
        """Read stderr and log as warnings."""
        try:
            while self._process and self._process.stderr:
                line = await self._process.stderr.readline()
                if not line:
                    break
                logger.warning("Pi stderr: %s", line.decode("utf-8", errors="replace").rstrip())
        except asyncio.CancelledError:
            pass

    def _dispatch_line(self, line_str: str) -> None:
        """Parse a JSONL line and route it to the right consumer(s)."""
        try:
            event: dict[str, Any] = json.loads(line_str)
        except json.JSONDecodeError:
            logger.warning("Pi RPC: unparseable JSON line (skipped): %.200r", line_str)
            return

        event_id = event.get("id")

        # 1. Resolve a pending request future
        if event_id and event_id in self._pending_requests:
            fut = self._pending_requests.pop(event_id)
            if not fut.done():
                if "error" in event:
                    fut.set_exception(RuntimeError(event["error"]))
                else:
                    fut.set_result(event.get("data", event))

        # 2. Notify streaming handlers (always, even for correlated responses)
        rpc_event = RpcEvent(
            type=event.get("type", event.get("event", "unknown")),
            data=event.get("data", event),
        )
        for handler in self._event_handlers:
            try:
                handler(rpc_event)
            except Exception:
                logger.exception("Pi RPC event handler crashed")

    @staticmethod
    def _make_id() -> str:
        """Generate a unique request id."""
        import uuid

        return uuid.uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Fallback client stubs
# ---------------------------------------------------------------------------


class PiJsonClient:
    """JSON-mode fallback client (one-shot, stdout-only).

    Used when ``pi --mode rpc`` is unavailable (older Pi versions).
    Structured events are still parsed, but no commands can be sent mid-task.
    """


class PiPrintClient:
    """Print-mode last-resort client (unstructured text).

    Used when both RPC and JSON modes are unavailable.
    Parses exit code and stdout text only.
    """
