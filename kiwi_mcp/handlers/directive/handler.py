"""
Directive handler for kiwi-mcp.

Implements search, load, execute operations for directives.
Handles LOCAL file operations directly, only uses registry for REMOTE operations.
"""

from typing import Dict, Any, Optional, List, Literal

from kiwi_mcp.handlers import SortBy
from pathlib import Path
import xml.etree.ElementTree as ET
import re

from kiwi_mcp.api.directive_registry import DirectiveRegistry
from kiwi_mcp.utils.logger import get_logger
from kiwi_mcp.utils.resolvers import DirectiveResolver, get_user_space
from kiwi_mcp.utils.parsers import parse_directive_file
from kiwi_mcp.utils.file_search import search_markdown_files, score_relevance
from kiwi_mcp.utils.metadata_manager import MetadataManager
from kiwi_mcp.utils.validators import ValidationManager, compare_versions
from kiwi_mcp.mcp import MCPClientPool, SchemaCache


class DirectiveHandler:
    """Handler for directive operations."""

    def __init__(self, project_path: str):
        """Initialize handler with project path."""
        self.project_path = Path(project_path)
        self.logger = get_logger("directive_handler")
        self.registry = DirectiveRegistry()  # Only for remote operations

        # Local file handling
        self.resolver = DirectiveResolver(self.project_path)
        self.search_paths = [self.resolver.project_directives, self.resolver.user_directives]

        # MCP support
        self.mcp_pool = MCPClientPool()
        self.schema_cache = SchemaCache()

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
        date_to: Optional[str] = None,
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
        self.logger.info(
            f"DirectiveHandler.search: query='{query}', source={source}, limit={limit}"
        )

        try:
            results = []

            # Search local files
            if source in ("local", "all"):
                local_results = self._search_local(
                    query, categories, subcategories, tags, tech_stack
                )
                results.extend(local_results)

            # Search registry
            if source in ("registry", "all"):
                try:
                    # Registry search only accepts: query, category (singular), limit, tech_stack
                    category_filter = categories[0] if categories and len(categories) > 0 else None

                    registry_results = await self.registry.search(
                        query=query, category=category_filter, limit=limit, tech_stack=tech_stack
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
                        x.get("name", "").lower(),
                        source_priority.get(x.get("source", ""), 99),
                    )
                )
            else:  # "score" (default)
                results.sort(
                    key=lambda x: (-x.get("score", 0), source_priority.get(x.get("source", ""), 99))
                )

            # Apply limit
            results = results[:limit]

            return {"query": query, "source": source, "results": results, "total": len(results)}
        except Exception as e:
            return {"error": str(e), "message": "Failed to search directives"}

    async def load(
        self,
        directive_name: str,
        source: Literal["project", "user", "registry"],
        destination: Optional[Literal["project", "user"]] = None,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Load directive from specified source.

        Args:
            directive_name: Name of directive to load
            source: Where to load from - "project" | "user" | "registry"
            destination: Where to copy to (optional). If None or same as source, read-only mode.
            version: Specific version to load (registry only)

        Returns:
            Dict with directive details and metadata
        """
        self.logger.info(
            f"DirectiveHandler.load: directive={directive_name}, source={source}, destination={destination}"
        )

        try:
            # Determine if this is read-only mode (no copy)
            # Read-only when: destination is None OR destination equals source (for non-registry)
            is_read_only = destination is None or (source == destination and source != "registry")

            # LOAD FROM REGISTRY
            if source == "registry":
                # Fetch from registry
                registry_data = await self.registry.get(name=directive_name, version=version)

                if not registry_data:
                    return {"error": f"Directive '{directive_name}' not found in registry"}

                # Extract metadata
                content = registry_data.get("content")
                category = registry_data.get("category", "core")
                subcategory = registry_data.get("subcategory")

                if not content:
                    return {"error": f"Directive '{directive_name}' has no content"}

                # For registry, default destination to "project" if not specified
                effective_destination = destination or "project"

                # Determine target path based on destination
                if effective_destination == "user":
                    base_path = Path.home() / ".ai" / "directives"
                else:  # destination == "project"
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

                # Verify hash after download for safety
                file_content = target_path.read_text()
                signature_status = MetadataManager.verify_signature("directive", file_content)

                # Parse and return
                directive_data = parse_directive_file(target_path)
                directive_data["source"] = "registry"
                directive_data["destination"] = effective_destination
                directive_data["path"] = str(target_path)

                # Add warning if signature is invalid or modified (registry content should be valid)
                if signature_status and signature_status.get("status") in ["modified", "invalid"]:
                    directive_data["warning"] = {
                        "message": "Registry directive content signature is invalid or modified - content may be corrupted",
                        "signature": signature_status,
                        "solution": "Use execute action 'update' or 'create' to re-validate the directive",
                    }
                    self.logger.warning(
                        f"Registry directive '{directive_name}' has invalid signature: {signature_status}"
                    )

                return directive_data

            # LOAD FROM PROJECT
            if source == "project":
                search_base = self.project_path / ".ai" / "directives"
                file_path = self._find_in_path(directive_name, search_base)
                if not file_path:
                    return {"error": f"Directive '{directive_name}' not found in project"}

                # If destination differs from source, copy the file
                if destination == "user":
                    # Copy from project to user space
                    content = file_path.read_text()

                    # Verify hash before copying
                    signature_status = MetadataManager.verify_signature("directive", content)
                    if signature_status:
                        if signature_status.get("status") in ["modified", "invalid"]:
                            return {
                                "error": f"Directive content has been modified or signature is invalid",
                                "signature": signature_status,
                                "path": str(file_path),
                                "solution": "Use execute action 'update' or 'create' to re-validate the directive before copying",
                            }

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
                    # Read-only mode: verify and warn, but don't block
                    file_content = file_path.read_text()
                    signature_status = MetadataManager.verify_signature("directive", file_content)

                    directive_data = parse_directive_file(file_path)
                    directive_data["source"] = "project"
                    directive_data["path"] = str(file_path)
                    directive_data["mode"] = "read_only"

                    if signature_status and signature_status.get("status") in [
                        "modified",
                        "invalid",
                    ]:
                        directive_data["warning"] = {
                            "message": "Directive content has been modified or signature is invalid",
                            "signature": signature_status,
                            "solution": "Use execute action 'update' or 'create' to re-validate",
                        }

                    return directive_data

            # LOAD FROM USER
            # source == "user" (only remaining option due to Literal typing)
            search_base = Path.home() / ".ai" / "directives"
            file_path = self._find_in_path(directive_name, search_base)
            if not file_path:
                return {"error": f"Directive '{directive_name}' not found in user space"}

            # If destination differs from source, copy the file
            if destination == "project":
                # Copy from user to project space
                content = file_path.read_text()

                # Verify hash before copying
                signature_status = MetadataManager.verify_signature("directive", content)
                if signature_status:
                    if signature_status.get("status") in ["modified", "invalid"]:
                        return {
                            "error": f"Directive content has been modified or signature is invalid",
                            "signature": signature_status,
                            "path": str(file_path),
                            "solution": "Use execute action 'update' or 'create' to re-validate the directive before copying",
                        }

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
                # Read-only mode: verify and warn, but don't block
                file_content = file_path.read_text()
                signature_status = MetadataManager.verify_signature("directive", file_content)

                directive_data = parse_directive_file(file_path)
                directive_data["source"] = "user"
                directive_data["path"] = str(file_path)
                directive_data["mode"] = "read_only"

                if signature_status and signature_status.get("status") in ["modified", "invalid"]:
                    directive_data["warning"] = {
                        "message": "Directive content has been modified or signature is invalid",
                        "signature": signature_status,
                        "solution": "Use execute action 'update' or 'create' to re-validate",
                    }

                return directive_data
        except Exception as e:
            return {"error": str(e), "message": f"Failed to load directive '{directive_name}'"}

    async def execute(
        self, action: str, directive_name: str, parameters: Optional[Dict[str, Any]] = None
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
                    "supported_actions": ["run", "publish", "delete", "create", "update"],
                }
        except Exception as e:
            return {
                "error": str(e),
                "message": f"Failed to execute action '{action}' on directive '{directive_name}'",
            }

    def _search_local(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        subcategories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        tech_stack: Optional[List[str]] = None,
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

                    results.append(
                        {
                            "name": directive["name"],
                            "description": directive["description"],
                            "version": directive["version"],
                            "score": score,
                            "source": "project" if is_project else "user",
                            "path": str(file_path),
                        }
                    )
            except Exception as e:
                self.logger.warning(f"Error parsing {file_path}: {e}")

        return results

    async def _run_directive(self, directive_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Load and return directive for agent to execute."""
        # Find local directive file
        file_path = self.resolver.resolve(directive_name)
        if not file_path:
            return {
                "error": f"Directive '{directive_name}' not found locally",
                "suggestion": "Use load() to download from registry first",
            }

        # Parse directive file
        try:
            directive_data = parse_directive_file(file_path)
            legacy_warning = directive_data.get("legacy_warning")

            # Validate directive using centralized validator
            validation_result = ValidationManager.validate("directive", file_path, directive_data)
            if not validation_result["valid"]:
                # Format error response
                error_response = {
                    "error": "Directive validation failed",
                    "details": validation_result["issues"],
                    "path": str(file_path),
                }
                # Add specific error context
                if any("permission" in issue.lower() for issue in validation_result["issues"]):
                    error_response["error"] = "Directive permissions not satisfied"
                    error_response["permissions_required"] = directive_data.get("permissions", [])
                elif any("model" in issue.lower() for issue in validation_result["issues"]):
                    error_response["error"] = "Directive model not valid"
                    model_data = directive_data.get("model") or directive_data.get("model_class")
                    error_response["model_found"] = model_data
                    error_response["hint"] = (
                        "The <model> tag must have a 'tier' attribute. Example: <model tier=\"reasoning\">...</model>"
                    )
                elif any(
                    "code block" in issue.lower()
                    or "closing" in issue.lower()
                    or "must end" in issue.lower()
                    or "unexpected content" in issue.lower()
                    for issue in validation_result["issues"]
                ):
                    error_response["error"] = "Directive XML structure not valid"
                    error_response["hint"] = (
                        "The directive XML must end with </directive> tag followed immediately by the closing ```. No content should appear after the closing tag."
                    )
                    error_response["solution"] = {
                        "message": "Remove any content after the closing ``` in the directive file",
                        "option_1": f"Use edit_directive directive: Run directive 'edit_directive' with directive_name='{directive_name}' to fix the XML structure",
                        "option_2": f"Edit the file directly: Remove lines after ``` in {file_path}. Then revalidate the directive with 'update' or 'create' action",
                        "example": '```xml\n<directive name="example" version="1.0.0">\n  ...\n</directive>\n```',
                    }
                return error_response

            # ENFORCE hash validation - ALWAYS check, never skip
            file_content = file_path.read_text()
            signature_status = MetadataManager.verify_signature("directive", file_content)

            # Block execution if signature is missing, invalid, or modified
            # Missing signature means directive was created manually (bypassing create_directive)
            if signature_status is None:
                # Check if it has pending-validation marker
                has_pending = "kiwi-mcp:pending-validation" in file_content
                return {
                    "error": "Directive has no valid signature",
                    "status": "missing",
                    "path": str(file_path),
                    "hint": "Directives must be created via create_directive, not create_file"
                    if has_pending
                    else "Directive needs validation",
                    "solution": (
                        f"Run: execute(item_type='directive', action='update', "
                        f"item_id='{directive_name}', parameters={{'location': 'project'}}, "
                        f"project_path='{self.project_path}')"
                    ),
                }

            if signature_status.get("status") == "modified":
                return {
                    "error": "Directive content has been modified since last validation",
                    "signature": signature_status,
                    "path": str(file_path),
                    "solution": "Use execute action 'update' or 'create' to re-validate the directive",
                }
            elif signature_status.get("status") == "invalid":
                return {
                    "error": "Directive signature is invalid",
                    "signature": signature_status,
                    "path": str(file_path),
                    "solution": "Use execute action 'update' or 'create' to re-validate the directive",
                }

            # Extract process steps and inputs for execution
            parsed = directive_data["parsed"]

            # Get process steps from parsed XML
            process_steps = []
            if "process" in parsed and "step" in parsed["process"]:
                steps = parsed["process"]["step"]
                # Handle single step vs list of steps
                if isinstance(steps, dict):
                    steps = [steps]
                for step in steps:
                    attrs = step.get("_attrs", {})
                    process_steps.append(
                        {
                            "name": attrs.get("name", ""),
                            "description": step.get("description", ""),
                            "action": step.get("action", ""),
                        }
                    )

            # Get inputs from parsed XML
            inputs_spec = []
            if "inputs" in parsed and "input" in parsed["inputs"]:
                inp_list = parsed["inputs"]["input"]
                if isinstance(inp_list, dict):
                    inp_list = [inp_list]
                for inp in inp_list:
                    attrs = inp.get("_attrs", {})
                    inputs_spec.append(
                        {
                            "name": attrs.get("name", ""),
                            "type": attrs.get("type", "string"),
                            "required": attrs.get("required", "false") == "true",
                            "description": inp.get("_text", ""),
                        }
                    )

            # Validate required inputs are provided
            missing_inputs = []
            for inp in inputs_spec:
                if inp["required"]:
                    input_name = inp["name"]
                    # Check if input is provided (handle None, empty string, etc.)
                    if (
                        input_name not in params
                        or params[input_name] is None
                        or (isinstance(params[input_name], str) and not params[input_name].strip())
                    ):
                        missing_inputs.append(
                            {
                                "name": input_name,
                                "type": inp["type"],
                                "description": inp["description"],
                            }
                        )

            # If required inputs are missing, return error instead of "ready"
            if missing_inputs:
                return {
                    "error": "Required directive inputs are missing",
                    "missing_inputs": missing_inputs,
                    "name": directive_data["name"],
                    "description": directive_data["description"],
                    "all_inputs": inputs_spec,
                    "provided_inputs": params,
                    "solution": f"Provide the missing required inputs in the 'parameters' field. Example: parameters={{'{missing_inputs[0]['name']}': 'value'}}",
                }

            # Parse MCP declarations and fetch tool schemas
            mcps_required = self._parse_mcps(directive_data)
            mcp_tools = {}

            if mcps_required:
                for mcp_decl in mcps_required:
                    mcp_name = mcp_decl["name"]
                    tool_filter = mcp_decl.get("tools")
                    refresh = mcp_decl.get("refresh", False)

                    if not mcp_name:
                        continue

                    try:
                        # Check cache first
                        schemas = self.schema_cache.get(mcp_name, force_refresh=refresh)
                        if schemas is None:
                            schemas = await self.mcp_pool.get_tool_schemas(mcp_name, tool_filter)
                            self.schema_cache.set(mcp_name, schemas)

                        mcp_tools[mcp_name] = {"available": True, "tools": schemas}
                    except Exception as e:
                        if mcp_decl.get("required"):
                            return {
                                "error": f"Required MCP '{mcp_name}' connection failed",
                                "mcp_error": str(e),
                                "solution": "Check MCP configuration and credentials",
                            }
                        mcp_tools[mcp_name] = {"available": False, "error": str(e)}

            result = {
                "status": "ready",
                "name": directive_data["name"],
                "description": directive_data["description"],
                "inputs": inputs_spec,
                "process": process_steps,
                "provided_inputs": params,
                "instructions": (
                    "Follow each process step in order. "
                    "Use provided_inputs for any matching input names."
                ),
            }

            # Add MCP tool context if any MCPs were declared
            if mcp_tools:
                result["tool_context"] = mcp_tools
                result["call_format"] = {
                    "description": "All MCP tools called via Kiwi execute",
                    "example": "execute(item_type='tool', action='call', ...)",
                }

            # Add legacy warning if present (non-blocking)
            if legacy_warning:
                result["warning"] = legacy_warning

            # Check for newer versions in other locations
            # Version is guaranteed to exist after validation, but add safety check
            current_version = directive_data.get("version")
            if current_version and current_version != "0.0.0":
                # Determine source location
                is_project = str(file_path).startswith(str(self.resolver.project_directives))
                current_source = "project" if is_project else "user"

                version_warning = await self._check_for_newer_version(
                    directive_name=directive_name,
                    current_version=current_version,
                    current_source=current_source,
                )
                if version_warning:
                    result["version_warning"] = version_warning

            return result
        except Exception as e:
            return {"error": f"Failed to parse directive: {str(e)}", "path": str(file_path)}

    async def _check_for_newer_version(
        self,
        directive_name: str,
        current_version: str,
        current_source: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Check for newer versions of a directive in other locations.

        Args:
            directive_name: Name of directive
            current_version: Current version being run (guaranteed to exist - validated)
            current_source: "project" or "user"

        Returns:
            Warning dict if newer version found, None otherwise
        """
        newest_version = current_version
        newest_location = None

        # Check user space (if running from project)
        if current_source == "project":
            try:
                user_file_path = self._find_in_path(directive_name, self.resolver.user_directives)
                if user_file_path and user_file_path.exists():
                    try:
                        user_directive_data = parse_directive_file(user_file_path)
                        user_version = user_directive_data.get("version")
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
                            f"Failed to parse user space directive {directive_name}: {e}"
                        )
            except Exception as e:
                self.logger.warning(
                    f"Failed to check user space for directive {directive_name}: {e}"
                )

        # Check registry (always)
        try:
            registry_data = await self.registry.get(directive_name)
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
            self.logger.warning(f"Failed to check registry for directive {directive_name}: {e}")

        # Return warning if newer version found
        if newest_location and newest_version != current_version:
            suggestion = (
                f"Use load() to download the newer version from {newest_location}"
                if newest_location == "registry"
                else f"Use load() to copy the newer version from user space"
            )
            return {
                "message": "A newer version of this directive is available",
                "current_version": current_version,
                "newer_version": newest_version,
                "location": newest_location,
                "suggestion": suggestion,
            }

        return None

    def _parse_mcps(self, directive_data: dict) -> list[dict]:
        """Parse <mcps> declarations from directive metadata."""
        # Try to get MCPs from parsed XML structure
        parsed = directive_data.get("parsed", {})
        mcps_list = []

        # Check if there's an <mcps> section in the parsed data
        if "mcps" in parsed and "mcp" in parsed["mcps"]:
            mcp_data = parsed["mcps"]["mcp"]

            # Handle single MCP vs list of MCPs
            if isinstance(mcp_data, dict):
                mcp_data = [mcp_data]

            for mcp in mcp_data:
                attrs = mcp.get("_attrs", {})
                mcps_list.append(
                    {
                        "name": attrs.get("name"),
                        "required": attrs.get("required", "false").lower() == "true",
                        "tools": attrs.get("tools", "").split(",") if attrs.get("tools") else None,
                        "refresh": attrs.get("refresh", "false").lower() == "true",
                    }
                )

        return mcps_list

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

    async def _publish_directive(
        self, directive_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Publish directive to registry."""
        # Find local directive file first (needed to extract version)
        file_path = self.resolver.resolve(directive_name)
        if not file_path:
            return {
                "error": f"Directive '{directive_name}' not found locally",
                "suggestion": "Create directive first before publishing",
            }

        # ENFORCE hash validation - ALWAYS check, never skip
        file_content = file_path.read_text()
        signature_status = MetadataManager.verify_signature("directive", file_content)

        # Block publishing if signature is missing, invalid, or modified
        if signature_status is None:
            has_pending = "kiwi-mcp:pending-validation" in file_content
            return {
                "error": "Cannot publish: directive has no valid signature",
                "status": "missing",
                "path": str(file_path),
                "hint": "Directives must be validated before publishing",
                "solution": (
                    f"Run: execute(item_type='directive', action='update', "
                    f"item_id='{directive_name}', parameters={{'location': 'project'}}, "
                    f"project_path='{self.project_path}')"
                ),
            }

        if signature_status.get("status") == "modified":
            return {
                "error": "Directive content has been modified since last validation",
                "signature": signature_status,
                "path": str(file_path),
                "solution": "Use execute action 'update' or 'create' to re-validate the directive before publishing",
            }
        elif signature_status.get("status") == "invalid":
            return {
                "error": "Directive signature is invalid",
                "signature": signature_status,
                "path": str(file_path),
                "solution": "Use execute action 'update' or 'create' to re-validate the directive before publishing",
            }

        # Parse directive to get content and metadata (including version from XML)
        # parse_directive_file() will validate filename/directive name match and raise if mismatch
        try:
            directive_data = parse_directive_file(file_path)
        except ValueError as e:
            # Convert parse validation error to structured response
            return {
                "error": "Cannot publish: filename and directive name mismatch",
                "details": str(e),
                "path": str(file_path),
            }

        # Explicit validation check after parsing (double-check for clarity)
        parsed_name = directive_data["name"]
        expected_filename = f"{parsed_name}.md"
        if file_path.stem != parsed_name:
            return {
                "error": "Cannot publish: filename and directive name mismatch",
                "problem": {
                    "expected": expected_filename,
                    "actual": file_path.name,
                    "directive_name": parsed_name,
                    "path": str(file_path),
                },
                "solution": {
                    "message": "Filename must match the directive name attribute in XML",
                    "option_1": f"Rename file: mv '{file_path}' '{file_path.parent / expected_filename}'",
                    "option_2": f'Update XML: Change <directive name="{file_path.stem}" ...> in {file_path}',
                    "option_3": f"Use edit_directive directive to fix",
                },
            }

        # Use explicit param if provided, otherwise fall back to XML version
        version = params.get("version") or directive_data.get("version")

        # Prevent publishing placeholder version
        if not version or not str(version).strip() or version == "0.0.0":
            return {
                "error": "version is required for publish",
                "hint": f"Set <directive ... version='x.y.z'> in {file_path}",
                "file_version": directive_data.get("version"),
                "example": "parameters={'version': '1.0.0'}",
            }

        # Use registry publish method
        result = await self.registry.publish(
            name=directive_name,
            version=version,
            content=directive_data.get("content", ""),
            category=directive_data.get("category", "custom"),
            description=directive_data.get("description", ""),
            tech_stack=directive_data.get("tech_stack", []),
        )

        # Ensure response includes version actually used
        if isinstance(result, dict) and "error" not in result:
            result["name"] = directive_name
            result["version"] = version

        return result

    async def _delete_directive(
        self, directive_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delete directive from local and/or registry."""
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
            file_path = self.resolver.resolve(directive_name)
            if file_path:
                file_path.unlink()
                deleted.append("local")

        # Delete from registry
        if source in ("registry", "all"):
            try:
                result = await self.registry.delete(name=directive_name)
                if "error" in result:
                    self.logger.warning(f"Registry delete failed: {result.get('error')}")
                else:
                    deleted.append("registry")
            except Exception as e:
                self.logger.warning(f"Registry delete failed: {e}")

        if not deleted:
            return {"error": f"Directive '{directive_name}' not found in specified location(s)"}

        return {"status": "deleted", "name": directive_name, "deleted_from": deleted}

    async def _create_directive(
        self, directive_name: str, params: Dict[str, Any]
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
                "valid_locations": ["project", "user"],
            }

        # Find the directive file
        if location == "project":
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
                "searched_in": str(
                    self.resolver.project_directives
                    if location == "project"
                    else self.resolver.user_directives
                ),
            }

        # Read and validate the file
        content = file_path.read_text()

        # Validate XML can be parsed
        try:
            strategy = MetadataManager.get_strategy("directive")
            xml_content = strategy.extract_content_for_hash(content)
            if not xml_content:
                return {
                    "error": "No XML directive found in content",
                    "hint": "Content must contain <directive>...</directive> XML block",
                    "file": str(file_path),
                }

            ET.fromstring(xml_content)  # Validate XML syntax

        except ET.ParseError as e:
            return {
                "error": "Invalid directive XML",
                "parse_error": str(e),
                "hint": "Check for unescaped < > & characters. Use CDATA for special chars.",
                "file": str(file_path),
            }
        except Exception as e:
            return {
                "error": "Failed to validate directive",
                "details": str(e),
                "file": str(file_path),
            }

        # Parse and validate
        try:
            directive_data = parse_directive_file(file_path)
            legacy_warning = directive_data.get("legacy_warning")

            # Validate using centralized validator
            validation_result = ValidationManager.validate("directive", file_path, directive_data)
            if not validation_result["valid"]:
                # Format error response with helpful details
                error_response = {
                    "error": "Directive validation failed",
                    "details": validation_result["issues"],
                    "path": str(file_path),
                }

                # Add filename mismatch details if applicable
                filename_issue = next(
                    (
                        issue
                        for issue in validation_result["issues"]
                        if "filename" in issue.lower() or "mismatch" in issue.lower()
                    ),
                    None,
                )
                if filename_issue:
                    parsed_name = directive_data["name"]
                    expected_filename = f"{parsed_name}.md"
                    error_response["error"] = "Cannot create: filename and directive name mismatch"
                    error_response["problem"] = {
                        "expected": expected_filename,
                        "actual": file_path.name,
                        "directive_name": parsed_name,
                        "path": str(file_path),
                    }
                    error_response["solution"] = {
                        "message": "Filename must match the directive name attribute in XML",
                        "option_1": f"Rename file: mv '{file_path}' '{file_path.parent / expected_filename}'",
                        "option_2": f'Update XML: Change <directive name="{file_path.stem}" ...> in {file_path}',
                        "option_3": f"Use edit_directive directive to fix",
                    }
                elif any("permission" in issue.lower() for issue in validation_result["issues"]):
                    error_response["error"] = "Directive permissions not satisfied"
                    error_response["permissions_required"] = directive_data.get("permissions", [])
                elif any("model" in issue.lower() for issue in validation_result["issues"]):
                    error_response["error"] = "Directive model not valid"
                    model_data = directive_data.get("model") or directive_data.get("model_class")
                    error_response["model_found"] = model_data
                    error_response["hint"] = (
                        "The <model> tag must have a 'tier' attribute. Example: <model tier=\"reasoning\">...</model>"
                    )
                elif any(
                    "code block" in issue.lower()
                    or "closing" in issue.lower()
                    or "must end" in issue.lower()
                    or "unexpected content" in issue.lower()
                    for issue in validation_result["issues"]
                ):
                    error_response["error"] = "Directive XML structure not valid"
                    error_response["hint"] = (
                        "The directive XML must end with </directive> tag followed immediately by the closing ```. No content should appear after the closing tag."
                    )
                    error_response["solution"] = {
                        "message": "Remove any content after the closing ``` in the directive file",
                        "option_1": f"Use edit_directive directive: Run directive 'edit_directive' with directive_name='{directive_name}' to fix the XML structure",
                        "option_2": f"Edit the file directly: Remove lines after ``` in {file_path}. Then revalidate the directive with 'update' or 'create' action",
                        "example": '```xml\n<directive name="example" version="1.0.0">\n  ...\n</directive>\n```',
                    }

                return error_response
        except ValueError as e:
            # Convert parse validation error to structured response
            return {
                "error": "Cannot create: filename and directive name mismatch",
                "details": str(e),
                "path": str(file_path),
            }
        except Exception as e:
            return {
                "error": "Failed to validate directive metadata",
                "details": str(e),
                "file": str(file_path),
            }

        # Generate and add signature for validated content
        signed_content = MetadataManager.sign_content("directive", content)

        # Update file with signature
        file_path.write_text(signed_content)

        # Get signature info for response
        signature_info = MetadataManager.get_signature_info("directive", signed_content)
        content_hash = signature_info["hash"] if signature_info else None
        timestamp = signature_info["timestamp"] if signature_info else None

        # Parse to get category and check for legacy warnings
        try:
            directive = parse_directive_file(file_path)
            category = directive.get("category", "unknown")
            legacy_warning = directive.get("legacy_warning")
        except:
            category = "unknown"
            legacy_warning = None

        result = {
            "status": "created",
            "name": directive_name,
            "path": str(file_path),
            "location": location,
            "category": category,
            "validated": True,
            "signature": {"hash": content_hash, "timestamp": timestamp},
            "message": f"Directive validated and signed. Ready to use.",
        }

        # Add legacy warning if present (non-blocking)
        if legacy_warning:
            result["warning"] = legacy_warning

        return result

    async def _update_directive(
        self, directive_name: str, params: Dict[str, Any]
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
                "suggestion": "Use 'create' action for new directives",
            }

        if not file_path.exists():
            return {"error": f"Directive file not found: {directive_name}", "path": str(file_path)}

        # Read the existing file
        content = file_path.read_text()

        # Validate XML can be parsed
        try:
            strategy = MetadataManager.get_strategy("directive")
            xml_content = strategy.extract_content_for_hash(content)
            if not xml_content:
                return {
                    "error": "No XML directive found in content",
                    "hint": "Content must contain <directive>...</directive> XML block",
                    "file": str(file_path),
                }

            ET.fromstring(xml_content)  # Validate XML syntax

        except ET.ParseError as e:
            return {
                "error": "Invalid directive XML",
                "parse_error": str(e),
                "hint": "Check for unescaped < > & characters. Use CDATA for special chars.",
                "file": str(file_path),
            }
        except Exception as e:
            return {
                "error": "Failed to validate directive",
                "details": str(e),
                "file": str(file_path),
            }

        # Parse and validate
        try:
            directive_data = parse_directive_file(file_path)
            legacy_warning = directive_data.get("legacy_warning")

            # Validate using centralized validator
            validation_result = ValidationManager.validate("directive", file_path, directive_data)
            if not validation_result["valid"]:
                # Format error response with helpful details
                error_response = {
                    "error": "Directive validation failed",
                    "details": validation_result["issues"],
                    "path": str(file_path),
                }

                # Add filename mismatch details if applicable
                filename_issue = next(
                    (
                        issue
                        for issue in validation_result["issues"]
                        if "filename" in issue.lower() or "mismatch" in issue.lower()
                    ),
                    None,
                )
                if filename_issue:
                    file_directive_name = directive_data["name"]
                    expected_filename = f"{file_directive_name}.md"
                    error_response["error"] = "Cannot update: filename and directive name mismatch"
                    error_response["problem"] = {
                        "expected": expected_filename,
                        "actual": file_path.name,
                        "directive_name": file_directive_name,
                        "path": str(file_path),
                    }
                    error_response["solution"] = {
                        "message": "Filename must match the directive name attribute in XML",
                        "option_1": f"Rename file: mv '{file_path}' '{file_path.parent / expected_filename}'",
                        "option_2": f'Update XML: Change <directive name="{file_path.stem}" ...> in {file_path}',
                        "option_3": f"Use edit_directive directive to fix",
                    }
                elif any("permission" in issue.lower() for issue in validation_result["issues"]):
                    error_response["error"] = "Directive permissions not satisfied"
                    error_response["permissions_required"] = directive_data.get("permissions", [])
                elif any("model" in issue.lower() for issue in validation_result["issues"]):
                    error_response["error"] = "Directive model not valid"
                    model_data = directive_data.get("model") or directive_data.get("model_class")
                    error_response["model_found"] = model_data
                    error_response["hint"] = (
                        "The <model> tag must have a 'tier' attribute. Example: <model tier=\"reasoning\">...</model>"
                    )
                elif any(
                    "code block" in issue.lower()
                    or "closing" in issue.lower()
                    or "must end" in issue.lower()
                    or "unexpected content" in issue.lower()
                    for issue in validation_result["issues"]
                ):
                    error_response["error"] = "Directive XML structure not valid"
                    error_response["hint"] = (
                        "The directive XML must end with </directive> tag followed immediately by the closing ```. No content should appear after the closing tag."
                    )
                    error_response["solution"] = {
                        "message": "Remove any content after the closing ``` in the directive file",
                        "option_1": f"Use edit_directive directive: Run directive 'edit_directive' with directive_name='{directive_name}' to fix the XML structure",
                        "option_2": f"Edit the file directly: Remove lines after ``` in {file_path}. Then revalidate the directive with 'update' or 'create' action",
                        "example": '```xml\n<directive name="example" version="1.0.0">\n  ...\n</directive>\n```',
                    }

                return error_response
        except ValueError as e:
            # Convert parse validation error to structured response
            return {
                "error": "Cannot update: filename and directive name mismatch",
                "details": str(e),
                "path": str(file_path),
            }
        except Exception as e:
            return {
                "error": "Failed to validate directive metadata",
                "details": str(e),
                "file": str(file_path),
            }

        # Generate and add signature for validated content
        signed_content = MetadataManager.sign_content("directive", content)

        # Update file
        file_path.write_text(signed_content)

        # Get signature info for response
        signature_info = MetadataManager.get_signature_info("directive", signed_content)
        content_hash = signature_info["hash"] if signature_info else None
        timestamp = signature_info["timestamp"] if signature_info else None

        # Parse to get category and check for legacy warnings
        try:
            directive = parse_directive_file(file_path)
            new_category = directive.get("category")
            legacy_warning = directive.get("legacy_warning")
        except:
            new_category = None
            legacy_warning = None

        # Determine current category from file path
        # Path structure: .../directives/{category}/{name}.md
        # If parent is "directives", category is unknown (file in root)
        # Otherwise, parent.name is the category
        current_category = None
        if file_path.parent.name != "directives":
            current_category = file_path.parent.name

        # Handle category change: move file if category changed
        moved = False
        final_path = file_path
        if new_category and new_category != current_category and new_category != "unknown":
            # Determine new path based on project or user space
            if self.project_path and str(file_path).startswith(str(self.project_path)):
                # Project space
                new_dir = self.project_path / ".ai" / "directives" / new_category
            else:
                # User space
                from kiwi_mcp.utils.paths import get_user_space

                new_dir = get_user_space() / "directives" / new_category

            new_dir.mkdir(parents=True, exist_ok=True)
            final_path = new_dir / file_path.name

            # Move file
            file_path.rename(final_path)
            moved = True
            self.logger.info(
                f"Moved directive from {file_path} to {final_path} (category: {current_category} -> {new_category})"
            )

            # Clean up empty old directory if it's a category folder
            old_dir = file_path.parent
            if old_dir.name != "directives" and not any(old_dir.iterdir()):
                try:
                    old_dir.rmdir()
                    self.logger.info(f"Removed empty directory: {old_dir}")
                except OSError:
                    pass  # Directory not empty or other error, ignore

        result = {
            "status": "updated",
            "name": directive_name,
            "path": str(final_path),
            "category": new_category or current_category or "unknown",
            "validated": True,
            "signature": {"hash": content_hash, "timestamp": timestamp},
            "message": f"Directive validated and signed. Ready to use.",
        }

        if moved:
            result["moved"] = True
            result["old_category"] = current_category
            result["new_category"] = new_category
            result["message"] = (
                f"Directive validated, signed, and moved to category '{new_category}'."
            )
            result["registry_sync_note"] = (
                "Category changed. If this directive is published to the registry, "
                "republish it to sync the category: "
                f"execute(action='publish', item_id='{directive_name}', parameters={{'version': '...'}})"
            )

        # Add legacy warning if present (non-blocking)
        if legacy_warning:
            result["warning"] = legacy_warning

        return result
