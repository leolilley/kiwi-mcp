"""
Directive handler for kiwi-mcp.

Implements search, load, execute operations for directives.
Handles LOCAL file operations directly, only uses registry for REMOTE operations.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from kiwi_mcp.handlers import SortBy
from kiwi_mcp.primitives.integrity import compute_directive_integrity
from kiwi_mcp.utils.file_search import score_relevance, search_markdown_files
from kiwi_mcp.utils.logger import get_logger
from kiwi_mcp.utils.metadata_manager import MetadataManager, compute_unified_integrity
from kiwi_mcp.utils.parsers import parse_directive_file
from kiwi_mcp.utils.resolvers import DirectiveResolver
from kiwi_mcp.utils.schema_validator import SchemaValidator
from kiwi_mcp.utils.validators import ValidationManager, compare_versions
from kiwi_mcp.utils.xml_error_helper import format_error_with_context


class DirectiveHandler:
    """Handler for directive operations."""

    def __init__(self, project_path: str):
        """Initialize handler with project path."""
        self.project_path = Path(project_path)
        self.logger = get_logger("directive_handler")

        # Local file handling
        self.resolver = DirectiveResolver(self.project_path)
        self.search_paths = [
            self.resolver.project_directives,
            self.resolver.user_directives,
        ]

        # MCP tool discovery removed - handled by tools

        # Input schema validation
        self._schema_validator = SchemaValidator()

        # Vector store for automatic embedding
        self._vector_store = None
        self._init_vector_store()

    def _init_vector_store(self):
        """Initialize project vector store for automatic embedding."""
        try:
            from kiwi_mcp.storage.vector import (
                EmbeddingService,
                LocalVectorStore,
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
                source="project",
            )
        except ValueError as e:
            # Missing config - vector search disabled
            self.logger.debug(f"Vector store not configured: {e}")
            self._vector_store = None
        except Exception as e:
            self.logger.warning(f"Vector store init failed: {e}")
            self._vector_store = None

    def _compute_directive_integrity(
        self, directive_data: Dict[str, Any], file_content: str
    ) -> str:
        """
        Compute canonical integrity hash for a directive.

        Args:
            directive_data: Parsed directive data
            file_content: Raw file content

        Returns:
            SHA256 hex digest (64 characters)
        """
        strategy = MetadataManager.get_strategy("directive")
        xml_content = strategy.extract_content_for_hash(file_content)

        # Build metadata dict for integrity computation
        metadata = {
            "category": directive_data.get("category"),
            "description": directive_data.get("description"),
            "model_tier": (
                directive_data.get("model", {}).get("tier")
                if isinstance(directive_data.get("model"), dict)
                else None
            ),
        }

        return compute_directive_integrity(
            directive_name=directive_data.get("name", ""),
            version=directive_data.get("version", "0.0.0"),
            xml_content=xml_content or "",
            metadata=metadata,
        )

    def _verify_directive_integrity(
        self, directive_data: Dict[str, Any], file_content: str, stored_hash: str
    ) -> bool:
        """
        Verify directive content matches stored canonical integrity hash.

        Args:
            directive_data: Parsed directive data
            file_content: Raw file content
            stored_hash: Expected integrity hash

        Returns:
            True if computed hash matches stored hash
        """
        computed = self._compute_directive_integrity(directive_data, file_content)
        return computed == stored_hash

    def _extract_input_schema(self, parsed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract optional input_schema from parsed directive XML.

        The input_schema can be defined in <inputs> as a JSON schema attribute
        or as a child <schema> element containing JSON.

        Example XML:
            <inputs>
              <input name="topic" type="string" required="true">Topic to research</input>
              <schema>{"type": "object", "properties": {"topic": {"minLength": 3}}}</schema>
            </inputs>

        Args:
            parsed: Parsed directive XML structure

        Returns:
            JSON Schema dict or None if not defined
        """
        if "inputs" not in parsed:
            return None

        inputs_section = parsed["inputs"]

        # Check for <schema> element
        if "schema" in inputs_section:
            schema_data = inputs_section["schema"]
            # Handle both text content and _text attribute
            schema_text = (
                schema_data.get("_text")
                if isinstance(schema_data, dict)
                else schema_data
            )
            if schema_text:
                try:
                    return json.loads(schema_text)
                except json.JSONDecodeError:
                    self.logger.warning("Invalid JSON in directive input_schema")
                    return None

        # Check for schema attribute on inputs element
        if isinstance(inputs_section, dict):
            attrs = inputs_section.get("_attrs", {})
            schema_attr = attrs.get("schema")
            if schema_attr:
                try:
                    return json.loads(schema_attr)
                except json.JSONDecodeError:
                    self.logger.warning(
                        "Invalid JSON in directive input_schema attribute"
                    )
                    return None

        return None

    def _build_input_schema_from_spec(
        self, inputs_spec: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build a JSON Schema from the directive's input specifications.

        This auto-generates a schema from the <input> elements if no
        explicit schema is provided.

        Args:
            inputs_spec: List of input specifications from _extract_inputs()

        Returns:
            JSON Schema dict
        """
        properties = {}
        required = []

        for inp in inputs_spec:
            name = inp.get("name", "")
            if not name:
                continue

            # Map directive types to JSON Schema types
            type_mapping = {
                "string": "string",
                "number": "number",
                "integer": "integer",
                "boolean": "boolean",
                "array": "array",
                "object": "object",
            }

            inp_type = inp.get("type", "string")
            json_type = type_mapping.get(inp_type, "string")

            prop_schema = {"type": json_type}

            # Add description if available
            if inp.get("description"):
                prop_schema["description"] = inp["description"]

            properties[name] = prop_schema

            if inp.get("required"):
                required.append(name)

        schema = {
            "type": "object",
            "properties": properties,
        }

        if required:
            schema["required"] = required

        return schema

    def _validate_inputs_with_schema(
        self, params: Dict[str, Any], schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate input parameters against JSON Schema.

        Args:
            params: Input parameters to validate
            schema: JSON Schema to validate against

        Returns:
            Validation result with valid, issues, warnings
        """
        if not self._schema_validator.is_available():
            return {
                "valid": True,
                "issues": [],
                "warnings": [
                    "JSON Schema validation not available - skipping input validation"
                ],
            }

        return self._schema_validator.validate(params, schema)

    async def search(
        self,
        query: str,
        source: str = "project",
        limit: int = 10,
        sort_by: SortBy = "score",
        categories: Optional[List[str]] = None,
        subcategories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for directives in local files and/or registry.

        Args:
            query: Search query (natural language)
            source: "project", "user", "all" (both project and user)
            limit: Maximum number of results to return
            sort_by: "score", "success_rate", "date", or "downloads"
            categories: Filter by categories
            subcategories: Filter by subcategories
            tags: Filter by tags
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

            # Search local files only
            local_results = self._search_local(query, categories, subcategories, tags)
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
                        x.get("name", "").lower(),
                        source_priority.get(x.get("source", ""), 99),
                    )
                )
            else:  # "score" (default)
                results.sort(
                    key=lambda x: (
                        -x.get("score", 0),
                        source_priority.get(x.get("source", ""), 99),
                    )
                )

            # Apply limit
            results = results[:limit]

            return {
                "query": query,
                "source": source,
                "results": results,
                "total": len(results),
            }
        except Exception as e:
            return {"error": str(e), "message": "Failed to search directives"}

    async def load(
        self,
        directive_name: str,
        source: Literal["project", "user"],
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
            # LOAD FROM PROJECT
            if source == "project":
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

                    # Check signature before copying
                    signature_info = MetadataManager.get_signature_info(
                        "directive", content
                    )
                    if not signature_info:
                        return {
                            "error": "Directive has no signature",
                            "path": str(file_path),
                            "solution": "Use execute action 'sign' to re-validate the directive before copying",
                        }

                    # Determine category from source path
                    relative_path = file_path.relative_to(search_base)
                    target_path = Path.home() / ".ai" / "directives" / relative_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(content)
                    self.logger.info(
                        f"Copied directive from project to user: {target_path}"
                    )

                    directive_data = parse_directive_file(target_path)
                    directive_data["source"] = "project"
                    directive_data["destination"] = "user"
                    directive_data["path"] = str(target_path)
                    return directive_data
                else:
                    # Read-only mode: verify and warn, but don't block
                    file_content = file_path.read_text()
                    signature_info = MetadataManager.get_signature_info(
                        "directive", file_content
                    )

                    directive_data = parse_directive_file(file_path)
                    directive_data["source"] = "project"
                    directive_data["path"] = str(file_path)
                    directive_data["mode"] = "read_only"

                    if not signature_info:
                        directive_data["warning"] = {
                            "message": "Directive has no signature",
                            "solution": "Use execute action 'sign' to re-validate",
                        }

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
                # Check signature before copying
                content = file_path.read_text()

                signature_info = MetadataManager.get_signature_info(
                    "directive", content
                )
                if not signature_info:
                    return {
                        "error": "Directive has no signature",
                        "path": str(file_path),
                        "solution": "Use execute action 'sign' to re-validate the directive before copying",
                    }

                # Determine category from source path
                relative_path = file_path.relative_to(search_base)
                target_path = self.project_path / ".ai" / "directives" / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content)
                self.logger.info(
                    f"Copied directive from user to project: {target_path}"
                )

                directive_data = parse_directive_file(target_path)
                directive_data["source"] = "user"
                directive_data["destination"] = "project"
                directive_data["path"] = str(target_path)
                return directive_data
            else:
                # Read-only mode: check signature and warn if missing
                file_content = file_path.read_text()
                signature_info = MetadataManager.get_signature_info(
                    "directive", file_content
                )

                directive_data = parse_directive_file(file_path)
                directive_data["source"] = "user"
                directive_data["path"] = str(file_path)
                directive_data["mode"] = "read_only"

                if not signature_info:
                    directive_data["warning"] = {
                        "message": "Directive has no signature",
                        "solution": "Use execute action 'sign' to re-validate",
                    }

                return directive_data
        except Exception as e:
            return {
                "error": str(e),
                "message": f"Failed to load directive '{directive_name}'",
            }

    async def execute(
        self,
        action: str,
        directive_name: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a directive or perform directive operation.

        Args:
            action: "run", "sign"
            directive_name: Name of directive
            parameters: Directive inputs/parameters

        Returns:
            Dict with execution result
        """
        self.logger.info(
            f"DirectiveHandler.execute: action={action}, directive={directive_name}"
        )

        try:
            if action == "run":
                return await self._run_directive(directive_name, parameters or {})
            elif action == "sign":
                return await self._sign_directive(directive_name, parameters or {})
            else:
                return {
                    "error": f"Unknown action: {action}",
                    "supported_actions": ["run", "sign"],
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
                    is_project = str(file_path).startswith(
                        str(self.resolver.project_directives)
                    )

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

    def _get_directive_paths(self, source: str = "project") -> List[Path]:
        """
        Get directive file paths from specified source.

        Args:
            source: "project", "user", or "all" (both project and user)

        Returns:
            List of Path objects for directive files
        """
        paths = []

        if source in ("project", "all"):
            project_dir = self.project_path / ".ai" / "directives"
            if project_dir.exists():
                paths.extend(project_dir.rglob("*.md"))

        if source in ("user", "all"):
            user_dir = Path.home() / ".ai" / "directives"
            if user_dir.exists():
                paths.extend(user_dir.rglob("*.md"))

        return paths

    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """
        Extract metadata from directive file content.

        Args:
            content: Raw file content

        Returns:
            Dict with extracted metadata (name, description, category, etc.)
        """
        metadata = {
            "name": "",
            "description": "",
            "category": "",
            "version": "0.0.0",
        }

        try:
            # Extract XML content
            import re

            xml_match = re.search(r"```xml\s*(.*?)\s*```", content, re.DOTALL)
            if not xml_match:
                return metadata

            xml_content = xml_match.group(1)

            # Parse XML to extract metadata
            root = ET.fromstring(xml_content)

            # Get directive attributes
            metadata["name"] = root.get("name", "")
            metadata["version"] = root.get("version", "0.0.0")

            # Get metadata section
            metadata_elem = root.find("metadata")
            if metadata_elem is not None:
                desc_elem = metadata_elem.find("description")
                if desc_elem is not None and desc_elem.text:
                    metadata["description"] = desc_elem.text

                category_elem = metadata_elem.find("category")
                if category_elem is not None and category_elem.text:
                    metadata["category"] = category_elem.text

        except Exception as e:
            self.logger.debug(f"Failed to extract metadata: {e}")

        return metadata

    async def _run_directive(
        self, directive_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
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

            # Validate directive using centralized validator and embed if valid
            validation_result = await ValidationManager.validate_and_embed(
                "directive",
                file_path,
                directive_data,
                vector_store=self._vector_store,
                item_id=directive_data.get("name"),
            )
            if not validation_result["valid"]:
                # Format error response
                error_response = {
                    "error": "Directive validation failed",
                    "details": validation_result["issues"],
                    "path": str(file_path),
                }
                # Add specific error context
                if any(
                    "permission" in issue.lower()
                    for issue in validation_result["issues"]
                ):
                    error_response["error"] = "Directive permissions not satisfied"
                    error_response["permissions_required"] = directive_data.get(
                        "permissions", []
                    )
                elif any(
                    "model" in issue.lower() for issue in validation_result["issues"]
                ):
                    error_response["error"] = "Directive model not valid"
                    model_data = directive_data.get("model") or directive_data.get(
                        "model_class"
                    )
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
                        "option_2": f"Edit the file directly: Remove lines after ``` in {file_path}. Then revalidate the directive with 'sign' action",
                        "example": '```xml\n<directive name="example" version="1.0.0">\n  ...\n</directive>\n```',
                    }
                return error_response

            # Extract integrity hash from signature
            file_content = file_path.read_text()
            stored_hash = MetadataManager.get_signature_hash(
                "directive",
                file_content,
                file_path=file_path,
                project_path=self.project_path,
            )

            if not stored_hash:
                return {
                    "error": "Directive has no signature",
                    "status": "missing",
                    "path": str(file_path),
                    "hint": "Directive needs validation",
                    "solution": (
                        f"Run: execute(item_type='directive', action='sign', "
                        f"item_id='{directive_name}', parameters={{'location': 'project'}}, "
                        f"project_path='{self.project_path}')"
                    ),
                }

            # Verify integrity - recompute hash and compare
            computed_hash = compute_unified_integrity(
                item_type="directive",
                item_id=directive_name,
                version=directive_data.get("version", "0.0.0"),
                file_content=file_content,
                file_path=file_path,
                metadata=None,  # Let compute_unified_integrity extract what it needs
            )

            if computed_hash != stored_hash:
                from kiwi_mcp.primitives.integrity import short_hash

                return {
                    "error": "Directive content has been modified since last validation",
                    "details": f"Integrity mismatch for {directive_name}@{directive_data.get('version')}: computed={short_hash(computed_hash)}, stored={short_hash(stored_hash)}",
                    "path": str(file_path),
                    "solution": "Run execute(action='sign', ...) to re-validate the directive",
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
                        or (
                            isinstance(params[input_name], str)
                            and not params[input_name].strip()
                        )
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

            # Schema-based input validation (optional but recommended)
            # First check for explicit schema in directive, then auto-generate from spec
            input_schema = self._extract_input_schema(parsed)
            if input_schema is None and inputs_spec:
                # Auto-generate schema from input specifications
                input_schema = self._build_input_schema_from_spec(inputs_spec)

            schema_validation_result = None
            if input_schema and params:
                schema_validation_result = self._validate_inputs_with_schema(
                    params, input_schema
                )

                if not schema_validation_result.get("valid", True):
                    return {
                        "error": "Input validation failed",
                        "validation_issues": schema_validation_result.get("issues", []),
                        "name": directive_data["name"],
                        "description": directive_data["description"],
                        "all_inputs": inputs_spec,
                        "provided_inputs": params,
                        "input_schema": input_schema,
                        "solution": "Fix the validation issues in the provided inputs",
                    }

            # MCP tool discovery removed - directives should use mcp_stdio/mcp_http tools directly
            # Parse MCP declarations for informational purposes only
            mcps_required = self._parse_mcps(directive_data)
            mcp_tools = {}

            if mcps_required:
                # Inform agent that MCPs are declared but discovery must be done via tools
                for mcp_decl in mcps_required:
                    mcp_name = mcp_decl["name"]
                    if mcp_name:
                        mcp_tools[mcp_name] = {
                            "available": "check_via_tool",
                            "note": "Use mcp_stdio or mcp_http tools to discover and call tools",
                        }

            # Get integrity hash from signature
            signature_info = MetadataManager.get_signature_info(
                "directive", file_content
            )
            content_hash = signature_info["hash"] if signature_info else None

            result = {
                "status": "ready",
                "name": directive_data["name"],
                "description": directive_data["description"],
                "version": directive_data.get("version", "0.0.0"),
                "inputs": inputs_spec,
                "process": process_steps,
                "provided_inputs": params,
                "integrity": content_hash,
                "integrity_short": content_hash[:12] if content_hash else None,
                "inputs_validated": schema_validation_result is not None,
                "instructions": (
                    "Follow each process step in order. "
                    "Use provided_inputs for any matching input names."
                ),
            }

            # Add input schema if defined
            if input_schema:
                result["input_schema"] = input_schema

            # Add validation warnings if any
            if schema_validation_result and schema_validation_result.get("warnings"):
                result["validation_warnings"] = schema_validation_result["warnings"]

            # Add MCP tool context if any MCPs were declared
            if mcp_tools:
                result["tool_context"] = mcp_tools
                result["call_format"] = {
                    "description": "Use mcp_stdio or mcp_http tools to discover and call MCP tools",
                    "example": "execute(item_type='tool', action='run', item_id='mcp_stdio', ...)",
                }

            # Check for newer versions in other locations
            # Version is guaranteed to exist after validation, but add safety check
            current_version = directive_data.get("version")
            if current_version and current_version != "0.0.0":
                # Determine source location
                is_project = str(file_path).startswith(
                    str(self.resolver.project_directives)
                )
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
            return {
                "error": f"Failed to parse directive: {str(e)}",
                "path": str(file_path),
            }

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
                user_file_path = self._find_in_path(
                    directive_name, self.resolver.user_directives
                )
                if user_file_path and user_file_path.exists():
                    try:
                        user_directive_data = parse_directive_file(user_file_path)
                        user_version = user_directive_data.get("version")
                        if user_version:
                            try:
                                if compare_versions(current_version, user_version) < 0:
                                    # User version is newer
                                    if (
                                        compare_versions(newest_version, user_version)
                                        < 0
                                    ):
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

        # Return warning if newer version found
        if newest_location and newest_version != current_version:
            suggestion = f"Use load() to copy the newer version from {newest_location}"
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
                        "tools": (
                            attrs.get("tools", "").split(",")
                            if attrs.get("tools")
                            else None
                        ),
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

    async def _sign_directive(
        self, directive_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate and sign an existing directive file.

        Expects the directive file to already exist on disk.
        This action validates the XML, checks permissions, and signs the file.
        Always allows re-signing - signatures are included in the validation chain.
        """
        location = params.get("location", "project")
        if location not in ("project", "user"):
            return {
                "error": f"Invalid location: {location}",
                "valid_locations": ["project", "user"],
            }

        # Find the directive file - try resolver first, then search by location
        file_path = self.resolver.resolve(directive_name)

        if not file_path or not file_path.exists():
            # Search by location if resolver didn't find it
            if location == "project":
                file_path = None
                for search_path in [self.resolver.project_directives]:
                    for candidate in Path(search_path).rglob(f"*{directive_name}.md"):
                        if candidate.stem == directive_name:
                            file_path = candidate
                            break
                    if file_path:
                        break
            else:
                file_path = None
                for candidate in Path(self.resolver.user_directives).rglob(
                    f"*{directive_name}.md"
                ):
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

        # Validate path structure
        from kiwi_mcp.utils.paths import validate_path_structure

        path_validation = validate_path_structure(
            file_path, "directive", location, self.project_path
        )
        if not path_validation["valid"]:
            return {
                "error": "Directive path structure invalid",
                "details": path_validation["issues"],
                "path": str(file_path),
                "solution": "File must be under .ai/directives/ with correct structure",
            }

        # Read the file (with existing signature if present - we include it in validation)
        content = file_path.read_text()

        # Validate XML can be parsed
        strategy = MetadataManager.get_strategy("directive")
        xml_content = strategy.extract_content_for_hash(content)
        if not xml_content:
            return {
                "error": "No XML directive found in content",
                "hint": "Content must contain <directive>...</directive> XML block",
                "file": str(file_path),
            }

        try:
            ET.fromstring(xml_content)  # Validate XML syntax

        except ET.ParseError as e:
            # Use enhanced error formatting with context and suggestions
            enhanced_error = format_error_with_context(
                str(e), xml_content, str(file_path)
            )
            return {
                "error": "Invalid directive XML",
                "parse_error": enhanced_error,
                "hint": "See parse_error field for detailed error message with line numbers and suggestions.",
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

            # Validate using centralized validator and embed if valid
            validation_result = await ValidationManager.validate_and_embed(
                "directive",
                file_path,
                directive_data,
                vector_store=self._vector_store,
                item_id=directive_data.get("name"),
            )
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
                    error_response["error"] = (
                        "Cannot sign: filename and directive name mismatch"
                    )
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
                        "option_3": "Use edit_directive directive to fix",
                    }
                elif any(
                    "permission" in issue.lower()
                    for issue in validation_result["issues"]
                ):
                    error_response["error"] = "Directive permissions not satisfied"
                    error_response["permissions_required"] = directive_data.get(
                        "permissions", []
                    )
                elif any(
                    "model" in issue.lower() for issue in validation_result["issues"]
                ):
                    error_response["error"] = "Directive model not valid"
                    model_data = directive_data.get("model") or directive_data.get(
                        "model_class"
                    )
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
                        "option_2": f"Edit the file directly: Remove lines after ``` in {file_path}. Then revalidate the directive with 'sign' action",
                        "example": '```xml\n<directive name="example" version="1.0.0">\n  ...\n</directive>\n```',
                    }

                return error_response
        except ValueError as e:
            # Convert parse validation error to structured response
            return {
                "error": "Cannot sign: filename and directive name mismatch",
                "details": str(e),
                "path": str(file_path),
            }
        except Exception as e:
            return {
                "error": "Failed to validate directive metadata",
                "details": str(e),
                "file": str(file_path),
            }

        # Strict version requirement - fail if missing
        version = directive_data.get("version")
        if not version or version == "0.0.0":
            return {
                "error": "Directive validation failed",
                "details": [
                    "Directive is missing required 'version' attribute. "
                    'Add version attribute to <directive> tag: <directive name="..." version="1.0.0">'
                ],
                "path": str(file_path),
                "solution": "Add version metadata and re-run sign action",
            }

        # Compute unified integrity hash on content WITHOUT signature
        # This allows re-signing to produce consistent hashes
        from kiwi_mcp.utils.metadata_manager import compute_unified_integrity

        # Remove existing signature before hashing (chained validation)
        strategy = MetadataManager.get_strategy("directive")
        content_without_sig = strategy.remove_signature(content)

        content_hash = compute_unified_integrity(
            item_type="directive",
            item_id=directive_name,
            version=version,
            file_content=content_without_sig,  # Hash only original content, not signature
            file_path=file_path,
            metadata=None,
        )

        # Generate and add signature for validated content with unified integrity hash
        signed_content = MetadataManager.sign_content_with_hash(
            "directive", content, content_hash
        )

        # Update file with signature
        file_path.write_text(signed_content)

        # Get signature info for response
        signature_info = MetadataManager.get_signature_info("directive", signed_content)
        timestamp = signature_info["timestamp"] if signature_info else None

        try:
            directive = parse_directive_file(file_path)
            new_category = directive.get("category")
        except Exception:
            new_category = None

        # Extract current category from file path (supports nested categories)
        from kiwi_mcp.utils.paths import extract_category_path

        # Determine location
        determined_location = (
            "project" if str(file_path).startswith(str(self.project_path)) else "user"
        )
        current_category = extract_category_path(
            file_path, "directive", determined_location, self.project_path
        )

        # Handle category change: move file if category changed
        moved = False
        final_path = file_path
        if (
            new_category
            and new_category != current_category
            and new_category != "unknown"
        ):
            # Determine new path based on project or user space
            if determined_location == "project":
                # Build path from slash-separated category
                new_dir = self.project_path / ".ai" / "directives"
                if new_category:
                    for part in new_category.split("/"):
                        new_dir = new_dir / part
            else:
                # User space
                from kiwi_mcp.utils.paths import get_user_space

                new_dir = get_user_space() / "directives"
                if new_category:
                    for part in new_category.split("/"):
                        new_dir = new_dir / part

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
            "status": "signed",
            "name": directive_name,
            "path": str(final_path),
            "location": determined_location,
            "category": new_category or current_category or "unknown",
            "validated": True,
            "signature": {"hash": content_hash, "timestamp": timestamp},
            "integrity": content_hash,
            "integrity_short": content_hash[:12],
            "message": "Directive validated and signed. Ready to use.",
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

        return result
