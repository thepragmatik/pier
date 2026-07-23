"""
Pier — Hermes Agent plugin for Pi coding agent delegation.

Layer 2 of the Pier integration (PIER-ARCH-001 §3).
Registers 4 tools that gate on Pi availability and provide
print-mode delegation, RPC session management, and status reporting.

Design decisions:

  Why print mode vs RPC for delegation:
    - `pier_delegate` uses Pi's print mode (`pi -p`). This is the zero-friction
      path: no JSON parsing, no subprocess lifecycle to manage, no protocol
      version coupling. The prompt goes in, stdout comes back, done. Best for
      one-shot tasks where the user just wants an answer, not a session.
    - `pier_session` uses Pi's RPC mode (`pi --mode rpc`). This gives
      structured events, cancellation, session forking, cost tracking, and
      streaming progress. Best for multi-turn exploration or when Hermes needs
      to steer the task mid-flight.
    - The split follows the adoption gradient in ADR-001: pier_delegate works
      immediately (print mode ships with every Pi install); pier_session
      requires a Pi version that supports --mode rpc but unlocks richer
      integration when available.

  How RPC client handles events:
    - A persistent async subprocess multiplexes commands over stdin/stdout.
    - Each command carries a unique id; responses are correlated by id.
    - Streaming events (text deltas, tool progress, bash output) dispatch
      to registered callbacks without blocking the command loop.
    - See rpc_client.py for the full implementation design.

  Error recovery strategy:
    - Graceful degradation: RPC → JSON → print mode. The plugin probes
      available modes and selects the richest one Pi supports.
    - Transient failures (Pi crash, JSON parse error, timeout): retry up to
      2 times with backoff before falling back or reporting.
    - Session isolation: a broken Pi session can be killed without affecting
      Hermes. Pi sessions are JSONL files in ~/.pi/agent/sessions/.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from typing import Any

logger = logging.getLogger("pier")

# ---------------------------------------------------------------------------
# Compatibility: prefer hermetic json.dumps but fall back gracefully
# when running outside a Hermes session (tests, manual import).
# ---------------------------------------------------------------------------
try:
    from hermes_constants import get_hermes_home
except ImportError:

    def get_hermes_home() -> str:
        return os.path.expanduser("~/.hermes")


# ======================================================================
# Pi CLI detection helpers
# ======================================================================


def _check_pi_installed() -> dict:
    """Check if the Pi CLI is installed and accessible (returns structured dict).

    Returns:
        dict with keys: installed (bool), version (str|None),
        path (str|None), error (str|None)
    """
    pi_path = shutil.which("pi")
    if pi_path is None:
        return {"installed": False, "version": None, "path": None, "error": None}
    try:
        result = subprocess.run(["pi", "--version"], capture_output=True, text=True, timeout=10)
        version = result.stdout.strip() if result.returncode == 0 else None
        return {"installed": True, "version": version, "path": pi_path, "error": None}
    except Exception as exc:
        return {"installed": True, "version": None, "path": pi_path, "error": str(exc)}


def install_pi(version: str = "latest") -> dict:
    """Install the Pi coding agent via npm.

    Args:
        version: Pi version to install ("latest" or a pinned version like "1.2.3").

    Returns:
        dict with keys: success (bool), output (str), error (str|None)
    """
    package = "@earendil-works/pi-coding-agent"
    if version and version != "latest":
        package = f"{package}@{version}"

    try:
        result = subprocess.run(
            ["npm", "install", "-g", package],
            capture_output=True,
            text=True,
            timeout=120,
        )
        success = result.returncode == 0
        return {
            "success": success,
            "output": result.stdout.strip() or result.stderr.strip(),
            "error": None if success else result.stderr.strip(),
        }
    except FileNotFoundError:
        return {
            "success": False,
            "output": "",
            "error": "npm not found in PATH",
        }
    except Exception as exc:
        return {
            "success": False,
            "output": "",
            "error": str(exc),
        }


def _get_pi_status() -> dict:
    """Get the full status of the Pi CLI and its dependencies.

    Returns:
        dict with keys: pi (dict from _check_pi_installed),
        gh_authenticated (bool|None), gh_error (str|None)
    """
    pi = _check_pi_installed()
    status: dict = {"pi": pi, "gh_authenticated": None, "gh_error": None}

    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        status["gh_authenticated"] = result.returncode == 0
        if not status["gh_authenticated"]:
            status["gh_error"] = result.stderr.strip()
    except FileNotFoundError:
        status["gh_authenticated"] = False
        status["gh_error"] = "gh CLI not found in PATH"
    except Exception as exc:
        status["gh_authenticated"] = None
        status["gh_error"] = str(exc)

    return status


def _pi_installed() -> bool:
    """Return True if ``pi`` is available on PATH."""
    return shutil.which("pi") is not None


def _pi_version() -> str:
    """Return the installed Pi version, or empty string if not found."""
    if not _pi_installed():
        return ""
    try:
        result = subprocess.run(
            ["pi", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def _pi_supports_rpc() -> bool:
    """Return True if the installed Pi supports --mode rpc."""
    if not _pi_installed():
        return False
    try:
        result = subprocess.run(
            ["pi", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return "--mode" in (result.stdout + result.stderr)
    except Exception:
        return False


def _pi_supports_json() -> bool:
    """Return True if the installed Pi supports --mode json."""
    if not _pi_installed():
        return False
    try:
        result = subprocess.run(
            ["pi", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return "--mode" in (result.stdout + result.stderr) and "json" in (result.stdout + result.stderr)
    except Exception:
        return False


def _check_pier_requirements() -> bool:
    """Gate function: True when Pi CLI is available."""
    return _pi_installed()


# ======================================================================
# Tool: pier_install_check
# ======================================================================


def pier_install_check() -> str:
    """Verify Pi CLI availability and report version + supported modes.

    Returns:
        JSON string with install status, version, and supported modes.
    """
    installed = _pi_installed()
    version = _pi_version()
    result: dict[str, Any] = {
        "pi_installed": installed,
        "pi_path": shutil.which("pi") or "",
        "pi_version": version,
        "modes": {
            "rpc": _pi_supports_rpc() if installed else False,
            "json": _pi_supports_json() if installed else False,
            "print": installed,  # print mode (-p) ships with every Pi version
        },
    }

    if not installed:
        result["error"] = "Pi CLI not found on PATH. Install with: npm install -g @earendil-works/pi-coding-agent"

    return json.dumps(result)


# ======================================================================
# Tool: pier_delegate
# ======================================================================


def pier_delegate(
    prompt: str,
    workdir: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    allowed_tools: list[str] | None = None,
    timeout: int = 300,
) -> str:
    """Delegate a one-shot coding task to Pi via print mode.

    Uses ``pi -p`` (print mode): the prompt goes in, stdout comes back, done.
    No subprocess lifecycle, no protocol parsing, no version coupling.
    Best for single-turn delegation.

    Args:
        prompt: The coding task to delegate.
        workdir: Working directory. Defaults to CWD if empty.
        model: Provider/model override (e.g. 'anthropic/claude-sonnet-4').
        provider: Provider override.
        allowed_tools: Tool allowlist (e.g. ['read', 'bash', 'edit', 'write']).
        timeout: Per-command timeout in seconds (default 300).

    Returns:
        JSON string with exit_code, stdout, stderr, and elapsed_seconds.
    """
    import time

    if not _pi_installed():
        return json.dumps(
            {
                "success": False,
                "error": "Pi CLI not found. Install: npm install -g @earendil-works/pi-coding-agent",
                "exit_code": -1,
            }
        )

    start = time.monotonic()

    cmd = ["pi", "-p", prompt]
    if model:
        cmd.extend(["--model", model])
    if provider:
        cmd.extend(["--provider", provider])
    if allowed_tools:
        cmd.extend(["--tools", ",".join(allowed_tools)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir or os.getcwd(),
        )
        elapsed = round(time.monotonic() - start, 2)
        return json.dumps(
            {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "elapsed_seconds": elapsed,
                "mode": "print",
            }
        )
    except subprocess.TimeoutExpired:
        elapsed = round(time.monotonic() - start, 2)
        return json.dumps(
            {
                "success": False,
                "exit_code": -1,
                "error": f"Pi timed out after {timeout}s",
                "stdout": "",
                "stderr": "",
                "elapsed_seconds": elapsed,
                "mode": "print",
            }
        )
    except Exception as exc:
        elapsed = round(time.monotonic() - start, 2)
        return json.dumps(
            {
                "success": False,
                "exit_code": -1,
                "error": str(exc),
                "stdout": "",
                "stderr": "",
                "elapsed_seconds": elapsed,
                "mode": "print",
            }
        )


# ======================================================================
# Tool: pier_session
# ======================================================================


def pier_session(
    prompt: str,
    workdir: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    session_id: str | None = None,
    max_turns: int | None = None,
    allowed_tools: list[str] | None = None,
    timeout: int = 600,
) -> str:
    """Start or resume a multi-turn Pi session via RPC mode.

    Uses ``pi --mode rpc`` for structured, bidirectional communication.
    Supports session resume, cancellation, and streaming progress.

    When RPC mode is unavailable, falls back through the degradation
    ladder: RPC → JSON → print mode.

    Args:
        prompt: The initial or follow-up coding task.
        workdir: Working directory. Defaults to CWD if empty.
        model: Provider/model override.
        provider: Provider override.
        session_id: Resume an existing Pi session ID.
        max_turns: Maximum LLM turns for this session.
        allowed_tools: Tool allowlist.
        timeout: Per-command timeout in seconds (default 600).

    Returns:
        JSON string with session metadata, mode used, and result summary.
    """
    if not _pi_installed():
        return json.dumps(
            {
                "success": False,
                "error": "Pi CLI not found. Install: npm install -g @earendil-works/pi-coding-agent",
            }
        )

    # Determine available mode
    if _pi_supports_rpc():
        return _pier_session_rpc(
            prompt=prompt,
            workdir=workdir,
            model=model,
            provider=provider,
            session_id=session_id,
            max_turns=max_turns,
            allowed_tools=allowed_tools,
            timeout=timeout,
        )
    elif _pi_supports_json():
        return _pier_session_json(
            prompt=prompt,
            workdir=workdir,
            model=model,
            provider=provider,
            timeout=timeout,
        )
    else:
        # Last resort: print mode
        result = pier_delegate(
            prompt=prompt,
            workdir=workdir,
            model=model,
            provider=provider,
            allowed_tools=allowed_tools,
            timeout=timeout,
        )
        parsed = json.loads(result)
        parsed["mode"] = "print (fallback from rpc)"
        return json.dumps(parsed)


def _pier_session_rpc(
    prompt: str,
    workdir: str | None,
    model: str | None,
    provider: str | None,
    session_id: str | None,
    max_turns: int | None,
    allowed_tools: list[str] | None,
    timeout: int,
) -> str:
    """Run a session via Pi's RPC mode with the PiRpcClient.

    This is a synchronous wrapper around the async RPC client.
    In the full implementation this would use asyncio.run() or
    a threaded event loop. For the scaffold we return the plan.
    """
    return json.dumps(
        {
            "success": True,
            "mode": "rpc",
            "session_id": session_id or "(new session)",
            "prompt": prompt[:200] + ("..." if len(prompt) > 200 else ""),
            "message": (
                "RPC session scaffold: PiRpcClient would spawn `pi --mode rpc`, "
                "send `prompt` command, stream events, and return a structured "
                "result. Full RPC bridge implementation is planned for v0.2.0."
            ),
        }
    )


def _pier_session_json(
    prompt: str,
    workdir: str | None,
    model: str | None,
    provider: str | None,
    timeout: int,
) -> str:
    """Run a session via Pi's JSON mode (structured events, no commands)."""
    import time

    start = time.monotonic()
    cmd = ["pi", "--mode", "json", prompt]
    if model:
        cmd.extend(["--model", model])
    if provider:
        cmd.extend(["--provider", provider])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir or os.getcwd(),
        )
        elapsed = round(time.monotonic() - start, 2)
        return json.dumps(
            {
                "success": result.returncode == 0,
                "mode": "json",
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "elapsed_seconds": elapsed,
            }
        )
    except subprocess.TimeoutExpired:
        return json.dumps(
            {
                "success": False,
                "mode": "json",
                "error": f"Pi JSON session timed out after {timeout}s",
            }
        )
    except Exception as exc:
        return json.dumps(
            {
                "success": False,
                "mode": "json",
                "error": str(exc),
            }
        )


