"""Comprehensive tests for the Pier plugin (plugins.pier).

Covers: tool registration, install_check, delegate, session, status,
install, lifecycle helpers, error handling, and edge cases.
"""

import json
import subprocess
from unittest import mock

from plugins.pier import (
    _check_pi_installed,
    _check_pier_requirements,
    _get_pi_status,
    _pi_installed,
    _pi_supports_json,
    _pi_supports_rpc,
    _pi_version,
    install_pi,
    pier_delegate,
    pier_install_check,
    pier_session,
    pier_status,
    register,
)

# ==========================================================================
# register
# ==========================================================================


def test_register_registers_five_tools():
    """register() registers all 5 tools with the context."""
    ctx = mock.Mock()
    register(ctx)

    assert ctx.register_tool.call_count == 5

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


def test_register_tool_schemas_have_required_fields():
    """Every registered tool has name, toolset, schema, handler, check_fn."""
    ctx = mock.Mock()
    register(ctx)

    for call in ctx.register_tool.call_args_list:
        kw = call.kwargs
        assert "name" in kw
        assert "toolset" in kw
        assert "schema" in kw
        assert "handler" in kw
        assert callable(kw["handler"]), f"handler for {kw['name']} is not callable"


def test_register_pier_install_check_schema():
    """Verify pier_install_check schema structure."""
    ctx = mock.Mock()
    register(ctx)

    call = next(c for c in ctx.register_tool.call_args_list if c.kwargs["name"] == "pier_install_check")
    schema = call.kwargs["schema"]
    assert schema["parameters"]["type"] == "object"
    assert schema["parameters"]["required"] == []


def test_register_pier_delegate_schema():
    """Verify pier_delegate schema includes all expected parameters."""
    ctx = mock.Mock()
    register(ctx)

    call = next(c for c in ctx.register_tool.call_args_list if c.kwargs["name"] == "pier_delegate")
    schema = call.kwargs["schema"]
    props = schema["parameters"]["properties"]
    assert "prompt" in props
    assert "workdir" in props
    assert "model" in props
    assert "provider" in props
    assert "allowed_tools" in props
    assert "timeout" in props
    assert schema["parameters"]["required"] == ["prompt"]


def test_register_pier_session_schema():
    """Verify pier_session schema includes session_id and max_turns."""
    ctx = mock.Mock()
    register(ctx)

    call = next(c for c in ctx.register_tool.call_args_list if c.kwargs["name"] == "pier_session")
    schema = call.kwargs["schema"]
    props = schema["parameters"]["properties"]
    assert "prompt" in props
    assert "session_id" in props
    assert "max_turns" in props
    assert "allowed_tools" in props
    assert "timeout" in props


def test_register_pier_install_schema():
    """Verify pier_install schema accepts optional version."""
    ctx = mock.Mock()
    register(ctx)

    call = next(c for c in ctx.register_tool.call_args_list if c.kwargs["name"] == "pier_install")
    schema = call.kwargs["schema"]
    assert "version" in schema["parameters"]["properties"]
    assert schema["parameters"]["required"] == []


