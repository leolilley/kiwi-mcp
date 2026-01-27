"""
Knowledge handler for kiwi-mcp.

Implements search, load, execute operations for knowledge entries.
Handles LOCAL file operations directly, only uses registry for REMOTE operations.
"""

from typing import Dict, Any, Optional, List, Literal

from kiwi_mcp.handlers import SortBy
import json
from pathlib import Path

from kiwi_mcp.utils.logger import get_logger
from kiwi_mcp.utils.resolvers import KnowledgeResolver, get_user_space
from kiwi_mcp.utils.parsers import parse_knowledge_entry
from kiwi_mcp.utils.file_search import search_markdown_files, score_relevance
from kiwi_mcp.utils.metadata_manager import MetadataManager
from kiwi_mcp.utils.validators import ValidationManager, compare_versions
from kiwi_mcp.primitives.integrity import (
    compute_knowledge_integrity,
    short_hash,
)
from kiwi_mcp.utils.schema_validator import SchemaValidator


class KnowledgeHandler:
    """Handler for knowledge operations."""

    def __init__(self, project_path: str):
        """Initialize handler with project path."""
        self.project_path = Path(project_path)
        self.logger = get_logger("knowledge_handler")

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
            from kiwi_mcp.storage.vector import (
                LocalVectorStore,
                EmbeddingService,
                load_vector_config,
            )

            # Load embedding config from environment
            config = load_vector_config()
            embedding_service = EmbeddingService(config)

            vector_path = self.project_path / ".ai" / "vector" / "project"
            vector_path.mkdir(parents=True, exist_ok=True)

            self._vector_store = LocalVectorStore(
                storage_path=vector_path,
                collection_name="project_items",
                embedding_service=embedding_service,
            )
        except ValueError as e:
            # Missing config - vector search disabled
            self.logger.debug(f"Vector store not configured: {e}")
            self._vector_store = None
        except Exception as e:
            self.logger.warning(f"Vector store init failed: {e}")
            self._vector_store = None

    def _compute_knowledge_integrity(self, entry_data: Dict[str, Any]) -> str:
        """
        Compute canonical integrity hash for a knowledge entry.

        Args:
            entry_data: Parsed knowledge entry data

        Returns:
            SHA256 hex digest (64 characters)
        """
        metadata = {
            "category": entry_data.get("category"),
            "entry_type": entry_data.get("entry_type"),
            "tags": entry_data.get("tags", []),
        }

        return compute_knowledge_integrity(
            zettel_id=entry_data.get("zettel_id", ""),
            version=entry_data.get("version", "1.0.0"),
            content=entry_data.get("content", ""),
            metadata=metadata,
        )

    def _verify_knowledge_integrity(self, entry_data: Dict[str, Any], stored_hash: str) -> bool:
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
                    "description": "Unique identifier for the knowledge entry",
                },
                "title": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Title of the knowledge entry",
                },
                "entry_type": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Type of knowledge entry (e.g., pattern, learning, reference, concept, decision, insight, procedure, api_fact, experiment, template, workflow, etc.)",
                },
                "category": {"type": "string", "description": "Category for organization"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization",
                },
                "version": {
                    "type": "string",
                    "pattern": "^\\d+\\.\\d+\\.\\d+$",
                    "description": "Semantic version",
                },
            },
            "required": ["zettel_id", "title", "entry_type"],
        }

    def _validate_frontmatter_with_schema(
        self, entry_data: Dict[str, Any], custom_schema: Optional[Dict[str, Any]] = None
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
                "warnings": [
                    "JSON Schema validation not available - skipping frontmatter validation"
                ],
            }

        # Build combined schema
        base_schema = self._build_base_frontmatter_schema()

        if custom_schema:
            # Merge custom schema properties into base
            if "properties" in custom_schema:
                base_schema["properties"].update(custom_schema["properties"])
            if "required" in custom_schema:
                base_schema["required"] = list(
                    set(base_schema.get("required", []) + custom_schema["required"])
                )

        # Extract frontmatter fields for validation (exclude content and validation fields)
        frontmatter_to_validate = {
            k: v
            for k, v in entry_data.items()
            if k
            not in (
                "content",
                "validated_at",
                "content_hash",
                "integrity",
                "path",
                "source",
                "schema",
            )
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

            # Search local files only
            local_results = self._search_local(query, category, entry_type, tags)
            results.extend(local_results)

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
        source: Literal["project", "user"],
        destination: Optional[Literal["project", "user"]] = None,
        include_relationships: bool = False,
    ) -> Dict[str, Any]:
        """
        Load knowledge entry from specified source.

        Args:
            zettel_id: Entry ID to load
            source: Where to load from - "project" | "user"
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
            is_read_only = destination is None or (source == destination)

            # LOAD FROM PROJECT
            if source == "project":
                search_base = self.project_path / ".ai" / "knowledge"
                file_path = self._find_entry_in_path(zettel_id, search_base)
                if not file_path:
                    return {"error": f"Knowledge entry '{zettel_id}' not found in project"}

                # If destination differs from source, copy the file
                if destination == "user":
                    # Check signature before copying
                    content = file_path.read_text()
                    signature_info = MetadataManager.get_signature_info("knowledge", content)
                    if not signature_info:
                        return {
                            "error": f"Knowledge entry has no signature",
                            "path": str(file_path),
                            "solution": "Use execute action 'sign' to re-validate the entry before copying",
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
                    # Read-only mode: check signature and warn if missing
                    file_content = file_path.read_text()
                    signature_info = MetadataManager.get_signature_info("knowledge", file_content)

                    entry_data = parse_knowledge_entry(file_path)
                    entry_data["source"] = "project"
                    entry_data["path"] = str(file_path)
                    entry_data["mode"] = "read_only"

                    if not signature_info:
                        entry_data["warning"] = {
                            "message": "Knowledge entry has no signature",
                            "solution": "Use execute action 'sign' to re-validate",
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
                # Check signature before copying
                content = file_path.read_text()
                signature_info = MetadataManager.get_signature_info("knowledge", content)
                if not signature_info:
                    return {
                        "error": f"Knowledge entry has no signature",
                        "path": str(file_path),
                        "solution": "Use execute action 'sign' to re-validate the entry before copying",
                    }

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
                # Read-only mode: check signature and warn if missing
                file_content = file_path.read_text()
                signature_info = MetadataManager.get_signature_info("knowledge", file_content)

                entry_data = parse_knowledge_entry(file_path)
                entry_data["source"] = "user"
                entry_data["path"] = str(file_path)
                entry_data["mode"] = "read_only"

                if not signature_info:
                    entry_data["warning"] = {
                        "message": "Knowledge entry has no signature",
                        "solution": "Use execute action 'sign' to re-validate",
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
                                self.logger.warning(
                                    f"Failed to compare versions with user space: {e}"
                                )
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to parse user space knowledge {zettel_id}: {e}"
                        )
            except Exception as e:
                self.logger.warning(f"Failed to check user space for knowledge {zettel_id}: {e}")

        if newest_location and newest_version != current_version:
            return {
                "message": "A newer version of this knowledge entry is available",
                "current_version": current_version,
                "newer_version": newest_version,
                "location": newest_location,
                "suggestion": "Use load() to copy the newer version from user space",
            }
        return None

    async def execute(
        self, action: str, zettel_id: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a knowledge operation.

        Args:
            action: "run", "sign"
            zettel_id: Entry ID
            parameters: Action parameters (title, content, etc.)

        Returns:
            Dict with operation result
        """
        try:
            params = parameters or {}

            if action == "run":
                return await self._run_knowledge(zettel_id, params)
            elif action == "sign":
                return await self._sign_knowledge(zettel_id, params)
            else:
                return {
                    "error": f"Unknown action: {action}",
                    "supported_actions": ["run", "sign"],
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

        # Extract integrity hash from signature
        file_content = file_path.read_text()
        stored_hash = MetadataManager.get_signature_hash(
            "knowledge", file_content, file_path=file_path, project_path=self.project_path
        )

        if not stored_hash:
            return {
                "status": "error",
                "error": "Knowledge entry has no signature",
                "path": str(file_path),
                "hint": "Knowledge entry needs validation",
                "solution": (
                    f"Run: execute(item_type='knowledge', action='sign', "
                    f"item_id='{zettel_id}', parameters={{'location': 'project'}}, "
                    f"project_path='{self.project_path}')"
                ),
            }

        # Parse entry to get version
        try:
            entry_data = parse_knowledge_entry(file_path)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to parse knowledge entry: {e}",
                "path": str(file_path),
            }

        # Verify integrity - recompute hash and compare
        from kiwi_mcp.utils.metadata_manager import compute_unified_integrity

        computed_hash = compute_unified_integrity(
            item_type="knowledge",
            item_id=zettel_id,
            version=entry_data.get("version", "0.0.0"),
            file_content=file_content,
            file_path=file_path,
            metadata=None,  # Let compute_unified_integrity extract what it needs
        )

        if computed_hash != stored_hash:
            return {
                "status": "error",
                "error": "Knowledge entry content has been modified since last validation",
                "details": f"Integrity mismatch for {zettel_id}@{entry_data.get('version')}: computed={short_hash(computed_hash)}, stored={short_hash(stored_hash)}",
                "path": str(file_path),
                "solution": "Run execute(action='sign', ...) to re-validate the entry",
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
                item_id=entry_data.get("zettel_id"),
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
            frontmatter_validation = self._validate_frontmatter_with_schema(
                entry_data, custom_schema
            )

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

            # Get integrity hash from signature
            signature_info = MetadataManager.get_signature_info("knowledge", file_content)
            content_hash = signature_info["hash"] if signature_info else None

            out = {
                "status": "ready",
                "zettel_id": entry_data["zettel_id"],
                "title": entry_data["title"],
                "version": current_version,
                "content": entry_data["content"],
                "entry_type": entry_data.get("entry_type"),
                "category": entry_data.get("category"),
                "tags": entry_data.get("tags", []),
                "integrity": content_hash,
                "integrity_short": content_hash[:12] if content_hash else None,
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

    async def _sign_knowledge(self, zettel_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sign an existing knowledge entry file.

        Expects the knowledge entry file to already exist on disk.
        This action validates the frontmatter, content, and signs the file.
        Always allows re-signing - signatures are included in the validation chain.
        """
        location = params.get("location", "project")
        if location not in ("project", "user"):
            return {
                "error": f"Invalid location: {location}",
                "valid_locations": ["project", "user"],
            }

        # Find the knowledge entry file - try resolver first, then search by location
        file_path = self.resolver.resolve(zettel_id)

        if not file_path or not file_path.exists():
            # Search by location if resolver didn't find it
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
            }

        # Validate path structure
        from kiwi_mcp.utils.paths import validate_path_structure

        determined_location = (
            "project" if str(file_path).startswith(str(self.project_path)) else "user"
        )
        path_validation = validate_path_structure(
            file_path, "knowledge", determined_location, self.project_path
        )
        if not path_validation["valid"]:
            return {
                "error": "Knowledge entry path structure invalid",
                "details": path_validation["issues"],
                "path": str(file_path),
                "solution": "File must be under .ai/knowledge/ with correct structure",
            }

        # Read file content (with existing signature if present - we include it in validation)
        current_content = file_path.read_text()

        # Parse existing entry
        try:
            entry_data = parse_knowledge_entry(file_path)
        except Exception as e:
            return {"error": f"Failed to parse existing entry: {str(e)}", "path": str(file_path)}

        # Validate entry
        validation_result = await ValidationManager.validate_and_embed(
            "knowledge",
            file_path,
            entry_data,
            vector_store=self._vector_store,
            item_id=entry_data.get("zettel_id"),
        )
        if not validation_result["valid"]:
            return {
                "error": "Knowledge entry validation failed",
                "details": validation_result["issues"],
                "path": str(file_path),
                "solution": "Fix validation issues and re-run sign action",
            }

        # Use zettel_id from file's frontmatter (not parameter) - parse_knowledge_entry() already validated match
        file_zettel_id = entry_data["zettel_id"]

        # Explicit validation check before writing (double-check)
        expected_filename = f"{file_zettel_id}.md"
        if file_path.stem != file_zettel_id:
            return {
                "error": "Cannot sign: filename and zettel_id mismatch",
                "problem": {
                    "filename": file_path.name,
                    "frontmatter_zettel_id": file_zettel_id,
                    "expected_filename": expected_filename,
                    "path": str(file_path),
                },
                "solution": {
                    "option_1": {
                        "action": "Rename file to match frontmatter zettel_id",
                        "command": f"mv '{file_path}' '{file_path.parent / expected_filename}'",
                        "then": f"Re-run sign action with item_id='{file_zettel_id}'",
                    },
                    "option_2": {
                        "action": "Update frontmatter to match current filename",
                        "steps": [
                            f"1. Edit {file_path}",
                            f"2. Change frontmatter: zettel_id: {file_path.stem}",
                            f"3. Re-run: mcp__kiwi_mcp__execute(item_type='knowledge', action='sign', item_id='{file_path.stem}')",
                        ],
                    },
                    "option_3": {
                        "action": "Use edit_knowledge directive",
                        "steps": [
                            f"Run: edit_knowledge directive with zettel_id='{file_path.stem}'",
                            f"Update frontmatter zettel_id to '{file_path.stem}' OR rename file to '{expected_filename}'",
                        ],
                    },
                },
            }

        # Strict version requirement - fail if missing
        version = entry_data.get("version")
        if not version or version == "0.0.0":
            return {
                "error": "Knowledge entry validation failed",
                "details": [
                    "Knowledge entry is missing required 'version' in YAML frontmatter. "
                    'Add to frontmatter: version: "1.0.0"'
                ],
                "path": str(file_path),
                "solution": "Add version metadata and re-run sign action",
            }

        # Compute unified integrity hash on content WITHOUT signature
        # This allows re-signing to produce consistent hashes
        from kiwi_mcp.utils.metadata_manager import compute_unified_integrity, MetadataManager

        # Remove existing signature before hashing (chained validation)
        strategy = MetadataManager.get_strategy("knowledge")
        content_without_sig = strategy.remove_signature(current_content)

        # Hash only original content, not signature
        content_hash = compute_unified_integrity(
            item_type="knowledge",
            item_id=file_zettel_id,
            version=version,
            file_content=content_without_sig,  # Hash only original content, not signature
            file_path=file_path,
        )

        # Sign the validated content with unified integrity hash (adds signature at top, removes old signature fields)
        signed_content = MetadataManager.sign_content_with_hash(
            "knowledge",
            content_without_sig,
            content_hash,
            file_path=file_path,
            project_path=self.project_path,
        )
        file_path.write_text(signed_content)

        # Get signature info for response
        signature_info = MetadataManager.get_signature_info(
            "knowledge", signed_content, file_path=file_path, project_path=self.project_path
        )

        return {
            "status": "signed",
            "zettel_id": file_zettel_id,
            "path": str(file_path),
            "location": determined_location,
            "category": entry_data.get("category"),
            "entry_type": entry_data.get("entry_type"),
            "signature": signature_info,
            "integrity": content_hash,
            "integrity_short": content_hash[:12],
        }
