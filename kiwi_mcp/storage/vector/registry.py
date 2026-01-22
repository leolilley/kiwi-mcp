import os
from typing import Optional

from .base import VectorStore, SearchResult
from .embeddings import EmbeddingModel


class RegistryVectorStore(VectorStore):
    def __init__(self, embedding_model: Optional[EmbeddingModel] = None):
        self._client = None
        self.embedder = embedding_model or EmbeddingModel()

    def _get_client(self):
        """Lazy load Supabase client."""
        if self._client is None:
            try:
                from supabase import create_client

                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_KEY")

                if not supabase_url or not supabase_key:
                    raise ValueError(
                        "SUPABASE_URL and SUPABASE_KEY environment variables are required"
                    )

                self._client = create_client(supabase_url, supabase_key)
            except ImportError:
                raise ImportError(
                    "supabase is required for registry vector storage. "
                    "Install with: pip install supabase"
                )
        return self._client

    async def embed_and_store(
        self,
        item_id: str,
        item_type: str,
        content: str,
        metadata: dict,
        signature: Optional[str] = None,
    ) -> bool:
        embedding = self.embedder.embed(content)
        client = self._get_client()

        try:
            client.table("item_embeddings").upsert(
                {
                    "item_id": item_id,
                    "item_type": item_type,
                    "embedding": embedding,
                    "content": content,
                    "metadata": metadata,
                    "signature": signature,
                }
            ).execute()
            return True
        except Exception:
            return False

    async def search(
        self,
        query: str,
        limit: int = 20,
        item_type: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> list[SearchResult]:
        query_embedding = self.embedder.embed(query)
        client = self._get_client()

        try:
            result = client.rpc(
                "search_embeddings",
                {
                    "query_embedding": query_embedding,
                    "match_count": limit,
                    "filter_type": item_type,
                },
            ).execute()

            return [
                SearchResult(
                    item_id=r["item_id"],
                    item_type=r["item_type"],
                    score=r["similarity"],
                    content_preview=r["content"][:200],
                    metadata=r["metadata"],
                    source="registry",
                )
                for r in result.data or []
            ]
        except Exception:
            return []

    async def delete(self, item_id: str) -> bool:
        try:
            client = self._get_client()
            client.table("item_embeddings").delete().eq("item_id", item_id).execute()
            return True
        except Exception:
            return False

    async def update(self, item_id: str, content: str, metadata: dict) -> bool:
        # Update by re-embedding and storing
        return await self.embed_and_store(
            item_id=item_id,
            item_type=metadata.get("item_type", ""),
            content=content,
            metadata=metadata,
        )

    async def exists(self, item_id: str) -> bool:
        try:
            client = self._get_client()
            result = (
                client.table("item_embeddings").select("item_id").eq("item_id", item_id).execute()
            )
            return len(result.data) > 0
        except Exception:
            return False