# ==========================================================================
# _check_pi_installed
# ==========================================================================


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

    with (
        mock.patch("plugins.pier.shutil.which", return_value=fake_path),
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = fake_version
        mock_run.return_value = mock_result

        result = _check_pi_installed()

    assert result["installed"] is True
    assert result["version"] == fake_version
    assert result["path"] == fake_path
    assert result["error"] is None


def test_check_pi_installed_subprocess_error():
    """_check_pi_installed handles subprocess exceptions gracefully."""
    with (
        mock.patch("plugins.pier.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch("plugins.pier.subprocess.run", side_effect=OSError("broken pipe")),
    ):
        result = _check_pi_installed()

    assert result["installed"] is True
    assert result["path"] == "/usr/local/bin/pi"
    assert result["error"] == "broken pipe"


def test_check_pi_installed_nonzero_returncode():
    """_check_pi_installed handles non-zero pi --version return."""
    with (
        mock.patch("plugins.pier.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_result = mock.MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "version error"
        mock_run.return_value = mock_result

        result = _check_pi_installed()

    assert result["installed"] is True
    assert result["version"] is None


# ==========================================================================
# _pi_installed / _pi_version / _pi_supports_*
# ==========================================================================


def test_pi_installed_true():
    """_pi_installed returns True when pi is on PATH."""
    with mock.patch("plugins.pier.shutil.which", return_value="/usr/local/bin/pi"):
        assert _pi_installed() is True


def test_pi_installed_false():
    """_pi_installed returns False when pi is not on PATH."""
    with mock.patch("plugins.pier.shutil.which", return_value=None):
        assert _pi_installed() is False


def test_pi_version_installed():
    """_pi_version returns version string when Pi is available."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "pi 2.0.0\n"
        mock_run.return_value = mock_result

        assert _pi_version() == "pi 2.0.0"


def test_pi_version_not_installed():
    """_pi_version returns empty string when Pi is not installed."""
    with mock.patch("plugins.pier._pi_installed", return_value=False):
        assert _pi_version() == ""


def test_pi_version_subprocess_error():
    """_pi_version returns empty string on subprocess error."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier.subprocess.run", side_effect=OSError),
    ):
        assert _pi_version() == ""


def test_pi_supports_rpc_true():
    """_pi_supports_rpc returns True when --mode rpc is in help output."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Usage: pi [options]\n  --mode rpc    RPC mode\n  --mode json   JSON mode"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        assert _pi_supports_rpc() is True


def test_pi_supports_rpc_false():
    """_pi_supports_rpc returns False when --mode not in help."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Usage: pi [options]"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        assert _pi_supports_rpc() is False


def test_pi_supports_rpc_not_installed():
    """_pi_supports_rpc returns False when Pi is not installed."""
    with mock.patch("plugins.pier._pi_installed", return_value=False):
        assert _pi_supports_rpc() is False


def test_pi_supports_rpc_subprocess_error():
    """_pi_supports_rpc returns False on subprocess error."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier.subprocess.run", side_effect=OSError),
    ):
        assert _pi_supports_rpc() is False


def test_pi_supports_json_true():
    """_pi_supports_json returns True when json mode is in help."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "  --mode json   JSON mode"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        assert _pi_supports_json() is True


def test_pi_supports_json_false():
    """_pi_supports_json returns False when only rpc mode present."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "  --mode rpc    RPC mode"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        assert _pi_supports_json() is False


def test_pi_supports_json_not_installed():
    """_pi_supports_json returns False when Pi is not installed."""
    with mock.patch("plugins.pier._pi_installed", return_value=False):
        assert _pi_supports_json() is False


def test_check_pier_requirements_with_pi():
    """_check_pier_requirements returns True when pi is on PATH."""
    with mock.patch("plugins.pier._pi_installed", return_value=True):
        assert _check_pier_requirements() is True


def test_check_pier_requirements_without_pi():
    """_check_pier_requirements returns False when pi is not on PATH."""
    with mock.patch("plugins.pier._pi_installed", return_value=False):
        assert _check_pier_requirements() is False


# ==========================================================================
# pier_install_check
# ==========================================================================


def test_pier_install_check_installed():
    """Returns JSON with installed info when Pi is available."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier._pi_version", return_value="pi 1.2.3"),
        mock.patch("plugins.pier._pi_supports_rpc", return_value=True),
        mock.patch("plugins.pier._pi_supports_json", return_value=True),
        mock.patch("plugins.pier.shutil.which", return_value="/usr/local/bin/pi"),
    ):
        result = pier_install_check()
        data = json.loads(result)

    assert data["pi_installed"] is True
    assert data["pi_version"] == "pi 1.2.3"
    assert data["pi_path"] == "/usr/local/bin/pi"
    assert data["modes"]["rpc"] is True
    assert data["modes"]["json"] is True
    assert data["modes"]["print"] is True
    assert "error" not in data


