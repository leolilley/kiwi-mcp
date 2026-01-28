"""Context Kiwi Handler - Search, Load, Execute, Sign directives."""

from .handler import DirectiveHandler


async def search(query: str, source: str = "project", **kwargs):
    """Search for directives."""
    handler = DirectiveHandler(project_path=kwargs.get("project_path"))
    return await handler.search(query, source=source, **kwargs)


async def load(directive_name: str, destination: str = "project", **kwargs):
    """Load a directive specification."""
    handler = DirectiveHandler(project_path=kwargs.get("project_path"))
    return await handler.load(directive_name, destination=destination, **kwargs)


async def execute(directive_name: str, parameters=None, **kwargs):
    """Execute a directive."""
    handler = DirectiveHandler(project_path=kwargs.get("project_path"))
    return await handler.execute(directive_name, parameters=parameters)


async def sign(directive_name: str, parameters=None, **kwargs):
    """Validate and sign a directive."""
    handler = DirectiveHandler(project_path=kwargs.get("project_path"))
    return await handler.sign(directive_name, parameters=parameters)


__all__ = ["search", "load", "execute", "sign", "DirectiveHandler"]
