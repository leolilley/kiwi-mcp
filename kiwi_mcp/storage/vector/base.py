from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class SearchResult:
    item_id: str
    item_type: str
    score: float
    content_preview: str
    metadata: dict
    source: str


@dataclass
class EmbeddingRecord:
    item_id: str
    item_type: str
    embedding: list[float]
    content: str
    metadata: dict
    validated_at: datetime
    signature: Optional[str] = None


class VectorStore(ABC):
    @abstractmethod
    async def embed_and_store(
        self,
        item_id: str,
        item_type: str,
        content: str,
        metadata: dict,
        signature: Optional[str] = None,
    ) -> bool:
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 20,
        item_type: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> list[SearchResult]:
        pass

    @abstractmethod
    async def delete(self, item_id: str) -> bool:
        pass

    @abstractmethod
    async def update(self, item_id: str, content: str, metadata: dict) -> bool:
        pass

    @abstractmethod
    async def exists(self, item_id: str) -> bool:
        pass
