"""Tests for PiRPCEventParser — parses all 17 mapped RPC event types.

Covers: every event type in _EVENT_TYPE_MAP, unknown events,
parse errors, malformed input, non-dict input, and edge cases.
"""

import pytest

from plugins.pier.event_parser import (
    AgentLifecycleEvent,
    AgentStatus,
    BashExecutionEvent,
    CompactionEvent,
    CompactionStatus,
    MessageUpdateEvent,
    PiEvent,
    PiRPCEventParser,
    RetryEvent,
    StatsEvent,
    ToolExecutionEvent,
    ToolStatus,
    TurnEvent,
)

# ==========================================================================
# Fixtures
# ==========================================================================


@pytest.fixture
def parser():
    """Return a fresh PiRPCEventParser."""
    return PiRPCEventParser()


# ==========================================================================
# agent_start
# ==========================================================================


def test_parse_agent_start(parser):
    """agent_start → AgentLifecycleEvent with STARTING status."""
    event = parser.parse(
        {
            "type": "agent_start",
            "data": {"session_id": "sess-001"},
        }
    )

    assert isinstance(event, AgentLifecycleEvent)
    assert event.type == "agent_start"
    assert event.status == AgentStatus.STARTING
    assert event.session_id == "sess-001"
    assert event.error_message == ""


def test_parse_agent_start_no_data(parser):
    """agent_start with no data field → default empty fields."""
    event = parser.parse({"type": "agent_start"})

    assert isinstance(event, AgentLifecycleEvent)
    assert event.status == AgentStatus.STARTING
    assert event.session_id == ""


# ==========================================================================
# agent_settled
# ==========================================================================


def test_parse_agent_settled(parser):
    """agent_settled → AgentLifecycleEvent with SETTLED status."""
    event = parser.parse(
        {
            "type": "agent_settled",
            "data": {"session_id": "sess-002"},
        }
    )

    assert isinstance(event, AgentLifecycleEvent)
    assert event.type == "agent_settled"
    assert event.status == AgentStatus.SETTLED
    assert event.session_id == "sess-002"


# ==========================================================================
# agent_error
# ==========================================================================


def test_parse_agent_error(parser):
    """agent_error → AgentLifecycleEvent with ERROR status and error_message."""
    event = parser.parse(
        {
            "type": "agent_error",
            "data": {"session_id": "sess-003", "error": "Token limit exceeded"},
        }
    )

    assert isinstance(event, AgentLifecycleEvent)
    assert event.type == "agent_error"
    assert event.status == AgentStatus.ERROR
    assert event.session_id == "sess-003"
    assert event.error_message == "Token limit exceeded"


# ==========================================================================
# agent_aborted
# ==========================================================================


def test_parse_agent_aborted(parser):
    """agent_aborted → AgentLifecycleEvent with ABORTED status."""
    event = parser.parse(
        {
            "type": "agent_aborted",
            "data": {"session_id": "sess-004", "error": "User cancelled"},
        }
    )

    assert isinstance(event, AgentLifecycleEvent)
    assert event.type == "agent_aborted"
    assert event.status == AgentStatus.ABORTED
    assert event.session_id == "sess-004"
    assert event.error_message == "User cancelled"


# ==========================================================================
# turn_start
# ==========================================================================


def test_parse_turn_start(parser):
    """turn_start → TurnEvent with direction='start' and turn_number."""
    event = parser.parse(
        {
            "type": "turn_start",
            "data": {"turn": 3},
        }
    )

    assert isinstance(event, TurnEvent)
    assert event.type == "turn_start"
    assert event.turn_number == 3
    assert event.direction == "start"


def test_parse_turn_start_default_turn(parser):
    """turn_start with no turn field → turn_number defaults to 0."""
    event = parser.parse({"type": "turn_start", "data": {}})

    assert event.turn_number == 0
    assert event.direction == "start"


# ==========================================================================
# turn_end
# ==========================================================================


