"""Knowledge Kiwi Handler - Search, Load, Execute, Sign knowledge entries."""

from .handler import KnowledgeHandler


async def search(query: str, source: str = "project", **kwargs):
    """Search for knowledge entries."""
    handler = KnowledgeHandler(project_path=kwargs.get("project_path"))
    return await handler.search(query, source=source, **kwargs)


async def load(id: str, destination: str = "project", **kwargs):
    """Load a knowledge entry."""
    handler = KnowledgeHandler(project_path=kwargs.get("project_path"))
    return await handler.load(id, destination=destination, **kwargs)


async def execute(id: str, parameters=None, **kwargs):
    """Execute a knowledge entry - load and return content."""
    handler = KnowledgeHandler(project_path=kwargs.get("project_path"))
    return await handler.execute(id, parameters=parameters)


async def sign(id: str, parameters=None, **kwargs):
    """Validate and sign a knowledge entry."""
    handler = KnowledgeHandler(project_path=kwargs.get("project_path"))
    return await handler.sign(id, parameters=parameters)


__all__ = ["search", "load", "execute", "sign", "KnowledgeHandler"]
