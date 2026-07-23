# Layer 1 Integration Test: Skill Delegation via Terminal

**Date:** 2026-07-24
**Task:** 4.1 — Integration test of skill-based delegation via Pi coding agent
**Assignee:** hswarm-vrfy

## Summary

End-to-end integration test of Layer 1 (skill-based delegation) using the Pi coding agent
(`@earendil-works/pi-coding-agent`) installed globally via npm and invoked non-interactively
with `-p`.

## Test Steps & Results

### Step 1: Install Pi

```bash
npm install -g @earendil-works/pi-coding-agent
```

**Result:** ✅ PASS
- 140 packages installed
- Deprecation warning for `node-domexception@1.0.0` (cosmetic, non-blocking)

### Step 2: Verify Installation

```bash
pi --version
```

**Result:** ✅ PASS
- Version: `0.81.1`

### Step 3: Smoke Test

```bash
pi -p "echo PI_SMOKE_OK"
```

**Result:** ✅ PASS
- Output contained `PI_SMOKE_OK`

### Step 4: Real Task — Code Generation

```bash
pi -p "Write a Python function that returns the Fibonacci sequence up to n"
```

**Result:** ✅ PASS
- Created `fibonacci.py` with a valid Python function
- Function handles edge cases: `n <= 0` → `[]`, `n == 1` → `[0]`
- Iteratively builds the sequence for `n >= 2`
- Example output: `fibonacci(10)` → `[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]`

### Generated Code

```python
def fibonacci(n):
    """Return the Fibonacci sequence up to n terms."""
    if n <= 0:
        return []
    if n == 1:
        return [0]
    seq = [0, 1]
    for _ in range(2, n):
        seq.append(seq[-1] + seq[-2])
    return seq


if __name__ == "__main__":
    print(fibonacci(10))
```

## Configuration

- **Provider:** wafer (custom) → `https://pass.wafer.ai/v1`
- **Model:** GLM-5.2
- **Auth:** API key via `~/.pi/agent/auth.json`

## Notes

- The smoke test confirmed that Pi can be invoked non-interactively via `-p` and returns expected output
- The real task confirmed that Pi can generate valid, runnable Python code from a natural language prompt
- Pi's default provider/model were pre-configured; changing providers requires `--provider` and `--model` flags
- The `auth.json` format must use `{"type": "api_key", "key": "..."}` for Pi v0.81.1

## Verdict

**All 4 test steps passed.** Layer 1 skill-based delegation via Pi is functional.
