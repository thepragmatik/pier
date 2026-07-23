"""Tests for the Pier plugin (plugins.pier)."""

import json
import subprocess
from unittest import mock

from plugins.pier import (
    _check_pi_installed,
    _check_pier_requirements,
    _pi_installed,
    install_pi,
    pier_delegate,
    pier_install_check,
    register,
)

# --- Tool function tests ---


def test_register_registers_five_tools():
    """register() registers all 5 tools with the context."""
    ctx = mock.Mock()
    register(ctx)

    assert ctx.register_tool.call_count == 5

    # Collect registered tool names
    tool_names = [call.kwargs["name"] for call in ctx.register_tool.call_args_list]
    assert "pier_install_check" in tool_names
    assert "pier_delegate" in tool_names
    assert "pier_session" in tool_names
    assert "pier_status" in tool_names
    assert "pier_install" in tool_names


def test_register_uses_correct_toolset():
    """All registered tools belong to the 'pier' toolset."""
    ctx = mock.Mock()
    register(ctx)

    for call in ctx.register_tool.call_args_list:
        assert call.kwargs.get("toolset") == "pier"


def test_register_gates_on_pi_availability():
    """All tools are gated by _check_pier_requirements."""
    ctx = mock.Mock()
    register(ctx)

    for call in ctx.register_tool.call_args_list:
        assert call.kwargs.get("check_fn") is _check_pier_requirements


# --- pier_install_check ---


def test_pier_install_check_installed():
    """Returns JSON with installed info when Pi is available."""
    with mock.patch("plugins.pier._pi_installed", return_value=True), \
         mock.patch("plugins.pier._pi_version", return_value="pi 1.2.3"), \
         mock.patch("plugins.pier._pi_supports_rpc", return_value=True), \
         mock.patch("plugins.pier._pi_supports_json", return_value=True), \
         mock.patch("plugins.pier.shutil.which", return_value="/usr/local/bin/pi"):
        result = pier_install_check()
        data = json.loads(result)

    assert data["pi_installed"] is True
    assert data["pi_version"] == "pi 1.2.3"
    assert data["pi_path"] == "/usr/local/bin/pi"
    assert data["modes"]["rpc"] is True
    assert data["modes"]["json"] is True
    assert data["modes"]["print"] is True


def test_pier_install_check_not_installed():
    """Returns install instructions when Pi is missing."""
    with mock.patch("plugins.pier._pi_installed", return_value=False), \
         mock.patch("plugins.pier._pi_version", return_value=""), \
         mock.patch("plugins.pier.shutil.which", return_value=None):
        result = pier_install_check()
        data = json.loads(result)

    assert data["pi_installed"] is False
    assert "error" in data
    assert "npm install -g" in data["error"]


# --- pier_delegate ---


def test_pier_delegate_success():
    """Mock subprocess and verify correct output."""
    fake_run = mock.Mock(
        returncode=0,
        stdout="Feature implemented successfully.",
        stderr="",
    )
    with mock.patch("plugins.pier.subprocess.run", return_value=fake_run), \
         mock.patch("plugins.pier._pi_installed", return_value=True):
        result = pier_delegate(prompt="Implement login page")
        data = json.loads(result)

    assert data["success"] is True
    assert "Feature implemented" in data["stdout"]
    assert data["mode"] == "print"


def test_pier_delegate_with_model():
    """Model name is passed via --model flag."""
    with mock.patch("plugins.pier._pi_installed", return_value=True), \
         mock.patch("plugins.pier.subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
        pier_delegate(prompt="Refactor", model="gpt-4o")

    call_args = mock_run.call_args[0][0]
    assert "--model" in call_args
    assert "gpt-4o" in call_args


def test_pier_delegate_timeout():
    """Timeout produces error response."""
    with mock.patch("plugins.pier._pi_installed", return_value=True), \
         mock.patch("plugins.pier.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["pi"], timeout=5)):
        result = pier_delegate(prompt="Long task", timeout=5)
        data = json.loads(result)

    assert data["success"] is False
    assert "timed out" in data["error"].lower()


def test_pier_delegate_pi_not_installed():
    """Graceful error when Pi is not installed."""
    with mock.patch("plugins.pier._pi_installed", return_value=False):
        result = pier_delegate(prompt="Implement feature")
        data = json.loads(result)

    assert data["success"] is False
    assert "not found" in data["error"].lower()


def test_pier_delegate_nonzero_exit():
    """Non-zero exit code captured with success=False."""
    fake_run = mock.Mock(
        returncode=1,
        stdout="",
        stderr="Syntax error in generated code.",
    )
    with mock.patch("plugins.pier.subprocess.run", return_value=fake_run), \
         mock.patch("plugins.pier._pi_installed", return_value=True):
        result = pier_delegate(prompt="Bad task")
        data = json.loads(result)

    assert data["success"] is False
    assert "Syntax error" in data["stderr"]


# --- install_pi ---


def test_install_pi_success():
    """install_pi returns success when npm install succeeds."""
    with mock.patch("plugins.pier.subprocess.run") as mock_run:
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "+ @earendil-works/pi-coding-agent@latest"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = install_pi()

    assert result["success"] is True
    assert "@earendil-works/pi-coding-agent" in result["output"]
    assert result["error"] is None


def test_install_pi_pinned_version():
    """install_pi supports pinned versions."""
    with mock.patch("plugins.pier.subprocess.run") as mock_run:
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "+ @earendil-works/pi-coding-agent@1.5.0"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = install_pi(version="1.5.0")

    assert result["success"] is True
    call_args = mock_run.call_args[0][0]
    assert "@earendil-works/pi-coding-agent@1.5.0" in call_args


# --- _check_pi_installed (structured dict version) ---


def test_check_pi_installed_not_found():
    """_check_pi_installed reports not-installed when Pi is not in PATH."""
    with mock.patch("plugins.pier.shutil.which", return_value=None):
        result = _check_pi_installed()

    assert result["installed"] is False
    assert result["version"] is None
    assert result["path"] is None
    assert result["error"] is None


def test_check_pi_installed_found():
    """_check_pi_installed returns version when Pi is installed and working."""
    fake_path = "/usr/local/bin/pi"
    fake_version = "pi 1.2.3"

    with mock.patch("plugins.pier.shutil.which", return_value=fake_path), \
         mock.patch("plugins.pier.subprocess.run") as mock_run:
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = fake_version
        mock_run.return_value = mock_result

        result = _check_pi_installed()

    assert result["installed"] is True
    assert result["version"] == fake_version
    assert result["path"] == fake_path
    assert result["error"] is None


# --- _pi_installed ---


def test_pi_installed_true():
    """_pi_installed returns True when pi is on PATH."""
    with mock.patch("plugins.pier.shutil.which", return_value="/usr/local/bin/pi"):
        assert _pi_installed() is True


def test_pi_installed_false():
    """_pi_installed returns False when pi is not on PATH."""
    with mock.patch("plugins.pier.shutil.which", return_value=None):
        assert _pi_installed() is False
