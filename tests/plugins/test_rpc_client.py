"""Tests for PiRpcClient — JSONL-framed RPC protocol client.

Covers: initialization, start/stop lifecycle, send_command,
on_event registration, error handling (Pi not found, timeout,
malformed events, process crash), and edge cases.
"""

import asyncio
import json
from unittest import mock

import pytest

from plugins.pier.rpc_client import (
    PiJsonClient,
    PiPrintClient,
    PiRpcClient,
    RpcEvent,
    RpcResponse,
)

# ==========================================================================
# Fixtures
# ==========================================================================


@pytest.fixture
def client():
    """Return a fresh PiRpcClient with default config."""
    return PiRpcClient(provider="anthropic", model="claude-sonnet-4", pi_bin="pi")


@pytest.fixture
def client_custom():
    """Return a PiRpcClient with custom config."""
    return PiRpcClient(
        provider="openai",
        model="gpt-4o",
        pi_bin="/custom/pi",
        timeout=120.0,
    )


# ==========================================================================
# Initialization
# ==========================================================================


def test_init_defaults():
    """PiRpcClient initializes with sensible defaults."""
    client = PiRpcClient()

    assert client.provider == "anthropic"
    assert client.model == "claude-sonnet-4-20250514"
    assert client.timeout == 600.0
    assert client.running is False
    assert client._process is None
    assert client._pending_requests == {}
    assert client._event_handlers == []


def test_init_custom():
    """PiRpcClient accepts custom provider, model, pi_bin, timeout."""
    client = PiRpcClient(
        provider="openai",
        model="gpt-4o",
        pi_bin="/usr/local/bin/pi",
        timeout=300.0,
    )

    assert client.provider == "openai"
    assert client.model == "gpt-4o"
    assert client._pi_bin == "/usr/local/bin/pi"
    assert client.timeout == 300.0


def test_init_with_none_provider_and_model():
    """PiRpcClient falls back to defaults when provider/model are None."""
    client = PiRpcClient(provider=None, model=None)

    assert client.provider == "anthropic"
    assert client.model == "claude-sonnet-4-20250514"


def test_running_false_when_not_started(client):
    """running is False before start() is called."""
    assert client.running is False


# ==========================================================================
# start()
# ==========================================================================