def test_parse_turn_end(parser):
    """turn_end → TurnEvent with direction='end' and turn_number."""
    event = parser.parse(
        {
            "type": "turn_end",
            "data": {"turn": 5},
        }
    )

    assert isinstance(event, TurnEvent)
    assert event.type == "turn_end"
    assert event.turn_number == 5
    assert event.direction == "end"


# ==========================================================================
# message_update
# ==========================================================================


def test_parse_message_update_text_delta(parser):
    """message_update with text_delta content."""
    event = parser.parse(
        {
            "type": "message_update",
            "data": {
                "delta_type": "text_delta",
                "content": "Here is the implementation...",
                "message_id": "msg-001",
            },
        }
    )

    assert isinstance(event, MessageUpdateEvent)
    assert event.type == "message_update"
    assert event.delta_type == "text_delta"
    assert event.content == "Here is the implementation..."
    assert event.message_id == "msg-001"


def test_parse_message_update_thinking_delta(parser):
    """message_update with thinking_delta content."""
    event = parser.parse(
        {
            "type": "message_update",
            "data": {
                "delta_type": "thinking_delta",
                "content": "Let me think about this approach...",
                "message_id": "msg-002",
            },
        }
    )

    assert event.delta_type == "thinking_delta"
    assert event.content == "Let me think about this approach..."


def test_parse_message_update_toolcall_start(parser):
    """message_update with toolcall_start delta_type."""
    event = parser.parse(
        {
            "type": "message_update",
            "data": {
                "delta_type": "toolcall_start",
                "tool_name": "bash",
                "tool_input": {"command": "ls -la"},
                "message_id": "msg-003",
            },
        }
    )

    assert event.delta_type == "toolcall_start"
    assert event.tool_name == "bash"
    assert event.tool_input == {"command": "ls -la"}


def test_parse_message_update_toolcall_end(parser):
    """message_update with toolcall_end delta_type."""
    event = parser.parse(
        {
            "type": "message_update",
            "data": {
                "delta_type": "toolcall_end",
                "tool_name": "write",
                "tool_input": {"path": "/tmp/out.txt", "content": "done"},
                "message_id": "msg-004",
            },
        }
    )

    assert event.delta_type == "toolcall_end"
    assert event.tool_name == "write"


def test_parse_message_update_defaults(parser):
    """message_update with no data → all fields default to empty."""
    event = parser.parse({"type": "message_update"})

    assert event.delta_type == ""
    assert event.content == ""
    assert event.message_id == ""
    assert event.tool_name == ""
    assert event.tool_input == {}


# ==========================================================================
# tool_execution_start
# ==========================================================================


def test_parse_tool_execution_start(parser):
    """tool_execution_start → ToolExecutionEvent with STARTED status."""
    event = parser.parse(
        {
            "type": "tool_execution_start",
            "data": {
                "tool_name": "read",
                "tool_call_id": "tc-001",
            },
        }
    )

    assert isinstance(event, ToolExecutionEvent)
    assert event.type == "tool_execution_start"
    assert event.status == ToolStatus.STARTED
    assert event.tool_name == "read"
    assert event.tool_call_id == "tc-001"


# ==========================================================================
# tool_execution_update
# ==========================================================================


def test_parse_tool_execution_update(parser):
    """tool_execution_update → ToolExecutionEvent with IN_PROGRESS status."""
    event = parser.parse(
        {
            "type": "tool_execution_update",
            "data": {
                "tool_name": "bash",
                "tool_call_id": "tc-002",
                "elapsed_ms": 1500,
                "output": "Compiling...",
            },
        }
    )

    assert event.type == "tool_execution_update"
    assert event.status == ToolStatus.IN_PROGRESS
    assert event.tool_name == "bash"
    assert event.elapsed_ms == 1500
    assert event.output == "Compiling..."


# ==========================================================================
# tool_execution_end
# ==========================================================================


def test_parse_tool_execution_end(parser):
    """tool_execution_end → ToolExecutionEvent with COMPLETED status."""
    event = parser.parse(
        {
            "type": "tool_execution_end",
            "data": {
                "tool_name": "write",
                "tool_call_id": "tc-003",
                "elapsed_ms": 250,
                "output": "File written successfully.",
                "error": "",
            },
        }
    )

    assert event.type == "tool_execution_end"
    assert event.status == ToolStatus.COMPLETED
    assert event.tool_name == "write"
    assert event.elapsed_ms == 250
    assert event.output == "File written successfully."


