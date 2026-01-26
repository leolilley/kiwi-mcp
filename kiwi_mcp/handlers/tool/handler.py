"""
Tool handler for kiwi-mcp.

Implements search, load, execute operations for tools.
Handles LOCAL file operations directly, only uses registry for REMOTE operations.

Tool handler with executor pattern support.
"""

from typing import Dict, Any, Optional, List, Literal
from pathlib import Path

from kiwi_mcp.handlers import SortBy
from kiwi_mcp.api.tool_registry import ToolRegistry
from kiwi_mcp.utils.logger import get_logger
from kiwi_mcp.utils.resolvers import ToolResolver, get_user_space
from kiwi_mcp.utils.file_search import search_python_files, score_relevance
from kiwi_mcp.utils.output_manager import OutputManager, truncate_for_response
from kiwi_mcp.utils.metadata_manager import MetadataManager
from kiwi_mcp.utils.validators import ValidationManager, compare_versions
from kiwi_mcp.utils.extensions import get_tool_extensions
from kiwi_mcp.schemas import extract_tool_metadata, validate_tool_metadata
from kiwi_mcp.primitives.executor import PrimitiveExecutor, ExecutionResult


class ToolHandler:
    """Handler for tool operations with executor abstraction."""

    def __init__(self, project_path: str):
        """Initialize handler with project path."""
        self.project_path = Path(project_path)
        self.resolver = ToolResolver(project_path=self.project_path)
        self.registry = ToolRegistry()
        self.logger = get_logger("tool_handler")

        # Output manager for saving large results
        self.output_manager = OutputManager(project_path=self.project_path)

        # Initialize primitive executor with project path for local chain resolution
        self.primitive_executor = PrimitiveExecutor(
            project_path=self.project_path
        )
        
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

    def _has_git(self) -> bool:
        """Check if project is in a git repository."""
        try:
            import subprocess

            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"], cwd=self.project_path, capture_output=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    async def search(
        self, query: str, source: str = "all", limit: int = 10, sort_by: SortBy = "score"
    ) -> Dict[str, Any]:
        """
        Search for tools/scripts.

        Args:
            query: Search query
            source: "local", "registry", or "all"
            limit: Max results
            sort_by: Sort method ("score", "date", "name")

        Returns:
            Dict with search results
        """
        results = []

        # Search local files
        if source in ["local", "all"]:
            local_results = await self._search_local(query, limit)
            results.extend(local_results)

        # Search registry
        if source in ["registry", "all"]:
            registry_results = await self._search_registry(query, limit, sort_by)
            results.extend(registry_results)

        # Sort and limit
        if sort_by == "score":
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
        elif sort_by == "date":
            results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        elif sort_by == "name":
            results.sort(key=lambda x: x.get("name", ""))

        return {"results": results[:limit], "total": len(results), "query": query, "source": source}

    async def _search_local(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search local tool/script files."""
        results = []

        search_dirs = []
        
        project_tools = self.project_path / ".ai" / "tools"
        if project_tools.exists():
            search_dirs.append(project_tools)
        
        user_tools = get_user_space() / "tools"
        if user_tools.exists():
            search_dirs.append(user_tools)

        # Search each directory
        for search_dir in search_dirs:
            files = search_python_files(search_dir, query)

            for file_path in files:
                try:
                    meta = extract_tool_metadata(file_path, self.project_path)

                    searchable_text = f"{meta['name']} {meta.get('description', '')}"
                    score = score_relevance(searchable_text, query.split())

                    results.append(
                        {
                            "name": meta["name"],
                            "description": meta.get("description", ""),
                            "source": "project" if ".ai/" in str(file_path) else "user",
                            "path": str(file_path),
                            "score": score,
                            "tool_type": meta.get("tool_type", "unknown"),
                        }
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to parse {file_path}: {e}")

        return results

    async def _search_registry(
        self, query: str, limit: int, sort_by: SortBy
    ) -> List[Dict[str, Any]]:
        """Search registry for tools using ToolRegistry."""
        if not self.registry.is_configured:
            return []

        try:
            # ToolRegistry.search returns tools with source already set
            results = await self.registry.search(query, limit=limit)
            return results
        except Exception as e:
            self.logger.error(f"Registry search failed: {e}")
            return []

    def _detect_tool_type(self, file_path: Path) -> str:
        """Detect tool type using schema-driven extraction."""
        try:
            meta = extract_tool_metadata(file_path, self.project_path)
            return meta.get("tool_type") or "unknown"
        except Exception:
            return "unknown"

    async def load(
        self,
        tool_name: str,
        source: Literal["project", "user", "registry"],
        destination: Optional[Literal["project", "user"]] = None,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Load tool from specified source.

        Args:
            tool_name: Name of tool
            source: Where to load from - "project" | "user" | "registry"
            destination: Where to copy to (optional). If None or same as source, read-only mode.

        Returns:
            Dict with tool details
        """
        self.logger.info(
            f"ToolHandler.load: tool={tool_name}, source={source}, destination={destination}"
        )

        try:
            # Determine if this is read-only mode (no copy)
            is_read_only = destination is None or (source == destination and source != "registry")

            # LOAD FROM REGISTRY
            if source == "registry":
                if not self.registry.is_configured:
                    return {
                        "error": "Registry not configured",
                        "message": "Set SUPABASE_URL and SUPABASE_KEY to load from registry",
                    }

                # Get from registry (version defaults to latest if not specified)
                tool_data = await self.registry.get(tool_name, version=version)
                if not tool_data:
                    return {"error": f"Tool '{tool_name}' not found in registry"}

                effective_destination = destination or "project"

                if effective_destination == "user":
                    target_dir = get_user_space() / "tools"
                else:
                    target_dir = self.project_path / ".ai" / "tools"

                target_dir.mkdir(parents=True, exist_ok=True)

                # Extract category: check manifest first, then derive from tool_type
                manifest = tool_data.get("manifest", {})
                category = manifest.get("category") or tool_data.get("category")
                
                # If no category, derive from tool_type (e.g., "primitive" -> "primitives")
                if not category:
                    tool_type = manifest.get("tool_type") or tool_data.get("tool_type")
                    if tool_type:
                        # Map tool_type to category directory
                        type_to_category = {
                            "primitive": "primitives",
                            "runtime": "runtimes",
                            "mcp_server": "mcp_servers",
                            "mcp_tool": "mcp_tools",
                            "script": "scripts",
                            "api": "apis",
                        }
                        category = type_to_category.get(tool_type, tool_type + "s")
                    else:
                        return {
                            "error": f"Tool '{tool_name}' missing both 'category' and 'tool_type' fields",
                            "message": "Cannot determine installation directory for tool",
                        }
                
                category_dir = target_dir / category
                category_dir.mkdir(exist_ok=True)

                # Write script file (for now, treating as Python script)
                target_file = category_dir / f"{tool_name}.py"
                target_file.write_text(tool_data["content"])

                self.logger.info(f"Downloaded tool from registry to: {target_file}")

                meta = extract_tool_metadata(target_file, self.project_path)

                return {
                    "name": tool_name,
                    "path": str(target_file),
                    "content": tool_data["content"],
                    "source": "registry",
                    "destination": effective_destination,
                    "metadata": meta,
                    "message": f"Tool downloaded from registry to {effective_destination}",
                }

            # LOAD FROM LOCAL (project or user)
            else:
                file_path = self.resolver.resolve(tool_name)
                if not file_path:
                    return {"error": f"Tool '{tool_name}' not found locally"}

                if not is_read_only:
                    if destination == "user":
                        target_dir = get_user_space() / "tools"
                    else:
                        target_dir = self.project_path / ".ai" / "tools"

                    target_dir.mkdir(parents=True, exist_ok=True)

                    # Copy with same relative structure
                    relative_path = file_path.relative_to(
                        file_path.parents[1]
                    )  # Remove scripts/ part
                    target_file = target_dir / relative_path

                    # Create target directory structure
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file
                    target_file.write_text(file_path.read_text())

                    self.logger.info(f"Copied tool from {source} to {destination}: {target_file}")
                    file_path = target_file  # Use new path for metadata extraction

                meta = extract_tool_metadata(file_path, self.project_path)

                result = {
                    "name": tool_name,
                    "path": str(file_path),
                    "content": file_path.read_text(),
                    "source": source,
                    "metadata": meta,
                }

                if not is_read_only:
                    result["destination"] = destination
                    result["message"] = f"Tool copied from {source} to {destination}"

                return result

        except Exception as e:
            self.logger.error(f"Load failed: {e}")
            return {"error": str(e)}

    async def execute(
        self,
        action: str,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a tool or perform tool operation.

        Args:
            action: "run", "publish", "delete", "sign"
            tool_name: Name of tool to execute
            parameters: Tool parameters (for run action)
            dry_run: If True, validate without executing

        Returns:
            Dict with execution result
        """
        # Extract dry_run from parameters if present
        params = parameters or {}
        if params and "dry_run" in params:
            dry_run = params.pop("dry_run")

        try:
            if action == "run":
                return await self._run_tool(tool_name, params, dry_run)

            elif action == "publish":
                return await self._publish_tool(tool_name, params.get("version"))

            elif action == "delete":
                return await self._delete_tool(tool_name, params.get("confirm", False))

            elif action == "sign":
                return await self._sign_tool(
                    tool_name,
                    params.get("location", "project"),
                    params.get("category"),
                )

            else:
                return {"error": f"Unknown action: {action}"}

        except Exception as e:
            self.logger.error(f"Execute failed: {e}")
            return {"error": str(e)}

    async def _run_tool(
        self, tool_name: str, params: Dict[str, Any], dry_run: bool
    ) -> Dict[str, Any]:
        """Execute a tool using appropriate executor."""
        # Find tool file
        file_path = self.resolver.resolve(tool_name)
        if not file_path:
            return {
                "error": f"Tool '{tool_name}' not found locally",
                "suggestion": "Use load() to download from registry first",
            }

        # Extract metadata using schema
        tool_meta = extract_tool_metadata(file_path, self.project_path)

        # Extract integrity hash from signature
        file_content = file_path.read_text()
        stored_hash = MetadataManager.get_signature_hash("tool", file_content, file_path=file_path, project_path=self.project_path)

        if not stored_hash:
            return {
                "status": "error",
                "error": "Tool has no signature",
                "path": str(file_path),
                "hint": "Tool needs validation",
                "solution": (
                    f"Run: execute(item_type='tool', action='sign', "
                    f"item_id='{tool_name}', parameters={{'location': 'project'}}, "
                    f"project_path='{self.project_path}')"
                ),
            }

        # Get version - must be present
        version = tool_meta.get("version")
        if not version or version == "0.0.0":
            return {
                "status": "error",
                "error": "Tool validation failed",
                "details": ['Tool is missing required version. Add at module level: __version__ = "1.0.0"'],
                "path": str(file_path),
                "solution": "Add version metadata and retry",
            }
        
        # Verify integrity using IntegrityVerifier
        from kiwi_mcp.primitives.integrity_verifier import IntegrityVerifier
        verifier = IntegrityVerifier()
        
        verification = verifier.verify_single_file(
            item_type="tool",
            item_id=tool_name,
            version=version,
            file_path=file_path,
            stored_hash=stored_hash,
            project_path=self.project_path
        )
        
        if not verification.success:
            return {
                "status": "error",
                "error": "Tool content has been modified since last validation",
                "details": verification.error,
                "path": str(file_path),
                "solution": "Run execute(action='sign', ...) to re-validate the tool",
            }

        # Validate using schema
        validation_result = validate_tool_metadata(tool_meta)
        if not validation_result["valid"]:
            return {
                "status": "error",
                "error": "Tool validation failed",
                "details": validation_result["issues"],
                "path": str(file_path),
                "warnings": validation_result.get("warnings", []),
            }

        current_version = tool_meta.get("version")
        current_source = (
            "project"
            if str(file_path).startswith(str(self.resolver.project_tools))
            else "user"
        )
        version_warning = await self._check_for_newer_version(
            tool_name, current_version, current_source
        )

        if dry_run:
            response = {
                "status": "validation_passed",
                "message": "Tool is ready to execute",
                "path": str(file_path),
                "metadata": tool_meta,
            }
            if version_warning:
                response["version_warning"] = version_warning
            return response

        # Execute using PrimitiveExecutor with chain resolution
        try:
            # Inject file path and project path for subprocess execution
            exec_params = params.copy()
            exec_params["_file_path"] = str(file_path)
            exec_params["_project_path"] = str(self.project_path)
            result = await self.primitive_executor.execute(tool_meta["name"], exec_params)

            if result.success:
                response = {
                    "status": "success",
                    "data": result.data,
                    "metadata": {
                        "duration_ms": result.duration_ms,
                        "tool_type": tool_meta.get("tool_type"),
                        "primitive_type": result.metadata.get("type")
                        if result.metadata
                        else "unknown",
                    },
                }

                if tool_meta.get("mutates_state") and self._has_git():
                    response["checkpoint_recommended"] = True
                    tool_name_val = tool_meta.get("name", "unknown")
                    response["checkpoint_hint"] = (
                        "This tool mutates state. Consider running git_checkpoint: "
                        f"execute(item_type='directive', action='run', item_id='git_checkpoint', "
                        f"parameters={{'operation': '{tool_name_val}'}})"
                    )

                # Add version warning if newer version exists
                if version_warning:
                    response["version_warning"] = version_warning

                return response
            else:
                return {
                    "status": "error",
                    "error": result.error or "Unknown execution error",
                    "metadata": {
                        "duration_ms": result.duration_ms,
                        "tool_type": tool_meta.get("tool_type"),
                        "primitive_type": result.metadata.get("type")
                        if result.metadata
                        else "unknown",
                    },
                }

        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _publish_tool(self, tool_name: str, version: Optional[str]) -> Dict[str, Any]:
        """
        Publish tool to registry.
        
        Enforces hash validation - content must be validated before publishing.
        """
        # Find local tool file
        file_path = self.resolver.resolve(tool_name)
        if not file_path:
            return {
                "error": f"Tool '{tool_name}' not found locally",
                "suggestion": "Create tool first before publishing",
            }
        
        # Extract integrity hash from signature
        file_content = file_path.read_text()
        stored_hash = MetadataManager.get_signature_hash("tool", file_content, file_path=file_path, project_path=self.project_path)
        
        if not stored_hash:
            return {
                "error": "Cannot publish: tool has no signature",
                "path": str(file_path),
                "hint": "Tools must be validated before publishing",
                "solution": (
                    f"Run: execute(item_type='tool', action='sign', "
                    f"item_id='{tool_name}', parameters={{'location': 'project'}}, "
                    f"project_path='{self.project_path}')"
                ),
            }

        # Verify integrity using IntegrityVerifier
        tool_meta = extract_tool_metadata(file_path, self.project_path)
        
        # Get version - must be present
        version = tool_meta.get("version")
        if not version or version == "0.0.0":
            return {
                "error": "Cannot publish: tool validation failed",
                "details": ['Tool is missing required version. Add at module level: __version__ = "1.0.0"'],
                "path": str(file_path),
                "solution": "Add version metadata and retry",
            }
        
        from kiwi_mcp.primitives.integrity_verifier import IntegrityVerifier
        verifier = IntegrityVerifier()
        
        verification = verifier.verify_single_file(
            item_type="tool",
            item_id=tool_name,
            version=version,
            file_path=file_path,
            stored_hash=stored_hash,
            project_path=self.project_path
        )
        
        if not verification.success:
            return {
                "error": "Tool content has been modified since last validation",
                "details": verification.error,
                "path": str(file_path),
                "solution": "Run execute(action='sign', ...) to re-validate before publishing",
            }
        
        # Validate using schema
        validation_result = validate_tool_metadata(tool_meta)
        if not validation_result["valid"]:
            return {
                "error": "Tool validation failed",
                "details": validation_result["issues"],
                "path": str(file_path),
            }
        
        publish_version = version or tool_meta.get("version")
        files = {file_path.name: file_content}
        
        try:
            result = await self.registry.publish(
                tool_id=tool_name,
                version=publish_version,
                tool_type=tool_meta.get("tool_type"),
                executor_id=tool_meta.get("executor_id"),
                manifest=tool_meta,
                files=files,
                category=tool_meta.get("category"),
                description=tool_meta.get("description"),
                changelog=f"Published version {publish_version}",
            )
            
            if "error" in result:
                return result
            
            return {
                "status": "published",
                "tool_id": tool_name,
                "version": publish_version,
                "registry_result": result,
                "path": str(file_path),
            }
        except Exception as e:
            self.logger.error(f"Publish failed: {e}")
            return {"error": f"Publish failed: {e}"}

    async def _delete_tool(self, tool_name: str, confirm: bool) -> Dict[str, Any]:
        """Delete tool from local and/or registry."""
        if not confirm:
            return {
                "error": "Delete requires confirmation",
                "required": {"confirm": True},
                "example": "parameters={'confirm': True}",
            }
        
        deleted = []
        
        # Delete local file
        file_path = self.resolver.resolve(tool_name)
        if file_path:
            file_path.unlink()
            deleted.append("local")
            
            # Also delete manifest if present
            manifest_path = file_path.parent / "tool.yaml"
            if manifest_path.exists():
                manifest_path.unlink()
        
        # Delete from registry
        if self.registry.is_configured:
            try:
                result = await self.registry.delete(tool_name, confirm=True)
                if "error" not in result:
                    deleted.append("registry")
            except Exception as e:
                self.logger.warning(f"Registry delete failed: {e}")
        
        if not deleted:
            return {"error": f"Tool '{tool_name}' not found in any location"}
        
        return {"status": "deleted", "tool_id": tool_name, "deleted_from": deleted}

    async def _sign_tool(
        self, tool_name: str, location: str = "project", category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate and sign an existing tool file.

        Expects the tool file to already exist on disk.
        This action validates the Python/metadata and signs the file.
        Always allows re-signing - signatures are included in the validation chain.
        """
        if location not in ("project", "user"):
            return {
                "error": f"Invalid location: {location}",
                "valid_locations": ["project", "user"],
            }
        
        # Find the tool file - try resolver first, then search by location
        file_path = self.resolver.resolve(tool_name)
        
        if not file_path or not file_path.exists():
            # Search by location if resolver didn't find it
            if location == "project":
                search_base = self.project_path / ".ai" / "tools"
            else:
                search_base = get_user_space() / "tools"
            
            # Search for the tool file (all supported extensions)
            supported_extensions = get_tool_extensions(self.project_path)
            if search_base.exists():
                for ext in supported_extensions:
                    for candidate in Path(search_base).rglob(f"{tool_name}{ext}"):
                        if candidate.stem == tool_name:
                            file_path = candidate
                            break
                    if file_path:
                        break
        
        if not file_path or not file_path.exists():
            category_hint = category or "utility"
            supported_extensions = get_tool_extensions(self.project_path)
            ext_list = ", ".join(supported_extensions)
            search_base_ref = search_base if 'search_base' in locals() else self.project_path / ".ai" / "tools"
            return {
                "error": f"Tool file not found: {tool_name}",
                "hint": f"Create the file first at .ai/tools/{category_hint}/{tool_name}<ext> (supported: {ext_list})",
                "searched_in": str(search_base_ref),
            }
        
        # Validate path structure
        from kiwi_mcp.utils.paths import validate_path_structure
        determined_location = "project" if str(file_path).startswith(str(self.project_path)) else "user"
        path_validation = validate_path_structure(
            file_path, "tool", determined_location, self.project_path
        )
        if not path_validation["valid"]:
            return {
                "error": "Tool path structure invalid",
                "details": path_validation["issues"],
                "path": str(file_path),
                "solution": "File must be under .ai/tools/ with correct structure",
            }
        
        # Read file content (may include existing signature)
        file_content = file_path.read_text()
        
        # Extract and validate using schema
        try:
            tool_meta = extract_tool_metadata(file_path, self.project_path)
            validation_result = validate_tool_metadata(tool_meta)
            if not validation_result["valid"]:
                return {
                    "error": "Tool validation failed",
                    "details": validation_result["issues"],
                    "warnings": validation_result.get("warnings", []),
                    "path": str(file_path),
                    "solution": "Fix validation issues and re-run sign action",
                }
        except Exception as e:
            return {
                "error": f"Failed to validate tool: {e}",
                "path": str(file_path),
            }
        
        # Strict version requirement - fail if missing
        version = tool_meta.get("version")
        if not version or version == "0.0.0":
            return {
                "error": "Tool validation failed",
                "details": ['Tool is missing required version. Add at module level: __version__ = "1.0.0"'],
                "path": str(file_path),
                "solution": "Add version metadata and re-run sign action",
            }
        
        # Compute unified integrity hash on content WITHOUT signature
        # This allows re-signing to produce consistent hashes
        from kiwi_mcp.utils.metadata_manager import compute_unified_integrity, MetadataManager
        
        # Remove existing signature before hashing (chained validation)
        strategy = MetadataManager.get_strategy("tool", file_path=file_path, project_path=self.project_path)
        content_without_sig = strategy.remove_signature(file_content)
        
        content_hash = compute_unified_integrity(
            item_type="tool",
            item_id=tool_name,
            version=version,
            file_content=content_without_sig,  # Hash only original content, not signature
            file_path=file_path
        )
        
        # Sign the validated content with unified integrity hash
        signed_content = MetadataManager.sign_content_with_hash(
            "tool", file_content, content_hash, file_path=file_path, project_path=self.project_path
        )
        file_path.write_text(signed_content)
        
        # Get signature info for response
        signature_info = MetadataManager.get_signature_info("tool", signed_content, file_path=file_path, project_path=self.project_path)
        
        return {
            "status": "signed",
            "tool_id": tool_name,
            "path": str(file_path),
            "location": determined_location,
            "category": tool_meta.get("category"),
            "signature": signature_info,
        }


    async def _check_for_newer_version(
        self,
        tool_name: str,
        current_version: str,
        current_source: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Check for newer versions of a tool in other locations.

        Args:
            tool_name: Name of tool
            current_version: Current version being run
            current_source: "project" or "user"

        Returns:
            Warning dict if newer version found, None otherwise
        """
        newest_version = current_version
        newest_location = None

        # Check user space (if running from project)
        if current_source == "project":
            try:
                user_file_path = self.resolver.resolve(tool_name)
                # Check if it's in user space
                if user_file_path and str(user_file_path).startswith(str(get_user_space() / "tools")):
                    try:
                        user_tool_meta = extract_tool_metadata(user_file_path, self.project_path)
                        user_version = user_tool_meta.get("version")
                        if user_version:
                            try:
                                if compare_versions(current_version, user_version) < 0:
                                    # User version is newer
                                    if compare_versions(newest_version, user_version) < 0:
                                        newest_version = user_version
                                        newest_location = "user"
                            except Exception as e:
                                self.logger.warning(
                                    f"Failed to compare versions with user space: {e}"
                                )
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to parse user space tool {tool_name}: {e}"
                        )
            except Exception as e:
                self.logger.warning(
                    f"Failed to check user space for tool {tool_name}: {e}"
                )

        # Check registry (always)
        try:
            registry_data = await self.registry.get(tool_name)
            if registry_data and registry_data.get("version"):
                registry_version = registry_data["version"]
                try:
                    if compare_versions(current_version, registry_version) < 0:
                        # Registry version is newer
                        if compare_versions(newest_version, registry_version) < 0:
                            newest_version = registry_version
                            newest_location = "registry"
                except Exception as e:
                    self.logger.warning(f"Failed to compare versions with registry: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to check registry for tool {tool_name}: {e}")

        # Return warning if newer version found
        if newest_location and newest_version != current_version:
            suggestion = (
                f"Use load() to download the newer version from {newest_location}"
                if newest_location == "registry"
                else f"Use load() to copy the newer version from user space"
            )
            return {
                "message": "A newer version of this tool is available",
                "current_version": current_version,
                "newer_version": newest_version,
                "location": newest_location,
                "suggestion": suggestion,
            }

        return None
