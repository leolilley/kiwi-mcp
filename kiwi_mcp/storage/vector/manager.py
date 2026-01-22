from typing import Optional

from .base import SearchResult
from .local import LocalVectorStore
from .registry import RegistryVectorStore


class ThreeTierVectorManager:
    """Coordinate searches across project → user → registry."""

    def __init__(
        self,
        project_store: LocalVectorStore,
        user_store: LocalVectorStore,
        registry_store: RegistryVectorStore,
    ):
        self.project = project_store
        self.user = user_store
        self.registry = registry_store

    async def search(
        self, query: str, source: str = "all", item_type: Optional[str] = None, limit: int = 20
    ) -> list[SearchResult]:
        """Search across tiers based on source."""
        results = []

        if source in ["local", "all"]:
            # Project first (highest priority)
            try:
                project_results = await self.project.search(query, limit, item_type)
                results.extend(project_results)
            except Exception:
                pass  # Continue even if one store fails

            # Then user
            try:
                user_results = await self.user.search(query, limit, item_type)
                results.extend(user_results)
            except Exception:
                pass

        if source in ["registry", "all"]:
            try:
                registry_results = await self.registry.search(query, limit, item_type)
                results.extend(registry_results)
            except Exception:
                pass

        # Dedupe by item_id, keep highest score
        seen = {}
        for r in results:
            if r.item_id not in seen or r.score > seen[r.item_id].score:
                seen[r.item_id] = r

        # Sort by score and return top N
        return sorted(seen.values(), key=lambda x: x.score, reverse=True)[:limit]

    async def embed_and_store(
        self, item_id: str, item_type: str, content: str, metadata: dict, location: str = "project"
    ) -> bool:
        """Store embedding in specified location."""
        if location == "user":
            return await self.user.embed_and_store(item_id, item_type, content, metadata)
        elif location == "registry":
            return await self.registry.embed_and_store(item_id, item_type, content, metadata)
        else:  # Default to project
            return await self.project.embed_and_store(item_id, item_type, content, metadata)

    async def delete(self, item_id: str, source: str = "all") -> bool:
        """Delete embedding from specified sources."""
        success = True

        if source in ["local", "all", "project"]:
            success &= await self.project.delete(item_id)

        if source in ["local", "all", "user"]:
            success &= await self.user.delete(item_id)

        if source in ["registry", "all"]:
            success &= await self.registry.delete(item_id)

        return success
