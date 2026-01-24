"""
Directive Registry API Client

Handles all interactions with Supabase directives table.
Ported from context-kiwi.
"""

from typing import Any, Dict, List, Optional
from kiwi_mcp.api.base import BaseRegistry


class DirectiveRegistry(BaseRegistry):
    """Client for Directive Supabase registry."""
    
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search directives with multi-term matching and relevance scoring.
        
        Uses natural language search that:
        - Requires ALL terms to match (AND logic)
        - Intelligent relevance scoring
        - Better results ranking
        
        Args:
            query: Search query (natural language, supports multiple terms)
            category: Optional category filter
            limit: Max results
        
        Returns:
            List of matching directives with relevance scores
        """
        if not self.is_configured:
            return []
        
        # Parse and normalize query
        query_terms = self._parse_search_query(query)
        if not query_terms:
            return []
        
        try:
            # Build query with DB-side filtering using ilike
            query_builder = self.client.table("directives").select(
                "id, name, category, description, is_official, "
                "download_count, quality_score, created_at, updated_at"
            )
            
            # Apply category filter
            if category:
                query_builder = query_builder.eq("category", category)
            
            # Build ilike filter for each term - must match in name OR description
            # Using or_ filter: each term must appear somewhere in name+description
            for term in query_terms:
                pattern = f"%{term}%"
                query_builder = query_builder.or_(f"name.ilike.{pattern},description.ilike.{pattern}")
            
            # Execute with reasonable limit
            result = query_builder.limit(limit * 2).execute()
            
            directives = []
            for row in (result.data or []):
                directive = {
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "category": row.get("category"),
                    "description": row.get("description"),
                    "is_official": row.get("is_official", False),
                    "download_count": row.get("download_count", 0),
                    "quality_score": row.get("quality_score", 0),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                }
                
                # Calculate relevance score
                relevance_score = self._calculate_relevance_score(
                    query_terms, directive["name"], directive.get("description", "")
                )
                directive["relevance_score"] = relevance_score
                
                directives.append(directive)
            
            # Sort results by relevance score, quality, and downloads
            directives.sort(
                key=lambda x: (
                    x.get("relevance_score", 0),
                    x.get("quality_score", 0),
                    x.get("download_count", 0)
                ),
                reverse=True
            )
            
            return directives[:limit]
        except Exception as e:
            print(f"Error searching directives: {e}")
            return []
    
    async def get(self, name: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get directive by name and optional version.
        
        Args:
            name: Directive name
            version: Optional version (defaults to latest)
        
        Returns:
            Directive data with content or None
        """
        if not self.is_configured:
            return None
        
        try:
            # Get directive metadata
            result = self.client.table("directives").select(
                "id, name, category, description, is_official, "
                "download_count, quality_score, created_at, updated_at"
            ).eq("name", name).single().execute()
            
            if not result.data:
                return None
            
            directive = result.data
            directive_id = directive["id"]
            
            # Get versions
            version_query = self.client.table("directive_versions").select(
                "version, content, content_hash, changelog, is_latest, created_at"
            ).eq("directive_id", directive_id).order("created_at", desc=True)
            
            if version:
                version_query = version_query.eq("version", version)
            else:
                # Get latest
                version_result = version_query.limit(1).execute()
                if not version_result.data:
                    return None
                version = version_result.data[0]
            
            if isinstance(version, dict):
                # Result from filtered query
                version_data = version
            else:
                # Get the version if single result
                version_result = version_query.execute()
                if not version_result.data:
                    return None
                version_data = version_result.data[0]
            
            return {
                **directive,
                "content": version_data.get("content"),
                "version": version_data.get("version"),
                "changelog": version_data.get("changelog")
            }
        except Exception as e:
            print(f"Error getting directive: {e}")
            return None
    
    async def list(
        self,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List directives with optional category filter.
        
        Args:
            category: Optional category filter
            limit: Max results
        
        Returns:
            List of directives
        """
        if not self.is_configured:
            return []
        
        try:
            query = self.client.table("directives").select(
                "id, name, category, description, is_official, "
                "download_count, quality_score, created_at, updated_at"
            )
            
            if category:
                query = query.eq("category", category)
            
            result = query.limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"Error listing directives: {e}")
            return []
    
    async def publish(
        self,
        name: str,
        version: str,
        content: str,
        category: str,
        description: Optional[str] = None,
        changelog: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Publish directive to registry.
        
        If directive exists, creates new version. Otherwise creates new directive.
        
        Args:
            name: Directive name
            version: Semver version
            content: Markdown content
            category: Category path (slash-separated, e.g., "core/api/endpoints")
            description: Optional description
            changelog: Optional changelog
            metadata: Optional additional metadata
        
        Returns:
            Publish result with directive_id, version_id, version, status
        """
        if not self.is_configured:
            return {"error": "Supabase client not initialized"}
        
        try:
            # Check if directive exists
            existing = None
            try:
                result = self.client.table("directives").select("id").eq("name", name).single().execute()
                existing = result.data
            except:
                pass
            
            if existing:
                # Update existing directive
                directive_id = existing["id"]
                update_data = {}
                if description:
                    update_data["description"] = description
                if category:
                    update_data["category"] = category
                
                if update_data:
                    self.client.table("directives").update(update_data).eq("id", directive_id).execute()
            else:
                # Create new directive
                directive_data = {
                    "name": name,
                    "category": category,
                    "description": description or "",
                }
                
                directive_result = self.client.table("directives").insert(directive_data).execute()
                directive_id = directive_result.data[0]["id"]
            
            # Mark old versions as not latest
            self.client.table("directive_versions").update(
                {"is_latest": False}
            ).eq("directive_id", directive_id).execute()
            
            # Insert new version
            import hashlib
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            version_data = {
                "directive_id": directive_id,
                "version": version,
                "content": content,
                "content_hash": content_hash,
                "changelog": changelog,
                "is_latest": True
            }
            
            version_result = self.client.table("directive_versions").insert(version_data).execute()
            
            # Create embedding for registry vector search
            await self._create_embedding(
                item_id=name,
                item_type="directive",
                content=f"{name} {description or ''} {content[:1000]}",
                metadata={"category": category, "version": version}
            )
            
            return {
                "directive_id": directive_id,
                "version_id": version_result.data[0]["id"] if version_result.data else None,
                "version": version,
                "status": "published"
            }
        except Exception as e:
            return {
                "error": "Publish failed",
                "details": str(e)
            }
    
    async def delete(
        self,
        name: str,
        version: Optional[str] = None,
        cascade: bool = False
    ) -> Dict[str, Any]:
        """
        Delete directive or specific version.
        
        Args:
            name: Directive name
            version: Optional specific version (default: all versions)
            cascade: If True, also delete dependent directives
        
        Returns:
            Deletion result
        """
        if not self.is_configured:
            return {"error": "Supabase client not initialized"}
        
        try:
            # Get directive ID
            directive_result = self.client.table("directives").select(
                "id"
            ).eq("name", name).single().execute()
            
            if not directive_result.data:
                return {"error": f"Directive '{name}' not found"}
            
            directive_id = directive_result.data["id"]
            
            if version:
                # Delete specific version
                self.client.table("directive_versions").delete().eq(
                    "directive_id", directive_id
                ).eq("version", version).execute()
                
                return {
                    "deleted": True,
                    "directive": name,
                    "version": version
                }
            else:
                # Delete all versions and directive record
                self.client.table("directive_versions").delete().eq(
                    "directive_id", directive_id
                ).execute()
                
                self.client.table("directives").delete().eq("id", directive_id).execute()
                
                # Delete embedding
                await self._delete_embedding(name)
                
                return {
                    "deleted": True,
                    "directive": name,
                    "all_versions": True
                }
        except Exception as e:
            return {"error": str(e)}
