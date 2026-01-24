"""
Knowledge Registry API Client

Handles all interactions with Supabase knowledge and knowledge_versions tables.
Ported from knowledge-kiwi.
"""

from typing import Any, Dict, List, Optional
from kiwi_mcp.api.base import BaseRegistry


class KnowledgeRegistry(BaseRegistry):
    """Client for Knowledge Supabase registry."""
    
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        entry_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search entries in registry using full-text search with multi-term matching.
        
        Args:
            query: Search query
            category: Optional category filter
            entry_type: Optional entry type filter
            tags: Optional tags filter
            limit: Max results
        
        Returns:
            List of entries with relevance scores
        """
        if not self.is_configured:
            return []
        
        # Parse query into normalized terms
        query_terms = self._parse_search_query(query)
        if not query_terms:
            return []
        
        try:
            # Use the search function - get more results to filter client-side
            result = self.client.rpc(
                "search_knowledge_fulltext",
                {
                    "search_query": query,
                    "match_count": limit * 3,  # Get more results for client-side filtering
                    "filter_entry_type": entry_type,
                    "filter_tags": tags,
                    "filter_category": category
                }
            ).execute()
            
            entries = []
            for row in (result.data or []):
                title = row.get("title", "")
                snippet = row.get("snippet", "")
                
                # CRITICAL: Multi-term matching - ensure ALL terms appear
                title_snippet = f"{title} {snippet}".lower()
                if not all(term in title_snippet for term in query_terms):
                    continue  # Skip if not all terms match
                
                # Calculate relevance score
                relevance_score = self._calculate_relevance_score(
                    query_terms,
                    title,
                    snippet
                )
                
                entries.append({
                    "zettel_id": row["zettel_id"],
                    "title": title,
                    "entry_type": row["entry_type"],
                    "category": row.get("category"),
                    "tags": row.get("tags", []),
                    "source_location": "registry",
                    "relevance_score": relevance_score / 100.0,  # Normalize to 0-1 range
                    "snippet": snippet
                })
            
            # Sort by relevance score (highest first)
            entries.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            return entries[:limit]
        except Exception as e:
            print(f"Error searching registry: {e}")
            return []
    
    async def get(self, zettel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get entry from registry.
        
        Args:
            zettel_id: Entry identifier
        
        Returns:
            Entry data or None
        """
        if not self.is_configured:
            return None
        
        try:
            # Join knowledge with knowledge_versions to get content and version
            result = self.client.rpc(
                "get_knowledge_with_content",
                {"p_zettel_id": zettel_id}
            ).execute()
            
            if result.data and len(result.data) > 0:
                row = result.data[0]
                return {
                    "zettel_id": row["zettel_id"],
                    "title": row["title"],
                    "content": row["content"],
                    "entry_type": row["entry_type"],
                    "category": row.get("category"),
                    "tags": row.get("tags", []),
                    "source_type": row.get("source_type"),
                    "source_url": row.get("source_url"),
                    "version": row.get("version", "1.0.0"),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at")
                }
            return None
        except Exception as e:
            # Fallback to direct query if RPC function doesn't exist yet
            try:
                result = self.client.table("knowledge").select(
                    "id, zettel_id, title, entry_type, category, tags, source_type, source_url, created_at, updated_at"
                ).eq("zettel_id", zettel_id).single().execute()
                
                if result.data:
                    # Get latest version content
                    version_result = self.client.table("knowledge_versions").select(
                        "version, content"
                    ).eq("knowledge_id", result.data["id"]).eq("is_latest", True).single().execute()
                    
                    return {
                        "zettel_id": result.data["zettel_id"],
                        "title": result.data["title"],
                        "content": version_result.data["content"] if version_result.data else "",
                        "entry_type": result.data["entry_type"],
                        "category": result.data.get("category"),
                        "tags": result.data.get("tags", []),
                        "source_type": result.data.get("source_type"),
                        "source_url": result.data.get("source_url"),
                        "version": version_result.data["version"] if version_result.data else "1.0.0",
                        "created_at": result.data.get("created_at"),
                        "updated_at": result.data.get("updated_at")
                    }
            except:
                pass
            print(f"Error getting entry from registry: {e}")
            return None
    
    async def list(
        self,
        category: Optional[str] = None,
        entry_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List entries with optional filters.
        
        Args:
            category: Optional category filter
            entry_type: Optional entry type filter
            tags: Optional tags filter
            limit: Max results
        
        Returns:
            List of entries
        """
        if not self.is_configured:
            return []
        
        try:
            # Get from knowledge table (no longer need version since it's in knowledge_versions)
            query = self.client.table("knowledge").select(
                "zettel_id, title, entry_type, category, tags, created_at, updated_at"
            )
            
            if category:
                query = query.eq("category", category)
            if entry_type:
                query = query.eq("entry_type", entry_type)
            
            result = query.limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"Error listing entries: {e}")
            return []
    
    async def publish(
        self,
        zettel_id: str,
        title: str,
        content: str,
        entry_type: str,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        source_type: Optional[str] = None,
        source_url: Optional[str] = None,
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish entry to registry.
        
        If entry exists, updates metadata and creates new version. Otherwise creates new entry with first version.
        
        Args:
            zettel_id: Entry identifier
            title: Entry title
            content: Markdown content
            entry_type: Entry type (api_fact, pattern, concept, learning, etc)
            tags: Optional tags
            category: Optional category
            source_type: Optional source type (youtube, docs, experiment, etc)
            source_url: Optional source URL
            version: Optional version (auto-incremented if not provided)
        
        Returns:
            Publish result with zettel_id, version, status
        """
        if not self.is_configured:
            return {"error": "Supabase client not initialized"}
        
        try:
            # Check if entry exists
            existing = await self.get(zettel_id)
            
            # Metadata for knowledge table (no content or version)
            entry_metadata = {
                "zettel_id": zettel_id,
                "title": title,
                "entry_type": entry_type,
                "tags": tags or [],
                "category": category,
                "source_type": source_type,
                "source_url": source_url,
            }
            
            # Determine version number
            if version:
                new_version = version
            elif existing:
                # Auto-increment version
                current_version = existing.get("version", "1.0.0")
                try:
                    parts = current_version.split(".")
                    patch = int(parts[-1]) + 1
                    new_version = ".".join(parts[:-1] + [str(patch)])
                except:
                    new_version = "1.0.1"
            else:
                new_version = "1.0.0"
            
            knowledge_id = None
            
            if existing:
                # Update existing entry metadata
                result = self.client.table("knowledge").update(entry_metadata).eq("zettel_id", zettel_id).execute()
                # Get knowledge_id
                knowledge_result = self.client.table("knowledge").select("id").eq("zettel_id", zettel_id).single().execute()
                knowledge_id = knowledge_result.data["id"]
                
                # Mark all previous versions as not latest
                self.client.table("knowledge_versions").update({"is_latest": False}).eq("knowledge_id", knowledge_id).execute()
            else:
                # Create new entry
                import hashlib
                result = self.client.table("knowledge").insert(entry_metadata).execute()
                knowledge_id = result.data[0]["id"]
            
            # Create new version with content
            import hashlib
            version_data = {
                "knowledge_id": knowledge_id,
                "version": new_version,
                "content": content,
                "content_hash": hashlib.md5(content.encode()).hexdigest(),
                "is_latest": True
            }
            
            self.client.table("knowledge_versions").insert(version_data).execute()
            
            # Create embedding for registry vector search
            await self._create_embedding(
                item_id=zettel_id,
                item_type="knowledge",
                content=f"{zettel_id} {title} {content[:1000]}",
                metadata={"category": category, "entry_type": entry_type, "version": new_version}
            )
            
            return {
                "status": "success",
                "zettel_id": zettel_id,
                "version": new_version
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def get_relationships(
        self,
        zettel_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get relationships for an entry.
        
        Returns:
            {
                "outgoing": [...],  # Relationships from this entry
                "incoming": [...]   # Relationships to this entry
            }
        """
        if not self.is_configured:
            return {"outgoing": [], "incoming": []}
        
        try:
            # Get outgoing relationships
            outgoing_result = self.client.table("knowledge_relationships").select("*").eq("from_zettel_id", zettel_id).execute()
            
            # Get incoming relationships
            incoming_result = self.client.table("knowledge_relationships").select("*").eq("to_zettel_id", zettel_id).execute()
            
            return {
                "outgoing": [
                    {
                        "zettel_id": rel["to_zettel_id"],
                        "relationship_type": rel["relationship_type"]
                    }
                    for rel in (outgoing_result.data or [])
                ],
                "incoming": [
                    {
                        "zettel_id": rel["from_zettel_id"],
                        "relationship_type": rel["relationship_type"]
                    }
                    for rel in (incoming_result.data or [])
                ]
            }
        except Exception as e:
            print(f"Error getting relationships: {e}")
            return {"outgoing": [], "incoming": []}
    
    async def create_relationship(
        self,
        from_zettel_id: str,
        to_zettel_id: str,
        relationship_type: str
    ) -> Dict[str, Any]:
        """Create a relationship between two entries."""
        if not self.is_configured:
            return {"error": "Supabase client not initialized"}
        
        try:
            result = self.client.table("knowledge_relationships").insert({
                "from_zettel_id": from_zettel_id,
                "to_zettel_id": to_zettel_id,
                "relationship_type": relationship_type
            }).execute()
            
            return {
                "status": "success",
                "relationship": {
                    "from_zettel_id": from_zettel_id,
                    "to_zettel_id": to_zettel_id,
                    "relationship_type": relationship_type
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def create_collection(
        self,
        name: str,
        zettel_ids: List[str],
        collection_type: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a collection of entries."""
        if not self.is_configured:
            return {"error": "Supabase client not initialized"}
        
        try:
            result = self.client.table("knowledge_collections").insert({
                "name": name,
                "description": description,
                "zettel_ids": zettel_ids,
                "collection_type": collection_type
            }).execute()
            
            return {
                "status": "success",
                "collection_id": result.data[0]["id"] if result.data else None
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def delete(
        self,
        zettel_id: str,
        cascade_relationships: bool = False
    ) -> Dict[str, Any]:
        """
        Delete entry from registry.
        
        Args:
            zettel_id: Entry to delete
            cascade_relationships: If True, delete related relationships first.
                                   If False, prevent deletion if relationships exist.
        
        Returns:
            {"status": "success"} or {"error": "..."}
        """
        if not self.is_configured:
            return {"error": "Supabase client not initialized"}
        
        try:
            # Check if entry exists
            existing = await self.get(zettel_id)
            if not existing:
                return {"error": f"Entry '{zettel_id}' not found in registry"}
            
            # Check for relationships
            relationships = await self.get_relationships(zettel_id)
            total_relationships = len(relationships.get("outgoing", [])) + len(relationships.get("incoming", []))
            
            if total_relationships > 0 and not cascade_relationships:
                return {
                    "error": f"Cannot delete entry: {total_relationships} relationship(s) exist. Set cascade_relationships: true to delete relationships first."
                }
            
            # Delete relationships if cascade is enabled
            if cascade_relationships and total_relationships > 0:
                # Delete outgoing relationships
                self.client.table("knowledge_relationships").delete().eq("from_zettel_id", zettel_id).execute()
                # Delete incoming relationships
                self.client.table("knowledge_relationships").delete().eq("to_zettel_id", zettel_id).execute()
            
            # Delete the entry (CASCADE will automatically delete versions)
            self.client.table("knowledge").delete().eq("zettel_id", zettel_id).execute()
            
            # Delete embedding
            await self._delete_embedding(zettel_id)
            
            return {
                "status": "success",
                "zettel_id": zettel_id,
                "relationships_deleted": total_relationships if cascade_relationships else 0
            }
        except Exception as e:
            return {"error": str(e)}
