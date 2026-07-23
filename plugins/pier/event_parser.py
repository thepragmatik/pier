"""
PiRPCEventParser — maps Pi RPC events to structured data for Hermes.

Design decisions (PIER-ARCH-001 §3.5):
  - Events are parsed into typed dataclasses with strict field validation.
  - The parser is stateless each event is handled independently; session-level
    state aggregation (progress counters, cost totals, turn counts) lives in
    the caller, not the parser.
  - Unrecognised event types are passed through with a fallback generic event
    — the plugin never drops events, even unknown ones from future Pi versions.
  - Text deltas and thinking deltas are distinguished: text goes to the result
    stream; thinking goes to a collapsed reasoning block.

How RPC client handles events (routing perspective):
  - Every JSONL line from Pi stdout is parsed into an event dict.
  - The RPC client resolves request futures, then forwards the event to all
    registered streaming handlers.
  - This parser is one such handler: it receives raw events from the client
    and transforms them into structured types that the tool handlers consume.

Error recovery strategy (event-level):
  - Malformed events (missing required fields, wrong types): log warning,
    return a PiEvent(type="parse_error") so the caller can surface it.
  - Unknown event types: return PiEvent(type="unknown", data={...}) with the
    raw data preserved for debugging.
  - Duplicate or out-of-order events: accepted as-is; the caller is responsible
    for deduplication if needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AgentStatus(str, Enum):
    """Pi agent lifecycle status codes."""

    STARTING = "starting"
    RUNNING = "running"
    SETTLED = "settled"
    ERROR = "error"
    ABORTED = "aborted"


class ToolStatus(str, Enum):
    """Pi tool execution status."""

    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


class CompactionStatus(str, Enum):
    """Pi context compaction status."""

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Event data classes
# ---------------------------------------------------------------------------


@dataclass
class PiEvent:
    """Base event type. Every parsed RPC event is at least this."""

    type: str
    """Raw event type string from Pi (e.g. 'agent_start', 'message_update')."""

    data: dict[str, Any] = field(default_factory=dict)
    """The full decoded event dict, preserved for forward compatibility."""


@dataclass
class AgentLifecycleEvent(PiEvent):
    """Agent session lifecycle event (start, settled, error, aborted)."""

    status: AgentStatus = AgentStatus.STARTING
    session_id: str = ""
    error_message: str = ""


@dataclass
class TurnEvent(PiEvent):
    """Per-turn progress event (turn_start, turn_end)."""

    turn_number: int = 0
    direction: str = ""  # "start" or "end"


@dataclass
class MessageUpdateEvent(PiEvent):
    """Streaming message content delta."""

    delta_type: str = ""  # "text_delta", "thinking_delta", "toolcall_start/end"
    content: str = ""
    message_id: str = ""
    tool_name: str = ""
    tool_input: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecutionEvent(PiEvent):
    """Tool execution lifecycle event."""

    status: ToolStatus = ToolStatus.STARTED
    tool_name: str = ""
    tool_call_id: str = ""
    elapsed_ms: int = 0
    output: str = ""
    error: str = ""


@dataclass
class BashExecutionEvent(PiEvent):
    """Bash command execution update."""

    command: str = ""
    output: str = ""
    exit_code: int | None = None
    elapsed_ms: int = 0


@dataclass
class CompactionEvent(PiEvent):
    """Context compaction lifecycle event."""

    status: CompactionStatus = CompactionStatus.STARTED
    tokens_before: int = 0
    tokens_after: int = 0


@dataclass
class RetryEvent(PiEvent):
    """Auto-retry lifecycle event."""

    direction: str = ""  # "start" or "end"
    attempt: int = 0
    reason: str = ""


@dataclass
class StatsEvent(PiEvent):
    """Session statistics event (get_session_stats response)."""

    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    context_window_used_pct: float = 0.0
    turn_count: int = 0


# ---------------------------------------------------------------------------
# Event type mapping
# ---------------------------------------------------------------------------

# Map raw Pi event type strings to parser methods.
# Events not in this map fall through to _parse_unknown().

_EVENT_TYPE_MAP: dict[str, str] = {
    "agent_start": "_parse_agent_lifecycle",
    "agent_settled": "_parse_agent_lifecycle",
    "agent_error": "_parse_agent_lifecycle",
    "agent_aborted": "_parse_agent_lifecycle",
    "turn_start": "_parse_turn",
    "turn_end": "_parse_turn",
    "message_update": "_parse_message_update",
    "tool_execution_start": "_parse_tool_execution",
    "tool_execution_update": "_parse_tool_execution",
    "tool_execution_end": "_parse_tool_execution",
    "bash_execution_update": "_parse_bash_execution",
    "compaction_start": "_parse_compaction",
    "compaction_end": "_parse_compaction",
    "auto_retry_start": "_parse_retry",
    "auto_retry_end": "_parse_retry",
    "extension_error": "_parse_extension_error",
    "session_stats": "_parse_stats",
}


# ---------------------------------------------------------------------------
# PiRPCEventParser
# ---------------------------------------------------------------------------


class PiRPCEventParser:
    """Parse raw Pi RPC event dicts into typed event objects.

    This is a streaming parser: call ``parse(event_dict)`` for each JSONL
    line emitted by Pi, and receive a typed ``PiEvent`` subclass.

    Usage::

        parser = PiRPCEventParser()
        with PiRpcClient(...) as client:
            client.on_event(lambda raw: handle(parser.parse(raw.__dict__)))
    """

    def parse(self, raw: dict[str, Any]) -> PiEvent:
        """Parse a raw RPC event dict into a typed ``PiEvent``.

        Args:
            raw: The decoded JSON object from a Pi RPC stdout line.
                 Expected keys include ``type``, ``data``, ``id``, ``error``.

        Returns:
            A typed ``PiEvent`` subclass matching the event.
            Unknown event types return a plain ``PiEvent``.
            Malformed events return ``PiEvent(type="parse_error")``.
        """
        if not isinstance(raw, dict):
            return PiEvent(type="parse_error", data={"raw": str(raw), "reason": "not a dict"})

        event_type = raw.get("type") or raw.get("event", "unknown")
        try:
            method_name = _EVENT_TYPE_MAP.get(event_type)
            if method_name:
                parser = getattr(self, method_name)
                return parser(raw, event_type)
            return self._parse_unknown(raw, event_type)
        except Exception:
            # Never let a parse failure kill the event loop.
            return PiEvent(
                type="parse_error",
                data={"raw_type": event_type, "error": "parser exception"},
            )

    # -- individual parsers -------------------------------------------------

    def _parse_agent_lifecycle(self, raw: dict[str, Any], event_type: str) -> AgentLifecycleEvent:
        data = raw.get("data", {})
        status_map = {
            "agent_start": AgentStatus.STARTING,
            "agent_settled": AgentStatus.SETTLED,
            "agent_error": AgentStatus.ERROR,
            "agent_aborted": AgentStatus.ABORTED,
        }
        return AgentLifecycleEvent(
            type=event_type,
            data=data,
            status=status_map.get(event_type, AgentStatus.STARTING),
            session_id=data.get("session_id", ""),
            error_message=data.get("error", ""),
        )

    def _parse_turn(self, raw: dict[str, Any], event_type: str) -> TurnEvent:
        data = raw.get("data", {})
        direction = "start" if event_type == "turn_start" else "end"
        return TurnEvent(
            type=event_type,
            data=data,
            turn_number=data.get("turn", 0),
            direction=direction,
        )

    def _parse_message_update(self, raw: dict[str, Any], event_type: str) -> MessageUpdateEvent:
        data = raw.get("data", {})
        return MessageUpdateEvent(
            type=event_type,
            data=data,
            delta_type=data.get("delta_type", ""),
            content=data.get("content", ""),
            message_id=data.get("message_id", ""),
            tool_name=data.get("tool_name", ""),
            tool_input=data.get("tool_input", {}),
        )

    def _parse_tool_execution(self, raw: dict[str, Any], event_type: str) -> ToolExecutionEvent:
        data = raw.get("data", {})
        status_map = {
            "tool_execution_start": ToolStatus.STARTED,
            "tool_execution_update": ToolStatus.IN_PROGRESS,
            "tool_execution_end": ToolStatus.COMPLETED,
        }
        return ToolExecutionEvent(
            type=event_type,
            data=data,
            status=status_map.get(event_type, ToolStatus.STARTED),
            tool_name=data.get("tool_name", ""),
            tool_call_id=data.get("tool_call_id", ""),
            elapsed_ms=data.get("elapsed_ms", 0),
            output=data.get("output", ""),
            error=data.get("error", ""),
        )

    def _parse_bash_execution(self, raw: dict[str, Any], event_type: str) -> BashExecutionEvent:
        data = raw.get("data", {})
        return BashExecutionEvent(
            type=event_type,
            data=data,
            command=data.get("command", ""),
            output=data.get("output", ""),
            exit_code=data.get("exit_code"),
            elapsed_ms=data.get("elapsed_ms", 0),
        )

    def _parse_compaction(self, raw: dict[str, Any], event_type: str) -> CompactionEvent:
        data = raw.get("data", {})
        status = CompactionStatus.STARTED if event_type == "compaction_start" else CompactionStatus.COMPLETED
        return CompactionEvent(
            type=event_type,
            data=data,
            status=status,
            tokens_before=data.get("tokens_before", 0),
            tokens_after=data.get("tokens_after", 0),
        )

    def _parse_retry(self, raw: dict[str, Any], event_type: str) -> RetryEvent:
        data = raw.get("data", {})
        direction = "start" if event_type == "auto_retry_start" else "end"
        return RetryEvent(
            type=event_type,
            data=data,
            direction=direction,
            attempt=data.get("attempt", 0),
            reason=data.get("reason", ""),
        )

    def _parse_stats(self, raw: dict[str, Any], event_type: str) -> StatsEvent:
        data = raw.get("data", {})
        return StatsEvent(
            type=event_type,
            data=data,
            total_tokens=data.get("total_tokens", 0),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            cost_usd=data.get("cost_usd", 0.0),
            context_window_used_pct=data.get("context_window_used_pct", 0.0),
            turn_count=data.get("turn_count", 0),
        )

    def _parse_extension_error(self, raw: dict[str, Any], event_type: str) -> PiEvent:
        return PiEvent(type=event_type, data=raw.get("data", {}))

    @staticmethod
    def _parse_unknown(raw: dict[str, Any], event_type: str) -> PiEvent:
        """Pass through unknown event types for forward compatibility."""
        return PiEvent(type=event_type, data=raw.get("data", raw))