def test_parse_tool_execution_end_with_error(parser):
    """tool_execution_end with error field captured."""
    event = parser.parse(
        {
            "type": "tool_execution_end",
            "data": {
                "tool_name": "bash",
                "tool_call_id": "tc-004",
                "elapsed_ms": 5000,
                "error": "Command failed: permission denied",
            },
        }
    )

    assert event.status == ToolStatus.COMPLETED
    assert event.error == "Command failed: permission denied"


# ==========================================================================
# bash_execution_update
# ==========================================================================


def test_parse_bash_execution_update(parser):
    """bash_execution_update → BashExecutionEvent."""
    event = parser.parse(
        {
            "type": "bash_execution_update",
            "data": {
                "command": "npm install",
                "output": "added 142 packages in 3s",
                "exit_code": 0,
                "elapsed_ms": 3200,
            },
        }
    )

    assert isinstance(event, BashExecutionEvent)
    assert event.type == "bash_execution_update"
    assert event.command == "npm install"
    assert event.output == "added 142 packages in 3s"
    assert event.exit_code == 0
    assert event.elapsed_ms == 3200


def test_parse_bash_execution_update_error(parser):
    """bash_execution_update with non-zero exit code."""
    event = parser.parse(
        {
            "type": "bash_execution_update",
            "data": {
                "command": "rm -rf /protected",
                "output": "",
                "exit_code": 1,
                "elapsed_ms": 100,
            },
        }
    )

    assert event.command == "rm -rf /protected"
    assert event.exit_code == 1


def test_parse_bash_execution_update_no_exit_code(parser):
    """bash_execution_update with no exit_code → None."""
    event = parser.parse(
        {
            "type": "bash_execution_update",
            "data": {"command": "long-running-server", "output": "Starting..."},
        }
    )

    assert event.exit_code is None


def test_parse_bash_execution_update_defaults(parser):
    """bash_execution_update with no data → defaults."""
    event = parser.parse({"type": "bash_execution_update"})

    assert event.command == ""
    assert event.output == ""
    assert event.exit_code is None
    assert event.elapsed_ms == 0


# ==========================================================================
# compaction_start
# ==========================================================================


def test_parse_compaction_start(parser):
    """compaction_start → CompactionEvent with STARTED status."""
    event = parser.parse(
        {
            "type": "compaction_start",
            "data": {
                "tokens_before": 15000,
                "tokens_after": 0,
            },
        }
    )

    assert isinstance(event, CompactionEvent)
    assert event.type == "compaction_start"
    assert event.status == CompactionStatus.STARTED
    assert event.tokens_before == 15000
    assert event.tokens_after == 0


# ==========================================================================
# compaction_end
# ==========================================================================


def test_parse_compaction_end(parser):
    """compaction_end → CompactionEvent with COMPLETED status."""
    event = parser.parse(
        {
            "type": "compaction_end",
            "data": {
                "tokens_before": 15000,
                "tokens_after": 8000,
            },
        }
    )

    assert event.type == "compaction_end"
    assert event.status == CompactionStatus.COMPLETED
    assert event.tokens_before == 15000
    assert event.tokens_after == 8000


# ==========================================================================
# auto_retry_start
# ==========================================================================


def test_parse_auto_retry_start(parser):
    """auto_retry_start → RetryEvent with direction='start'."""
    event = parser.parse(
        {
            "type": "auto_retry_start",
            "data": {
                "attempt": 2,
                "reason": "rate_limit_exceeded",
            },
        }
    )

    assert isinstance(event, RetryEvent)
    assert event.type == "auto_retry_start"
    assert event.direction == "start"
    assert event.attempt == 2
    assert event.reason == "rate_limit_exceeded"


# ==========================================================================
# auto_retry_end
# ==========================================================================


