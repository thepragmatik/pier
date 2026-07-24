# Dogfooding Final — Clean Docker Integration Test

**Date:** 2026-07-24
**Tool:** Pi v0.81.1
**Provider:** DeepSeek V4 Flash (medium thinking)
**Container:** python:3.11-slim (ephemeral, --rm)
**Pi Config:** maxTurns=3, defaultThinkingLevel=medium (via .pi/settings.json)

## Summary

Ran a definitive clean-slate Docker dogfooding test of Pi coding agent. All gates passed:

| Gate | Result |
|------|--------|
| Smoke test | ✅ Pi responded and confirmed readiness |
| pytest | ✅ **163 passed** (10 warnings, 0 failures) |
| Scenario 1 (Fibonacci) | ✅ Generated `plugins/pier/fibonacci.py` with edge cases |
| Scenario 2 (Calculator CLI) | ✅ Created `/tmp/calc.py` with error handling |
| Scenario 3 (Security review) | ✅ Identified 3 critical/high vulnerabilities |
| No `--max-turns` errors | ✅ maxTurns respected via settings.json |

## Environment

```
Docker:   python:3.11-slim
Node.js:  v22.23.1 (NodeSource setup_22.x)
Pi:       0.81.1 (npm install -g @earendil-works/pi-coding-agent)
Python:   3.11 (slim base)
pytest:   latest (pip install pytest pytest-asyncio)
```

## Smoke Test

```bash
pi -p --provider deepseek "echo PIER_READY"
```

Pi responded: "I'm here and ready to help! What would you like me to do?"

The agent successfully received the prompt, processed it via DeepSeek V4 Flash with medium thinking, and responded — confirming end-to-end connectivity.

## Test Suite

```bash
git clone https://github.com/thepragmatik/pier.git /pier
cd /pier && pip install -e . && pytest tests/ -q
```

Result: **163 passed, 10 warnings in 5.15s**

All test files passed:
- `tests/test_plugin.py`
- `tests/plugins/test_pier_plugin.py`
- `tests/plugins/test_rpc_client.py`
- `tests/test_rpc_bridge.py`
- `tests/plugins/test_rpc_bridge.py`

## Scenario 1: Fibonacci

```
pi -p --provider deepseek --thinking medium "Write fibonacci(n). Handle n<=0. Add assertions."
```

Pi created `plugins/pier/fibonacci.py` with:
- `fibonacci(n)` — iterative O(n), O(1) space, 0-indexed
- `n < 0` → `ValueError`
- Non-int `n` → `AssertionError`
- Edge cases: n=0 returns 0, n=1 returns 1

## Scenario 2: Calculator CLI

```
pi -p --provider deepseek --thinking medium "Create /tmp/calc.py: 2 nums + operator from argv. Handle division by zero."
```

Pi created `/tmp/calc.py` with:
- Usage: `python3 calc.py <num1> <op> <num2>`
- Operators: `+`, `-`, `*`, `/`
- Error handling: non-numeric operands, unknown operators, division by zero

## Scenario 3: Security Review

```
pi -p --provider deepseek --thinking medium "Review this code for security bugs: def process(d): q=SELECT * FROM users WHERE name=d[name]; r=db.execute(q); pw=d.get(pw,admin); eval(proc_+d[a]+()); return r"
```

Pi identified 3 vulnerabilities:

| # | Issue | Severity | Impact |
|---|-------|----------|--------|
| 1 | SQL injection via `d[name]` | Critical | Full database compromise |
| 2 | `eval()` on user-controlled `d[a]` | Critical | Remote code execution |
| 3 | Hardcoded default password (`admin`) | High | Unauthenticated admin access |

Each finding included exploit examples and fix recommendations (parameterized queries, whitelist dispatch, no default credentials).

## Configuration

Pi was configured via `.pi/settings.json`:

```json
{"maxTurns": 3, "defaultThinkingLevel": "medium"}
```

- `maxTurns: 3` — Pi honored the turn limit; no `Error: --max-turns` CLI errors (the flag doesn't exist)
- `defaultThinkingLevel: medium` — DeepSeek reasoning applied across all three scenarios

## Lessons Learned

1. **Node.js version matters.** The `python:3.11-slim` image ships with Node 18/20 via `apt`. Pi v0.81.1 requires Node ≥ 22.19.0. Use NodeSource's `setup_22.x` to get a compatible version.
2. **`--max-turns` does not exist in Pi CLI.** The integration must use `.pi/settings.json` (`maxTurns`) instead. Any skill documentation referencing `--max-turns` should be updated.
3. **pytest-asyncio is a transitive dependency.** It's not listed in `pyproject.toml` but is required by the test suite. Install explicitly: `pip install pytest pytest-asyncio`.
4. **163 tests > 160 target.** The test suite has grown by 3 tests since the original 160-target benchmark. All pass.

## Raw Log

The full container output is preserved at the workspace:
- Script: `workspaces/t_37ec6438/dogfood.sh`
- Log: `/tmp/dogfooding-output/run.log` (209 lines)
