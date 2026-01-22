from typing import Optional, Tuple

from .base import VectorStore


class ValidationGatedEmbedding:
    """Only embed content that passes validation."""

    def __init__(
        self,
        vector_store: VectorStore,
        validator=None,  # Optional validator - can be added later
    ):
        self.validator = validator
        self.store = vector_store

    async def embed_if_valid(
        self, item_id: str, item_type: str, content: str, metadata: dict
    ) -> Tuple[bool, Optional[str]]:
        """Validate content, then embed if valid.

        Returns (success, error_message)
        """
        # Skip validation if no validator provided
        if self.validator is None:
            success = await self.store.embed_and_store(
                item_id=item_id, item_type=item_type, content=content, metadata=metadata
            )
            return success, None if success else "Failed to store embedding"

        # Validate first
        result = await self.validator.validate(content, item_type)

        if not result.valid:
            return False, f"Validation failed: {result.error}"

        # Embed only valid content
        success = await self.store.embed_and_store(
            item_id=item_id,
            item_type=item_type,
            content=content,
            metadata=metadata,
            signature=getattr(result, "signature", None),
        )

        if not success:
            return False, "Failed to store embedding"

        return True, None

    async def update_if_valid(
        self, item_id: str, item_type: str, content: str, metadata: dict
    ) -> Tuple[bool, Optional[str]]:
        """Update embedding only if content passes validation."""
        return await self.embed_if_valid(item_id, item_type, content, metadata)