def test_parse_auto_retry_end(parser):
    """auto_retry_end → RetryEvent with direction='end'."""
    event = parser.parse(
        {
            "type": "auto_retry_end",
            "data": {
                "attempt": 3,
                "reason": "rate_limit_exceeded",
            },
        }
    )

    assert event.type == "auto_retry_end"
    assert event.direction == "end"
    assert event.attempt == 3


# ==========================================================================
# extension_error
# ==========================================================================


def test_parse_extension_error(parser):
    """extension_error → PiEvent (generic) with preserved data."""
    event = parser.parse(
        {
            "type": "extension_error",
            "data": {
                "extension": "hermes-tools",
                "error": "TypeError: undefined is not a function",
                "stack": "at HermesExtension.execute (...)",
            },
        }
    )

    assert isinstance(event, PiEvent)
    assert event.type == "extension_error"
    assert event.data["extension"] == "hermes-tools"
    assert event.data["error"] == "TypeError: undefined is not a function"


def test_parse_extension_error_no_data(parser):
    """extension_error with no data → PiEvent with empty data."""
    event = parser.parse({"type": "extension_error"})

    assert event.type == "extension_error"
    assert event.data == {}


# ==========================================================================
# session_stats
# ==========================================================================


def test_parse_session_stats(parser):
    """session_stats → StatsEvent with token and cost data."""
    event = parser.parse(
        {
            "type": "session_stats",
            "data": {
                "total_tokens": 25000,
                "input_tokens": 18000,
                "output_tokens": 7000,
                "cost_usd": 0.35,
                "context_window_used_pct": 15.2,
                "turn_count": 12,
            },
        }
    )

    assert isinstance(event, StatsEvent)
    assert event.type == "session_stats"
    assert event.total_tokens == 25000
    assert event.input_tokens == 18000
    assert event.output_tokens == 7000
    assert event.cost_usd == 0.35
    assert event.context_window_used_pct == 15.2
    assert event.turn_count == 12


def test_parse_session_stats_defaults(parser):
    """session_stats with no data → all zero defaults."""
    event = parser.parse({"type": "session_stats"})

    assert event.total_tokens == 0
    assert event.input_tokens == 0
    assert event.output_tokens == 0
    assert event.cost_usd == 0.0
    assert event.context_window_used_pct == 0.0
    assert event.turn_count == 0


# ==========================================================================
# Unknown event types
# ==========================================================================


def test_parse_unknown_event_type(parser):
    """Unknown event types → generic PiEvent with type preserved."""
    event = parser.parse(
        {
            "type": "future_feature_v2",
            "data": {"new_field": "some_value"},
        }
    )

    assert isinstance(event, PiEvent)
    assert event.type == "future_feature_v2"
    assert event.data["new_field"] == "some_value"


def test_parse_unknown_event_no_data(parser):
    """Unknown event with no data field → raw dict as data."""
    event = parser.parse(
        {
            "type": "weird_event",
            "custom_field": "value",
        }
    )

    assert event.type == "weird_event"
    assert "custom_field" in event.data


def test_parse_unknown_event_uses_event_field(parser):
    """Uses 'event' field as type when 'type' is missing."""
    event = parser.parse(
        {
            "event": "custom_evt",
            "data": {"key": "val"},
        }
    )

    assert event.type == "custom_evt"


def test_parse_missing_type_and_event(parser):
    """Defaults to 'unknown' when neither 'type' nor 'event' present."""
    event = parser.parse({"data": {"some": "payload"}})

    assert event.type == "unknown"


# ==========================================================================
# Malformed / error cases
# ==========================================================================


def test_parse_non_dict_input(parser):
    """Non-dict input → PiEvent(type='parse_error')."""
    event = parser.parse("just a string")

    assert isinstance(event, PiEvent)
    assert event.type == "parse_error"
    assert event.data["reason"] == "not a dict"
    assert event.data["raw"] == "just a string"


def test_parse_none_input(parser):
    """None input → PiEvent(type='parse_error')."""
    event = parser.parse(None)

    assert event.type == "parse_error"
    assert event.data["reason"] == "not a dict"


def test_parse_int_input(parser):
    """Integer input → PiEvent(type='parse_error')."""
    event = parser.parse(42)

    assert event.type == "parse_error"