def test_pier_install_check_not_installed():
    """Returns install instructions when Pi is missing."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=False),
        mock.patch("plugins.pier._pi_version", return_value=""),
        mock.patch("plugins.pier.shutil.which", return_value=None),
    ):
        result = pier_install_check()
        data = json.loads(result)

    assert data["pi_installed"] is False
    assert "error" in data
    assert "npm install -g" in data["error"]
    assert data["modes"]["rpc"] is False
    assert data["modes"]["json"] is False
    assert data["modes"]["print"] is False


def test_pier_install_check_installed_no_rpc():
    """Returns rpc=False when --mode rpc unsupported."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier._pi_version", return_value="pi 0.9.0"),
        mock.patch("plugins.pier._pi_supports_rpc", return_value=False),
        mock.patch("plugins.pier._pi_supports_json", return_value=False),
        mock.patch("plugins.pier.shutil.which", return_value="/usr/local/bin/pi"),
    ):
        result = pier_install_check()
        data = json.loads(result)

    assert data["pi_installed"] is True
    assert data["modes"]["rpc"] is False
    assert data["modes"]["json"] is False
    assert data["modes"]["print"] is True


# ==========================================================================
# pier_delegate
# ==========================================================================


def test_pier_delegate_success():
    """Mock subprocess and verify correct output."""
    fake_run = mock.Mock(
        returncode=0,
        stdout="Feature implemented successfully.",
        stderr="",
    )
    with (
        mock.patch("plugins.pier.subprocess.run", return_value=fake_run),
        mock.patch("plugins.pier._pi_installed", return_value=True),
    ):
        result = pier_delegate(prompt="Implement login page")
        data = json.loads(result)

    assert data["success"] is True
    assert "Feature implemented" in data["stdout"]
    assert data["mode"] == "print"


def test_pier_delegate_with_model():
    """Model name is passed via --model flag."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_run.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
        pier_delegate(prompt="Refactor", model="gpt-4o")

    call_args = mock_run.call_args[0][0]
    assert "--model" in call_args
    assert "gpt-4o" in call_args


def test_pier_delegate_with_provider():
    """Provider is passed via --provider flag."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_run.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
        pier_delegate(prompt="Task", provider="openai")

    call_args = mock_run.call_args[0][0]
    assert "--provider" in call_args
    assert "openai" in call_args


def test_pier_delegate_with_allowed_tools():
    """Allowed tools are passed as comma-separated --tools."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_run.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
        pier_delegate(prompt="Task", allowed_tools=["read", "bash", "edit"])

    call_args = mock_run.call_args[0][0]
    assert "--tools" in call_args
    assert "read,bash,edit" in call_args


def test_pier_delegate_with_workdir():
    """Workdir is passed as cwd to subprocess."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_run.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
        pier_delegate(prompt="Task", workdir="/tmp/work")

    assert mock_run.call_args[1]["cwd"] == "/tmp/work"


def test_pier_delegate_default_workdir():
    """When workdir is None, cwd defaults to os.getcwd()."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier.subprocess.run") as mock_run,
        mock.patch("plugins.pier.os.getcwd", return_value="/default/cwd"),
    ):
        mock_run.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
        pier_delegate(prompt="Task")

    assert mock_run.call_args[1]["cwd"] == "/default/cwd"


def test_pier_delegate_timeout():
    """Timeout produces error response."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch(
            "plugins.pier.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["pi"], timeout=5),
        ),
    ):
        result = pier_delegate(prompt="Long task", timeout=5)
        data = json.loads(result)

    assert data["success"] is False
    assert "timed out" in data["error"].lower()
    assert data["mode"] == "print"
    assert data["exit_code"] == -1


def test_pier_delegate_pi_not_installed():
    """Graceful error when Pi is not installed."""
    with mock.patch("plugins.pier._pi_installed", return_value=False):
        result = pier_delegate(prompt="Implement feature")
        data = json.loads(result)

    assert data["success"] is False
    assert "not found" in data["error"].lower()
    assert data["exit_code"] == -1


def test_pier_delegate_nonzero_exit():
    """Non-zero exit code captured with success=False."""
    fake_run = mock.Mock(
        returncode=1,
        stdout="",
        stderr="Syntax error in generated code.",
    )
    with (
        mock.patch("plugins.pier.subprocess.run", return_value=fake_run),
        mock.patch("plugins.pier._pi_installed", return_value=True),
    ):
        result = pier_delegate(prompt="Bad task")
        data = json.loads(result)

    assert data["success"] is False
    assert "Syntax error" in data["stderr"]