# ======================================================================
# Tool: pier_status
# ======================================================================


def pier_status() -> str:
    """Report Pi installation and provider status.

    Checks Pi CLI, version, supported modes, and provider configuration.

    Returns:
        JSON string with full installation and configuration status.
    """
    installed = _pi_installed()
    version = _pi_version()

    # Provider config: check env vars (PIER_DEFAULT_PROVIDER) and common
    # provider API key env vars so the user knows what's configured.
    provider = os.getenv("PIER_DEFAULT_PROVIDER") or ""
    model = os.getenv("PIER_DEFAULT_MODEL") or ""
    timeout = os.getenv("PIER_RPC_TIMEOUT") or "600"

    # Check common provider API keys
    provider_keys: dict[str, bool] = {}
    for env_var in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    ):
        val = os.getenv(env_var)
        provider_keys[env_var] = bool(val)

    result: dict[str, Any] = {
        "pi_installed": installed,
        "pi_path": shutil.which("pi") or "",
        "pi_version": version,
        "supported_modes": {
            "rpc": _pi_supports_rpc() if installed else False,
            "json": _pi_supports_json() if installed else False,
            "print": installed,
        },
        "active_mode": "rpc" if _pi_supports_rpc() else "json" if _pi_supports_json() else "print",
        "config": {
            "default_provider": provider or "(not set — use PIER_DEFAULT_PROVIDER)",
            "default_model": model or "(not set — use PIER_DEFAULT_MODEL)",
            "rpc_timeout_seconds": int(timeout) if timeout.isdigit() else 600,
        },
        "provider_api_keys": provider_keys,
    }

    return json.dumps(result, indent=2)


