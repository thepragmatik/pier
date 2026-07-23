"""Tests for the Pier plugin."""

import subprocess
from unittest import mock

from pier import PierPlugin, _check_pi_installed, _delegate_print_mode, create_plugin

# --- Existing plugin metadata tests ---

def test_plugin_metadata():
    """Plugin has the expected identity fields."""
    plugin = PierPlugin()
    assert plugin.name == "pier"
    assert plugin.version == "0.1.0"
    assert "Pi" in plugin.description


def test_create_plugin_returns_pier_plugin():
    """Factory returns a PierPlugin instance."""
    plugin = create_plugin()
    assert isinstance(plugin, PierPlugin)


def test_tools_is_list():
    """tools property returns a list (may be empty in early versions)."""
    plugin = PierPlugin()
    assert isinstance(plugin.tools, list)


def test_skills_is_list():
    """skills property returns a list (may be empty in early versions)."""
    plugin = PierPlugin()
    assert isinstance(plugin.skills, list)


# --- _check_pi_installed ---

def test_check_pi_installed_found():
    """Returns True when pi is on PATH."""
    with mock.patch("shutil.which", return_value="/usr/local/bin/pi"):
        assert _check_pi_installed() is True


def test_check_pi_installed_not_found():
    """Returns False when pi is not on PATH."""
    with mock.patch("shutil.which", return_value=None):
        assert _check_pi_installed() is False


# --- _delegate_print_mode ---

def test_delegate_basic():
    """Mock subprocess and verify correct output is returned."""
    fake_run = mock.Mock(
        returncode=0,
        stdout="Feature implemented successfully.",
        stderr="",
    )
    with mock.patch("subprocess.run", return_value=fake_run), mock.patch("pier._check_pi_installed", return_value=True):
        result = _delegate_print_mode(goal="Implement login page")

    assert result["success"] is True
    assert result["output"] == "Feature implemented successfully."
    assert result["error"] == ""
    assert result["returncode"] == 0


def test_delegate_with_context():
    """Context is prepended to the prompt before goal."""
    with mock.patch("pier._check_pi_installed", return_value=True), mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0, stdout="done", stderr="", spec=["returncode", "stdout", "stderr"])
        _delegate_print_mode(
            goal="Fix the bug",
            context="This is a Python project using FastAPI.",
        )

    call_args = mock_run.call_args[0][0]  # cmd list
    prompt = call_args[call_args.index("-p") + 1]
    assert "This is a Python project using FastAPI." in prompt
    assert "Fix the bug" in prompt
    assert prompt.startswith("This is a Python project using FastAPI.")


def test_delegate_with_model_flag():
    """Model name is passed via --model flag when provided."""
    with mock.patch("pier._check_pi_installed", return_value=True), mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0, stdout="ok", stderr="", spec=["returncode", "stdout", "stderr"])
        _delegate_print_mode(goal="Refactor", model="gpt-4o")

    call_args = mock_run.call_args[0][0]
    assert "--model" in call_args
    assert "gpt-4o" in call_args


def test_delegate_timeout():
    """Mock timeout and verify error response."""
    with mock.patch("pier._check_pi_installed", return_value=True), mock.patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["pi"], timeout=5)
    ):
        result = _delegate_print_mode(goal="Long task", timeout=5)

    assert result["success"] is False
    assert result["output"] == ""
    assert "timed out" in result["error"].lower()
    assert result["returncode"] == -1


def test_delegate_pi_not_installed():
    """Verify graceful error when Pi is not installed."""
    with mock.patch("pier._check_pi_installed", return_value=False):
        result = _delegate_print_mode(goal="Implement feature")

    assert result["success"] is False
    assert result["output"] == ""
    assert "not installed" in result["error"].lower()
    assert result["returncode"] == -1


def test_delegate_nonzero_exit():
    """Non-zero exit code is captured with success=False."""
    fake_run = mock.Mock(
        returncode=1,
        stdout="",
        stderr="Syntax error in generated code.",
    )
    with mock.patch("subprocess.run", return_value=fake_run), mock.patch("pier._check_pi_installed", return_value=True):
        result = _delegate_print_mode(goal="Bad task")

    assert result["success"] is False
    assert result["output"] == ""
    assert result["error"] == "Syntax error in generated code."
    assert result["returncode"] == 1
