# Layer 3 Integration Test: RPC Bridge (PiRpcClient)

**Date:** 2026-07-24
**Task:** 4.3 — Integration test of the RPC bridge (PiRpcClient)
**Assignee:** hswarm-vrfy
**Pi Version:** 0.81.1 (Homebrew)
**Model:** wafer/GLM-5.2

## Summary

End-to-end integration test of the Pi RPC bridge (`pi --mode rpc`). The RPC protocol uses JSON
commands sent over stdin and JSONL events streamed over stdout. Three scenarios were tested:
basic prompt → response, abort during processing, and post-completion state queries.

All 3 tests pass.

## Test Results

### Test 1: Basic Prompt → Response

| Check | Result |
|---|---|
| Prompt accepted (`response.success: true`) | PASS |
| Event lifecycle: `agent_start` → `agent_end` → `agent_settled` | PASS |
| Turn structure: `turn_start` → `turn_end` | PASS |
| Streaming updates: `message_update` with `text_delta`/`text_end` | PASS |
| Assistant response contains expected text | PASS ("2+2 equals 4.") |

**Events observed (14):** `response` → `agent_start` → `turn_start` → `message_start`(user) →
`message_end`(user) → `message_start`(assistant) → `message_update`(text_start) →
`text_delta` → `text_end` → `message_end`(assistant) → `turn_end` → `agent_end` → `agent_settled`

### Test 2: Abort During Processing

| Check | Result |
|---|---|
| Prompt accepted | PASS |
| Abort response (`command: "abort", success: true`) | PASS |
| Clean shutdown (`agent_settled` received) | PASS |
| No hung process or error state | PASS |

**Events observed (11):** `response`(prompt) → `agent_start` → `turn_start` → `turn_end` →
`agent_end` → `agent_settled` → `response`(abort)

### Test 3: get_state Query

| Check | Result |
|---|---|
| `get_state` response received with `success: true` | PASS |
| Required fields present: `model`, `thinkingLevel`, `isStreaming`, `messageCount` | PASS |
| `messageCount` reflects conversation (1 user + 1 assistant = 2) | PASS |
| `isStreaming` is `false` after agent settles | PASS |

**State fields:** `autoCompactionEnabled`, `followUpMode`, `isCompacting`, `isStreaming`,
`messageCount`, `model`, `pendingMessageCount`, `sessionId`, `steeringMode`, `thinkingLevel`

## Event Protocol Verification

| Event Type | Test 1 | Test 2 | Test 3 |
|---|---|---|---|
| `agent_start` | yes | yes | yes |
| `agent_end` | yes | yes | yes |
| `agent_settled` | yes | yes | yes |
| `turn_start` | yes | yes | yes |
| `turn_end` | yes | yes | yes |
| `message_start` | yes | yes | yes |
| `message_end` | yes | yes | yes |
| `message_update` | yes | no | yes |
| `response` | yes | yes | yes |

## Protocol Notes

1. **stdin lifecycle:** stdin must remain open until `agent_settled` for normal prompt
   completion. Closing stdin prematurely truncates the response.

2. **Abort + close:** Sending abort followed by immediate stdin close produces the abort
   response after `agent_settled` — the agent settles cleanly, then acknowledges the abort.

3. **Post-settle commands:** Commands like `get_state` work when sent after `agent_settled`
   but before stdin closes.

4. **--no-session:** Session state queries return complete metadata even with ephemeral sessions.

## Test Script

`tests/test_rpc_bridge.py` — Python 3 script requiring `pi` on PATH and a configured provider.

```bash
python3 tests/test_rpc_bridge.py
```