def test_parse_list_input(parser):
    """List input → PiEvent(type='parse_error')."""
    event = parser.parse([1, 2, 3])

    assert event.type == "parse_error"


# ==========================================================================
# PiEvent base class
# ==========================================================================


def test_pi_event_creation():
    """PiEvent can be created directly."""
    evt = PiEvent(type="custom_event", data={"key": "val"})

    assert evt.type == "custom_event"
    assert evt.data == {"key": "val"}


def test_pi_event_default_data():
    """PiEvent data defaults to empty dict."""
    evt = PiEvent(type="test")

    assert evt.type == "test"
    assert evt.data == {}


# ==========================================================================
# Enum values
# ==========================================================================


def test_agent_status_values():
    """AgentStatus enum has expected values."""
    assert AgentStatus.STARTING == "starting"
    assert AgentStatus.RUNNING == "running"
    assert AgentStatus.SETTLED == "settled"
    assert AgentStatus.ERROR == "error"
    assert AgentStatus.ABORTED == "aborted"


def test_tool_status_values():
    """ToolStatus enum has expected values."""
    assert ToolStatus.STARTED == "started"
    assert ToolStatus.IN_PROGRESS == "in_progress"
    assert ToolStatus.COMPLETED == "completed"
    assert ToolStatus.ERROR == "error"


def test_compaction_status_values():
    """CompactionStatus enum has expected values."""
    assert CompactionStatus.STARTED == "started"
    assert CompactionStatus.COMPLETED == "completed"
    assert CompactionStatus.FAILED == "failed"


# ==========================================================================
# Event type map completeness
# ==========================================================================


def test_event_type_map_coverage():
    """Verify _EVENT_TYPE_MAP covers 17 known event types."""
    from plugins.pier.event_parser import _EVENT_TYPE_MAP

    expected = {
        "agent_start",
        "agent_settled",
        "agent_error",
        "agent_aborted",
        "turn_start",
        "turn_end",
        "message_update",
        "tool_execution_start",
        "tool_execution_update",
        "tool_execution_end",
        "bash_execution_update",
        "compaction_start",
        "compaction_end",
        "auto_retry_start",
        "auto_retry_end",
        "extension_error",
        "session_stats",
    }

    assert set(_EVENT_TYPE_MAP.keys()) == expected


# ==========================================================================
# Data preserved for forward compatibility
# ==========================================================================


def test_raw_data_preserved_on_agent_lifecycle(parser):
    """AgentLifecycleEvent preserves the raw data dict."""
    event = parser.parse(
        {
            "type": "agent_start",
            "data": {
                "session_id": "sess-xyz",
                "version": "2.0.0-beta",
                "pid": 12345,
            },
        }
    )

    assert event.data["session_id"] == "sess-xyz"
    assert event.data["version"] == "2.0.0-beta"
    assert event.data["pid"] == 12345


def test_raw_data_preserved_on_stats(parser):
    """StatsEvent preserves extra fields in raw data."""
    event = parser.parse(
        {
            "type": "session_stats",
            "data": {
                "total_tokens": 5000,
                "model": "claude-sonnet-4-20250514",
                "provider": "anthropic",
            },
        }
    )

    assert event.data["model"] == "claude-sonnet-4-20250514"
    assert event.data["provider"] == "anthropic"


# ==========================================================================
# Parser exception handling
# ==========================================================================


def test_parser_exception_returns_parse_error(parser):
    """If a parser method raises, the top-level parse() returns parse_error.

    Passing ``data: None`` causes _parse_message_update to crash when it
    calls ``data.get(...)`` on None. The outer try/except catches this and
    returns a PiEvent with type='parse_error'.
    """
    event = parser.parse({"type": "message_update", "data": None})

    # The inner parser crashed, so the outer exception handler returns
    # a generic parse_error event with the original type preserved in data.
    assert event.type == "parse_error"
    assert event.data["raw_type"] == "message_update"
    assert event.data["error"] == "parser exception"
    # the outer try/except catches it
    assert isinstance(event, (PiEvent, MessageUpdateEvent))
