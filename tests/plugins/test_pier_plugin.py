"""Tests for Pi lifecycle management in the Pier plugin."""

from unittest.mock import MagicMock, patch

from plugins.pier import _check_pi_installed, _get_pi_status, install_pi


def test_check_pi_installed_not_found():
    """_check_pi_installed reports not-installed when Pi is not in PATH."""
    with patch("plugins.pier.shutil.which", return_value=None):
        result = _check_pi_installed()

    assert result["installed"] is False
    assert result["version"] is None
    assert result["path"] is None
    assert result["error"] is None


def test_check_pi_installed_found():
    """_check_pi_installed returns version when Pi is installed and working."""
    fake_path = "/usr/local/bin/pi"
    fake_version = "pi 1.2.3"

    with patch("plugins.pier.shutil.which", return_value=fake_path), patch("plugins.pier.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = fake_version
        mock_run.return_value = mock_result

        result = _check_pi_installed()

    assert result["installed"] is True
    assert result["version"] == fake_version
    assert result["path"] == fake_path
    assert result["error"] is None


def test_install_pi_success():
    """install_pi returns success when npm install succeeds."""
    with patch("plugins.pier.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "+ @earendil-works/pi-coding-agent@latest"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = install_pi()

    assert result["success"] is True
    assert "+ @earendil-works/pi-coding-agent" in result["output"]
    assert result["error"] is None


def test_install_pi_pinned_version():
    """install_pi supports pinned versions via @version suffix."""
    with patch("plugins.pier.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "+ @earendil-works/pi-coding-agent@1.5.0"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = install_pi(version="1.5.0")

    assert result["success"] is True
    # Verify the correct package string was passed
    call_args = mock_run.call_args[0][0]
    assert "@earendil-works/pi-coding-agent@1.5.0" in call_args


def test_install_pi_npm_not_found():
    """install_pi handles npm not found gracefully."""
    with patch("plugins.pier.subprocess.run", side_effect=FileNotFoundError("npm not found")):
        result = install_pi()

    assert result["success"] is False
    assert "npm not found" in result["error"]


def test_install_pi_network_failure():
    """install_pi handles general exceptions gracefully."""
    with patch("plugins.pier.subprocess.run", side_effect=Exception("Network error")):
        result = install_pi()

    assert result["success"] is False
    assert "Network error" in result["error"]


def test_get_pi_status():
    """_get_pi_status returns pi info and gh auth status."""
    with patch("plugins.pier._check_pi_installed") as mock_check:
        mock_check.return_value = {
            "installed": True,
            "version": "pi 1.2.3",
            "path": "/usr/local/bin/pi",
            "error": None,
        }
        with patch("plugins.pier.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            result = _get_pi_status()

    assert result["pi"]["installed"] is True
    assert result["pi"]["version"] == "pi 1.2.3"
    assert result["gh_authenticated"] is True
    assert result["gh_error"] is None
