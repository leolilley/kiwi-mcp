"""
Tool Registry API Client

Handles all interactions with Supabase tools and tool_versions tables.
Tool registry for unified tools architecture.
"""

from typing import Any, Dict, List, Optional
from kiwi_mcp.api.base import BaseRegistry


class ToolRegistry(BaseRegistry):
    """Client for unified Tools Supabase registry."""

    async def search(
        self,
        query: str,
        tool_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search tools using the search_tools function or direct query.

        Args:
            query: Search query
            tool_type: Optional filter (script, api, runtime, mcp_server, etc.)
            category: Optional category filter
            limit: Max results

        Returns:
            List of matching tools with relevance scores
        """
        if not self.is_configured:
            return []

        try:
            # Use the search_tools function we created
            result = self.client.rpc(
                "search_tools",
                {
                    "p_query": query,
                    "p_tool_type": tool_type,
                    "p_category": category,
                    "p_limit": limit,
                },
            ).execute()

            tools = []
            for row in result.data or []:
                tools.append(
                    {
                        "id": row.get("id"),
                        "tool_id": row.get("tool_id"),
                        "name": row.get("name") or row.get("tool_id"),
                        "tool_type": row.get("tool_type"),
                        "category": row.get("category"),
                        "description": row.get("description"),
                        "executor_id": row.get("executor_id"),
                        "latest_version": row.get("latest_version"),
                        "score": row.get("rank", 0),
                        "source": "registry",
                    }
                )

            return tools
        except Exception as e:
            print(f"Error searching tools: {e}")
            # Fallback to direct query if RPC fails
            return await self._search_fallback(query, tool_type, category, limit)

    async def _search_fallback(
        self,
        query: str,
        tool_type: Optional[str],
        category: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Fallback search using direct table query."""
        try:
            q = self.client.table("tools").select(
                "id, tool_id, name, tool_type, category, description, "
                "executor_id, latest_version, download_count, is_official"
            )

            if tool_type:
                q = q.eq("tool_type", tool_type)
            if category:
                q = q.eq("category", category)

            # Simple ILIKE search
            q = q.or_(f"tool_id.ilike.%{query}%,name.ilike.%{query}%,description.ilike.%{query}%")

            result = q.limit(limit).execute()

            return [
                {
                    "id": row.get("id"),
                    "tool_id": row.get("tool_id"),
                    "name": row.get("name") or row.get("tool_id"),
                    "tool_type": row.get("tool_type"),
                    "category": row.get("category"),
                    "description": row.get("description"),
                    "executor_id": row.get("executor_id"),
                    "latest_version": row.get("latest_version"),
                    "score": 1.0,
                    "source": "registry",
                }
                for row in (result.data or [])
            ]
        except Exception as e:
            print(f"Error in fallback search: {e}")
            return []

    async def get(
        self, tool_id: str, version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get tool by tool_id and optional version.

        Args:
            tool_id: Tool identifier (e.g., "python_runtime", "enrich_emails")
            version: Optional version (defaults to latest)

        Returns:
            Tool data with manifest and files, or None
        """
        if not self.is_configured:
            return None

        try:
            # Get tool metadata
            result = (
                self.client.table("tools")
                .select(
                    "id, tool_id, namespace, name, tool_type, category, "
                    "tags, executor_id, is_builtin, description, is_official, visibility, "
                    "download_count, quality_score, success_rate, latest_version, "
                    "created_at, updated_at"
                )
                .eq("tool_id", tool_id)
                .single()
                .execute()
            )

            if not result.data:
                return None

            tool = result.data
            tool_uuid = tool["id"]

            # Get version (latest or specific)
            version_query = (
                self.client.table("tool_versions")
                .select(
                    "id, version, manifest, manifest_yaml, content_hash, "
                    "changelog, is_latest, deprecated, created_at"
                )
                .eq("tool_id", tool_uuid)
                .order("created_at", desc=True)
            )

            if version:
                version_query = version_query.eq("version", version)
            else:
                version_query = version_query.eq("is_latest", True)

            version_result = version_query.limit(1).execute()
            if not version_result.data:
                return None

            version_data = version_result.data[0]
            version_uuid = version_data["id"]

            # Get files for this version
            files_result = (
                self.client.table("tool_version_files")
                .select("path, media_type, content_text, sha256, size_bytes, is_executable")
                .eq("tool_version_id", version_uuid)
                .execute()
            )

            files = {f["path"]: f for f in (files_result.data or [])}

            # Extract content from main file if present
            content = None
            if "main.py" in files:
                content = files["main.py"].get("content_text")
            elif "main.sh" in files:
                content = files["main.sh"].get("content_text")

            return {
                **tool,
                "version": version_data.get("version"),
                "manifest": version_data.get("manifest"),
                "manifest_yaml": version_data.get("manifest_yaml"),
                "content_hash": version_data.get("content_hash"),
                "changelog": version_data.get("changelog"),
                "content": content,
                "files": files,
            }
        except Exception as e:
            print(f"Error getting tool: {e}")
            return None

    async def list(
        self,
        tool_type: Optional[str] = None,
        category: Optional[str] = None,
        include_builtins: bool = True,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List tools with optional filters.

        Args:
            tool_type: Optional type filter
            category: Optional category filter
            include_builtins: Whether to include builtin tools
            limit: Max results

        Returns:
            List of tools
        """
        if not self.is_configured:
            return []

        try:
            query = self.client.table("tools").select(
                "id, tool_id, name, tool_type, category, description, "
                "executor_id, is_builtin, is_official, latest_version, "
                "download_count, created_at, updated_at"
            )

            if tool_type:
                query = query.eq("tool_type", tool_type)
            if category:
                query = query.eq("category", category)
            if not include_builtins:
                query = query.eq("is_builtin", False)

            result = query.limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"Error listing tools: {e}")
            return []

    async def publish(
        self,
        tool_id: str,
        version: str,
        tool_type: str,
        executor_id: str,
        manifest: Dict[str, Any],
        files: Optional[Dict[str, str]] = None,
        category: Optional[str] = None,
        description: Optional[str] = None,
        changelog: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish tool to registry.

        Args:
            tool_id: Tool identifier
            version: Semver version
            tool_type: Type (script, api, runtime, mcp_server)
            executor_id: Executor tool_id (e.g., "python_runtime", "subprocess")
            manifest: Tool manifest as dict
            files: Dict of {path: content} for tool files
            category: Optional category
            description: Optional description
            changelog: Optional changelog

        Returns:
            Publish result
        """
        if not self.is_configured:
            return {"error": "Supabase client not initialized"}

        try:
            import hashlib

            # Check if tool exists
            existing = None
            try:
                result = (
                    self.client.table("tools")
                    .select("id")
                    .eq("tool_id", tool_id)
                    .single()
                    .execute()
                )
                existing = result.data
            except Exception:
                pass

            if existing:
                # Update existing tool
                tool_uuid = existing["id"]
                update_data = {
                    "latest_version": version,
                    "tool_type": tool_type,
                    "executor_id": executor_id,
                }
                if description:
                    update_data["description"] = description
                if category:
                    update_data["category"] = category

                self.client.table("tools").update(update_data).eq("id", tool_uuid).execute()
            else:
                # Create new tool
                tool_data = {
                    "tool_id": tool_id,
                    "name": manifest.get("name", tool_id),
                    "tool_type": tool_type,
                    "executor_id": executor_id,
                    "category": category,
                    "description": description or manifest.get("description", ""),
                    "latest_version": version,
                }

                tool_result = self.client.table("tools").insert(tool_data).execute()
                tool_uuid = tool_result.data[0]["id"]

            # Mark old versions as not latest
            self.client.table("tool_versions").update({"is_latest": False}).eq(
                "tool_id", tool_uuid
            ).execute()

            # Compute file hashes first (needed for canonical integrity)
            file_entries = []
            if files:
                for path, content in files.items():
                    file_hash = hashlib.sha256(content.encode()).hexdigest()
                    file_entries.append({
                        "path": path,
                        "sha256": file_hash,
                        "is_executable": path.endswith((".py", ".sh")),
                        "content": content,
                        "size_bytes": len(content),
                    })
            
            # Compute canonical integrity hash (includes manifest + file hashes)
            from kiwi_mcp.primitives.integrity import compute_tool_integrity
            content_hash = compute_tool_integrity(
                tool_id=tool_id,
                version=version,
                manifest=manifest,
                files=file_entries
            )

            # Insert new version
            version_data = {
                "tool_id": tool_uuid,
                "version": version,
                "manifest": manifest,
                "content_hash": content_hash,
                "changelog": changelog,
                "is_latest": True,
            }

            version_result = self.client.table("tool_versions").insert(version_data).execute()
            version_uuid = version_result.data[0]["id"]

            # Insert files if provided
            for file_entry in file_entries:
                file_data = {
                    "tool_version_id": version_uuid,
                    "path": file_entry["path"],
                    "content_text": file_entry["content"],
                    "sha256": file_entry["sha256"],
                    "size_bytes": file_entry["size_bytes"],
                    "is_executable": file_entry["is_executable"],
                }
                self.client.table("tool_version_files").insert(file_data).execute()

            # Create embedding for registry vector search
            await self._create_embedding(
                item_id=tool_id,
                item_type="tool",
                content=f"{tool_id} {manifest.get('name', '')} {description or ''} {manifest.get('description', '')}",
                metadata={"category": category, "version": version, "tool_type": tool_type}
            )

            return {
                "tool_id": tool_id,
                "tool_uuid": tool_uuid,
                "version_uuid": version_uuid,
                "version": version,
                "content_hash": content_hash,
                "status": "published",
            }
        except Exception as e:
            return {"error": "Publish failed", "details": str(e)}

    async def delete(
        self, tool_id: str, version: Optional[str] = None, confirm: bool = False
    ) -> Dict[str, Any]:
        """
        Delete tool or specific version.

        Args:
            tool_id: Tool identifier
            version: Optional specific version (default: all versions)
            confirm: Must be True to actually delete

        Returns:
            Deletion result
        """
        if not self.is_configured:
            return {"error": "Supabase client not initialized"}

        if not confirm:
            return {"error": "Must set confirm=True to delete"}

        try:
            # Get tool
            tool_result = (
                self.client.table("tools")
                .select("id, is_builtin")
                .eq("tool_id", tool_id)
                .single()
                .execute()
            )

            if not tool_result.data:
                return {"error": f"Tool '{tool_id}' not found"}

            tool_uuid = tool_result.data["id"]

            # Prevent deletion of builtins
            if tool_result.data.get("is_builtin"):
                return {"error": f"Cannot delete builtin tool '{tool_id}'"}

            if version:
                # Delete specific version (cascades to files)
                self.client.table("tool_versions").delete().eq("tool_id", tool_uuid).eq(
                    "version", version
                ).execute()

                return {"deleted": True, "tool_id": tool_id, "version": version}
            else:
                # Delete tool (cascades to versions and files)
                self.client.table("tools").delete().eq("id", tool_uuid).execute()
                
                # Delete embedding
                await self._delete_embedding(tool_id)

                return {"deleted": True, "tool_id": tool_id, "all_versions": True}
        except Exception as e:
            return {"error": str(e)}

    async def resolve_chain(self, tool_id: str) -> List[Dict[str, Any]]:
        """
        Resolve executor chain for a tool.

        Args:
            tool_id: Tool identifier

        Returns:
            List of tools in chain from leaf to primitive
        """
        if not self.is_configured:
            return []

        try:
            result = self.client.rpc(
                "resolve_executor_chain", {"p_tool_id": tool_id}
            ).execute()

            return result.data or []
        except Exception as e:
            print(f"Error resolving chain: {e}")
            return []

    async def resolve_chains_batch(self, tool_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Resolve executor chains for multiple tools (avoids N+1).

        Args:
            tool_ids: List of tool identifiers

        Returns:
            Dict mapping tool_id to its chain
        """
        if not self.is_configured:
            return {}

        try:
            result = self.client.rpc(
                "resolve_executor_chains_batch", {"p_tool_ids": tool_ids}
            ).execute()

            # Group by requested_tool_id
            chains: Dict[str, List[Dict[str, Any]]] = {}
            for row in result.data or []:
                req_id = row.get("requested_tool_id")
                if req_id not in chains:
                    chains[req_id] = []
                chains[req_id].append(row)

            return chains
        except Exception as e:
            print(f"Error resolving chains batch: {e}")
            return {}
