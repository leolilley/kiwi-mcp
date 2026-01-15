"""Knowledge Kiwi Handler - Search, Load, Execute knowledge entries."""

from .handler import KnowledgeHandler


async def search(query: str, source: str = "local", **kwargs):
    """Search for knowledge entries."""
    handler = KnowledgeHandler(project_path=kwargs.get("project_path"))
    return await handler.search(query, source=source, **kwargs)


async def load(zettel_id: str, destination: str = "project", **kwargs):
    """Load a knowledge entry."""
    handler = KnowledgeHandler(project_path=kwargs.get("project_path"))
    return await handler.load(zettel_id, destination=destination, **kwargs)


async def execute(action: str, zettel_id: str, parameters=None, **kwargs):
    """Execute a knowledge operation."""
    handler = KnowledgeHandler(project_path=kwargs.get("project_path"))
    return await handler.execute(action, zettel_id, parameters=parameters, **kwargs)


__all__ = ["search", "load", "execute", "KnowledgeHandler"]
