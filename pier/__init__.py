"""Pier — Integration that lets Pi work with a Hermes orchestrator."""

import shutil
import subprocess

try:
    from hermes_agent.plugin import HermesPlugin
except ImportError:  # pragma: no cover — hermes-agent installed at runtime
    HermesPlugin = object  # type: ignore[assignment,misc]


class PierPlugin(HermesPlugin):  # type: ignore[valid-type]
    """Hermes Agent plugin for Pi coding agent integration."""

    name = "pier"
    version = "0.1.0"
    description = "Delegate coding tasks to Pi from within a Hermes orchestrator"

    @property
    def tools(self) -> list:
        """Return tool definitions for the Pi integration."""
        return []  # populated as tools are built out

    @property
    def skills(self) -> list:
        """Skill definitions to load when the plugin activates."""
        return []


def create_plugin() -> PierPlugin:
    """Hermes Agent plugin entry point."""
    return PierPlugin()


def _check_pi_installed() -> bool:
    """Check whether the ``pi`` CLI is available on the PATH."""
    return shutil.which("pi") is not None


def _delegate_print_mode(goal: str, context: str = "", model: str = "", timeout: int = 300) -> dict:
    """Delegate a coding task to Pi in print mode.

    Args:
        goal: The task description to send to Pi.
        context: Optional additional context prepended to the prompt.
        model: Optional model name to pass to Pi (``--model`` flag).
        timeout: Seconds to wait for Pi to finish (default 300).

    Returns:
        A dict with keys ``success`` (bool), ``output`` (str), ``error`` (str),
        and ``returncode`` (int).
    """
    if not _check_pi_installed():
        return {
            "success": False,
            "output": "",
            "error": "Pi CLI is not installed or not on PATH. Install it with: pip install pi-cli",
            "returncode": -1,
        }

    # Build the prompt: optional context + goal
    prompt = goal
    if context:
        prompt = f"{context}\n\n{goal}"

    # Build the command
    cmd = ["pi", "-p", prompt]
    if model:
        cmd.extend(["--model", model])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": f"Pi timed out after {timeout} seconds",
            "returncode": -1,
        }
