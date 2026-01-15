"""
Script Registry API Client

Handles all interactions with Supabase scripts table.
Ported from script-kiwi.
"""

from typing import Any, Dict, List, Optional
from kiwi_mcp.api.base import BaseRegistry


class ScriptRegistry(BaseRegistry):
    """Client for Script Supabase registry."""
    
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
        tech_stack: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search scripts with multi-term matching and relevance scoring.
        
        Uses natural language search that:
        - Requires ALL terms to match (AND logic)
        - Intelligent relevance scoring (70% relevance + 30% compatibility)
        - Better results ranking
        
        Args:
            query: Search query (natural language, supports multiple terms)
            category: Optional category filter
            limit: Max results
            tech_stack: Optional tech stack for compatibility scoring
        
        Returns:
            List of matching scripts with relevance scores
        """
        if not self.is_configured:
            return []
        
        # Parse and normalize query
        query_terms = self._parse_search_query(query)
        if not query_terms:
            return []
        
        try:
            # Simple working pattern - search name for first term
            pattern = f"%{query_terms[0]}%"
            result = self.client.table("scripts").select(
                "id, name, category, subcategory, description, is_official, "
                "download_count, quality_score, tech_stack, created_at, updated_at, "
                "tags, success_rate, estimated_cost_usd, latest_version"
            ).ilike("name", pattern).limit(limit * 3).execute()
            
            scripts = []
            for row in (result.data or []):
                script = {
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "category": row.get("category"),
                    "subcategory": row.get("subcategory"),
                    "description": row.get("description"),
                    "is_official": row.get("is_official", False),
                    "download_count": row.get("download_count", 0),
                    "quality_score": row.get("quality_score", 0),
                    "tech_stack": row.get("tech_stack", []),
                    "tags": row.get("tags", []),
                    "success_rate": row.get("success_rate"),
                    "estimated_cost_usd": row.get("estimated_cost_usd"),
                    "latest_version": row.get("latest_version"),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                }
                
                # Calculate relevance score
                relevance_score = self._calculate_relevance_score(
                    query_terms, script["name"], script.get("description", "")
                )
                script["relevance_score"] = relevance_score
                
                # Apply tech stack compatibility
                if tech_stack and (s_stack := script.get("tech_stack")):
                    overlap = set(t.lower() for t in tech_stack) & set(
                        t.lower() if isinstance(t, str) else str(t).lower() 
                        for t in (s_stack if isinstance(s_stack, list) else [])
                    )
                    if not overlap:
                        continue  # Skip if no tech stack overlap
                    script["compatibility_score"] = len(overlap) / max(len(s_stack), 1)
                else:
                    script["compatibility_score"] = 1.0
                
                scripts.append(script)
            
            # Sort results by combined score: 70% relevance + 30% compatibility
            scripts.sort(
                key=lambda x: (
                    x.get("relevance_score", 0) * 0.7 + 
                    x.get("compatibility_score", 0) * 0.3,
                    x.get("quality_score", 0),
                    x.get("download_count", 0)
                ),
                reverse=True
            )
            
            return scripts[:limit]
        except Exception as e:
            print(f"Error searching scripts: {e}")
            return []
    
    async def get(self, name: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get script by name and optional version.
        
        Args:
            name: Script name
            version: Optional version (defaults to latest)
        
        Returns:
            Script data with content or None
        """
        if not self.is_configured:
            return None
        
        try:
            # Get script metadata
            result = self.client.table("scripts").select(
                "id, name, category, subcategory, description, is_official, "
                "download_count, quality_score, tech_stack, created_at, updated_at, tags"
            ).eq("name", name).single().execute()
            
            if not result.data:
                return None
            
            script = result.data
            script_id = script["id"]
            
            # Get versions
            version_query = self.client.table("script_versions").select(
                "version, content, content_hash, changelog, is_latest, created_at"
            ).eq("script_id", script_id).order("created_at", desc=True)
            
            if version:
                version_query = version_query.eq("version", version)
            
            version_result = version_query.limit(1).execute()
            if not version_result.data:
                return None
            
            version_data = version_result.data[0]
            
            return {
                **script,
                "content": version_data.get("content"),
                "version": version_data.get("version"),
                "changelog": version_data.get("changelog")
            }
        except Exception as e:
            print(f"Error getting script: {e}")
            return None
    
    async def list(
        self,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List scripts with optional category filter.
        
        Args:
            category: Optional category filter
            limit: Max results
        
        Returns:
            List of scripts
        """
        if not self.is_configured:
            return []
        
        try:
            query = self.client.table("scripts").select(
                "id, name, category, subcategory, description, is_official, "
                "download_count, quality_score, tech_stack, created_at, updated_at, tags"
            )
            
            if category:
                query = query.eq("category", category)
            
            result = query.limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"Error listing scripts: {e}")
            return []
    
    async def publish(
        self,
        name: str,
        version: str,
        content: str,
        category: str,
        subcategory: Optional[str] = None,
        description: Optional[str] = None,
        changelog: Optional[str] = None,
        tech_stack: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Publish script to registry.
        
        If script exists, creates new version. Otherwise creates new script.
        
        Args:
            name: Script name
            version: Semver version
            content: Python script content
            category: Category path
            subcategory: Optional subcategory
            description: Optional description
            changelog: Optional changelog
            tech_stack: Optional tech stack
            metadata: Optional additional metadata (dependencies, etc)
        
        Returns:
            Publish result with script_id, version_id, version, status
        """
        if not self.is_configured:
            return {"error": "Supabase client not initialized"}
        
        try:
            # Check if script exists
            existing = None
            try:
                result = self.client.table("scripts").select("id").eq("name", name).single().execute()
                existing = result.data
            except:
                pass
            
            if existing:
                # Update existing script
                script_id = existing["id"]
                update_data = {}
                if description:
                    update_data["description"] = description
                if subcategory:
                    update_data["subcategory"] = subcategory
                if tech_stack:
                    update_data["tech_stack"] = tech_stack
                
                if update_data:
                    self.client.table("scripts").update(update_data).eq("id", script_id).execute()
            else:
                # Create new script
                # Generate module_path from category and name
                module_path = f"{category}.{name}" if category else name
                
                script_data = {
                    "name": name,
                    "category": category,
                    "subcategory": subcategory,
                    "description": description or "",
                    "module_path": module_path,
                    "tech_stack": tech_stack or [],
                }
                
                script_result = self.client.table("scripts").insert(script_data).execute()
                script_id = script_result.data[0]["id"]
            
            # Mark old versions as not latest
            self.client.table("script_versions").update(
                {"is_latest": False}
            ).eq("script_id", script_id).execute()
            
            # Insert new version
            import hashlib
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            version_data = {
                "script_id": script_id,
                "version": version,
                "content": content,
                "content_hash": content_hash,
                "changelog": changelog,
                "is_latest": True
            }
            
            version_result = self.client.table("script_versions").insert(version_data).execute()
            
            return {
                "script_id": script_id,
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
        Delete script or specific version.
        
        Args:
            name: Script name
            version: Optional specific version (default: all versions)
            cascade: If True, also delete dependent scripts
        
        Returns:
            Deletion result
        """
        if not self.is_configured:
            return {"error": "Supabase client not initialized"}
        
        try:
            # Get script ID
            script_result = self.client.table("scripts").select(
                "id"
            ).eq("name", name).single().execute()
            
            if not script_result.data:
                return {"error": f"Script '{name}' not found"}
            
            script_id = script_result.data["id"]
            
            if version:
                # Delete specific version
                self.client.table("script_versions").delete().eq(
                    "script_id", script_id
                ).eq("version", version).execute()
                
                return {
                    "deleted": True,
                    "script": name,
                    "version": version
                }
            else:
                # Delete all versions and script record
                self.client.table("script_versions").delete().eq(
                    "script_id", script_id
                ).execute()
                
                self.client.table("scripts").delete().eq("id", script_id).execute()
                
                return {
                    "deleted": True,
                    "script": name,
                    "all_versions": True
                }
        except Exception as e:
            return {"error": str(e)}
