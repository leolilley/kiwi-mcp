"""
Directive handler for kiwi-mcp.

Implements search, load, execute operations for directives.
Handles LOCAL file operations directly, only uses registry for REMOTE operations.
"""

from typing import Dict, Any, Optional, List

from kiwi_mcp.handlers import SortBy
import json
import logging
from pathlib import Path
import xml.etree.ElementTree as ET
import re

from kiwi_mcp.api.directive_registry import DirectiveRegistry
from kiwi_mcp.utils.logger import get_logger
from kiwi_mcp.utils.resolvers import DirectiveResolver, get_user_space
from kiwi_mcp.utils.parsers import parse_directive_file
from kiwi_mcp.utils.file_search import search_markdown_files, score_relevance


class DirectiveHandler:
    """Handler for directive operations."""
    
    def __init__(self, project_path: Optional[str] = None):
        """Initialize handler with optional project path."""
        self.project_path = Path(project_path) if project_path else None
        self.logger = get_logger("directive_handler")
        self.registry = DirectiveRegistry()  # Only for remote operations
        
        # Local file handling
        self.resolver = DirectiveResolver(self.project_path)
        self.search_paths = [
            self.resolver.project_directives,
            self.resolver.user_directives
        ]
    
    async def search(
        self,
        query: str,
        source: str = "local",
        limit: int = 10,
        sort_by: SortBy = "score",
        categories: Optional[List[str]] = None,
        subcategories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        tech_stack: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for directives in local files and/or registry.
        
        Args:
            query: Search query (natural language)
            source: "local", "registry", or "all"
            limit: Maximum number of results to return
            sort_by: "score", "success_rate", "date", or "downloads"
            categories: Filter by categories
            subcategories: Filter by subcategories
            tags: Filter by tags
            tech_stack: Filter by tech stack
            date_from: Filter by creation date (ISO format)
            date_to: Filter by creation date (ISO format)
        
        Returns:
            Dict with directives list and metadata
        """
        self.logger.info(f"DirectiveHandler.search: query='{query}', source={source}, limit={limit}")
        
        try:
            results = []
            
            # Search local files
            if source in ("local", "all"):
                local_results = self._search_local(query, categories, subcategories, tags, tech_stack)
                results.extend(local_results)
            
            # Search registry
            if source in ("registry", "all"):
                try:
                    # Registry search only accepts: query, category (singular), limit, tech_stack
                    category_filter = categories[0] if categories and len(categories) > 0 else None
                    
                    registry_results = await self.registry.search(
                        query=query,
                        category=category_filter,
                        limit=limit,
                        tech_stack=tech_stack
                    )
                    
                    # Registry returns list directly, not dict with "results" key
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
                    x.get("name", "").lower(),
                    source_priority.get(x.get("source", ""), 99)
                ))
            else:  # "score" (default)
                results.sort(key=lambda x: (
                    -x.get("score", 0),
                    source_priority.get(x.get("source", ""), 99)
                ))
            
            # Apply limit
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
                "message": "Failed to search directives"
            }
    
    async def load(
        self,
        directive_name: str,
        destination: str = "project",
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load directive from local files or download from registry.
        
        Args:
            directive_name: Name of directive to load
            destination: "project" or "user" (for downloading from registry)
            version: Specific version to load (registry only)
        
        Returns:
            Dict with directive details and metadata
        """
        self.logger.info(f"DirectiveHandler.load: directive={directive_name}, destination={destination}")
        
        try:
            # Try local first
            file_path = self.resolver.resolve(directive_name)
            if file_path:
                directive_data = parse_directive_file(file_path)
                directive_data["source"] = "project" if ".ai/" in str(file_path) else "user"
                directive_data["path"] = str(file_path)
                return directive_data
            
            # Not found locally - try registry if destination specified
            if destination:
                try:
                    result = await self.registry.get(
                        directive_name=directive_name,
                        destination=destination,
                        version=version,
                        project_path=str(self.project_path) if self.project_path else None
                    )
                    return result
                except Exception as e:
                    self.logger.warning(f"Registry get failed: {e}")
            
            return {
                "error": f"Directive '{directive_name}' not found locally",
                "suggestion": "Use search to find it, or specify destination to download from registry"
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": f"Failed to load directive '{directive_name}'"
            }
    
    async def execute(
        self,
        action: str,
        directive_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a directive or perform directive operation.
        
        Args:
            action: "run", "publish", "delete", "create", "update", "link"
            directive_name: Name of directive
            parameters: Directive inputs/parameters
        
        Returns:
            Dict with execution result
        """
        self.logger.info(f"DirectiveHandler.execute: action={action}, directive={directive_name}")
        
        try:
            if action == "run":
                return await self._run_directive(directive_name, parameters or {})
            elif action == "publish":
                return await self._publish_directive(directive_name, parameters or {})
            elif action == "delete":
                return await self._delete_directive(directive_name, parameters or {})
            elif action == "create":
                return await self._create_directive(directive_name, parameters or {})
            elif action == "update":
                return await self._update_directive(directive_name, parameters or {})
            elif action == "link":
                return await self._link_directive(directive_name, parameters or {})
            else:
                return {
                    "error": f"Unknown action: {action}",
                    "supported_actions": ["run", "publish", "delete", "create", "update", "link"]
                }
        except Exception as e:
            return {
                "error": str(e),
                "message": f"Failed to execute action '{action}' on directive '{directive_name}'"
            }
    
    def _search_local(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        subcategories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        tech_stack: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search local directive files."""
        results = []
        query_terms = query.lower().split()
        
        # Search all markdown files in search paths
        files = search_markdown_files(self.search_paths)
        
        for file_path in files:
            try:
                directive = parse_directive_file(file_path)
                
                # Calculate relevance score
                searchable_text = f"{directive['name']} {directive['description']}"
                score = score_relevance(searchable_text, query_terms)
                
                if score > 0:
                    # Determine source by checking if file is in project or user directives
                    is_project = str(file_path).startswith(str(self.resolver.project_directives))
                    
                    results.append({
                        "name": directive["name"],
                        "description": directive["description"],
                        "version": directive["version"],
                        "score": score,
                        "source": "project" if is_project else "user",
                        "path": str(file_path)
                    })
            except Exception as e:
                self.logger.warning(f"Error parsing {file_path}: {e}")
        
        return results
    
    async def _run_directive(
        self,
        directive_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Load and return directive for agent to execute."""
        # Find local directive file
        file_path = self.resolver.resolve(directive_name)
        if not file_path:
            return {
                "error": f"Directive '{directive_name}' not found locally",
                "suggestion": "Use load() to download from registry first"
            }
        
        # Parse directive file
        try:
            directive_data = parse_directive_file(file_path)
            
            return {
                "status": "ready",
                "directive": {
                    "name": directive_data["name"],
                    "version": directive_data["version"],
                    "description": directive_data["description"],
                    "content": directive_data["content"],
                    "parsed": directive_data["parsed"],
                    "source": "project" if str(file_path).startswith(str(self.resolver.project_directives)) else "user"
                },
                "inputs": params,
                "instructions": (
                    "Status 'ready' means the directive is loaded and ready for YOU to execute. "
                    "Read the directive's <process> section and follow each step."
                )
            }
        except Exception as e:
            return {
                "error": f"Failed to parse directive: {str(e)}",
                "path": str(file_path)
            }
    
    async def _publish_directive(
        self,
        directive_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Publish directive to registry."""
        version = params.get("version")
        if not version:
            return {
                "error": "version is required for publish",
                "example": "parameters={'version': '1.0.0'}"
            }
        
        # Find local directive file
        file_path = self.resolver.resolve(directive_name)
        if not file_path:
            return {
                "error": f"Directive '{directive_name}' not found locally",
                "suggestion": "Create directive first before publishing"
            }
        
        # Parse directive to get content and metadata
        directive_data = parse_directive_file(file_path)
        
        # Use registry publish method
        result = await self.registry.publish(
            name=directive_name,
            version=version,
            content=directive_data.get("content", ""),
            category=directive_data.get("category", "custom"),
            description=directive_data.get("description", ""),
            tech_stack=directive_data.get("tech_stack", [])
        )
        return result
    
    async def _delete_directive(
        self, 
        directive_name: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delete directive from local and/or registry."""
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
            file_path = self.resolver.resolve(directive_name)
            if file_path:
                file_path.unlink()
                deleted.append("local")
        
        # Delete from registry
        if source in ("registry", "all"):
            try:
                await self.registry.delete(
                    directive_name=directive_name,
                    source="registry",
                    project_path=str(self.project_path) if self.project_path else None
                )
                deleted.append("registry")
            except Exception as e:
                self.logger.warning(f"Registry delete failed: {e}")
        
        if not deleted:
            return {
                "error": f"Directive '{directive_name}' not found in specified location(s)"
            }
        
        return {
            "status": "deleted",
            "name": directive_name,
            "deleted_from": deleted
        }
    
    async def _create_directive(
        self,
        directive_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new directive with validation."""
        content = params.get("content")
        if not content:
            return {
                "error": "content is required",
                "required": {"content": "Markdown content with XML directive"},
                "example": "parameters={'content': '# My Directive\\n\\n```xml\\n<directive...', 'location': 'project'}"
            }
        
        location = params.get("location", "project")
        if location not in ("project", "user"):
            return {
                "error": f"Invalid location: {location}",
                "valid_locations": ["project", "user"]
            }
        
        # Validate XML can be parsed
        try:
            xml_match = re.search(r'```xml\n(.*?)\n```', content, re.DOTALL)
            if not xml_match:
                return {
                    "error": "No XML directive found in content",
                    "hint": "Content must contain XML directive wrapped in ```xml``` code block"
                }
            
            xml_content = xml_match.group(1)
            ET.fromstring(xml_content)  # Validate XML syntax
            
        except ET.ParseError as e:
            return {
                "error": "Invalid directive XML",
                "parse_error": str(e),
                "hint": "Check for unescaped < > & characters. Use CDATA for special chars."
            }
        except Exception as e:
            return {
                "error": "Failed to validate directive",
                "details": str(e)
            }
        
        # Save to file
        if location == "project":
            if not self.project_path:
                return {
                    "error": "project_path required for location='project'",
                    "suggestion": "Provide project_path or use location='user'"
                }
            base_dir = self.project_path / ".ai" / "directives"
        else:
            base_dir = get_user_space() / "directives"
        
        category = params.get("category", "custom")
        save_dir = base_dir / category
        save_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = save_dir / f"{directive_name}.md"
        
        if file_path.exists():
            return {
                "error": f"Directive '{directive_name}' already exists",
                "path": str(file_path),
                "suggestion": "Use 'update' action to modify existing directive"
            }
        
        file_path.write_text(content)
        
        return {
            "status": "created",
            "name": directive_name,
            "path": str(file_path),
            "location": location,
            "category": category,
            "validated": True
        }
    
    async def _update_directive(
        self,
        directive_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update existing directive with validation."""
        content = params.get("content")
        if not content:
            return {
                "error": "content is required for update",
                "required": {"content": "Updated markdown content with XML"}
            }
        
        # Find existing file
        file_path = self.resolver.resolve(directive_name)
        if not file_path:
            return {
                "error": f"Directive '{directive_name}' not found",
                "suggestion": "Use 'create' action for new directives"
            }
        
        # Validate new content
        try:
            xml_match = re.search(r'```xml\n(.*?)\n```', content, re.DOTALL)
            if not xml_match:
                return {
                    "error": "No XML directive found in content",
                    "hint": "Content must contain XML directive wrapped in ```xml``` code block"
                }
            
            xml_content = xml_match.group(1)
            ET.fromstring(xml_content)  # Validate XML syntax
            
        except ET.ParseError as e:
            return {
                "error": "Invalid directive XML",
                "parse_error": str(e),
                "hint": "Check for unescaped < > & characters. Use CDATA for special chars."
            }
        
        # Update file
        file_path.write_text(content)
        
        return {
            "status": "updated",
            "name": directive_name,
            "path": str(file_path),
            "validated": True
        }
    
    async def _link_directive(
        self,
        directive_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Link two directives together."""
        to_id = params.get("to")
        if not to_id:
            return {
                "error": "to is required (target directive name)",
                "example": "parameters={'to': 'other_directive', 'relationship': 'requires'}"
            }
        
        relationship = params.get("relationship", "related")
        valid_relationships = ["requires", "suggests", "extends", "related"]
        
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
        links_file = metadata_dir / "directive_links.json"
        
        # Load existing links
        if links_file.exists():
            links_data = json.loads(links_file.read_text())
        else:
            links_data = {"directive_links": []}
        
        # Add new link
        new_link = {
            "from": directive_name,
            "to": to_id,
            "relationship": relationship
        }
        
        # Check if link already exists
        existing = [
            l for l in links_data.get("directive_links", [])
            if l["from"] == directive_name and l["to"] == to_id
        ]
        
        if existing:
            # Update existing link
            for link in links_data["directive_links"]:
                if link["from"] == directive_name and link["to"] == to_id:
                    link["relationship"] = relationship
        else:
            # Add new link
            if "directive_links" not in links_data:
                links_data["directive_links"] = []
            links_data["directive_links"].append(new_link)
        
        # Save links
        links_file.write_text(json.dumps(links_data, indent=2))
        
        return {
            "status": "linked",
            "from": directive_name,
            "to": to_id,
            "relationship": relationship,
            "storage": str(links_file)
        }