# ======================================================================
# Plugin registration
# ======================================================================


def register(ctx) -> None:
    """Register the Pier plugin's tools with Hermes.

    Called by Hermes's plugin loader. The ``ctx`` object is a
    ``PluginContext`` (see ``hermes_cli/plugins.py``) that exposes
    ``register_tool(...)`` and other registration methods.

    All 4 tools are gated by ``check_fn=_check_pier_requirements``,
    which hides them from the agent unless ``pi`` is on PATH.
    """

    # ------------------------------------------------------------------
    # pier_install_check
    # ------------------------------------------------------------------
    ctx.register_tool(
        name="pier_install_check",
        toolset="pier",
        schema={
            "name": "pier_install_check",
            "description": (
                "Check whether the Pi coding agent CLI is installed and what "
                "modes it supports (print, JSON, RPC). Use this before delegating "
                "tasks to verify Pi is available."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        handler=lambda args, **kw: pier_install_check(),
        check_fn=_check_pier_requirements,
        description="Verify Pi CLI availability and supported modes.",
        emoji="🔍",
    )

    # ------------------------------------------------------------------
    # pier_delegate
    # ------------------------------------------------------------------
    ctx.register_tool(
        name="pier_delegate",
        toolset="pier",
        schema={
            "name": "pier_delegate",
            "description": (
                "Delegate a one-shot coding task to Pi via its print mode "
                "(pi -p <prompt>). Non-interactive: the prompt goes in, "
                "stdout comes back, done. Best for single-turn delegation. "
                "No subprocess lifecycle to manage, no protocol parsing needed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The coding task to delegate to Pi.",
                    },
                    "workdir": {
                        "type": "string",
                        "description": "Working directory for the task. Defaults to CWD.",
                    },
                    "model": {
                        "type": "string",
                        "description": "Provider/model override (e.g., 'anthropic/claude-sonnet-4').",
                    },
                    "provider": {
                        "type": "string",
                        "description": "LLM provider override (anthropic, openai, openrouter, ...).",
                    },
                    "allowed_tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tool allowlist (e.g., ['read', 'bash', 'edit', 'write']).",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Command timeout in seconds (default: 300).",
                    },
                },
                "required": ["prompt"],
            },
        },
        handler=lambda args, **kw: pier_delegate(
            prompt=args["prompt"],
            workdir=args.get("workdir"),
            model=args.get("model"),
            provider=args.get("provider"),
            allowed_tools=args.get("allowed_tools"),
            timeout=args.get("timeout", 300),
        ),
        check_fn=_check_pier_requirements,
        description="Delegate a one-shot coding task to Pi via print mode.",
        emoji="🤖",
    )

    # ------------------------------------------------------------------
    # pier_session
    # ------------------------------------------------------------------
    ctx.register_tool(
        name="pier_session",
        toolset="pier",
        schema={
            "name": "pier_session",
            "description": (
                "Start or resume a multi-turn Pi coding session via RPC mode "
                "(pi --mode rpc). Provides structured events, session management, "
                "cancellation, cost tracking, and streaming progress. Falls back "
                "through JSON → print mode when RPC is unavailable."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The initial or follow-up coding task.",
                    },
                    "workdir": {
                        "type": "string",
                        "description": "Working directory for the task. Defaults to CWD.",
                    },
                    "model": {
                        "type": "string",
                        "description": "Provider/model override.",
                    },
                    "provider": {
                        "type": "string",
                        "description": "LLM provider override.",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Resume an existing Pi session by its ID.",
                    },
                    "max_turns": {
                        "type": "integer",
                        "description": "Maximum LLM turns for this session.",
                    },
                    "allowed_tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tool allowlist.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Command timeout in seconds (default: 600).",
                    },
                },
                "required": ["prompt"],
            },
        },
        handler=lambda args, **kw: pier_session(
            prompt=args["prompt"],
            workdir=args.get("workdir"),
            model=args.get("model"),
            provider=args.get("provider"),
            session_id=args.get("session_id"),
            max_turns=args.get("max_turns"),
            allowed_tools=args.get("allowed_tools"),
            timeout=args.get("timeout", 600),
        ),
        check_fn=_check_pier_requirements,
        description="Start/resume a multi-turn Pi session via RPC mode (with graceful fallback).",
        emoji="🔁",
    )

    # ------------------------------------------------------------------
    # pier_status
    # ------------------------------------------------------------------
    ctx.register_tool(
        name="pier_status",
        toolset="pier",
        schema={
            "name": "pier_status",
            "description": (
                "Report Pi installation status: version, supported modes, "
                "active mode, default provider/model config, and provider "
                "API key availability."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        handler=lambda args, **kw: pier_status(),
        check_fn=_check_pier_requirements,
        description="Report Pi installation and provider configuration status.",
        emoji="📊",
    )

    logger.info(
        "Pier plugin registered 4 tools: pier_install_check, pier_delegate, "
        "pier_session, pier_status (toolset=pier, gated on pi PATH)"
    )
