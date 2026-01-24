"""
Knowledge handler for kiwi-mcp.

Implements search, load, execute operations for knowledge entries.
Handles LOCAL file operations directly, only uses registry for REMOTE operations.
"""

from typing import Dict, Any, Optional, List, Literal

from kiwi_mcp.handlers import SortBy
import json
from pathlib import Path

from kiwi_mcp.api.knowledge_registry import KnowledgeRegistry
from kiwi_mcp.utils.logger import get_logger
from kiwi_mcp.utils.resolvers import KnowledgeResolver, get_user_space
from kiwi_mcp.utils.parsers import parse_knowledge_entry
from kiwi_mcp.utils.file_search import search_markdown_files, score_relevance
from kiwi_mcp.utils.metadata_manager import MetadataManager
from kiwi_mcp.utils.validators import ValidationManager, compare_versions
from kiwi_mcp.primitives.integrity import (
    compute_knowledge_integrity,
    verify_knowledge_integrity,
    short_hash,
)
from kiwi_mcp.utils.schema_validator import SchemaValidator


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
        
        # Frontmatter schema validation
        self._schema_validator = SchemaValidator()
        
        # Vector store for automatic embedding
        self._vector_store = None
        self._init_vector_store()

    def _init_vector_store(self):
        """Initialize project vector store for automatic embedding."""
        try:
            from kiwi_mcp.storage.vector import LocalVectorStore, EmbeddingService, load_vector_config
            
            # Load embedding config from environment
            config = load_vector_config()
            embedding_service = EmbeddingService(config)
            
            vector_path = self.project_path / ".ai" / "vector" / "project"
            vector_path.mkdir(parents=True, exist_ok=True)
            
            self._vector_store = LocalVectorStore(
                storage_path=vector_path,
                collection_name="project_items",
                embedding_service=embedding_service
            )
        except ValueError as e:
            # Missing config - vector search disabled
            self.logger.debug(f"Vector store not configured: {e}")
            self._vector_store = None
        except Exception as e:
            self.logger.warning(f"Vector store init failed: {e}")
            self._vector_store = None

    def _compute_knowledge_integrity(
        self, entry_data: Dict[str, Any]
    ) -> str:
        """
        Compute canonical integrity hash for a knowledge entry.
        
        Args:
            entry_data: Parsed knowledge entry data
            
        Returns:
            SHA256 hex digest (64 characters)
        """
        # Build frontmatter dict (excluding validation fields)
        frontmatter = {
            "zettel_id": entry_data.get("zettel_id"),
            "title": entry_data.get("title"),
            "entry_type": entry_data.get("entry_type"),
            "category": entry_data.get("category"),
            "tags": entry_data.get("tags", []),
        }
        
        return compute_knowledge_integrity(
            zettel_id=entry_data.get("zettel_id", ""),
            version=entry_data.get("version", "1.0.0"),
            content=entry_data.get("content", ""),
            frontmatter=frontmatter,
        )
    
    def _verify_knowledge_integrity(
        self, entry_data: Dict[str, Any], stored_hash: str
    ) -> bool:
        """
        Verify knowledge entry content matches stored canonical integrity hash.
        
        Args:
            entry_data: Parsed knowledge entry data
            stored_hash: Expected integrity hash
            
        Returns:
            True if computed hash matches stored hash
        """
        computed = self._compute_knowledge_integrity(entry_data)
        return computed == stored_hash

    def _extract_frontmatter_schema(self, entry_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract optional frontmatter_schema from knowledge entry.
        
        The schema can be defined in the frontmatter as a 'schema' field
        containing a JSON Schema for validating custom frontmatter fields.
        
        Example frontmatter:
            ---
            zettel_id: 20260124-api-patterns
            title: API Design Patterns
            custom_field: some_value
            schema:
              type: object
              properties:
                custom_field:
                  type: string
                  minLength: 3
            ---
        
        Args:
            entry_data: Parsed knowledge entry data
            
        Returns:
            JSON Schema dict or None if not defined
        """
        schema = entry_data.get("schema")
        if schema and isinstance(schema, dict):
            return schema
        return None
    
    def _build_base_frontmatter_schema(self) -> Dict[str, Any]:
        """
        Build base JSON Schema for standard knowledge frontmatter fields.
        
        Returns:
            JSON Schema dict for base frontmatter validation
        """
        return {
            "type": "object",
            "properties": {
                "zettel_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Unique identifier for the knowledge entry"
                },
                "title": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Title of the knowledge entry"
                },
                "entry_type": {
                    "type": "string",
                    "enum": ["pattern", "learning", "reference", "concept", "decision", "insight", "procedure"],
                    "description": "Type of knowledge entry"
                },
                "category": {
                    "type": "string",
                    "description": "Category for organization"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization"
                },
                "version": {
                    "type": "string",
                    "pattern": "^\\d+\\.\\d+\\.\\d+$",
                    "description": "Semantic version"
                },
            },
            "required": ["zettel_id", "title"],
        }
    
    def _validate_frontmatter_with_schema(
        self, 
        entry_data: Dict[str, Any], 
        custom_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate knowledge entry frontmatter against schema.
        
        Args:
            entry_data: Parsed knowledge entry data (includes frontmatter fields)
            custom_schema: Optional custom schema to merge with base schema
            
        Returns:
            Validation result with valid, issues, warnings
        """
        if not self._schema_validator.is_available():
            return {
                "valid": True,
                "issues": [],
                "warnings": ["JSON Schema validation not available - skipping frontmatter validation"],
            }
        
        # Build combined schema
        base_schema = self._build_base_frontmatter_schema()
        
        if custom_schema:
            # Merge custom schema properties into base
            if "properties" in custom_schema:
                base_schema["properties"].update(custom_schema["properties"])
            if "required" in custom_schema:
                base_schema["required"] = list(set(base_schema.get("required", []) + custom_schema["required"]))
        
        # Extract frontmatter fields for validation (exclude content and validation fields)
        frontmatter_to_validate = {
            k: v for k, v in entry_data.items() 
            if k not in ("content", "validated_at", "content_hash", "integrity", "path", "source", "schema")
        }
        
        return self._schema_validator.validate(frontmatter_to_validate, base_schema)

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
                
                # Get entry from registry
                registry_data = await self.registry.get(zettel_id=zettel_id)
                if not registry_data:
                    return {"error": f"Knowledge entry '{zettel_id}' not found in registry"}

                content = registry_data.get("content")
                if not content:
                    return {"error": f"Knowledge entry '{zettel_id}' has no content"}

                # Determine target path based on destination
                if effective_destination == "user":
                    base_path = get_user_space() / "knowledge"
                else:  # destination == "project"
                    base_path = self.project_path / ".ai" / "knowledge"

                # Build category path
                category = registry_data.get("category", "")
                if category:
                    target_dir = base_path / category
                else:
                    target_dir = base_path

                # Create directory if needed
                target_dir.mkdir(parents=True, exist_ok=True)

                # Write file
                target_path = target_dir / f"{zettel_id}.md"
                target_path.write_text(content)

                self.logger.info(f"Downloaded knowledge entry from registry to: {target_path}")

                # Verify hash after download for safety
                file_content = target_path.read_text()
                signature_status = MetadataManager.verify_signature("knowledge", file_content)

                # Parse and return
                entry_data = parse_knowledge_entry(target_path)
                entry_data["source"] = "registry"
                entry_data["destination"] = effective_destination
                entry_data["path"] = str(target_path)

                # Add warning if signature is invalid or modified (registry content should be valid)
                if signature_status and signature_status.get("status") in ["modified", "invalid"]:
                    entry_data["warning"] = {
                        "message": "Registry knowledge entry content signature is invalid or modified - content may be corrupted",
                        "signature": signature_status,
                        "solution": "Use execute action 'update' or 'create' to re-validate the entry",
                    }
                    self.logger.warning(f"Registry knowledge entry '{zettel_id}' has invalid signature: {signature_status}")

                # Include relationships if requested
                if include_relationships:
                    relationships = await self.registry.get_relationships(zettel_id)
                    entry_data["relationships"] = relationships

                return entry_data

            # LOAD FROM PROJECT
            if source == "project":
                search_base = self.project_path / ".ai" / "knowledge"
                file_path = self._find_entry_in_path(zettel_id, search_base)
                if not file_path:
                    return {"error": f"Knowledge entry '{zettel_id}' not found in project"}

                # If destination differs from source, copy the file
                if destination == "user":
                    # Copy from project to user space
                    # Verify hash before copying
                    content = file_path.read_text()
                    signature_status = MetadataManager.verify_signature("knowledge", content)
                    if signature_status:
                        if signature_status.get("status") in ["modified", "invalid"]:
                            return {
                                "error": f"Knowledge entry content has been modified or signature is invalid",
                                "signature": signature_status,
                                "path": str(file_path),
                                "solution": "Use execute action 'update' or 'create' to re-validate the entry before copying",
                            }
                    
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
                    # Read-only mode: verify and warn, but don't block
                    file_content = file_path.read_text()
                    signature_status = MetadataManager.verify_signature("knowledge", file_content)
                    
                    entry_data = parse_knowledge_entry(file_path)
                    entry_data["source"] = "project"
                    entry_data["path"] = str(file_path)
                    entry_data["mode"] = "read_only"
                    
                    if signature_status and signature_status.get("status") in ["modified", "invalid"]:
                        entry_data["warning"] = {
                            "message": "Knowledge entry content has been modified or signature is invalid",
                            "signature": signature_status,
                            "solution": "Use execute action 'update' or 'create' to re-validate",
                        }
                    
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
                # Verify hash before copying
                content = file_path.read_text()
                signature_status = MetadataManager.verify_signature("knowledge", content)
                if signature_status:
                    if signature_status.get("status") in ["modified", "invalid"]:
                        return {
                            "error": f"Knowledge entry content has been modified or signature is invalid",
                            "signature": signature_status,
                            "path": str(file_path),
                            "solution": "Use execute action 'update' or 'create' to re-validate the entry before copying",
                        }
                
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
                # Read-only mode: verify and warn, but don't block
                file_content = file_path.read_text()
                signature_status = MetadataManager.verify_signature("knowledge", file_content)
                
                entry_data = parse_knowledge_entry(file_path)
                entry_data["source"] = "user"
                entry_data["path"] = str(file_path)
                entry_data["mode"] = "read_only"
                
                if signature_status and signature_status.get("status") in ["modified", "invalid"]:
                    entry_data["warning"] = {
                        "message": "Knowledge entry content has been modified or signature is invalid",
                        "signature": signature_status,
                        "solution": "Use execute action 'update' or 'create' to re-validate",
                    }
                
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

    async def _check_for_newer_version(
        self, zettel_id: str, current_version: str, current_source: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check for newer versions of a knowledge entry in other locations.
        From project: check userspace and registry. From user: check registry only.
        """
        newest_version = current_version
        newest_location = None

        if current_source == "project":
            try:
                user_path = self._find_entry_in_path(zettel_id, self.resolver.user_knowledge)
                if user_path and user_path.exists():
                    try:
                        user_data = parse_knowledge_entry(user_path)
                        user_version = user_data.get("version")
                        if user_version:
                            try:
                                if compare_versions(current_version, user_version) < 0:
                                    if compare_versions(newest_version, user_version) < 0:
                                        newest_version = user_version
                                        newest_location = "user"
                            except Exception as e:
                                self.logger.warning(f"Failed to compare versions with user space: {e}")
                    except Exception as e:
                        self.logger.warning(f"Failed to parse user space knowledge {zettel_id}: {e}")
            except Exception as e:
                self.logger.warning(f"Failed to check user space for knowledge {zettel_id}: {e}")

        try:
            reg = await self.registry.get(zettel_id)
            if reg and reg.get("version"):
                rv = reg["version"]
                try:
                    if compare_versions(current_version, rv) < 0:
                        if compare_versions(newest_version, rv) < 0:
                            newest_version = rv
                            newest_location = "registry"
                except Exception as e:
                    self.logger.warning(f"Failed to compare versions with registry: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to check registry for knowledge {zettel_id}: {e}")

        if newest_location and newest_version != current_version:
            sugg = (
                "Use load() to download the newer version from registry"
                if newest_location == "registry"
                else "Use load() to copy the newer version from user space"
            )
            return {
                "message": "A newer version of this knowledge entry is available",
                "current_version": current_version,
                "newer_version": newest_version,
                "location": newest_location,
                "suggestion": sugg,
            }
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
        file_content = file_path.read_text()
        signature_status = MetadataManager.verify_signature("knowledge", file_content)

        # Block execution if signature is missing, invalid, or modified
        if signature_status is None:
            return {
                "status": "error",
                "error": "Knowledge entry has no valid signature",
                "path": str(file_path),
                "hint": "Knowledge entry needs validation",
                "solution": (
                    f"Run: execute(item_type='knowledge', action='update', "
                    f"item_id='{zettel_id}', parameters={{'location': 'project'}}, "
                    f"project_path='{self.project_path}')"
                ),
            }

        if signature_status.get("status") == "modified":
            return {
                "status": "error",
                "error": "Knowledge entry content has been modified since last validation",
                "signature": signature_status,
                "path": str(file_path),
                "solution": "Use execute action 'update' or 'create' to re-validate the entry",
            }
        elif signature_status.get("status") == "invalid":
            return {
                "status": "error",
                "error": "Knowledge entry signature is invalid",
                "signature": signature_status,
                "path": str(file_path),
                "solution": "Use execute action 'update' or 'create' to re-validate the entry",
            }

        # Parse entry file and validate
        try:
            entry_data = parse_knowledge_entry(file_path)
            
            # Validate using centralized validator and embed if valid
            validation_result = await ValidationManager.validate_and_embed(
                "knowledge", 
                file_path, 
                entry_data,
                vector_store=self._vector_store,
                item_id=entry_data.get("zettel_id")
            )
            if not validation_result["valid"]:
                return {
                    "status": "error",
                    "error": "Knowledge entry validation failed",
                    "details": validation_result["issues"],
                    "path": str(file_path),
                }

            current_version = entry_data.get("version") or "1.0.0"
            current_source = (
                "project"
                if str(file_path).startswith(str(self.resolver.project_knowledge))
                else "user"
            )
            version_warning = await self._check_for_newer_version(
                zettel_id, current_version, current_source
            )
            
            # Frontmatter schema validation (optional but recommended)
            # Only fail on critical issues, warnings are acceptable
            custom_schema = self._extract_frontmatter_schema(entry_data)
            frontmatter_validation = self._validate_frontmatter_with_schema(entry_data, custom_schema)
            
            # Return error only if validation has critical issues (not just warnings)
            # Warnings are acceptable and don't block execution
            if not frontmatter_validation.get("valid", True):
                issues = frontmatter_validation.get("issues", [])
                # Only fail if there are actual errors, not just warnings
                if issues and not all("warning" in issue.lower() for issue in issues):
                    return {
                        "status": "error",
                        "error": "Frontmatter validation failed",
                        "validation_issues": issues,
                        "zettel_id": entry_data.get("zettel_id"),
                        "title": entry_data.get("title"),
                        "path": str(file_path),
                        "solution": "Fix the validation issues in the frontmatter",
                    }
            
            # Compute canonical integrity for verification reporting
            canonical_integrity = self._compute_knowledge_integrity(entry_data)

            out = {
                "status": "ready",
                "zettel_id": entry_data["zettel_id"],
                "title": entry_data["title"],
                "version": current_version,
                "content": entry_data["content"],
                "entry_type": entry_data.get("entry_type"),
                "category": entry_data.get("category"),
                "tags": entry_data.get("tags", []),
                "integrity": canonical_integrity,
                "integrity_short": short_hash(canonical_integrity),
                "frontmatter_validated": True,
                "instructions": "Use this knowledge to inform your decisions.",
            }
            
            # Add validation warnings if any
            if frontmatter_validation.get("warnings"):
                out["validation_warnings"] = frontmatter_validation["warnings"]
            
            if version_warning:
                out["version_warning"] = version_warning
            return out
        except Exception as e:
            return {"error": f"Failed to parse knowledge entry: {str(e)}", "path": str(file_path)}

    async def _create_knowledge(self, zettel_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and register an existing knowledge entry file.

        Expects the knowledge entry file to already exist on disk.
        This action validates the frontmatter, content, and adds a signature.
        """
        location = params.get("location", "project")
        if location not in ("project", "user"):
            return {
                "error": f"Invalid location: {location}",
                "valid_locations": ["project", "user"],
            }

        # Find the knowledge entry file
        if location == "project":
            search_base = self.project_path / ".ai" / "knowledge"
        else:
            search_base = get_user_space() / "knowledge"

        file_path = self._find_entry_in_path(zettel_id, search_base)

        if not file_path or not file_path.exists():
            category_hint = params.get("category", "learnings")  # Default category hint
            return {
                "error": f"Knowledge entry file not found: {zettel_id}",
                "hint": f"Create the file first at .ai/knowledge/{category_hint}/{zettel_id}.md",
                "searched_in": str(search_base),
            }

        # Validate path structure
        from kiwi_mcp.utils.paths import validate_path_structure
        path_validation = validate_path_structure(
            file_path, "knowledge", location, self.project_path
        )
        if not path_validation["valid"]:
            return {
                "error": "Knowledge entry path structure invalid",
                "details": path_validation["issues"],
                "path": str(file_path),
                "solution": "File must be under .ai/knowledge/ with correct structure",
            }

        # Read and validate the file
        content = file_path.read_text()

        # Parse and validate
        try:
            entry_data = parse_knowledge_entry(file_path)
            validation_result = await ValidationManager.validate_and_embed(
                "knowledge", 
                file_path, 
                entry_data,
                vector_store=self._vector_store,
                item_id=entry_data.get("zettel_id")
            )
            if not validation_result["valid"]:
                return {
                    "error": "Knowledge entry validation failed",
                    "details": validation_result["issues"],
                    "path": str(file_path),
                    "solution": "Fix validation issues and re-run create action",
                }
        except Exception as e:
            return {
                "error": "Failed to validate knowledge entry",
                "details": str(e),
                "path": str(file_path),
            }
        
        # Generate signature for validated content using MetadataManager
        from kiwi_mcp.utils.metadata_manager import compute_content_hash, generate_timestamp
        
        # Extract content part (without frontmatter) for hashing
        strategy = MetadataManager.get_strategy("knowledge")
        content_for_hash = strategy.extract_content_for_hash(content)
        content_hash = compute_content_hash(content_for_hash)
        timestamp = generate_timestamp()

        # Get existing frontmatter fields from parsed data
        existing_frontmatter = {
            "zettel_id": entry_data.get("zettel_id"),
            "title": entry_data.get("title"),
            "entry_type": entry_data.get("entry_type"),
            "category": entry_data.get("category"),
            "tags": entry_data.get("tags", []),
            "version": entry_data.get("version", "1.0.0"),
        }

        # Create final content with signature in frontmatter
        frontmatter = f"""---
zettel_id: {existing_frontmatter['zettel_id']}
title: {existing_frontmatter['title']}
entry_type: {existing_frontmatter['entry_type']}
category: {existing_frontmatter['category']}
tags: {json.dumps(existing_frontmatter['tags'])}
version: "{existing_frontmatter['version']}"
validated_at: {timestamp}
content_hash: {content_hash}
---

"""
        # Extract content part (everything after frontmatter)
        content_body = entry_data.get("content", "")
        full_content = frontmatter + content_body
        file_path.write_text(full_content)

        # Compute canonical integrity hash for version-aware verification
        canonical_integrity = self._compute_knowledge_integrity(entry_data)

        # Extract category from parsed entry data (validated by parser to match path)
        category = entry_data.get("category", "")

        return {
            "status": "created",
            "zettel_id": entry_data.get("zettel_id"),
            "path": str(file_path),
            "location": location,
            "category": category,
            "entry_type": existing_frontmatter["entry_type"],
            "signature": {"hash": content_hash, "timestamp": timestamp},
            "integrity": canonical_integrity,
            "integrity_short": short_hash(canonical_integrity),
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
        
        # Validate updated entry
        updated_entry_data = {
            "zettel_id": entry_data.get("zettel_id"),
            "title": title,
            "content": content,
            "entry_type": entry_type,
            "category": category,
            "tags": tags,
        }
        validation_result = await ValidationManager.validate_and_embed(
            "knowledge", 
            file_path, 
            updated_entry_data,
            vector_store=self._vector_store,
            item_id=updated_entry_data.get("zettel_id")
        )
        if not validation_result["valid"]:
            return {
                "error": "Knowledge entry validation failed",
                "details": validation_result["issues"],
                "path": str(file_path),
            }

        # Use zettel_id from file's frontmatter (not parameter) - parse_knowledge_entry() already validated match
        file_zettel_id = entry_data["zettel_id"]
        
        # Explicit validation check before writing (double-check)
        expected_filename = f"{file_zettel_id}.md"
        if file_path.stem != file_zettel_id:
            return {
                "error": "Cannot update: filename and zettel_id mismatch",
                "problem": {
                    "filename": file_path.name,
                    "frontmatter_zettel_id": file_zettel_id,
                    "expected_filename": expected_filename,
                    "path": str(file_path)
                },
                "solution": {
                    "option_1": {
                        "action": "Rename file to match frontmatter zettel_id",
                        "command": f"mv '{file_path}' '{file_path.parent / expected_filename}'",
                        "then": f"Re-run update action with item_id='{file_zettel_id}'"
                    },
                    "option_2": {
                        "action": "Update frontmatter to match current filename",
                        "steps": [
                            f"1. Edit {file_path}",
                            f"2. Change frontmatter: zettel_id: {file_path.stem}",
                            f"3. Re-run: mcp__kiwi_mcp__execute(item_type='knowledge', action='update', item_id='{file_path.stem}')"
                        ]
                    },
                    "option_3": {
                        "action": "Use edit_knowledge directive",
                        "steps": [
                            f"Run: edit_knowledge directive with zettel_id='{file_path.stem}'",
                            f"Update frontmatter zettel_id to '{file_path.stem}' OR rename file to '{expected_filename}'"
                        ]
                    }
                }
            }

        # Generate new signature for validated content using MetadataManager
        from kiwi_mcp.utils.metadata_manager import compute_content_hash, generate_timestamp
        content_hash = compute_content_hash(content)  # Hash just the content part
        timestamp = generate_timestamp()

        # Recreate frontmatter with signature (use file's zettel_id, not parameter)
        frontmatter = f"""---
zettel_id: {file_zettel_id}
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
        
        # Compute canonical integrity hash for version-aware verification
        # Use existing version or default to 1.0.0
        version = entry_data.get("version", "1.0.0")
        entry_data_for_integrity = {
            "zettel_id": file_zettel_id,
            "title": title,
            "entry_type": entry_type,
            "category": category,
            "tags": tags,
            "version": version,
            "content": content,
        }
        canonical_integrity = self._compute_knowledge_integrity(entry_data_for_integrity)

        return {
            "status": "updated",
            "zettel_id": file_zettel_id,
            "path": str(file_path),
            "signature": {"hash": content_hash, "timestamp": timestamp},
            "integrity": canonical_integrity,
            "integrity_short": short_hash(canonical_integrity),
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
                result = await self.registry.delete(
                    zettel_id=zettel_id,
                    cascade_relationships=params.get("cascade_relationships", False)
                )
                if "error" in result:
                    self.logger.warning(f"Registry delete failed: {result.get('error')}")
                else:
                    deleted.append("registry")
            except Exception as e:
                self.logger.warning(f"Registry delete failed: {e}")

        if not deleted:
            return {"error": f"Knowledge entry '{zettel_id}' not found in specified location(s)"}

        return {"status": "deleted", "zettel_id": zettel_id, "deleted_from": deleted}

    async def _publish_knowledge(self, zettel_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Publish knowledge entry to registry."""
        # Find local entry file first (needed to extract version)
        file_path = self.resolver.resolve(zettel_id)
        if not file_path:
            return {
                "error": f"Knowledge entry '{zettel_id}' not found locally",
                "suggestion": "Create entry first before publishing",
            }

        # ENFORCE hash validation - ALWAYS check, never skip
        file_content = file_path.read_text()
        signature_status = MetadataManager.verify_signature("knowledge", file_content)

        # Block publishing if signature is missing, invalid, or modified
        if signature_status is None:
            return {
                "error": "Cannot publish: knowledge entry has no valid signature",
                "path": str(file_path),
                "hint": "Knowledge entries must be validated before publishing",
                "solution": (
                    f"Run: execute(item_type='knowledge', action='update', "
                    f"item_id='{zettel_id}', parameters={{'location': 'project'}}, "
                    f"project_path='{self.project_path}')"
                ),
            }

        if signature_status.get("status") == "modified":
            return {
                "error": "Knowledge entry content has been modified since last validation",
                "signature": signature_status,
                "path": str(file_path),
                "solution": "Use execute action 'update' or 'create' to re-validate the entry before publishing",
            }
        elif signature_status.get("status") == "invalid":
            return {
                "error": "Knowledge entry signature is invalid",
                "signature": signature_status,
                "path": str(file_path),
                "solution": "Use execute action 'update' or 'create' to re-validate the entry before publishing",
            }

        # Parse entry to get content and metadata (including version)
        # parse_knowledge_entry() will validate filename/zettel_id match and raise if mismatch
        try:
            entry_data = parse_knowledge_entry(file_path)
        except ValueError as e:
            # Convert parse validation error to structured response
            return {
                "error": "Cannot publish: filename and zettel_id mismatch",
                "details": str(e),
                "path": str(file_path)
            }
        
        # Explicit validation check after parsing (double-check for clarity)
        expected_filename = f"{entry_data['zettel_id']}.md"
        if file_path.stem != entry_data["zettel_id"]:
            return {
                "error": "Cannot publish: filename and zettel_id mismatch",
                "problem": {
                    "filename": file_path.name,
                    "frontmatter_zettel_id": entry_data["zettel_id"],
                    "expected_filename": expected_filename,
                    "path": str(file_path)
                },
                "solution": {
                    "message": "Fix mismatch before publishing. Choose one option:",
                    "option_1": {
                        "action": "Rename file to match frontmatter",
                        "command": f"mv '{file_path}' '{file_path.parent / expected_filename}'",
                        "then": f"Re-run publish with: item_id='{entry_data['zettel_id']}'"
                    },
                    "option_2": {
                        "action": "Update frontmatter to match filename",
                        "steps": [
                            f"1. Edit {file_path}",
                            f"2. Change frontmatter: zettel_id: {file_path.stem}",
                            f"3. Run: mcp__kiwi_mcp__execute(item_type='knowledge', action='update', item_id='{file_path.stem}')",
                            f"4. Then re-run publish with: item_id='{file_path.stem}'"
                        ]
                    },
                    "option_3": {
                        "action": "Use edit_knowledge directive",
                        "steps": [
                            f"Run: edit_knowledge directive with zettel_id='{file_path.stem}'",
                            f"Fix mismatch (rename file or update frontmatter)",
                            f"Then re-run publish"
                        ]
                    }
                }
            }

        # Use explicit param if provided, otherwise fall back to parsed version (default 1.0.0)
        version = params.get("version") or entry_data.get("version", "1.0.0")

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

        # Ensure response includes version actually used
        if isinstance(result, dict) and "error" not in result:
            result["zettel_id"] = zettel_id
            result["version"] = version

        return result
