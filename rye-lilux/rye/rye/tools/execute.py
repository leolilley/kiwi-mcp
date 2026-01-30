"""RYE Execute Tool - Intelligent execution with orchestration.

Uses Lilux primitives for execution but adds:
- Chain parsing (tool->tool->tool resolution)
- Environment setup (PYTHONPATH, etc.)
- Telemetry tracking
- Protected content enforcement
- Lock management for concurrency
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Import Lilux primitives dynamically
from lilux.utils.resolvers import DirectiveResolver, ToolResolver, KnowledgeResolver
from lilux.utils.logger import get_logger


@dataclass
class ExecutionTelemetry:
    """Telemetry data for execution tracking (RYE intelligence)."""

    item_id: str
    item_type: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class ExecuteTool:
    """Intelligent execute tool with orchestration."""

    def __init__(self, project_path: Optional[str] = None):
        """Initialize execute tool with project path."""
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.logger = get_logger("rye_execute")

        # Initialize resolvers for each item type
        self.directive_resolver = DirectiveResolver(self.project_path)
        self.tool_resolver = ToolResolver(self.project_path)
        self.knowledge_resolver = KnowledgeResolver(self.project_path)

        # Telemetry storage (RYE intelligence)
        self._telemetry: Dict[str, ExecutionTelemetry] = {}

        # Lock manager for concurrency control (RYE delegates to Lilux)
        self._lock_manager = None
        self._init_lock_manager()

    def _init_lock_manager(self):
        """Initialize Lilux lock manager."""
        try:
            from lilux.primitives.lockfile import LockfileManager

            self._lock_manager = LockfileManager(self.project_path)
            self.logger.debug("Lock manager initialized")
        except Exception as e:
            self.logger.warning(f"Lock manager init failed: {e}")
            self._lock_manager = None

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute with RYE intelligence.

        Args:
            arguments: Execution parameters
                - item_type: "directive", "tool", or "knowledge"
                - item_id: ID/name of item to execute
                - project_path: Project path (optional, uses current if not provided)
                - parameters: Runtime parameters for the item
                - dry_run: If True, validate only without executing

        Returns:
            Dict with execution result and RYE telemetry
        """
        try:
            # Extract arguments
            item_type = arguments.get("item_type")
            item_id = arguments.get("item_id")
            project_path = Path(arguments.get("project_path", self.project_path))
            parameters = arguments.get("parameters", {})
            dry_run = arguments.get("dry_run", False)

            if not item_type or not item_id:
                return {"error": "item_type and item_id are required"}

            # Update project path if changed
            self.project_path = project_path
            self.directive_resolver = DirectiveResolver(project_path)
            self.tool_resolver = ToolResolver(project_path)
            self.knowledge_resolver = KnowledgeResolver(project_path)

            # Route to appropriate executor
            if item_type == "directive":
                return await self._execute_directive(item_id, parameters, dry_run)
            elif item_type == "tool":
                return await self._execute_tool(item_id, parameters, dry_run)
            elif item_type == "knowledge":
                return await self._execute_knowledge(item_id, parameters, dry_run)
            else:
                return {
                    "error": f"Unknown item_type: {item_type}",
                    "valid_types": ["directive", "tool", "knowledge"],
                }
        except Exception as e:
            self.logger.error(f"Execute failed: {e}")
            return {"error": str(e), "message": f"Failed to execute {item_id}"}

    async def _execute_directive(
        self, directive_name: str, params: Dict[str, Any], dry_run: bool
    ) -> Dict[str, Any]:
        """
        Execute directive with RYE intelligence.

        RYE parses directive XML and returns process steps for agent to follow.
        """
        # Find directive file
        file_path = self.directive_resolver.resolve(directive_name)

        if not file_path or not file_path.exists():
            return {
                "error": f"Directive '{directive_name}' not found",
                "suggestion": "Use load() to download from registry first",
            }

        # Parse directive XML (RYE intelligence)
        from lilux.utils.parsers import parse_directive_file

        directive_data = parse_directive_file(file_path)

        # Validate required inputs are provided
        inputs_spec = directive_data.get("inputs", [])
        missing_inputs = []
        for inp in inputs_spec:
            if inp.get("required"):
                input_name = inp.get("name")
                if (
                    input_name not in params
                    or params[input_name] is None
                    or (isinstance(params[input_name], str) and not params[input_name].strip())
                ):
                    missing_inputs.append(
                        {
                            "name": input_name,
                            "type": inp.get("type"),
                            "description": inp.get("description"),
                        }
                    )

        if missing_inputs:
            return {
                "error": "Required directive inputs are missing",
                "missing_inputs": missing_inputs,
                "name": directive_data.get("name"),
                "description": directive_data.get("description"),
                "all_inputs": inputs_spec,
                "provided_inputs": params,
            }

        # Extract process steps (RYE intelligence)
        process = directive_data.get("process", {})
        steps = process.get("step", [])
        if isinstance(steps, dict):
            steps = [steps]

        process_steps = []
        for step in steps:
            attrs = step.get("_attrs", {})
            process_steps.append(
                {
                    "name": attrs.get("name", ""),
                    "description": step.get("description", ""),
                    "action": step.get("action", ""),
                }
            )

        # Return ready directive for agent to execute
        result = {
            "status": "ready",
            "item_type": "directive",
            "name": directive_data.get("name"),
            "description": directive_data.get("description"),
            "version": directive_data.get("version", "0.0.0"),
            "inputs": inputs_spec,
            "process": process_steps,
            "provided_inputs": params,
            "instructions": (
                "Follow each process step in order. "
                "Use provided_inputs for any matching input names."
            ),
        }

        if dry_run:
            result["dry_run"] = True
            result["message"] = "Directive is valid and ready to execute"

        return result

    async def _execute_tool(
        self, tool_name: str, params: Dict[str, Any], dry_run: bool
    ) -> Dict[str, Any]:
        """
        Execute tool with RYE intelligence.

        RYE uses Lilux PrimitiveExecutor to:
        - Resolve tool chains
        - Execute via subprocess/http_client primitives
        - Track telemetry
        """
        from lilux.primitives.executor import PrimitiveExecutor

        # Initialize executor (RYE delegates to Lilux)
        executor = PrimitiveExecutor(project_path=self.project_path)

        if dry_run:
            # Validate tool without executing (RYE intelligence)
            try:
                # Resolve chain to validate dependencies
                chain = await executor.resolver.resolve(tool_name)

                if not chain:
                    return {
                        "status": "validation_passed",
                        "message": "Tool has no chain to validate",
                        "tool_id": tool_name,
                    }

                # Extract metadata
                from lilux.schemas import extract_tool_metadata

                tool_path = self.tool_resolver.resolve(tool_name)
                if not tool_path:
                    return {
                        "error": f"Tool '{tool_name}' not found locally",
                    }

                meta = extract_tool_metadata(tool_path, self.project_path)

                return {
                    "status": "validation_passed",
                    "message": "Tool is ready to execute",
                    "tool_id": tool_name,
                    "metadata": meta,
                    "chain_length": len(chain),
                }
            except Exception as e:
                return {
                    "error": f"Tool validation failed: {str(e)}",
                    "tool_id": tool_name,
                }

        # Execute tool (RYE delegates to Lilux)
        start_time = time.time()
        telemetry = ExecutionTelemetry(item_id=tool_name, item_type="tool", start_time=start_time)

        try:
            # Use PrimitiveExecutor to execute (Lilux primitive)
            result = await executor.execute(tool_name, params)

            # Track telemetry (RYE intelligence)
            telemetry.end_time = time.time()
            telemetry.duration_ms = int((telemetry.end_time - start_time) * 1000)
            telemetry.success = result.success
            telemetry.error = result.error

            self._telemetry[tool_name] = telemetry

            if result.success:
                response = {
                    "status": "success",
                    "data": result.data,
                    "telemetry": {
                        "duration_ms": telemetry.duration_ms,
                        "primitive_type": result.metadata.get("type") if result.metadata else None,
                    },
                }

                # Add metadata
                if result.metadata:
                    response["metadata"] = result.metadata

                return response
            else:
                return {
                    "status": "error",
                    "error": result.error or "Unknown execution error",
                    "telemetry": {
                        "duration_ms": telemetry.duration_ms,
                    },
                }

        except Exception as e:
            telemetry.end_time = time.time()
            telemetry.duration_ms = int((telemetry.end_time - start_time) * 1000)
            telemetry.success = False
            telemetry.error = str(e)

            self._telemetry[tool_name] = telemetry

            return {
                "status": "error",
                "error": str(e),
                "telemetry": {"duration_ms": telemetry.duration_ms},
            }

    async def _execute_knowledge(
        self, knowledge_id: str, params: Dict[str, Any], dry_run: bool
    ) -> Dict[str, Any]:
        """
        Execute knowledge entry with RYE intelligence.

        RYE loads knowledge content and returns it for agent reference.
        """
        # Find knowledge file
        file_path = self.knowledge_resolver.resolve(knowledge_id)

        if not file_path or not file_path.exists():
            return {
                "error": f"Knowledge entry '{knowledge_id}' not found",
                "suggestion": "Use load() to download from registry first",
            }

        # Parse knowledge frontmatter (RYE intelligence)
        from lilux.utils.parsers import parse_knowledge_entry

        entry_data = parse_knowledge_entry(file_path)

        result = {
            "status": "ready",
            "item_type": "knowledge",
            "id": entry_data.get("id"),
            "title": entry_data.get("title"),
            "content": entry_data.get("content"),
            "entry_type": entry_data.get("entry_type"),
            "category": entry_data.get("category"),
            "tags": entry_data.get("tags", []),
            "version": entry_data.get("version", "1.0.0"),
            "instructions": "Use this knowledge to inform your decisions.",
        }

        if dry_run:
            result["dry_run"] = True
            result["message"] = "Knowledge entry is valid and ready to use"

        return result

    def get_telemetry(self, item_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get execution telemetry (RYE intelligence).

        Args:
            item_id: Specific item ID, or None for all telemetry

        Returns:
            Telemetry data for item(s)
        """
        if item_id:
            telemetry = self._telemetry.get(item_id)
            if not telemetry:
                return {"error": f"No telemetry found for {item_id}"}

            return {
                "item_id": telemetry.item_id,
                "item_type": telemetry.item_type,
                "duration_ms": telemetry.duration_ms,
                "success": telemetry.success,
                "error": telemetry.error,
            }
        else:
            # Return all telemetry
            return {
                item_id: {
                    "duration_ms": t.duration_ms,
                    "success": t.success,
                    "error": t.error,
                }
                for item_id, t in self._telemetry.items()
            }