def test_pier_delegate_general_exception():
    """General exceptions produce error response."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier.subprocess.run", side_effect=RuntimeError("unexpected crash")),
    ):
        result = pier_delegate(prompt="Task")
        data = json.loads(result)

    assert data["success"] is False
    assert data["exit_code"] == -1
    assert "unexpected crash" in data["error"]


# ==========================================================================
# pier_session
# ==========================================================================


def test_pier_session_rpc_mode():
    """Returns RPC scaffold when --mode rpc is supported."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier._pi_supports_rpc", return_value=True),
        mock.patch("plugins.pier._pi_supports_json", return_value=False),
    ):
        result = pier_session(prompt="Build a CLI tool")
        data = json.loads(result)

    assert data["success"] is True
    assert data["mode"] == "rpc"
    assert "Build a CLI tool" in data["prompt"]


def test_pier_session_rpc_with_session_id():
    """Returns RPC scaffold with provided session_id."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier._pi_supports_rpc", return_value=True),
    ):
        result = pier_session(prompt="Continue work", session_id="sess-abc123")
        data = json.loads(result)

    assert data["session_id"] == "sess-abc123"


def test_pier_session_json_fallback():
    """Falls back to JSON mode when RPC unavailable but JSON is."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier._pi_supports_rpc", return_value=False),
        mock.patch("plugins.pier._pi_supports_json", return_value=True),
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"result": "ok"}'
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = pier_session(prompt="Task")
        data = json.loads(result)

    assert data["success"] is True
    assert data["mode"] == "json"


def test_pier_session_json_fallback_with_model():
    """JSON fallback passes --model flag."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier._pi_supports_rpc", return_value=False),
        mock.patch("plugins.pier._pi_supports_json", return_value=True),
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_run.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
        pier_session(prompt="Task", model="claude-sonnet-4")

    call_args = mock_run.call_args[0][0]
    assert "--model" in call_args
    assert "claude-sonnet-4" in call_args


def test_pier_session_print_fallback():
    """Falls back to print mode when neither RPC nor JSON available."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier._pi_supports_rpc", return_value=False),
        mock.patch("plugins.pier._pi_supports_json", return_value=False),
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_run.return_value = mock.Mock(returncode=0, stdout="done", stderr="")
        result = pier_session(prompt="Task")
        data = json.loads(result)

    assert "print (fallback from rpc)" in data["mode"]
    assert data["success"] is True


def test_pier_session_pi_not_installed():
    """Graceful error when Pi is not installed."""
    with mock.patch("plugins.pier._pi_installed", return_value=False):
        result = pier_session(prompt="Task")
        data = json.loads(result)

    assert data["success"] is False
    assert "not found" in data["error"].lower()


def test_pier_session_json_timeout():
    """JSON mode handles timeout gracefully."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier._pi_supports_rpc", return_value=False),
        mock.patch("plugins.pier._pi_supports_json", return_value=True),
        mock.patch(
            "plugins.pier.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["pi"], timeout=10),
        ),
    ):
        result = pier_session(prompt="Long task", timeout=10)
        data = json.loads(result)

    assert data["success"] is False
    assert "timed out" in data["error"].lower()
    assert data["mode"] == "json"


def test_pier_session_truncates_long_prompt():
    """RPC scaffold truncates prompts longer than 200 chars."""
    long_prompt = "A" * 300
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier._pi_supports_rpc", return_value=True),
    ):
        result = pier_session(prompt=long_prompt)
        data = json.loads(result)

    assert len(data["prompt"]) < 300
    assert data["prompt"].endswith("...")


# ==========================================================================
# pier_status
# ==========================================================================


def test_pier_status_installed():
    """Reports full status when Pi is installed with all modes."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier._pi_version", return_value="pi 2.0.0"),
        mock.patch("plugins.pier._pi_supports_rpc", return_value=True),
        mock.patch("plugins.pier._pi_supports_json", return_value=True),
        mock.patch("plugins.pier.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch.dict(
            "os.environ",
            {
                "PIER_DEFAULT_PROVIDER": "anthropic",
                "PIER_DEFAULT_MODEL": "claude-sonnet-4",
                "PIER_RPC_TIMEOUT": "300",
                "ANTHROPIC_API_KEY": "sk-test",
            },
            clear=True,
        ),
    ):
        result = pier_status()
        data = json.loads(result)

    assert data["pi_installed"] is True
    assert data["pi_version"] == "pi 2.0.0"
    assert data["pi_path"] == "/usr/local/bin/pi"
    assert data["supported_modes"]["rpc"] is True
    assert data["supported_modes"]["json"] is True
    assert data["supported_modes"]["print"] is True
    assert data["active_mode"] == "rpc"
    assert data["config"]["default_provider"] == "anthropic"
    assert data["config"]["default_model"] == "claude-sonnet-4"
    assert data["config"]["rpc_timeout_seconds"] == 300
    assert data["provider_api_keys"]["ANTHROPIC_API_KEY"] is True


