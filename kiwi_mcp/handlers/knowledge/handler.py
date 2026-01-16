"""
Knowledge handler for kiwi-mcp.

Implements search, load, execute operations for knowledge entries.
Handles LOCAL file operations directly, only uses registry for REMOTE operations.
"""

from typing import Dict, Any, Optional, List, Literal

from kiwi_mcp.handlers import SortBy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from kiwi_mcp.api.knowledge_registry import KnowledgeRegistry
from kiwi_mcp.utils.logger import get_logger
from kiwi_mcp.utils.resolvers import KnowledgeResolver, get_user_space
from kiwi_mcp.utils.parsers import parse_knowledge_entry
from kiwi_mcp.utils.file_search import search_markdown_files, score_relevance


class KnowledgeHandler:
    """Handler for knowledge operations."""

    def __init__(self, project_path: str):
        """Initialize handler with project path."""
        self.project_path = Path(project_path)
        self.logger = get_logger("knowledge_handler")
        self.registry = KnowledgeRegistry()  # Only for remote operations

        # Local file handling
        self.resolver = KnowledgeResolver(self.project_path)
        self.search_paths = [self.resolver.project_knowledge, self.resolver.user_knowledge]

    async def search(
        self,
        query: str,
        source: str = "local",
        category: Optional[str] = None,
        entry_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
        sort_by: SortBy = "score",
    ) -> Dict[str, Any]:
        """
        Search knowledge entries in local files and/or registry.

        Args:
            query: Search query (natural language)
            source: "local", "registry", or "all"
            category: Optional category filter
            entry_type: Optional entry type filter
            tags: Optional tags filter
            limit: Max results
            sort_by: "score" or "date"

        Returns:
            Dict with entries list and metadata
        """
        self.logger.info(
            f"KnowledgeHandler.search: query='{query}', source={source}, limit={limit}"
        )

        try:
            results = []

            # Search local files
            if source in ("local", "all"):
                local_results = self._search_local(query, category, entry_type, tags)
                results.extend(local_results)

            # Search registry
            if source in ("registry", "all"):
                try:
                    # Registry search accepts: query, category, entry_type, tags, limit
                    registry_results = await self.registry.search(
                        query=query,
                        category=category,
                        entry_type=entry_type,
                        tags=tags,
                        limit=limit,
                    )

                    # Registry returns list directly
                    if isinstance(registry_results, list):
                        for item in registry_results:
                            item["source"] = "registry"
                        results.extend(registry_results)
                except Exception as e:
                    self.logger.warning(f"Registry search failed: {e}")

            # Sort results based on sort_by parameter
            source_priority = {"project": 0, "user": 1, "registry": 2}

            if sort_by == "date":
                results.sort(
                    key=lambda x: (
                        x.get("updated_at") or x.get("created_at") or "",
                        source_priority.get(x.get("source", ""), 99),
                    ),
                    reverse=True,
                )
            elif sort_by == "name":
                results.sort(
                    key=lambda x: (
                        x.get("name", x.get("zettel_id", "")).lower(),
                        source_priority.get(x.get("source", ""), 99),
                    )
                )
            else:  # "score" (default)
                results.sort(
                    key=lambda x: (-x.get("score", 0), source_priority.get(x.get("source", ""), 99))
                )

            results = results[:limit]

            return {"query": query, "source": source, "results": results, "total": len(results)}
        except Exception as e:
            return {"error": str(e), "message": "Failed to search knowledge entries"}

    async def load(
        self,
        zettel_id: str,
        source: Literal["project", "user", "registry"],
        destination: Optional[Literal["project", "user"]] = None,
        include_relationships: bool = False,
    ) -> Dict[str, Any]:
        """
        Load knowledge entry from specified source.

        Args:
            zettel_id: Entry ID to load
            source: Where to load from - "project" | "user" | "registry"
            destination: Where to copy to (optional). If None or same as source, read-only mode.
            include_relationships: Include linked entries

        Returns:
            Dict with entry content and metadata
        """
        self.logger.info(
            f"KnowledgeHandler.load: zettel={zettel_id}, source={source}, destination={destination}"
        )

        try:
            # Determine if this is read-only mode (no copy)
            # Read-only when: destination is None OR destination equals source (for non-registry)
            is_read_only = destination is None or (source == destination and source != "registry")
            
            # LOAD FROM REGISTRY
            if source == "registry":
                # For registry, default destination to "project" if not specified
                effective_destination = destination or "project"
                
                result = await self.registry.get(
                    zettel_id=zettel_id,
                    destination=effective_destination,
                    include_relationships=include_relationships,
                    project_path=str(self.project_path) if self.project_path else None,
                )
                if result:
                    result["source"] = "registry"
                    result["destination"] = effective_destination
                return result

            # LOAD FROM PROJECT
            if source == "project":
                search_base = self.project_path / ".ai" / "knowledge"
                file_path = self._find_entry_in_path(zettel_id, search_base)
                if not file_path:
                    return {"error": f"Knowledge entry '{zettel_id}' not found in project"}

                # If destination differs from source, copy the file
                if destination == "user":
                    # Copy from project to user space
                    content = file_path.read_text()
                    # Determine category from source path
                    relative_path = file_path.relative_to(search_base)
                    target_path = get_user_space() / "knowledge" / relative_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(content)
                    self.logger.info(f"Copied knowledge entry from project to user: {target_path}")

                    entry_data = parse_knowledge_entry(target_path)
                    entry_data["source"] = "project"
                    entry_data["destination"] = "user"
                    entry_data["path"] = str(target_path)
                    return entry_data
                else:
                    # Read-only mode: just return project file info (no copy)
                    entry_data = parse_knowledge_entry(file_path)
                    entry_data["source"] = "project"
                    entry_data["path"] = str(file_path)
                    entry_data["mode"] = "read_only"
                    return entry_data

            # LOAD FROM USER
            # source == "user" (only remaining option due to Literal typing)
            search_base = get_user_space() / "knowledge"
            file_path = self._find_entry_in_path(zettel_id, search_base)
            if not file_path:
                return {"error": f"Knowledge entry '{zettel_id}' not found in user space"}

            # If destination differs from source, copy the file
            if destination == "project":
                # Copy from user to project space
                content = file_path.read_text()
                # Determine category from source path
                relative_path = file_path.relative_to(search_base)
                target_path = self.project_path / ".ai" / "knowledge" / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content)
                self.logger.info(f"Copied knowledge entry from user to project: {target_path}")

                entry_data = parse_knowledge_entry(target_path)
                entry_data["source"] = "user"
                entry_data["destination"] = "project"
                entry_data["path"] = str(target_path)
                return entry_data
            else:
                # Read-only mode: just return user file info (no copy)
                entry_data = parse_knowledge_entry(file_path)
                entry_data["source"] = "user"
                entry_data["path"] = str(file_path)
                entry_data["mode"] = "read_only"
                return entry_data
        except Exception as e:
            return {"error": str(e), "message": f"Failed to load entry '{zettel_id}'"}

    def _find_entry_in_path(self, zettel_id: str, base_path: Path) -> Optional[Path]:
        """Find knowledge entry file in specified path."""
        if not base_path.exists():
            return None

        # Search recursively for the entry
        for md_file in base_path.rglob(f"{zettel_id}.md"):
            return md_file

        # Also try with wildcards in case of naming variations
        for md_file in base_path.rglob("*.md"):
            if zettel_id in md_file.stem:
                return md_file

        return None

    async def execute(
        self, action: str, zettel_id: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a knowledge operation.

        Args:
            action: "run", "create", "update", "delete", "link", "publish"
            zettel_id: Entry ID
            parameters: Action parameters (title, content, etc.)

        Returns:
            Dict with operation result
        """
        try:
            params = parameters or {}

            if action == "run":
                return await self._run_knowledge(zettel_id, params)
            elif action == "create":
                return await self._create_knowledge(zettel_id, params)
            elif action == "update":
                return await self._update_knowledge(zettel_id, params)
            elif action == "delete":
                return await self._delete_knowledge(zettel_id, params)
            elif action == "publish":
                return await self._publish_knowledge(zettel_id, params)
            else:
                return {
                    "error": f"Unknown action: {action}",
                    "supported_actions": ["run", "create", "update", "delete", "publish"],
                }
        except Exception as e:
            return {
                "error": str(e),
                "message": f"Failed to execute action '{action}' on entry '{zettel_id}'",
            }

    def _verify_knowledge_signature(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Verify knowledge entry signature if present.

        Returns None if no signature, or a dict with status:
        - "valid": hash matches
        - "modified": hash doesn't match
        - "invalid": signature format is wrong
        """
        content = file_path.read_text()

        # Extract YAML frontmatter
        if not content.startswith("---"):
            return None  # No frontmatter, no signature

        end_idx = content.find("---", 3)
        if end_idx == -1:
            return None

        yaml_content = content[3:end_idx].strip()

        # Parse frontmatter for signature fields
        stored_timestamp = None
        stored_hash = None

        for line in yaml_content.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key == "validated_at":
                    stored_timestamp = value
                elif key == "content_hash":
                    stored_hash = value

        if not stored_timestamp or not stored_hash:
            return None  # No signature fields

        # Extract content (after frontmatter) to compute current hash
        entry_content = content[end_idx + 3 :].strip()
        current_hash = hashlib.sha256(entry_content.encode()).hexdigest()[:12]

        if current_hash == stored_hash:
            return {"status": "valid", "validated_at": stored_timestamp, "hash": stored_hash}
        else:
            return {
                "status": "modified",
                "validated_at": stored_timestamp,
                "original_hash": stored_hash,
                "current_hash": current_hash,
                "warning": "Content modified since last validation. Consider running 'update' to re-validate.",
            }

    def _search_local(
        self,
        query: str,
        category: Optional[str] = None,
        entry_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Search local knowledge entry files."""
        results = []
        query_terms = query.lower().split()

        # Search all markdown files in search paths
        files = search_markdown_files(self.search_paths)

        for file_path in files:
            try:
                entry = parse_knowledge_entry(file_path)

                # Calculate relevance score
                searchable_text = f"{entry['title']} {entry['content']}"
                score = score_relevance(searchable_text, query_terms)

                if score > 0:
                    # Determine source by checking if file is in project or user knowledge
                    is_project = str(file_path).startswith(str(self.resolver.project_knowledge))

                    results.append(
                        {
                            "zettel_id": entry["zettel_id"],
                            "title": entry["title"],
                            "entry_type": entry["entry_type"],
                            "category": entry["category"],
                            "tags": entry["tags"],
                            "score": score,
                            "source": "project" if is_project else "user",
                            "path": str(file_path),
                        }
                    )
            except Exception as e:
                self.logger.warning(f"Error parsing {file_path}: {e}")

        return results

    async def _run_knowledge(self, zettel_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Load and return knowledge content for agent to use."""
        # Find local knowledge entry
        file_path = self.resolver.resolve(zettel_id)
        if not file_path:
            return {
                "error": f"Knowledge entry '{zettel_id}' not found locally",
                "suggestion": "Use load() to download from registry first",
            }

        # ENFORCE hash validation - ALWAYS check, never skip
        signature_status = self._verify_knowledge_signature(file_path)

        # Block execution if signature is invalid or modified
        if signature_status:
            if signature_status.get("status") == "modified":
                return {
                    "status": "error",
                    "error": "Knowledge entry content has been modified since last validation",
                    "signature": signature_status,
                    "path": str(file_path),
                    "solution": "Run 'update' action to re-validate the entry",
                }
            elif signature_status.get("status") == "invalid":
                return {
                    "status": "error",
                    "error": "Knowledge entry signature is invalid",
                    "signature": signature_status,
                    "path": str(file_path),
                    "solution": "Run 'update' action to re-validate the entry",
                }

        # Parse entry file
        try:
            entry_data = parse_knowledge_entry(file_path)

            # Return content for decision making
            return {
                "status": "ready",
                "title": entry_data["title"],
                "content": entry_data["content"],
                "instructions": "Use this knowledge to inform your decisions.",
            }
        except Exception as e:
            return {"error": f"Failed to parse knowledge entry: {str(e)}", "path": str(file_path)}

    async def _create_knowledge(self, zettel_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new knowledge entry."""
        title = params.get("title")
        content = params.get("content")

        if not title or not content:
            return {
                "error": "title and content are required",
                "required": {"title": "Entry title", "content": "Markdown content"},
                "example": "parameters={'title': 'My Note', 'content': '...', 'location': 'project'}",
            }

        location = params.get("location", "project")
        if location not in ("project", "user"):
            return {
                "error": f"Invalid location: {location}",
                "valid_locations": ["project", "user"],
            }

        # Save to file
        if location == "project":
            base_dir = self.project_path / ".ai" / "knowledge"
        else:
            base_dir = get_user_space() / "knowledge"

        entry_type = params.get("entry_type", "learning")
        category = params.get("category", entry_type + "s")
        save_dir = base_dir / category
        save_dir.mkdir(parents=True, exist_ok=True)

        file_path = save_dir / f"{zettel_id}.md"

        if file_path.exists():
            return {
                "error": f"Knowledge entry '{zettel_id}' already exists",
                "path": str(file_path),
                "suggestion": "Use 'update' action to modify existing entry",
            }

        # Generate signature for validated content
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Create markdown content with YAML frontmatter (including signature)
        tags = params.get("tags", [])
        frontmatter = f"""---
zettel_id: {zettel_id}
title: {title}
entry_type: {entry_type}
category: {category}
tags: {json.dumps(tags)}
validated_at: {timestamp}
content_hash: {content_hash}
---

"""
        full_content = frontmatter + content
        file_path.write_text(full_content)

        return {
            "status": "created",
            "zettel_id": zettel_id,
            "path": str(file_path),
            "location": location,
            "category": category,
            "entry_type": entry_type,
            "signature": {"hash": content_hash, "timestamp": timestamp},
        }

    async def _update_knowledge(self, zettel_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing knowledge entry."""
        # Find existing file
        file_path = self.resolver.resolve(zettel_id)
        if not file_path:
            return {
                "error": f"Knowledge entry '{zettel_id}' not found",
                "suggestion": "Use 'create' action for new entries",
            }

        # Parse existing entry
        try:
            entry_data = parse_knowledge_entry(file_path)
        except Exception as e:
            return {"error": f"Failed to parse existing entry: {str(e)}", "path": str(file_path)}

        # Update fields
        title = params.get("title", entry_data.get("title"))
        content = params.get("content", entry_data.get("content"))
        entry_type = params.get("entry_type", entry_data.get("entry_type"))
        category = params.get("category", entry_data.get("category"))
        tags = params.get("tags", entry_data.get("tags", []))

        # Generate new signature for validated content
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Recreate frontmatter with signature
        frontmatter = f"""---
zettel_id: {zettel_id}
title: {title}
entry_type: {entry_type}
category: {category}
tags: {json.dumps(tags)}
validated_at: {timestamp}
content_hash: {content_hash}
---

"""
        full_content = frontmatter + content
        file_path.write_text(full_content)

        return {
            "status": "updated",
            "zettel_id": zettel_id,
            "path": str(file_path),
            "signature": {"hash": content_hash, "timestamp": timestamp},
        }

    async def _delete_knowledge(self, zettel_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete knowledge entry from local and/or registry."""
        if not params.get("confirm"):
            return {
                "error": "Delete requires confirmation",
                "required": {"confirm": True},
                "example": "parameters={'confirm': True, 'source': 'local'}",
            }

        source = params.get("source", "all")
        deleted = []

        # Delete local
        if source in ("local", "all"):
            file_path = self.resolver.resolve(zettel_id)
            if file_path:
                file_path.unlink()
                deleted.append("local")

        # Delete from registry
        if source in ("registry", "all"):
            try:
                await self.registry.delete(
                    zettel_id=zettel_id,
                    source="registry",
                    project_path=str(self.project_path) if self.project_path else None,
                )
                deleted.append("registry")
            except Exception as e:
                self.logger.warning(f"Registry delete failed: {e}")

        if not deleted:
            return {"error": f"Knowledge entry '{zettel_id}' not found in specified location(s)"}

        return {"status": "deleted", "zettel_id": zettel_id, "deleted_from": deleted}

    async def _publish_knowledge(self, zettel_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Publish knowledge entry to registry."""
        version = params.get("version")
        if not version:
            return {
                "error": "version is required for publish",
                "example": "parameters={'version': '1.0.0'}",
            }

        # Find local entry file
        file_path = self.resolver.resolve(zettel_id)
        if not file_path:
            return {
                "error": f"Knowledge entry '{zettel_id}' not found locally",
                "suggestion": "Create entry first before publishing",
            }

        # Parse entry to get content and metadata
        entry_data = parse_knowledge_entry(file_path)

        # Ensure tags is a list
        tags = entry_data.get("tags", [])
        if isinstance(tags, str):
            # Split comma-separated tags or treat as single tag
            tags = [t.strip() for t in tags.split(",")] if "," in tags else ([tags] if tags else [])
        elif not isinstance(tags, list):
            tags = []

        # Use registry publish method
        result = await self.registry.publish(
            zettel_id=zettel_id,
            title=entry_data.get("title", zettel_id),
            content=entry_data.get("content", ""),
            entry_type=entry_data.get("entry_type", "note"),
            version=version,
            category=entry_data.get("category", ""),
            tags=tags,
        )
        return result
