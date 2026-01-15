"""Script Kiwi Handler - Search, Load, Execute scripts."""

from .handler import ScriptHandler


async def search(query: str, source: str = "local", **kwargs):
    """Search for scripts."""
    handler = ScriptHandler(project_path=kwargs.get("project_path"))
    return await handler.search(query, source=source, **kwargs)


async def load(script_name: str, destination: str = "project", **kwargs):
    """Load script specification."""
    handler = ScriptHandler(project_path=kwargs.get("project_path"))
    return await handler.load(script_name, destination=destination, **kwargs)


async def execute(action: str, script_name: str, parameters=None, **kwargs):
    """Execute a script."""
    handler = ScriptHandler(project_path=kwargs.get("project_path"))
    return await handler.execute(action, script_name, parameters=parameters, **kwargs)


__all__ = ["search", "load", "execute", "ScriptHandler"]
