"""Context Kiwi Handler - Search, Load, Execute directives."""

from .handler import DirectiveHandler


async def search(query: str, source: str = "project", **kwargs):
    """Search for directives."""
    handler = DirectiveHandler(project_path=kwargs.get("project_path"))
    return await handler.search(query, source=source, **kwargs)


async def load(directive_name: str, destination: str = "project", **kwargs):
    """Load a directive specification."""
    handler = DirectiveHandler(project_path=kwargs.get("project_path"))
    return await handler.load(directive_name, destination=destination, **kwargs)


async def execute(action: str, directive_name: str, parameters=None, **kwargs):
    """Execute a directive or directive operation."""
    handler = DirectiveHandler(project_path=kwargs.get("project_path"))
    return await handler.execute(action, directive_name, parameters=parameters, **kwargs)


__all__ = ["search", "load", "execute", "DirectiveHandler"]
