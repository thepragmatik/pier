"""Tests for the Pier plugin."""

from pier import PierPlugin, create_plugin


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
