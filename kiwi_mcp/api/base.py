"""
Base Registry Client

Shared Supabase client and utilities for all registry types.
"""

import logging
import os
from typing import Any, Dict, Optional
from supabase import create_client, Client


class BaseRegistry:
    """Base class for all registry clients with shared Supabase logic."""
    
    def __init__(self):
        """Initialize Supabase client from environment."""
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_ANON_KEY")
        self.client: Optional[Client] = None
        
        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
            except Exception as e:
                self.client = None
    
    @property
    def is_configured(self) -> bool:
        """Check if Supabase is configured."""
        return bool(self.url and self.key and self.client is not None)
    
    def _parse_search_query(self, query: str) -> list[str]:
        """
        Parse search query into normalized terms.
        
        Handles:
        - Multiple words (split by whitespace)
        - Normalization (lowercase, strip)
        - Filters out single characters
        """
        if not query or not query.strip():
            return []
        
        terms = []
        for word in query.split():
            word = word.strip().lower()
            if word and len(word) >= 2:  # Ignore single characters
                terms.append(word)
        
        return terms
    
    def _calculate_relevance_score(
        self,
        query_terms: list[str],
        primary_text: str,
        secondary_text: str = ""
    ) -> float:
        """
        Calculate relevance score based on term matches.
        
        Scoring:
        - Exact match: 100
        - All terms in primary: 80
        - Some terms in primary: 60 * (matches/terms)
        - All terms in secondary: 40
        - Some terms in secondary: 20 * (matches/terms)
        
        Args:
            query_terms: List of normalized search terms
            primary_text: Primary text to search (name/title)
            secondary_text: Secondary text to search (description)
        
        Returns:
            Relevance score (0-100)
        """
        primary_lower = primary_text.lower()
        secondary_lower = (secondary_text or "").lower()
        
        # Check exact match
        primary_normalized = primary_lower.replace("_", " ").replace("-", " ")
        query_normalized = " ".join(query_terms)
        if primary_normalized == query_normalized or primary_lower == query_normalized.replace(" ", "_"):
            return 100.0
        
        # Count term matches
        primary_matches = sum(1 for term in query_terms if term in primary_lower)
        secondary_matches = sum(1 for term in query_terms if term in secondary_lower)
        
        # Calculate score
        score = 0.0
        
        if primary_matches == len(query_terms):
            score = 80.0  # All terms in primary
        elif primary_matches > 0:
            score = 60.0 * (primary_matches / len(query_terms))  # Some terms in primary
        
        if secondary_matches == len(query_terms):
            score = max(score, 40.0)  # All terms in secondary
        elif secondary_matches > 0:
            score = max(score, 20.0 * (secondary_matches / len(query_terms)))  # Some terms in secondary
        
        return score

    async def _create_embedding(
        self,
        item_id: str,
        item_type: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Create or update embedding in item_embeddings table.
        
        Args:
            item_id: Unique identifier for the item
            item_type: Type of item (directive, tool, knowledge)
            content: Text content to embed
            metadata: Additional metadata to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
            
        try:
            from kiwi_mcp.storage.vector import EmbeddingService, load_vector_config
            
            config = load_vector_config()
            embedding_service = EmbeddingService(config)
            embedding = await embedding_service.embed(content)
            
            # Upsert embedding
            self.client.table("item_embeddings").upsert({
                "item_id": item_id,
                "item_type": item_type,
                "embedding": embedding,
                "content": content[:2000],  # Truncate for storage
                "metadata": metadata,
            }).execute()
            
            await embedding_service.close()
            return True
        except Exception as e:
            logging.getLogger("registry").warning(f"Failed to create embedding for {item_id}: {e}")
            return False

    async def _delete_embedding(self, item_id: str) -> bool:
        """Delete embedding from item_embeddings table.
        
        Args:
            item_id: Unique identifier for the item
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
            
        try:
            self.client.table("item_embeddings").delete().eq("item_id", item_id).execute()
            return True
        except Exception as e:
            logging.getLogger("registry").warning(f"Failed to delete embedding for {item_id}: {e}")
            return False
