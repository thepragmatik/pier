"""Pier — Integration that lets Pi work with a Hermes orchestrator."""

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
