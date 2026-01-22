import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class CacheEntry:
    schemas: list[dict]
    fetched_at: float

    def is_valid(self, ttl: float) -> bool:
        return time.time() - self.fetched_at < ttl


class SchemaCache:
    def __init__(self, ttl_seconds: float = 3600):
        self._cache: dict[str, CacheEntry] = {}
        self.ttl = ttl_seconds

    def get(self, mcp_name: str, force_refresh: bool = False) -> Optional[list[dict]]:
        if force_refresh:
            return None

        entry = self._cache.get(mcp_name)
        if entry and entry.is_valid(self.ttl):
            return entry.schemas
        return None

    def set(self, mcp_name: str, schemas: list[dict]) -> None:
        self._cache[mcp_name] = CacheEntry(schemas=schemas, fetched_at=time.time())

    def invalidate(self, mcp_name: str = None) -> None:
        if mcp_name:
            self._cache.pop(mcp_name, None)
        else:
            self._cache.clear()
