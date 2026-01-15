"""
Knowledge handler for kiwi-mcp.

Implements search, load, execute operations for knowledge entries.
Handles LOCAL file operations directly, only uses registry for REMOTE operations.
"""

from typing import Dict, Any, Optional, List

from kiwi_mcp.handlers import SortBy
import json
from pathlib import Path

from kiwi_mcp.api.knowledge_registry import KnowledgeRegistry
from kiwi_mcp.utils.logger import get_logger
from kiwi_mcp.utils.resolvers import KnowledgeResolver, get_user_space
from kiwi_mcp.utils.parsers import parse_knowledge_entry
from kiwi_mcp.utils.file_search import search_markdown_files, score_relevance


class KnowledgeHandler:
    """Handler for knowledge operations."""
    
    def __init__(self, project_path: Optional[str] = None):
        """Initialize handler with optional project path."""
        self.project_path = Path(project_path) if project_path else None
        self.logger = get_logger("knowledge_handler")
        self.registry = KnowledgeRegistry()  # Only for remote operations
        
        # Local file handling
        self.resolver = KnowledgeResolver(self.project_path)
        self.search_paths = [
            self.resolver.project_knowledge,
            self.resolver.user_knowledge
        ]
    
    async def search(
        self,
        query: str,
        source: str = "local",
        category: Optional[str] = None,
        entry_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
        sort_by: SortBy = "score"
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
        self.logger.info(f"KnowledgeHandler.search: query='{query}', source={source}, limit={limit}")
        
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
                        limit=limit
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
                results.sort(key=lambda x: (
                    x.get("updated_at") or x.get("created_at") or "",
                    source_priority.get(x.get("source", ""), 99)
                ), reverse=True)
            elif sort_by == "name":
                results.sort(key=lambda x: (
                    x.get("name", x.get("zettel_id", "")).lower(),
                    source_priority.get(x.get("source", ""), 99)
                ))
            else:  # "score" (default)
                results.sort(key=lambda x: (
                    -x.get("score", 0),
                    source_priority.get(x.get("source", ""), 99)
                ))
            
            results = results[:limit]
            
            return {
                "query": query,
                "source": source,
                "results": results,
                "total": len(results)
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to search knowledge entries"
            }
    
    async def load(
        self,
        zettel_id: str,
        destination: str = "project",
        include_relationships: bool = False
    ) -> Dict[str, Any]:
        """
        Load knowledge entry from local files or download from registry.
        
        Args:
            zettel_id: Entry ID to load
            destination: "project", "user", or both (when getting from registry)
            include_relationships: Include linked entries
        
        Returns:
            Dict with entry content and metadata
        """
        try:
            # Try local first
            file_path = self.resolver.resolve(zettel_id)
            if file_path:
                entry_data = parse_knowledge_entry(file_path)
                entry_data["source"] = "project" if ".ai/" in str(file_path) else "user"
                entry_data["path"] = str(file_path)
                return entry_data
            
            # Not found locally - try registry if destination specified
            if destination:
                try:
                    result = await self.registry.get(
                        zettel_id=zettel_id,
                        destination=destination,
                        include_relationships=include_relationships,
                        project_path=str(self.project_path) if self.project_path else None
                    )
                    return result
                except Exception as e:
                    self.logger.warning(f"Registry get failed: {e}")
            
            return {
                "error": f"Knowledge entry '{zettel_id}' not found locally",
                "suggestion": "Use search to find it, or specify destination to download from registry"
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": f"Failed to load entry '{zettel_id}'"
            }
    
    async def execute(
        self,
        action: str,
        zettel_id: str,
        parameters: Optional[Dict[str, Any]] = None
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
            elif action == "link":
                return await self._link_knowledge(zettel_id, params)
            elif action == "publish":
                return await self._publish_knowledge(zettel_id, params)
            else:
                return {
                    "error": f"Unknown action: {action}",
                    "supported_actions": ["run", "create", "update", "delete", "link", "publish"]
                }
        except Exception as e:
            return {
                "error": str(e),
                "message": f"Failed to execute action '{action}' on entry '{zettel_id}'"
            }
    
    def _search_local(
        self,
        query: str,
        category: Optional[str] = None,
        entry_type: Optional[str] = None,
        tags: Optional[List[str]] = None
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
                    
                    results.append({
                        "zettel_id": entry["zettel_id"],
                        "title": entry["title"],
                        "entry_type": entry["entry_type"],
                        "category": entry["category"],
                        "tags": entry["tags"],
                        "score": score,
                        "source": "project" if is_project else "user",
                        "path": str(file_path)
                    })
            except Exception as e:
                self.logger.warning(f"Error parsing {file_path}: {e}")
        
        return results
    
    async def _run_knowledge(
        self,
        zettel_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Load and return knowledge content for agent to use."""
        # Find local knowledge entry
        file_path = self.resolver.resolve(zettel_id)
        if not file_path:
            return {
                "error": f"Knowledge entry '{zettel_id}' not found locally",
                "suggestion": "Use load() to download from registry first"
            }
        
        # Parse entry file
        try:
            entry_data = parse_knowledge_entry(file_path)
            
            return {
                "status": "ready",
                "action": "run",
                "zettel_id": entry_data["zettel_id"],
                "title": entry_data["title"],
                "content": entry_data["content"],
                "entry_type": entry_data["entry_type"],
                "category": entry_data["category"],
                "tags": entry_data["tags"],
                "source": "project" if str(file_path).startswith(str(self.resolver.project_knowledge)) else "user",
                "instructions": "Use this knowledge to inform your decisions."
            }
        except Exception as e:
            return {
                "error": f"Failed to parse knowledge entry: {str(e)}",
                "path": str(file_path)
            }
    
    async def _create_knowledge(
        self,
        zettel_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new knowledge entry."""
        title = params.get("title")
        content = params.get("content")
        
        if not title or not content:
            return {
                "error": "title and content are required",
                "required": {"title": "Entry title", "content": "Markdown content"},
                "example": "parameters={'title': 'My Note', 'content': '...', 'location': 'project'}"
            }
        
        location = params.get("location", "project")
        if location not in ("project", "user"):
            return {
                "error": f"Invalid location: {location}",
                "valid_locations": ["project", "user"]
            }
        
        # Save to file
        if location == "project":
            if not self.project_path:
                return {
                    "error": "project_path required for location='project'",
                    "suggestion": "Provide project_path or use location='user'"
                }
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
                "suggestion": "Use 'update' action to modify existing entry"
            }
        
        # Create markdown content with YAML frontmatter
        tags = params.get("tags", [])
        frontmatter = f"""---
zettel_id: {zettel_id}
title: {title}
entry_type: {entry_type}
category: {category}
tags: {json.dumps(tags)}
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
            "entry_type": entry_type
        }
    
    async def _update_knowledge(
        self,
        zettel_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update existing knowledge entry."""
        # Find existing file
        file_path = self.resolver.resolve(zettel_id)
        if not file_path:
            return {
                "error": f"Knowledge entry '{zettel_id}' not found",
                "suggestion": "Use 'create' action for new entries"
            }
        
        # Parse existing entry
        try:
            entry_data = parse_knowledge_entry(file_path)
        except Exception as e:
            return {
                "error": f"Failed to parse existing entry: {str(e)}",
                "path": str(file_path)
            }
        
        # Update fields
        title = params.get("title", entry_data.get("title"))
        content = params.get("content", entry_data.get("content"))
        entry_type = params.get("entry_type", entry_data.get("entry_type"))
        category = params.get("category", entry_data.get("category"))
        tags = params.get("tags", entry_data.get("tags", []))
        
        # Recreate frontmatter
        frontmatter = f"""---
zettel_id: {zettel_id}
title: {title}
entry_type: {entry_type}
category: {category}
tags: {json.dumps(tags)}
---

"""
        full_content = frontmatter + content
        file_path.write_text(full_content)
        
        return {
            "status": "updated",
            "zettel_id": zettel_id,
            "path": str(file_path)
        }
    
    async def _delete_knowledge(
        self,
        zettel_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delete knowledge entry from local and/or registry."""
        if not params.get("confirm"):
            return {
                "error": "Delete requires confirmation",
                "required": {"confirm": True},
                "example": "parameters={'confirm': True, 'source': 'local'}"
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
                    project_path=str(self.project_path) if self.project_path else None
                )
                deleted.append("registry")
            except Exception as e:
                self.logger.warning(f"Registry delete failed: {e}")
        
        if not deleted:
            return {
                "error": f"Knowledge entry '{zettel_id}' not found in specified location(s)"
            }
        
        return {
            "status": "deleted",
            "zettel_id": zettel_id,
            "deleted_from": deleted
        }
    
    async def _link_knowledge(
        self,
        zettel_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Link two knowledge entries together."""
        to_id = params.get("to")
        if not to_id:
            return {
                "error": "to is required (target entry ID)",
                "example": "parameters={'to': 'other_entry', 'relationship': 'references'}"
            }
        
        relationship = params.get("relationship", "related")
        valid_relationships = ["references", "contradicts", "extends", "implements", "supersedes", "depends_on", "related", "example_of"]
        
        if relationship not in valid_relationships:
            return {
                "error": f"Invalid relationship: {relationship}",
                "valid_relationships": valid_relationships
            }
        
        # Store link in local JSON file
        if self.project_path:
            metadata_dir = self.project_path / ".ai" / "metadata"
        else:
            metadata_dir = get_user_space() / "metadata"
        
        metadata_dir.mkdir(parents=True, exist_ok=True)
        links_file = metadata_dir / "knowledge_links.json"
        
        # Load existing links
        if links_file.exists():
            links_data = json.loads(links_file.read_text())
        else:
            links_data = {"knowledge_links": []}
        
        # Add new link
        new_link = {
            "from": zettel_id,
            "to": to_id,
            "relationship": relationship
        }
        
        # Check if link already exists
        existing = [
            l for l in links_data.get("knowledge_links", [])
            if l["from"] == zettel_id and l["to"] == to_id
        ]
        
        if existing:
            # Update existing link
            for link in links_data["knowledge_links"]:
                if link["from"] == zettel_id and link["to"] == to_id:
                    link["relationship"] = relationship
        else:
            # Add new link
            if "knowledge_links" not in links_data:
                links_data["knowledge_links"] = []
            links_data["knowledge_links"].append(new_link)
        
        # Save links
        links_file.write_text(json.dumps(links_data, indent=2))
        
        return {
            "status": "linked",
            "from": zettel_id,
            "to": to_id,
            "relationship": relationship,
            "storage": str(links_file)
        }
    
    async def _publish_knowledge(
        self,
        zettel_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Publish knowledge entry to registry."""
        version = params.get("version")
        if not version:
            return {
                "error": "version is required for publish",
                "example": "parameters={'version': '1.0.0'}"
            }
        
        # Find local entry file
        file_path = self.resolver.resolve(zettel_id)
        if not file_path:
            return {
                "error": f"Knowledge entry '{zettel_id}' not found locally",
                "suggestion": "Create entry first before publishing"
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
            tags=tags
        )
        return result
