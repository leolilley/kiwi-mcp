"""Simple embedding service - just URL + key + model."""

import hashlib
import json
from typing import List, Optional, Dict, Any
import httpx
from .embedding_registry import VectorConfig


class EmbeddingService:
    """Simple embedding service - just URL + key + model."""

    def __init__(self, vector_config: VectorConfig):
        self.config = vector_config

        # Validate required fields
        if not vector_config.embedding_url:
            raise ValueError("Embedding URL is required")

        self.endpoint_url = vector_config.embedding_url
        self.api_key = vector_config.embedding_key
        self.model = vector_config.embedding_model or "default"
        self.request_format = vector_config.request_format or "openai"
        self.auth_header = vector_config.auth_header or "Authorization"
        self.auth_format = vector_config.auth_format or "Bearer {key}"

        # Initialize client and cache
        self._cache: Dict[str, List[float]] = {}
        self._client = httpx.AsyncClient(timeout=30.0)
        self._dimension = None  # Will be determined from first API call

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text with caching."""
        cache_key = hashlib.md5(f"{self.endpoint_url}:{self.model}:{text}".encode()).hexdigest()

        if cache_key in self._cache:
            return self._cache[cache_key]

        embeddings = await self.embed_batch([text])
        if embeddings:
            self._cache[cache_key] = embeddings[0]
            self._set_dimension_from_embedding(embeddings[0])
            return embeddings[0]

        raise RuntimeError(f"Failed to generate embedding for text: {text[:50]}...")
    
    async def embed(self, text: str) -> List[float]:
        """Alias for embed_text."""
        return await self.embed_text(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using configured request format."""
        try:
            return await self._call_api(texts)

        except httpx.ConnectError:
            if "localhost" in self.endpoint_url:
                raise RuntimeError(
                    f"Cannot connect to local embedding server at {self.endpoint_url}. "
                    f"Is the server running?"
                )
            else:
                raise RuntimeError(f"Cannot connect to embedding service at {self.endpoint_url}")
        except httpx.TimeoutException:
            raise RuntimeError(f"Embedding service timeout at {self.endpoint_url}")

    async def _call_api(self, texts: List[str]) -> List[List[float]]:
        """Call embedding API using configured format."""
        # Build headers
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            auth_value = self.auth_format.format(key=self.api_key)
            headers[self.auth_header] = auth_value

        # Build payload based on request format
        if self.request_format == "openai":
            payload = {"input": texts, "model": self.model, "encoding_format": "float"}
            response_path = ["data", "*", "embedding"]  # data[*].embedding

        elif self.request_format == "cohere":
            payload = {"texts": texts, "model": self.model, "input_type": "search_document"}
            response_path = ["embeddings"]  # embeddings

        elif self.request_format == "custom":
            # Generic format - user can customize via config
            payload = {"texts": texts, "model": self.model}
            response_path = ["embeddings"]  # Default path

        else:
            # Default to OpenAI format
            payload = {"input": texts, "model": self.model}
            response_path = ["data", "*", "embedding"]

        # Make API call
        response = await self._client.post(self.endpoint_url, headers=headers, json=payload)

        if response.status_code != 200:
            error_text = response.text
            if response.status_code == 401:
                raise RuntimeError(f"Authentication failed: check API key")
            elif response.status_code == 404:
                raise RuntimeError(f"Model '{self.model}' not found")
            else:
                raise RuntimeError(f"API error: {response.status_code} - {error_text}")

        # Parse response based on format
        data = response.json()
        embeddings = self._extract_embeddings(data, response_path)

        # Set dimension from first successful call
        if embeddings and self._dimension is None:
            self._set_dimension_from_embedding(embeddings[0])

        return embeddings

    def _extract_embeddings(self, data: dict, path: List[str]) -> List[List[float]]:
        """Extract embeddings from API response using path."""
        current = data

        for key in path:
            if key == "*":
                # Handle array extraction
                if isinstance(current, list):
                    return [item.get("embedding", []) for item in current]
                else:
                    raise RuntimeError("Expected array in response path")
            else:
                current = current.get(key, {})

        # If we get here, return the current value (should be embeddings array)
        if isinstance(current, list):
            return current
        else:
            raise RuntimeError(f"Unexpected response format: {type(current)}")

    @property
    def dimension(self) -> Optional[int]:
        """Get embedding dimension (determined from first API call)."""
        return self._dimension

    def _set_dimension_from_embedding(self, embedding: List[float]):
        """Set dimension from first successful embedding."""
        if self._dimension is None:
            self._dimension = len(embedding)

    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()

    def get_info(self) -> Dict[str, Any]:
        """Get service configuration info."""
        return {
            "model": self.model,
            "endpoint": self.endpoint_url,
            "dimensions": self.dimension,
            "has_api_key": bool(self.api_key),
            "request_format": self.request_format,
            "auth_header": self.auth_header,
        }
