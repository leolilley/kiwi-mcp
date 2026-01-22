from pathlib import Path
from typing import Optional

from .base import VectorStore, SearchResult
from .embeddings import EmbeddingModel


class LocalVectorStore(VectorStore):
    def __init__(
        self,
        storage_path: Path,
        collection_name: str = "kiwi_items",
        embedding_model: Optional[EmbeddingModel] = None,
    ):
        self.storage_path = storage_path
        self.collection_name = collection_name
        storage_path.mkdir(parents=True, exist_ok=True)

        self._client = None
        self._collection = None
        self.embedder = embedding_model or EmbeddingModel()

    def _get_client(self):
        """Lazy load ChromaDB client."""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings

                self._client = chromadb.Client(
                    Settings(
                        chroma_db_impl="duckdb+parquet",
                        persist_directory=str(self.storage_path),
                        anonymized_telemetry=False,
                    )
                )
            except ImportError:
                raise ImportError(
                    "chromadb is required for local vector storage. "
                    "Install with: pip install chromadb"
                )
        return self._client

    def _get_collection(self):
        """Get or create the collection."""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.collection_name, metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    async def embed_and_store(
        self,
        item_id: str,
        item_type: str,
        content: str,
        metadata: dict,
        signature: Optional[str] = None,
    ) -> bool:
        embedding = self.embedder.embed(content)
        collection = self._get_collection()

        collection.upsert(
            ids=[item_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{"item_type": item_type, "signature": signature, **metadata}],
        )
        return True

    async def search(
        self,
        query: str,
        limit: int = 20,
        item_type: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> list[SearchResult]:
        query_embedding = self.embedder.embed(query)
        collection = self._get_collection()

        where = {}
        if item_type:
            where["item_type"] = item_type
        if filters:
            where.update(filters)

        results = collection.query(
            query_embeddings=[query_embedding], n_results=limit, where=where if where else None
        )

        search_results = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                search_results.append(
                    SearchResult(
                        item_id=results["ids"][0][i],
                        item_type=results["metadatas"][0][i].get("item_type", ""),
                        score=1 - results["distances"][0][i],  # Convert distance to similarity
                        content_preview=results["documents"][0][i][:200]
                        if results["documents"][0]
                        else "",
                        metadata=results["metadatas"][0][i],
                        source="local",
                    )
                )

        return search_results

    async def delete(self, item_id: str) -> bool:
        try:
            collection = self._get_collection()
            collection.delete(ids=[item_id])
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
            collection = self._get_collection()
            results = collection.get(ids=[item_id])
            return len(results["ids"]) > 0
        except Exception:
            return False
