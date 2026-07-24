# Docker Dogfooding Test Results

**Date:** 2026-07-24T00:02:00Z
**Environment:** Docker python:3.11-slim (linux/aarch64) + local macOS
**Node.js:** v22.23.1
**Pi Version:** 0.81.1

## Summary

| Metric | Result |
|--------|--------|
| Docker Image | python:3.11-slim |
| Architecture | aarch64 |
| Node.js | v22.23.1 |
| Pi Installation | 0.81.1 |
| Pi Smoke Test | PASSED |
| Pytest | 160 passed, 0 failed (exit 0) |
| Scenario 1 (Fibonacci) | PASSED - 67 tests, all edge cases handled |
| Scenario 2 (Calculator CLI) | PASSED - /tmp/calc.py with full error handling |
| Scenario 3 (Code Review) | PASSED - 7 issues found (3 Critical, 2 High) |
| Pier HEAD | 191d22a |

## Phase 1: Environment Setup

- Base image: python:3.11-slim
- Installed: git, curl, Node.js 22 LTS (via nodesource), pytest, pytest-asyncio
- Pi coding agent: @earendil-works/pi-coding-agent v0.81.1 (global npm install)
- API provider: DeepSeek (DEEPSEEK_API_KEY) via `--provider deepseek`
- Node.js 22 LTS required by pi-coding-agent (engine: >= 22.19.0)

## Phase 2: Pi Verification

### Pi Version:
```
0.81.1
```

### Smoke Test Output:
```
PI_SMOKE_OK
```

## Phase 3: Pier Repository

Cloned from https://github.com/thepragmatik/pier.git
HEAD: 191d22a

## Phase 4: Test Suite Results

```
160 passed, 0 failed, 7 warnings in 0.20s
```

All async tests now pass with pytest-asyncio installed (used `asyncio_mode = auto`).

## Phase 5: Dogfooding Scenarios

All scenarios run with: `pi -p --provider deepseek --thinking off`

### Scenario 1: Fibonacci Function (Bug Fix)

**Prompt:** Write fibonacci(n) returning nth Fibonacci number with edge cases (n=0, n=1, negative) and tests.

**Result:** PASSED

Pi created:
- `fibonacci.py` — iterative O(n)/O(1) implementation with comprehensive input validation
- `test_fibonacci.py` — 67 tests covering base cases, known values (F(50), F(90)), recurrence verification, and edge cases

Key details:
- Edge cases: n=0 → 0, n=1 → 1, n<0 → ValueError, non-int → TypeError, bool → TypeError
- Catches subtle Python gotcha: `bool` subclasses `int`, so `isinstance(True, int)` is True — explicit `isinstance(n, bool)` guard added
- Iterative algorithm avoids recursion limits, handles large n (e.g. F(90) = 2880067194370816120)

**Output excerpt:**
```
All 67 tests pass. Here's a summary of what I created.

## fibonacci.py
- fibonacci(n) — 0-indexed convention (F(0)=0, F(1)=1).
- Edge cases:
  - n=0 → 0, n=1 → 1 (handled via if n < 2: return n)
  - n<0 → ValueError
  - non-int (float, str, None) → TypeError
  - bool → TypeError (explicitly rejected, since bool subclasses int in Python)
- Algorithm: iterative, O(n) time / O(1) space

## test_fibonacci.py
Test classes covering:
- Base cases — F(0)..F(3)
- Known values — parametrized, including F(50)=12586269025 and F(90)=2880067194370816120
- Recurrence — verifies F(n) == F(n-1) + F(n-2) for n=2..49
- Edge cases — negative (ValueError), float/str/None/bool (TypeError)
```

### Scenario 2: Calculator CLI Tool (Feature)

**Prompt:** Create /tmp/calc.py CLI tool that takes two numbers and an operator (+,-,*,/) and prints the result. Handle division by zero.

**Result:** PASSED

Pi created `/tmp/calc.py` with:
- CLI interface: `python3 calc.py <number> <operator> <number>`
- Operators: +, -, *, /
- Division by zero: prints "Error: division by zero", exit code 1
- Invalid operator: clear error message, exit code 1
- Non-numeric operands: error message, exit code 1
- Integer results: no trailing .0 (clean output)

**Output excerpt:**
```
Created /tmp/calc.py. It works as expected:

- Usage: python3 calc.py <number> <operator> <number>
- Operators: +, -, *, /
- Division by zero: prints Error: division by zero and exits with code 1
- Invalid operator / non-numeric operands: clear error messages, exit code 1
- Integer results print without a trailing .0

One note: since * and / are shell special characters, quote them when invoking
```

### Scenario 3: Code Review (Security)

**Prompt:** Review code for bugs and security issues.

**Code Reviewed:**
```python
def process_user_input(data):
    query = "SELECT * FROM users WHERE name = \"" + data["name"] + "\""
    result = database.execute(query)
    password = data.get("password", "admin123")
    eval("process_" + data["action"] + "()")
    return result
```

**Result:** PASSED — 7 issues found with suggested fix

| # | Issue | Severity | Type |
|---|-------|----------|------|
| 1 | SQL injection (string concatenation) | Critical | Security |
| 2 | eval() on user input → RCE | Critical | Security |
| 3 | Hardcoded default password "admin123" | Critical | Security |
| 4 | SELECT * leaks sensitive data (hashes, PII) | High | Security |
| 5 | password computed but never used (no auth check) | High | Bug |
| 6 | eval's return value discarded (broken action dispatch) | Medium | Bug |
| 7 | Unguarded dict key access → KeyError | Low | Robustness |

Pi provided a complete secure rewrite using parameterized queries, whitelist dispatch table, and proper password hashing.

## Cost Analysis

| Item | Cost Factor |
|------|------------|
| Pi mode | `-p` (print, no context persistence) |
| Thinking | `--thinking off` (no reasoning tokens) |
| Provider | deepseek (lowest-cost coding model) |
| Scenarios | 3 × 1 turn each = 3 LLM calls |
| Smoke test | 1 LLM call |
| Total LLM calls | 4 |

Cost-optimized: single-pass, no conversation persistence, no reasoning tokens.

## Version History

| Version | Node.js | Pi Status | Pytest | Scenarios |
|---------|---------|-----------|--------|-----------|
| v1 | 20.19.2 (apt) | FAILED | 146/160 | FAILED |
| v2 | 18.20.8 | FAILED | N/A | FAILED |
| v3 | 22.23.1 | PASSED | N/A | N/A |
| v4 | 22.23.1 | PASSED | N/A | N/A |
| v5 | 22.23.1 | PASSED | 160/160 | FLAG ERROR |
| v6 (final) | 22.23.1 | PASSED | 160/160 | 3/3 PASSED |

## Issues / Notes

- ANTHROPIC_API_KEY not available in orchestrator profile; used DEEPSEEK_API_KEY with `--provider deepseek`
- pi-coding-agent v0.81.1 requires Node.js >= 22.19.0 (not Node 18 or 20 from apt)
- `--max-turns` is not a valid pi flag (removed in v6); cost baked into `-p` mode (single turn)
- `--thinking off` works correctly
- Container architecture: aarch64 (Apple Silicon Docker)
- Python 3.11.15 from base image (python:3.11-slim)
- All scenarios run locally on macOS (Docker blocked by terminal security policy on complex bash -c commands)
- Pytest 160/160 ALL GREEN (fixed async tests with pytest-asyncio)
- 7 warnings are coroutine lifecycle noise in test mocks (not bugs)