def test_pier_status_not_installed():
    """Reports not-installed when Pi is missing."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=False),
        mock.patch("plugins.pier._pi_version", return_value=""),
        mock.patch("plugins.pier.shutil.which", return_value=None),
        mock.patch.dict("os.environ", {}, clear=True),
    ):
        result = pier_status()
        data = json.loads(result)

    assert data["pi_installed"] is False
    assert data["pi_path"] == ""
    assert data["supported_modes"]["rpc"] is False
    assert data["supported_modes"]["json"] is False
    assert data["supported_modes"]["print"] is False
    assert data["active_mode"] == "print"


def test_pier_status_provider_config_unset():
    """Shows placeholder when provider env vars are not set."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier._pi_version", return_value="pi 1.0.0"),
        mock.patch("plugins.pier._pi_supports_rpc", return_value=False),
        mock.patch("plugins.pier._pi_supports_json", return_value=False),
        mock.patch("plugins.pier.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch.dict("os.environ", {}, clear=True),
    ):
        result = pier_status()
        data = json.loads(result)

    assert "not set" in data["config"]["default_provider"]
    assert "not set" in data["config"]["default_model"]
    for key_env in data["provider_api_keys"]:
        assert data["provider_api_keys"][key_env] is False


def test_pier_status_api_keys_detected():
    """Detects provider API keys from environment."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier._pi_version", return_value="pi 1.0.0"),
        mock.patch("plugins.pier._pi_supports_rpc", return_value=False),
        mock.patch("plugins.pier._pi_supports_json", return_value=False),
        mock.patch("plugins.pier.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch.dict(
            "os.environ",
            {
                "ANTHROPIC_API_KEY": "sk-ant-123",
                "OPENAI_API_KEY": "sk-openai-456",
            },
            clear=True,
        ),
    ):
        result = pier_status()
        data = json.loads(result)

    assert data["provider_api_keys"]["ANTHROPIC_API_KEY"] is True
    assert data["provider_api_keys"]["OPENAI_API_KEY"] is True
    assert data["provider_api_keys"]["OPENROUTER_API_KEY"] is False


def test_pier_status_active_mode_json():
    """Reports json as active mode when rpc unavailable but json is."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier._pi_version", return_value="pi 1.0.0"),
        mock.patch("plugins.pier._pi_supports_rpc", return_value=False),
        mock.patch("plugins.pier._pi_supports_json", return_value=True),
        mock.patch("plugins.pier.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch.dict("os.environ", {}, clear=True),
    ):
        result = pier_status()
        data = json.loads(result)

    assert data["active_mode"] == "json"


def test_pier_status_rpc_timeout_default():
    """Uses default 600 when PIER_RPC_TIMEOUT is invalid."""
    with (
        mock.patch("plugins.pier._pi_installed", return_value=True),
        mock.patch("plugins.pier._pi_version", return_value="pi 1.0.0"),
        mock.patch("plugins.pier._pi_supports_rpc", return_value=False),
        mock.patch("plugins.pier._pi_supports_json", return_value=False),
        mock.patch("plugins.pier.shutil.which", return_value="/usr/local/bin/pi"),
        mock.patch.dict("os.environ", {"PIER_RPC_TIMEOUT": "notanumber"}, clear=True),
    ):
        result = pier_status()
        data = json.loads(result)

    assert data["config"]["rpc_timeout_seconds"] == 600


