"""Local vector store - SQLite-based with API embeddings.

Wrapper around SimpleVectorStore for consistent interface.
"""

from pathlib import Path
from typing import Optional, Any

from .base import VectorStore, SearchResult
from .simple_store import SimpleVectorStore


class LocalVectorStore(VectorStore):
    """Local vector storage using SQLite and API embeddings.

    Wrapper around SimpleVectorStore for consistent interface.
    """

    def __init__(
        self,
        storage_path: Path,
        collection_name: str = "kiwi_items",
        embedding_service: Optional[Any] = None,
        source: str = "project",
    ):
        self.storage_path = Path(storage_path)
        self.collection_name = collection_name
        self.source = source
        storage_path.mkdir(parents=True, exist_ok=True)

        # Use SimpleVectorStore internally
        self._store = SimpleVectorStore(
            storage_path=storage_path,
            collection_name=collection_name,
            embedding_service=embedding_service,
            source=source,
        )

        # Keep reference to embedder
        self.embedder = embedding_service

    async def embed_and_store(
        self,
        item_id: str,
        item_type: str,
        content: str,
        metadata: dict,
        signature: Optional[str] = None,
    ) -> bool:
        """Store embedding for content."""
        return await self._store.embed_and_store(
            item_id=item_id,
            item_type=item_type,
            content=content,
            metadata=metadata,
            signature=signature,
        )

    async def search(
        self,
        query: str,
        limit: int = 20,
        item_type: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> list[SearchResult]:
        """Search for similar items."""
        return await self._store.search(
            query=query,
            limit=limit,
            item_type=item_type,
            filters=filters,
        )

    async def delete(self, item_id: str) -> bool:
        """Delete embedding."""
        return await self._store.delete(item_id)

    async def update(self, item_id: str, content: str, metadata: dict) -> bool:
        """Update embedding."""
        return await self._store.update(item_id, content, metadata)

    async def exists(self, item_id: str) -> bool:
        """Check if embedding exists."""
        return await self._store.exists(item_id)

    def get_stats(self) -> dict:
        """Get store statistics."""
        return self._store.get_stats()