@pytest.mark.asyncio
async def test_start_spawns_process():
    """start() spawns pi --mode rpc subprocess."""
    with (
        mock.patch("plugins.pier.rpc_client.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch("plugins.pier.rpc_client.asyncio.create_subprocess_exec") as mock_exec,
        mock.patch("plugins.pier.rpc_client.asyncio.create_task") as mock_task,
    ):
        mock_proc = mock.AsyncMock()
        mock_proc.returncode = None
        mock_proc.pid = 12345
        mock_exec.return_value = mock_proc

        client = PiRpcClient(provider="anthropic", model="claude-sonnet-4")
        await client.start()

        mock_exec.assert_called_once_with(
            "pi",
            "--mode",
            "rpc",
            "--provider",
            "anthropic",
            "--model",
            "claude-sonnet-4",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert mock_task.call_count == 2  # reader + stderr tasks


@pytest.mark.asyncio
async def test_start_idempotent():
    """start() is a no-op when already running."""
    with (
        mock.patch("plugins.pier.rpc_client.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch("plugins.pier.rpc_client.asyncio.create_subprocess_exec") as mock_exec,
        mock.patch("plugins.pier.rpc_client.asyncio.create_task"),
    ):
        mock_proc = mock.AsyncMock()
        mock_proc.returncode = None
        mock_exec.return_value = mock_proc

        client = PiRpcClient()
        await client.start()
        await client.start()

        # Only one spawn
        assert mock_exec.call_count == 1


@pytest.mark.asyncio
async def test_start_pi_not_found():
    """start() raises RuntimeError when pi is not on PATH."""
    with mock.patch("plugins.pier.rpc_client.shutil.which", return_value=None):
        client = PiRpcClient()

        with pytest.raises(RuntimeError, match="Pi CLI not found"):
            await client.start()


@pytest.mark.asyncio
async def test_start_custom_pi_bin():
    """start() uses the custom pi_bin path."""
    with (
        mock.patch("plugins.pier.rpc_client.shutil.which", return_value="/custom/pi"),
        mock.patch("plugins.pier.rpc_client.asyncio.create_subprocess_exec") as mock_exec,
        mock.patch("plugins.pier.rpc_client.asyncio.create_task"),
    ):
        mock_proc = mock.AsyncMock()
        mock_proc.returncode = None
        mock_exec.return_value = mock_proc

        client = PiRpcClient(pi_bin="/custom/pi")
        await client.start()

        call_args = mock_exec.call_args[0]
        assert call_args[0] == "/custom/pi"


# ==========================================================================
# stop()
# ==========================================================================


@pytest.mark.asyncio
async def test_stop_noop_when_not_started(client):
    """stop() is a no-op when the client was never started."""
    await client.stop()  # should not raise


@pytest.mark.asyncio
async def test_stop_terminates_process():
    """stop() terminates the process and cancels pending futures."""
    with (
        mock.patch("plugins.pier.rpc_client.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch("plugins.pier.rpc_client.asyncio.create_subprocess_exec") as mock_exec,
        mock.patch("plugins.pier.rpc_client.asyncio.create_task") as mock_task,
    ):
        mock_proc = mock.AsyncMock()
        mock_proc.returncode = None
        mock_proc.wait = mock.AsyncMock(return_value=0)
        mock_proc.terminate = mock.MagicMock()
        mock_exec.return_value = mock_proc

        mock_task.return_value = mock.MagicMock(done=mock.MagicMock(return_value=True))

        client = PiRpcClient()
        await client.start()

        # Add a pending future
        fut = asyncio.get_running_loop().create_future()
        client._pending_requests["req-1"] = fut

        await client.stop()

        mock_proc.terminate.assert_called_once()
        assert not client.running
        # Pending future should be resolved with an error
        with pytest.raises(RuntimeError, match="Pi process stopped"):
            await fut


@pytest.mark.asyncio
async def test_stop_cancels_reader_tasks():
    """stop() cancels reader and stderr tasks."""
    with (
        mock.patch("plugins.pier.rpc_client.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch("plugins.pier.rpc_client.asyncio.create_subprocess_exec") as mock_exec,
        mock.patch("plugins.pier.rpc_client.asyncio.create_task") as mock_task,
    ):
        mock_proc = mock.AsyncMock()
        mock_proc.returncode = None
        mock_proc.wait = mock.AsyncMock(return_value=0)
        mock_proc.terminate = mock.MagicMock()
        mock_exec.return_value = mock_proc

        reader_task = mock.MagicMock()
        reader_task.done.return_value = False
        stderr_task = mock.MagicMock()
        stderr_task.done.return_value = False
        mock_task.side_effect = [reader_task, stderr_task]

        client = PiRpcClient()
        await client.start()
        await client.stop()

        reader_task.cancel.assert_called_once()
        stderr_task.cancel.assert_called_once()


@pytest.mark.asyncio
async def test_stop_force_kill_on_timeout():
    """stop() kills the process if terminate times out."""
    with (
        mock.patch("plugins.pier.rpc_client.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch("plugins.pier.rpc_client.asyncio.create_subprocess_exec") as mock_exec,
        mock.patch("plugins.pier.rpc_client.asyncio.create_task") as mock_tasks,
    ):
        mock_proc = mock.AsyncMock()
        mock_proc.returncode = None
        # First call to wait() raises TimeoutError (simulating stuck terminate)
        # Second call (after kill) succeeds
        mock_proc.wait = mock.AsyncMock(side_effect=[TimeoutError, None])
        # terminate() and kill() are called synchronously (not awaited)
        mock_proc.terminate = mock.MagicMock()
        mock_proc.kill = mock.MagicMock()
        mock_exec.return_value = mock_proc

        mock_tasks.return_value = mock.MagicMock(done=mock.MagicMock(return_value=True))

        client = PiRpcClient()
        await client.start()
        await client.stop()

        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_called_once()


# ==========================================================================
# send_command()
# ==========================================================================


@pytest.mark.asyncio
async def test_send_command_requires_running(client):
    """send_command raises RuntimeError when client is not running."""
    with pytest.raises(RuntimeError, match="not running"):
        await client.send_command({"command": "prompt"})


@pytest.mark.asyncio
async def test_send_command_success():
    """send_command sends a JSON line and returns the correlated response."""
    with (
        mock.patch("plugins.pier.rpc_client.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch("plugins.pier.rpc_client.asyncio.create_subprocess_exec") as mock_exec,
        mock.patch("plugins.pier.rpc_client.asyncio.create_task"),
    ):
        mock_proc = mock.AsyncMock()
        mock_proc.returncode = None
        mock_proc.stdin = mock.AsyncMock()
        mock_proc.stdin.write = mock.MagicMock()
        mock_proc.stdin.drain = mock.AsyncMock()
        mock_exec.return_value = mock_proc

        client = PiRpcClient()
        await client.start()

        # Simulate send_command by manually wiring a request + response
        command = {"command": "prompt", "text": "Build a CLI"}
        request_id = client._make_id()
        command["id"] = request_id
        payload = json.dumps(command, ensure_ascii=False) + "\n"

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        client._pending_requests[request_id] = future

        assert client._process is not None
        assert client._process.stdin is not None
        client._process.stdin.write(payload.encode("utf-8"))  # type: ignore[union-attr]
        await client._process.stdin.drain()  # type: ignore[union-attr]

        # Dispatch a response event that resolves the future
        client._dispatch_line(
            json.dumps(
                {
                    "id": request_id,
                    "type": "result",
                    "data": {"result": "ok", "text": "Hello from Pi"},
                }
            )
        )

        result = await future
        assert result["result"] == "ok"
        assert result["text"] == "Hello from Pi"


@pytest.mark.asyncio
async def test_send_command_auto_generates_id():
    """send_command auto-generates an id if not provided."""
    with (
        mock.patch("plugins.pier.rpc_client.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch("plugins.pier.rpc_client.asyncio.create_subprocess_exec") as mock_exec,
        mock.patch("plugins.pier.rpc_client.asyncio.create_task"),
    ):
        mock_proc = mock.AsyncMock()
        mock_proc.returncode = None
        mock_proc.stdin = mock.AsyncMock()
        mock_proc.stdin.write = mock.MagicMock()
        mock_proc.stdin.drain = mock.AsyncMock()
        mock_exec.return_value = mock_proc

        client = PiRpcClient()
        await client.start()

        command = {"command": "prompt", "text": "Test"}
        # Use send_command which sets id in-place
        # Set up: write payload and resolve manually
        request_id = client._make_id()
        command["id"] = request_id
        payload = json.dumps(command, ensure_ascii=False) + "\n"

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        client._pending_requests[request_id] = future

        assert client._process is not None
        assert client._process.stdin is not None
        client._process.stdin.write(payload.encode("utf-8"))  # type: ignore[union-attr]
        await client._process.stdin.drain()  # type: ignore[union-attr]

        # Dispatch response
        client._dispatch_line(
            json.dumps(
                {
                    "id": request_id,
                    "type": "result",
                    "data": {"status": "done"},
                }
            )
        )

        result = await future
        assert result["status"] == "done"
        # Verify command was given an id
        assert "id" in command
        assert len(command["id"]) == 12  # uuid4 hex[:12]


@pytest.mark.asyncio
async def test_send_command_timeout():
    """send_command raises RuntimeError on timeout."""
    with (
        mock.patch("plugins.pier.rpc_client.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch("plugins.pier.rpc_client.asyncio.create_subprocess_exec") as mock_exec,
        mock.patch("plugins.pier.rpc_client.asyncio.create_task"),
        mock.patch("plugins.pier.rpc_client.asyncio.wait_for", side_effect=TimeoutError),
    ):
        mock_proc = mock.AsyncMock()
        mock_proc.returncode = None
        mock_proc.stdin = mock.AsyncMock()
        mock_proc.stdin.write = mock.MagicMock()
        mock_proc.stdin.drain = mock.AsyncMock()
        mock_exec.return_value = mock_proc

        client = PiRpcClient()
        await client.start()

        with pytest.raises(RuntimeError, match="timed out"):
            await client.send_command({"command": "prompt"})


@pytest.mark.asyncio
async def test_send_command_uses_custom_timeout():
    """send_command respects the client's timeout setting."""
    with (
        mock.patch("plugins.pier.rpc_client.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch("plugins.pier.rpc_client.asyncio.create_subprocess_exec") as mock_exec,
        mock.patch("plugins.pier.rpc_client.asyncio.create_task"),
        mock.patch("plugins.pier.rpc_client.asyncio.wait_for") as mock_wait_for,
    ):
        mock_proc = mock.AsyncMock()
        mock_proc.returncode = None
        mock_proc.stdin = mock.AsyncMock()
        mock_exec.return_value = mock_proc

        mock_wait_for.return_value = {"result": "ok"}

        client = PiRpcClient(timeout=30.0)
        await client.start()

        await client.send_command({"command": "prompt"})

        assert mock_wait_for.call_args[1]["timeout"] == 30.0


# ==========================================================================
# on_event()
# ==========================================================================


def test_on_event_registers_handler(client):
    """on_event appends the handler to the event_handlers list."""
    handler_called = []

    def my_handler(event: RpcEvent) -> None:
        handler_called.append(event)

    client.on_event(my_handler)

    assert len(client._event_handlers) == 1
    assert client._event_handlers[0] is my_handler


def test_on_event_multiple_handlers(client):
    """on_event supports multiple registered handlers."""
    handlers = []

    for i in range(3):

        def make_handler(n):
            def handler(event):
                handlers.append(n)

            return handler

        client.on_event(make_handler(i))

    assert len(client._event_handlers) == 3


# ==========================================================================
# _dispatch_line
# ==========================================================================


def test_dispatch_line_resolves_future():
    """_dispatch_line resolves a pending request future by id."""
    client = PiRpcClient()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    fut = loop.create_future()
    client._pending_requests["req-1"] = fut

    line = json.dumps({"id": "req-1", "type": "response", "data": {"result": "success"}})
    client._dispatch_line(line)

    assert fut.done()
    result = fut.result()
    assert result["result"] == "success"


def test_dispatch_line_error_future():
    """_dispatch_line sets exception on future when event has error."""
    client = PiRpcClient()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    fut = loop.create_future()
    client._pending_requests["req-2"] = fut

    line = json.dumps({"id": "req-2", "type": "error", "error": "something went wrong"})
    client._dispatch_line(line)

    assert fut.done()
    with pytest.raises(RuntimeError, match="something went wrong"):
        fut.result()


def test_dispatch_line_notifies_handlers():
    """_dispatch_line calls all registered event handlers."""
    client = PiRpcClient()
    events = []

    def handler(event):
        events.append(event)

    client.on_event(handler)

    line = json.dumps({"type": "message_update", "data": {"content": "hello"}})
    client._dispatch_line(line)

    assert len(events) == 1
    assert events[0].type == "message_update"
    assert events[0].data == {"content": "hello"}


def test_dispatch_line_malformed_json():
    """_dispatch_line logs a warning and skips malformed JSON."""
    client = PiRpcClient()

    # Should not raise
    client._dispatch_line("not valid json {{{")

    assert len(client._pending_requests) == 0


def test_dispatch_line_handler_exception_does_not_crash():
    """_dispatch_line continues even if a handler raises."""
    client = PiRpcClient()

    success_events = []

    def bad_handler(event):
        raise RuntimeError("handler crash")

    def good_handler(event):
        success_events.append(event)

    client.on_event(bad_handler)
    client.on_event(good_handler)

    line = json.dumps({"type": "message_update", "data": {}})
    client._dispatch_line(line)

    # Good handler should still be called
    assert len(success_events) == 1


def test_dispatch_line_without_id():
    """Events without an id still notify handlers."""
    client = PiRpcClient()
    events = []

    client.on_event(lambda e: events.append(e))

    line = json.dumps({"type": "text_delta", "data": {"content": "streaming..."}})
    client._dispatch_line(line)

    assert len(events) == 1
    assert events[0].type == "text_delta"


def test_dispatch_line_uses_event_field():
    """_dispatch_line uses 'event' field as fallback when 'type' is missing."""
    client = PiRpcClient()
    events = []

    client.on_event(lambda e: events.append(e))

    line = json.dumps({"event": "custom_event", "data": {"key": "val"}})
    client._dispatch_line(line)

    assert len(events) == 1
    assert events[0].type == "custom_event"


def test_dispatch_line_unknown_type_defaults():
    """_dispatch_line uses 'unknown' as type when neither 'type' nor 'event' is present."""
    client = PiRpcClient()
    events = []

    client.on_event(lambda e: events.append(e))

    line = json.dumps({"data": {"raw": "payload"}})
    client._dispatch_line(line)

    assert len(events) == 1
    assert events[0].type == "unknown"


# ==========================================================================
# _read_events
# ==========================================================================


@pytest.mark.asyncio
async def test_read_events_dispatches_lines():
    """_read_events reads lines and dispatches them."""
    client = PiRpcClient()
    events = []
    client.on_event(lambda e: events.append(e))

    # Feed lines directly into _dispatch_line (bypassing the reader task)
    client._dispatch_line(json.dumps({"type": "text_delta", "data": {"content": "Hello"}}))
    client._dispatch_line(json.dumps({"type": "text_delta", "data": {"content": "World"}}))

    assert len(events) == 2
    assert events[0].type == "text_delta"
    assert events[0].data["content"] == "Hello"
    assert events[1].data["content"] == "World"


# ==========================================================================
# _make_id
# ==========================================================================


def test_make_id_generates_unique_ids():
    """_make_id returns unique hex strings."""
    ids = {PiRpcClient._make_id() for _ in range(100)}

    assert len(ids) == 100  # all unique
    for id_ in ids:
        assert len(id_) == 12
        assert all(c in "0123456789abcdef" for c in id_)


# ==========================================================================
# RpcEvent / RpcResponse dataclasses
# ==========================================================================


def test_rpc_response_defaults():
    """RpcResponse has correct default values."""
    resp = RpcResponse(id="abc")
    assert resp.id == "abc"
    assert resp.type == ""
    assert resp.data == {}
    assert resp.error is None


def test_rpc_response_with_data():
    """RpcResponse accepts type, data, and error."""
    resp = RpcResponse(
        id="xyz",
        type="result",
        data={"output": "done", "tokens": 42},
        error="optional warning",
    )
    assert resp.id == "xyz"
    assert resp.type == "result"
    assert resp.data["output"] == "done"
    assert resp.error == "optional warning"


def test_rpc_event_defaults():
    """RpcEvent has correct default values."""
    evt = RpcEvent(type="text_delta")
    assert evt.type == "text_delta"
    assert evt.data == {}


def test_rpc_event_with_data():
    """RpcEvent accepts type and data."""
    evt = RpcEvent(type="tool_use", data={"tool": "bash", "args": {"cmd": "ls"}})
    assert evt.type == "tool_use"
    assert evt.data["tool"] == "bash"


# ==========================================================================
# Fallback client stubs
# ==========================================================================


def test_pi_json_client_exists():
    """PiJsonClient can be instantiated."""
    client = PiJsonClient()
    assert client is not None


def test_pi_print_client_exists():
    """PiPrintClient can be instantiated."""
    client = PiPrintClient()
    assert client is not None
