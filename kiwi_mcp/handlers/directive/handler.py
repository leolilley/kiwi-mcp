"""
Directive handler for kiwi-mcp.

Implements search, load, execute operations for directives.
Handles LOCAL file operations directly, only uses registry for REMOTE operations.
"""

from typing import Dict, Any, Optional, List, Literal

from kiwi_mcp.handlers import SortBy
import hashlib
from datetime import datetime, timezone
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
        source: Literal["project", "user", "registry"],
        destination: Literal["project", "user"],
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load directive from specified source.
        
        Args:
            directive_name: Name of directive to load
            source: Where to load from - "project" | "user" | "registry"
            destination: Where to save/return from - "project" | "user"
            version: Specific version to load (registry only)
        
        Returns:
            Dict with directive details and metadata
        """
        self.logger.info(f"DirectiveHandler.load: directive={directive_name}, source={source}, destination={destination}")
        
        try:
            # LOAD FROM REGISTRY
            if source == "registry":
                # Fetch from registry
                registry_data = await self.registry.get(
                    name=directive_name,
                    version=version
                )
                
                if not registry_data:
                    return {
                        "error": f"Directive '{directive_name}' not found in registry"
                    }
                
                # Extract metadata
                content = registry_data.get("content")
                category = registry_data.get("category", "core")
                subcategory = registry_data.get("subcategory")
                
                if not content:
                    return {
                        "error": f"Directive '{directive_name}' has no content"
                    }
                
                # Determine target path based on destination
                if destination == "user":
                    base_path = Path.home() / ".ai" / "directives"
                else:  # destination == "project"
                    if not self.project_path:
                        return {
                            "error": "project_path is required for destination='project'"
                        }
                    base_path = self.project_path / ".ai" / "directives"
                
                # Build category path
                if subcategory:
                    target_dir = base_path / category / subcategory
                else:
                    target_dir = base_path / category
                
                # Create directory if needed
                target_dir.mkdir(parents=True, exist_ok=True)
                
                # Write file
                target_path = target_dir / f"{directive_name}.md"
                target_path.write_text(content)
                
                self.logger.info(f"Downloaded directive from registry to: {target_path}")
                
                # Parse and return
                directive_data = parse_directive_file(target_path)
                directive_data["source"] = "registry"
                directive_data["destination"] = destination
                directive_data["path"] = str(target_path)
                return directive_data
            
            # LOAD FROM PROJECT
            if source == "project":
                if not self.project_path:
                    return {
                        "error": "project_path is required for source='project'"
                    }
                search_base = self.project_path / ".ai" / "directives"
                file_path = self._find_in_path(directive_name, search_base)
                if not file_path:
                    return {
                        "error": f"Directive '{directive_name}' not found in project"
                    }
                
                # If destination differs from source, copy the file
                if destination == "user":
                    # Copy from project to user space
                    content = file_path.read_text()
                    # Determine category from source path
                    relative_path = file_path.relative_to(search_base)
                    target_path = Path.home() / ".ai" / "directives" / relative_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(content)
                    self.logger.info(f"Copied directive from project to user: {target_path}")
                    
                    directive_data = parse_directive_file(target_path)
                    directive_data["source"] = "project"
                    directive_data["destination"] = "user"
                    directive_data["path"] = str(target_path)
                    return directive_data
                else:
                    # Just return project file info (no copy needed)
                    directive_data = parse_directive_file(file_path)
                    directive_data["source"] = "project"
                    directive_data["path"] = str(file_path)
                    return directive_data
            
            # LOAD FROM USER
            # source == "user" (only remaining option due to Literal typing)
            search_base = Path.home() / ".ai" / "directives"
            file_path = self._find_in_path(directive_name, search_base)
            if not file_path:
                return {
                    "error": f"Directive '{directive_name}' not found in user space"
                }
            
            # If destination differs from source, copy the file
            if destination == "project":
                if not self.project_path:
                    return {
                        "error": "project_path is required for destination='project'"
                    }
                # Copy from user to project space
                content = file_path.read_text()
                # Determine category from source path
                relative_path = file_path.relative_to(search_base)
                target_path = self.project_path / ".ai" / "directives" / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content)
                self.logger.info(f"Copied directive from user to project: {target_path}")
                
                directive_data = parse_directive_file(target_path)
                directive_data["source"] = "user"
                directive_data["destination"] = "project"
                directive_data["path"] = str(target_path)
                return directive_data
            else:
                # Just return user file info (no copy needed)
                directive_data = parse_directive_file(file_path)
                directive_data["source"] = "user"
                directive_data["path"] = str(file_path)
                return directive_data
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
            else:
                return {
                    "error": f"Unknown action: {action}",
                    "supported_actions": ["run", "publish", "delete", "create", "update"]
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
            
            # Enforce permissions - run action requires valid permissions
            permission_check = self._check_permissions(directive_data.get("permissions", []))
            if not permission_check["valid"]:
                return {
                    "error": "Directive permissions not satisfied",
                    "details": permission_check["issues"],
                    "path": str(file_path),
                    "permissions_required": directive_data.get("permissions", [])
                }
            
            # ENFORCE hash validation - ALWAYS check, never skip
            file_content = file_path.read_text()
            signature_status = self._verify_signature(file_content)
            
            # Block execution if signature is invalid or modified
            if signature_status:
                if signature_status.get("status") == "modified":
                    return {
                        "error": "Directive content has been modified since last validation",
                        "signature": signature_status,
                        "path": str(file_path),
                        "solution": "Run 'update' action to re-validate the directive"
                    }
                elif signature_status.get("status") == "invalid":
                    return {
                        "error": "Directive signature is invalid",
                        "signature": signature_status,
                        "path": str(file_path),
                        "solution": "Run 'update' action to re-validate the directive"
                    }
            
            result = {
                "status": "ready",
                "directive": {
                    "name": directive_data["name"],
                    "version": directive_data["version"],
                    "description": directive_data["description"],
                    "content": directive_data["content"],
                    "parsed": directive_data["parsed"],
                    "permissions": directive_data.get("permissions", []),
                    "source": "project" if str(file_path).startswith(str(self.resolver.project_directives)) else "user"
                },
                "inputs": params,
                "instructions": (
                    "Status 'ready' means the directive is loaded and ready for YOU to execute. "
                    "Read the directive's <process> section and follow each step."
                )
            }
            
            return result
        except Exception as e:
            return {
                "error": f"Failed to parse directive: {str(e)}",
                "path": str(file_path)
            }
    
    def _find_in_path(self, directive_name: str, base_path: Path) -> Optional[Path]:
        """Find directive file in specified path."""
        if not base_path.exists():
            return None
        
        # Search recursively for the directive
        for md_file in base_path.rglob(f"{directive_name}.md"):
            return md_file
        
        # Also try with wildcards in case of naming variations
        for md_file in base_path.rglob("*.md"):
            if directive_name in md_file.stem:
                return md_file
        
        return None
    
    def _check_permissions(self, permissions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate directive permissions.
        
        Checks that required permissions are satisfied.
        Current implementation validates permission structure.
        
        Args:
            permissions: List of permission dicts from parsed directive
        
        Returns:
            {"valid": bool, "issues": list[str]}
        """
        issues = []
        
        if not permissions:
            return {"valid": False, "issues": ["No permissions defined in directive"]}
        
        for perm in permissions:
            if not isinstance(perm, dict):
                issues.append(f"Invalid permission format: {perm}")
                continue
            
            if "tag" not in perm:
                issues.append("Permission missing 'tag' field")
            if not perm.get("attrs"):
                issues.append(f"Permission '{perm.get('tag', 'unknown')}' missing attributes")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def _verify_signature(self, file_content: str) -> Optional[Dict[str, Any]]:
        """Verify content signature if present."""
        # Match timestamp (ISO format with colons) and hash (12 hex chars)
        sig_match = re.match(r'^<!-- kiwi-mcp:validated:(.*?):([a-f0-9]{12}) -->', file_content)
        if not sig_match:
            return None  # No signature - that's fine, might be legacy
        
        stored_timestamp = sig_match.group(1)
        stored_hash = sig_match.group(2)
        
        # Extract XML from file_content and compute current hash
        xml_match = re.search(r'```xml\n(.*?)\n```', file_content, re.DOTALL)
        if not xml_match:
            return {"status": "invalid", "reason": "no_xml_found"}
        
        current_hash = hashlib.sha256(xml_match.group(1).encode()).hexdigest()[:12]
        
        if current_hash == stored_hash:
            return {
                "status": "valid",
                "validated_at": stored_timestamp,
                "hash": stored_hash
            }
        else:
            return {
                "status": "modified",
                "validated_at": stored_timestamp,
                "original_hash": stored_hash,
                "current_hash": current_hash,
                "warning": "Content modified since last validation. Consider running 'update' to re-validate."
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
        """
        Validate and register an existing directive file.
        
        Expects the directive file to already exist on disk.
        This action validates the XML, checks permissions, and adds a signature.
        """
        location = params.get("location", "project")
        if location not in ("project", "user"):
            return {
                "error": f"Invalid location: {location}",
                "valid_locations": ["project", "user"]
            }
        
        # Find the directive file
        if location == "project":
            if not self.project_path:
                return {
                    "error": "project_path required for location='project'",
                    "suggestion": "Provide project_path or use location='user'"
                }
            # Search in project directives
            file_path = None
            for search_path in [self.resolver.project_directives]:
                for candidate in Path(search_path).rglob(f"*{directive_name}.md"):
                    if candidate.stem == directive_name:
                        file_path = candidate
                        break
                if file_path:
                    break
        else:
            # Search in user directives
            file_path = None
            for candidate in Path(self.resolver.user_directives).rglob(f"*{directive_name}.md"):
                if candidate.stem == directive_name:
                    file_path = candidate
                    break
        
        if not file_path or not file_path.exists():
            return {
                "error": f"Directive file not found: {directive_name}",
                "hint": f"Create the file first at .ai/directives/{{category}}/{directive_name}.md",
                "searched_in": str(self.resolver.project_directives if location == "project" else self.resolver.user_directives)
            }
        
        # Read and validate the file
        content = file_path.read_text()
        
        # Validate XML can be parsed
        try:
            xml_match = re.search(r'```xml\n(.*?)\n```', content, re.DOTALL)
            if not xml_match:
                return {
                    "error": "No XML directive found in content",
                    "hint": "Content must contain XML directive wrapped in ```xml``` code block",
                    "file": str(file_path)
                }
            
            xml_content = xml_match.group(1)
            ET.fromstring(xml_content)  # Validate XML syntax
            
        except ET.ParseError as e:
            return {
                "error": "Invalid directive XML",
                "parse_error": str(e),
                "hint": "Check for unescaped < > & characters. Use CDATA for special chars.",
                "file": str(file_path)
            }
        except Exception as e:
            return {
                "error": "Failed to validate directive",
                "details": str(e),
                "file": str(file_path)
            }
        
        # Parse and check permissions
        try:
            directive_data = parse_directive_file(file_path)
            permission_check = self._check_permissions(directive_data.get("permissions", []))
            if not permission_check["valid"]:
                return {
                    "error": "Directive permissions not satisfied",
                    "details": permission_check["issues"],
                    "path": str(file_path),
                    "permissions_required": directive_data.get("permissions", [])
                }
        except Exception as e:
            return {
                "error": "Failed to validate directive permissions",
                "details": str(e),
                "file": str(file_path)
            }
        
        # Generate signature for validated content
        content_hash = hashlib.sha256(xml_content.encode()).hexdigest()[:12]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        signature = f"<!-- kiwi-mcp:validated:{timestamp}:{content_hash} -->\n"
        
        # Remove old signature if present, then prepend new one
        content_without_sig = re.sub(r'^<!-- kiwi-mcp:validated:[^>]+-->\n', '', content)
        signed_content = signature + content_without_sig
        
        # Update file with signature
        file_path.write_text(signed_content)
        
        # Parse to get category
        try:
            directive = parse_directive_file(file_path)
            category = directive.get("category", "unknown")
        except:
            category = "unknown"
        
        return {
            "status": "created",
            "name": directive_name,
            "path": str(file_path),
            "location": location,
            "category": category,
            "validated": True,
            "signature": {
                "hash": content_hash,
                "timestamp": timestamp
            },
            "message": f"Directive validated and signed. Ready to use."
        }
    
    async def _update_directive(
        self,
        directive_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate and update an existing directive file.
        
        Expects the directive file to already exist on disk.
        This action validates the XML, checks permissions, and updates the signature.
        Uses the same pattern as _create_directive: works with file paths, not content strings.
        """
        # Find existing file
        file_path = self.resolver.resolve(directive_name)
        if not file_path:
            return {
                "error": f"Directive '{directive_name}' not found",
                "suggestion": "Use 'create' action for new directives"
            }
        
        if not file_path.exists():
            return {
                "error": f"Directive file not found: {directive_name}",
                "path": str(file_path)
            }
        
        # Read the existing file
        content = file_path.read_text()
        
        # Validate XML can be parsed
        try:
            xml_match = re.search(r'```xml\n(.*?)\n```', content, re.DOTALL)
            if not xml_match:
                return {
                    "error": "No XML directive found in content",
                    "hint": "Content must contain XML directive wrapped in ```xml``` code block",
                    "file": str(file_path)
                }
            
            xml_content = xml_match.group(1)
            ET.fromstring(xml_content)  # Validate XML syntax
            
        except ET.ParseError as e:
            return {
                "error": "Invalid directive XML",
                "parse_error": str(e),
                "hint": "Check for unescaped < > & characters. Use CDATA for special chars.",
                "file": str(file_path)
            }
        except Exception as e:
            return {
                "error": "Failed to validate directive",
                "details": str(e),
                "file": str(file_path)
            }
        
        # Parse and check permissions
        try:
            directive_data = parse_directive_file(file_path)
            permission_check = self._check_permissions(directive_data.get("permissions", []))
            if not permission_check["valid"]:
                return {
                    "error": "Directive permissions not satisfied",
                    "details": permission_check["issues"],
                    "path": str(file_path),
                    "permissions_required": directive_data.get("permissions", [])
                }
        except Exception as e:
            return {
                "error": "Failed to validate directive permissions",
                "details": str(e),
                "file": str(file_path)
            }
        
        # Generate new signature for validated content
        content_hash = hashlib.sha256(xml_content.encode()).hexdigest()[:12]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        signature = f"<!-- kiwi-mcp:validated:{timestamp}:{content_hash} -->\n"
        
        # Remove old signature if present, then prepend new one
        content_without_sig = re.sub(r'^<!-- kiwi-mcp:validated:[^>]+-->\n', '', content)
        signed_content = signature + content_without_sig
        
        # Update file
        file_path.write_text(signed_content)
        
        # Parse to get category
        try:
            directive = parse_directive_file(file_path)
            category = directive.get("category", "unknown")
        except:
            category = "unknown"
        
        return {
            "status": "updated",
            "name": directive_name,
            "path": str(file_path),
            "category": category,
            "validated": True,
            "signature": {
                "hash": content_hash,
                "timestamp": timestamp
            },
            "message": f"Directive validated and signed. Ready to use."
        }
    
