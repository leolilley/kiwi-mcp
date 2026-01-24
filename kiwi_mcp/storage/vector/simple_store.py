"""SQLite-based vector store with NumPy cosine similarity.

Lightweight alternative to ChromaDB that stores embeddings locally
and performs similarity search using NumPy.
"""

import json
import sqlite3
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Any

from .base import VectorStore, SearchResult


def _pack_embedding(embedding: List[float]) -> bytes:
    """Pack embedding as binary float32 array."""
    return struct.pack(f'{len(embedding)}f', *embedding)


def _unpack_embedding(data: bytes) -> List[float]:
    """Unpack binary float32 array to embedding."""
    count = len(data) // 4  # 4 bytes per float32
    return list(struct.unpack(f'{count}f', data))


def _normalize(vec: List[float]) -> List[float]:
    """Normalize vector to unit length."""
    try:
        import numpy as np
        arr = np.array(vec, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()
    except ImportError:
        # Fallback without numpy
        import math
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            return [x / norm for x in vec]
        return vec


def _cosine_similarity_batch(query: List[float], embeddings: List[List[float]]) -> List[float]:
    """Compute cosine similarity between query and batch of embeddings."""
    try:
        import numpy as np
        q = np.array(query, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm > 0:
            q = q / q_norm
        
        scores = []
        for emb in embeddings:
            e = np.array(emb, dtype=np.float32)
            e_norm = np.linalg.norm(e)
            if e_norm > 0:
                e = e / e_norm
            scores.append(float(np.dot(q, e)))
        return scores
    except ImportError:
        # Fallback without numpy
        import math
        q_norm = math.sqrt(sum(x * x for x in query))
        if q_norm > 0:
            query = [x / q_norm for x in query]
        
        scores = []
        for emb in embeddings:
            e_norm = math.sqrt(sum(x * x for x in emb))
            if e_norm > 0:
                emb = [x / e_norm for x in emb]
            scores.append(sum(q * e for q, e in zip(query, emb)))
        return scores


class SimpleVectorStore(VectorStore):
    """SQLite-based vector store with cosine similarity search."""

    def __init__(
        self,
        storage_path: Path,
        collection_name: str = "kiwi_items",
        embedding_service: Optional[Any] = None,
    ):
        self.storage_path = Path(storage_path)
        self.collection_name = collection_name
        self.embedder = embedding_service
        
        # Ensure directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Database file
        self.db_path = self.storage_path / f"{collection_name}.db"
        
        # Initialize schema
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    item_id TEXT PRIMARY KEY,
                    item_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT,
                    signature TEXT,
                    embedding BLOB NOT NULL,
                    dimension INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_item_type ON embeddings(item_type)")
            
            # Meta table for tracking embedding model info
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(str(self.db_path))

    async def embed_and_store(
        self,
        item_id: str,
        item_type: str,
        content: str,
        metadata: dict,
        signature: Optional[str] = None,
    ) -> bool:
        """Embed content and store in SQLite."""
        if self.embedder is None:
            raise RuntimeError("Embedding service not configured")
        
        # Get embedding (handle both sync and async embedders)
        import inspect
        if inspect.iscoroutinefunction(self.embedder.embed):
            embedding = await self.embedder.embed(content)
        else:
            embedding = self.embedder.embed(content)
        
        # Store normalized embedding
        normalized = _normalize(embedding)
        packed = _pack_embedding(normalized)
        
        now = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata)
        
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO embeddings 
                (item_id, item_type, content, metadata_json, signature, embedding, dimension, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id, item_type, content, metadata_json, signature,
                packed, len(normalized), now, now
            ))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    async def search(
        self,
        query: str,
        limit: int = 20,
        item_type: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> List[SearchResult]:
        """Search using cosine similarity."""
        if self.embedder is None:
            raise RuntimeError("Embedding service not configured")
        
        # Get query embedding
        import inspect
        if inspect.iscoroutinefunction(self.embedder.embed):
            query_embedding = await self.embedder.embed(query)
        else:
            query_embedding = self.embedder.embed(query)
        
        # Fetch candidates from DB
        conn = self._get_conn()
        try:
            sql = "SELECT item_id, item_type, content, metadata_json, embedding FROM embeddings"
            params = []
            
            if item_type:
                sql += " WHERE item_type = ?"
                params.append(item_type)
            
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
        finally:
            conn.close()
        
        if not rows:
            return []
        
        # Unpack embeddings and compute similarities
        candidates = []
        embeddings = []
        for row in rows:
            item_id, itype, content, metadata_json, emb_blob = row
            embedding = _unpack_embedding(emb_blob)
            embeddings.append(embedding)
            candidates.append({
                "item_id": item_id,
                "item_type": itype,
                "content": content,
                "metadata": json.loads(metadata_json) if metadata_json else {},
            })
        
        # Compute similarities
        scores = _cosine_similarity_batch(query_embedding, embeddings)
        
        # Combine and sort
        results = []
        for i, cand in enumerate(candidates):
            results.append(SearchResult(
                item_id=cand["item_id"],
                item_type=cand["item_type"],
                score=scores[i],
                content_preview=cand["content"][:200] if cand["content"] else "",
                metadata=cand["metadata"],
                source="local",
            ))
        
        # Sort by score descending and limit
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    async def delete(self, item_id: str) -> bool:
        """Delete embedding by item_id."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("DELETE FROM embeddings WHERE item_id = ?", (item_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            return False
        finally:
            conn.close()

    async def update(self, item_id: str, content: str, metadata: dict) -> bool:
        """Update embedding by re-embedding content."""
        # Get existing item type
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT item_type FROM embeddings WHERE item_id = ?", (item_id,)
            )
            row = cursor.fetchone()
        finally:
            conn.close()
        
        if not row:
            return False
        
        return await self.embed_and_store(
            item_id=item_id,
            item_type=row[0],
            content=content,
            metadata=metadata,
        )

    async def exists(self, item_id: str) -> bool:
        """Check if embedding exists."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM embeddings WHERE item_id = ?", (item_id,)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def get_stats(self) -> dict:
        """Get store statistics."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT COUNT(*), item_type FROM embeddings GROUP BY item_type")
            by_type = {row[1]: row[0] for row in cursor.fetchall()}
            
            cursor = conn.execute("SELECT COUNT(*) FROM embeddings")
            total = cursor.fetchone()[0]
            
            return {
                "total": total,
                "by_type": by_type,
                "db_path": str(self.db_path),
            }
        finally:
            conn.close()
