#!/usr/bin/env python3
"""
Integration test for Pi RPC bridge (PiRpcClient).

Tests:
  1. Basic prompt → collect JSONL events → verify response text
  2. Abort: send prompt, immediately abort → verify clean shutdown
  3. get_state: verify session state query works

Usage: python3 test_rpc_bridge.py
"""

import subprocess
import json
import sys
import time

PI_BIN = "pi"
TIMEOUT = 90


def extract_text(events: list[dict]) -> str:
    """Extract all assistant text content from events."""
    parts = []
    for e in events:
        if e.get("type") == "message_update":
            ame = e.get("assistantMessageEvent", {})
            if ame.get("type") == "text_delta":
                parts.append(ame.get("delta", ""))
            elif ame.get("type") == "text_end":
                parts.append(ame.get("content", ""))
    return "".join(parts)


def read_events(proc, timeout: int, print_progress: bool = False) -> list[dict]:
    """Read JSONL events from proc.stdout until process exits or timeout."""
    events = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.05)
            continue
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
            events.append(ev)
            if print_progress:
                t = ev.get("type", "?")
                if t in ("agent_settled", "agent_start", "agent_end", "response"):
                    print(f"    [{t}]")
        except json.JSONDecodeError:
            events.append({"type": "parse_error", "raw": line[:200]})
    return events


# ---------------------------------------------------------------------------
# Test 1: Basic prompt
# ---------------------------------------------------------------------------
def test_basic_prompt():
    print("\n[TEST 1] Basic prompt: 'What is 2+2?'")

    cmd = [PI_BIN, "--mode", "rpc", "--no-session"]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )

    events = []
    try:
        proc.stdin.write(json.dumps({
            "type": "prompt",
            "message": "What is 2+2? Answer in one sentence."
        }) + "\n")
        proc.stdin.flush()

        # Wait for agent_settled
        settled = False
        deadline = time.time() + TIMEOUT
        while not settled and time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
                continue
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                events.append(ev)
                if ev.get("type") == "agent_settled":
                    settled = True
            except json.JSONDecodeError:
                events.append({"type": "parse_error", "raw": line[:200]})

        proc.stdin.close()
        # Read any remaining events
        events += read_events(proc, 5)

    finally:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except:
            pass

    text = extract_text(events)
    prompt_ok = any(
        e.get("command") == "prompt" and e.get("success")
        for e in events
    )

    results = {
        "pass": len(text) > 0 and prompt_ok and settled,
        "text": text[:200],
        "text_length": len(text),
        "prompt_accepted": prompt_ok,
        "agent_settled": settled,
        "event_count": len(events),
    }
    return results


# ---------------------------------------------------------------------------
# Test 2: Abort
# ---------------------------------------------------------------------------
def test_abort():
    print("\n[TEST 2] Abort: send prompt, immediately abort")

    cmd = [PI_BIN, "--mode", "rpc", "--no-session"]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )

    events = []
    try:
        proc.stdin.write(json.dumps({
            "type": "prompt",
            "message": "Write a long story about a cat on an epic galaxy adventure."
        }) + "\n")
        proc.stdin.flush()

        # Brief delay so processing can start
        time.sleep(0.5)

        # Send abort and close stdin immediately
        proc.stdin.write(json.dumps({"type": "abort"}) + "\n")
        proc.stdin.flush()
        proc.stdin.close()

        # Read all events
        events = read_events(proc, TIMEOUT, print_progress=False)

    finally:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except:
            pass

    abort_ok = any(
        e.get("command") == "abort" and e.get("success")
        for e in events
    )
    settled = any(e.get("type") == "agent_settled" for e in events)

    results = {
        "pass": abort_ok and settled,
        "abort_success": abort_ok,
        "agent_settled": settled,
        "event_count": len(events),
    }
    return results


# ---------------------------------------------------------------------------
# Test 3: get_state
# ---------------------------------------------------------------------------
def test_get_state():
    print("\n[TEST 3] get_state: verify session state query")

    cmd = [PI_BIN, "--mode", "rpc", "--no-session"]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )

    events = []
    try:
        # Send prompt
        proc.stdin.write(json.dumps({
            "type": "prompt",
            "message": "Hello"
        }) + "\n")
        proc.stdin.flush()

        # Wait for agent_settled from the prompt
        settled = False
        deadline = time.time() + TIMEOUT
        while not settled and time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
                continue
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                events.append(ev)
                if ev.get("type") == "agent_settled":
                    settled = True
            except json.JSONDecodeError:
                events.append({"type": "parse_error", "raw": line[:200]})

        # Now send get_state
        if settled:
            proc.stdin.write(json.dumps({"type": "get_state"}) + "\n")
            proc.stdin.flush()

            # Read get_state response
            state_deadline = time.time() + 10
            got_state = False
            while not got_state and time.time() < state_deadline:
                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        break
                    time.sleep(0.05)
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    events.append(ev)
                    if ev.get("command") == "get_state":
                        got_state = True
                except json.JSONDecodeError:
                    events.append({"type": "parse_error", "raw": line[:200]})

        proc.stdin.close()
        # Read any remaining events
        events += read_events(proc, 5)

    finally:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except:
            pass

    # Find get_state response
    state_response = None
    for e in events:
        if e.get("command") == "get_state":
            state_response = e
            break

    state_data = state_response.get("data", {}) if state_response else {}
    state_fields = set(state_data.keys())
    expected = {"model", "thinkingLevel", "isStreaming", "messageCount"}

    results = {
        "pass": (state_response is not None
                 and state_response.get("success", False)
                 and expected.issubset(state_fields)),
        "state_found": state_response is not None,
        "state_success": state_response.get("success", False) if state_response else False,
        "state_fields": sorted(state_fields),
        "has_expected": expected.issubset(state_fields),
        "event_count": len(events),
    }
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  Pi RPC Bridge Integration Tests")
    print("=" * 60)

    all_results = {}

    r1 = test_basic_prompt()
    all_results["basic_prompt"] = r1
    s1 = "PASS" if r1["pass"] else "FAIL"
    print(f"\n  [{s1}] basic_prompt  text={r1['text_length']} chars  settled={r1['agent_settled']}")
    if r1["text"]:
        print(f"    response: {r1['text'][:120]}")

    r2 = test_abort()
    all_results["abort"] = r2
    s2 = "PASS" if r2["pass"] else "FAIL"
    print(f"\n  [{s2}] abort  abort_ok={r2['abort_success']}  settled={r2['agent_settled']}")

    r3 = test_get_state()
    all_results["get_state"] = r3
    s3 = "PASS" if r3["pass"] else "FAIL"
    print(f"\n  [{s3}] get_state  success={r3['state_success']}  fields={r3['state_fields']}")

    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)
    passed = sum(1 for r in all_results.values() if r["pass"])
    total = len(all_results)
    for name, r in all_results.items():
        print(f"  [{'PASS' if r['pass'] else 'FAIL'}] {name}")
    print(f"\n  {passed}/{total} tests passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
