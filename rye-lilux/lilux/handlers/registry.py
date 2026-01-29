"""
TypeHandlerRegistry - Routes operations to type-specific handlers.

Maps item_type (directive, tool, knowledge) to appropriate handler
and dispatches search, load, and execute operations.
"""

from typing import Dict, Any, Optional
import logging

try:
    from lilux.handlers.directive.handler import DirectiveHandler
except ImportError as e:
    DirectiveHandler = None


try:
    from lilux.handlers.tool.handler import ToolHandler
except ImportError as e:
    ToolHandler = None

try:
    from lilux.handlers.knowledge.handler import KnowledgeHandler
except ImportError as e:
    KnowledgeHandler = None


class TypeHandlerRegistry:
    """Registry that routes operations to type-specific handlers."""

    def __init__(self, project_path: str):
        """
        Initialize registry with all type handlers.

        Args:
            project_path: Path to project for local operations
        """
        self.project_path = project_path
        self.logger = logging.getLogger("TypeHandlerRegistry")

        # Initialize all handlers (gracefully handle missing dependencies)
        self.directive_handler = (
            DirectiveHandler(project_path=project_path) if DirectiveHandler else None
        )

        self.tool_handler = ToolHandler(project_path=project_path) if ToolHandler else None
        self.knowledge_handler = (
            KnowledgeHandler(project_path=project_path) if KnowledgeHandler else None
        )

        # Map item types to handlers (only add those that loaded successfully)
        self.handlers: Dict[str, Any] = {}
        if self.directive_handler:
            self.handlers["directive"] = self.directive_handler

        if self.tool_handler:
            self.handlers["tool"] = self.tool_handler

        if self.knowledge_handler:
            self.handlers["knowledge"] = self.knowledge_handler

        loaded_count = len(self.handlers)
        self.logger.info(
            f"TypeHandlerRegistry initialized with {loaded_count}/3 handlers "
            f"(directive, tool, knowledge) project_path={project_path}"
        )

    async def search(self, item_type: str, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search for items of a specific type.

        Args:
            item_type: "directive", "tool", or "knowledge"
            query: Search query
            **kwargs: Additional search parameters (source, limit, filters, etc.)

        Returns:
            Dict with search results or error
        """
        handler = self._get_handler(item_type)
        if not handler:
            return {
                "error": f"Unknown item_type: {item_type}",
                "supported_types": list(self.handlers.keys()),
            }

        try:
            self.logger.info(f"Searching {item_type}: {query}")
            result = await handler.search(query, **kwargs)
            return result
        except Exception as e:
            self.logger.error(f"Search failed for {item_type}: {str(e)}")
            return {
                "error": str(e),
                "item_type": item_type,
                "message": f"Failed to search {item_type}",
            }

    async def load(self, item_type: str, item_id: str, **kwargs) -> Dict[str, Any]:
        """
        Load/get a specific item.

        Args:
            item_type: "directive", "tool", or "knowledge"
            item_id: Item identifier (directive_name, tool_name, id)
            **kwargs: Additional load parameters (destination, version, etc.)

        Returns:
            Dict with item details or error
        """
        handler = self._get_handler(item_type)
        if not handler:
            return {
                "error": f"Unknown item_type: {item_type}",
                "supported_types": list(self.handlers.keys()),
            }

        try:
            self.logger.info(f"Loading {item_type}: {item_id}")

            # Map item_id to handler-specific parameter names
            result = None
            if item_type == "directive":
                result = await handler.load(directive_name=item_id, **kwargs)
            elif item_type == "tool":
                result = await handler.load(tool_name=item_id, **kwargs)
            elif item_type == "knowledge":
                result = await handler.load(id=item_id, **kwargs)

            if result is None:
                return {"error": f"Unsupported item_type: {item_type}"}

            return result
        except Exception as e:
            self.logger.error(f"Load failed for {item_type} {item_id}: {str(e)}")
            return {
                "error": str(e),
                "item_type": item_type,
                "item_id": item_id,
                "message": f"Failed to load {item_type}",
            }

    async def execute(
        self,
        item_type: str,
        item_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute an item (directive, tool, or knowledge).

        Args:
            item_type: "directive", "tool", or "knowledge"
            item_id: Item identifier
            parameters: Execution parameters
            **kwargs: Additional execution parameters (dry_run, etc.)

        Returns:
            Dict with operation result or error
        """
        handler = self._get_handler(item_type)
        if not handler:
            return {
                "error": f"Unknown item_type: {item_type}",
                "supported_types": list(self.handlers.keys()),
            }

        try:
            self.logger.info(f"Executing {item_type}: {item_id}")

            # Map item_id to handler-specific parameter names
            result = None
            if item_type == "directive":
                result = await handler.execute(
                    directive_name=item_id, parameters=parameters, **kwargs
                )
            elif item_type == "tool":
                result = await handler.execute(
                    tool_name=item_id, parameters=parameters, **kwargs
                )
            elif item_type == "knowledge":
                result = await handler.execute(
                    id=item_id, parameters=parameters, **kwargs
                )

            if result is None:
                return {"error": f"Unsupported item_type: {item_type}"}

            return result
        except Exception as e:
            self.logger.error(f"Execute failed for {item_type} {item_id}: {str(e)}")
            return {
                "error": str(e),
                "item_type": item_type,
                "item_id": item_id,
                "message": f"Failed to execute {item_type}",
            }

    async def sign(
        self,
        item_type: str,
        item_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Validate and sign an item (directive, tool, or knowledge).

        Args:
            item_type: "directive", "tool", or "knowledge"
            item_id: Item identifier
            parameters: Sign parameters (location, category)
            **kwargs: Additional parameters

        Returns:
            Dict with sign result or error
        """
        handler = self._get_handler(item_type)
        if not handler:
            return {
                "error": f"Unknown item_type: {item_type}",
                "supported_types": list(self.handlers.keys()),
            }

        try:
            self.logger.info(f"Signing {item_type}: {item_id}")

            # Map item_id to handler-specific parameter names
            result = None
            if item_type == "directive":
                result = await handler.sign(
                    directive_name=item_id, parameters=parameters, **kwargs
                )
            elif item_type == "tool":
                result = await handler.sign(
                    tool_name=item_id, parameters=parameters, **kwargs
                )
            elif item_type == "knowledge":
                result = await handler.sign(
                    id=item_id, parameters=parameters, **kwargs
                )

            if result is None:
                return {"error": f"Unsupported item_type: {item_type}"}

            return result
        except Exception as e:
            self.logger.error(f"Sign failed for {item_type} {item_id}: {str(e)}")
            return {
                "error": str(e),
                "item_type": item_type,
                "item_id": item_id,
                "message": f"Failed to sign {item_type}",
            }

    def _get_handler(self, item_type: str) -> Optional[Any]:
        """Get handler for item type, return None if unknown."""
        handler = self.handlers.get(item_type)
        if not handler:
            self.logger.warning(f"Unknown item_type: {item_type}")
        return handler

    def get_supported_types(self) -> list[str]:
        """Get list of supported item types."""
        return list(self.handlers.keys())

    def get_handler_info(self) -> Dict[str, Any]:
        """Get information about all registered handlers."""
        return {
            "registry": "TypeHandlerRegistry",
            "project_path": self.project_path,
            "supported_types": self.get_supported_types(),
            "operations": ["search", "load", "execute", "sign"],
            "handlers": {
                "directive": {
                    "class": "DirectiveHandler",
                    "operations": ["search", "load", "execute", "sign"],
                    "execute_behavior": "Returns parsed XML content for agent to follow",
                },
                "tool": {
                    "class": "ToolHandler",
                    "operations": ["search", "load", "execute", "sign"],
                    "execute_behavior": "Executes tool code and returns results",
                },
                "knowledge": {
                    "class": "KnowledgeHandler",
                    "operations": ["search", "load", "execute", "sign"],
                    "execute_behavior": "Returns knowledge content for agent context",
                },
            },
        }