# ==========================================================================
# install_pi
# ==========================================================================


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
    """install_pi supports pinned versions via @version suffix."""
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


def test_install_pi_default_latest():
    """install_pi uses 'latest' by default (no version suffix)."""
    with mock.patch("plugins.pier.subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
        install_pi()

    call_args = mock_run.call_args[0][0]
    assert "@earendil-works/pi-coding-agent" in call_args
    # "latest" default means no @version suffix
    assert "@latest" not in str(call_args)


def test_install_pi_npm_not_found():
    """install_pi handles npm not found gracefully."""
    with mock.patch("plugins.pier.subprocess.run", side_effect=FileNotFoundError("npm not found")):
        result = install_pi()

    assert result["success"] is False
    assert "npm not found" in result["error"]


def test_install_pi_network_failure():
    """install_pi handles general exceptions gracefully."""
    with mock.patch("plugins.pier.subprocess.run", side_effect=Exception("Network error")):
        result = install_pi()

    assert result["success"] is False
    assert "Network error" in result["error"]


def test_install_pi_npm_failure():
    """install_pi returns success=False when npm install fails."""
    with mock.patch("plugins.pier.subprocess.run") as mock_run:
        mock_result = mock.MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "EACCES: permission denied"
        mock_run.return_value = mock_result

        result = install_pi()

    assert result["success"] is False
    assert "permission denied" in result["error"]


# ==========================================================================
# _get_pi_status
# ==========================================================================


def test_get_pi_status_with_gh_auth():
    """_get_pi_status returns gh_authenticated=True when gh auth status passes."""
    with (
        mock.patch("plugins.pier._check_pi_installed") as mock_check,
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_check.return_value = {
            "installed": True,
            "version": "pi 1.2.3",
            "path": "/usr/local/bin/pi",
            "error": None,
        }
        mock_gh = mock.MagicMock()
        mock_gh.returncode = 0
        mock_gh.stderr = ""
        mock_run.return_value = mock_gh

        result = _get_pi_status()

    assert result["pi"]["installed"] is True
    assert result["gh_authenticated"] is True
    assert result["gh_error"] is None


def test_get_pi_status_gh_not_authenticated():
    """_get_pi_status reports unauthenticated when gh auth status fails."""
    with (
        mock.patch("plugins.pier._check_pi_installed") as mock_check,
        mock.patch("plugins.pier.subprocess.run") as mock_run,
    ):
        mock_check.return_value = {
            "installed": True,
            "version": "pi 1.2.3",
            "path": "/usr/local/bin/pi",
            "error": None,
        }
        mock_gh = mock.MagicMock()
        mock_gh.returncode = 1
        mock_gh.stderr = "not logged in"
        mock_run.return_value = mock_gh

        result = _get_pi_status()

    assert result["gh_authenticated"] is False
    assert "not logged in" in result["gh_error"]


def test_get_pi_status_gh_not_found():
    """_get_pi_status handles gh CLI missing gracefully."""
    with mock.patch("plugins.pier._check_pi_installed") as mock_check:
        mock_check.return_value = {
            "installed": True,
            "version": "pi 1.2.3",
            "path": "/usr/local/bin/pi",
            "error": None,
        }
        with mock.patch("plugins.pier.subprocess.run", side_effect=FileNotFoundError):
            result = _get_pi_status()

    assert result["gh_authenticated"] is False
    assert "gh CLI not found" in result["gh_error"]


def test_get_pi_status_gh_exception():
    """_get_pi_status handles unexpected gh errors gracefully."""
    with (
        mock.patch("plugins.pier._check_pi_installed") as mock_check,
        mock.patch("plugins.pier.subprocess.run", side_effect=OSError("broken pipe")),
    ):
        mock_check.return_value = {
            "installed": True,
            "version": "pi 1.2.3",
            "path": "/usr/local/bin/pi",
            "error": None,
        }
        result = _get_pi_status()

    assert result["gh_authenticated"] is None
    assert "broken pipe" in result["gh_error"]
