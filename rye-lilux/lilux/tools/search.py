"""Search tool - unified search across directives, scripts, and knowledge."""

import json
from pathlib import Path
from mcp.types import Tool
from lilux.tools.base import BaseTool
from lilux.utils.logger import get_logger


class SearchTool(BaseTool):
    """Search for items across all Lilux types."""

    def __init__(self, registry=None):
        """Initialize with optional registry reference."""
        self.registry = registry
        self.logger = get_logger("search_tool")
        self._vector_manager = None
        self._hybrid_search = None

    @property
    def schema(self) -> Tool:
        return Tool(
            name="search",
            description="Search for directives, scripts, or knowledge entries",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "enum": ["directive", "tool", "knowledge"],
                        "description": "Type of item to search for",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (natural language or keywords)",
                    },
                    "source": {
                        "type": "string",
                        "enum": ["project", "user"],
                        "default": "project",
                        "description": "Search source: 'project' (local .ai/) or 'user' (~/.ai/)",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum results to return",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Absolute path to project root (where .ai/ folder lives). Example: '/home/user/myproject'",
                    },
                },
                "required": ["item_type", "query", "project_path"],
            },
        )

    def _has_vector_search(self, project_path: str) -> bool:
        """Check if vector search dependencies and setup are available."""
        try:
            # Check if vector storage directory exists
            vector_path = Path(project_path) / ".ai" / "vector"
            return vector_path.exists()
        except Exception:
            return False

    def _setup_vector_search(self, project_path: str):
        """Setup vector search from RAG environment config."""
        if self._vector_manager is not None:
            return

        try:
            from lilux.storage.vector import (
                LocalVectorStore,
                ThreeTierVectorManager,
                HybridSearch,
            )
            from lilux.storage.vector.api_embeddings import EmbeddingService
            from lilux.storage.vector.embedding_registry import load_vector_config

            # Load RAG config (validated at server startup)
            config = load_vector_config()
            embedding_service = EmbeddingService(config)

            # Setup three-tier storage
            project_store = LocalVectorStore(
                storage_path=Path(project_path) / ".ai" / "vector" / "project",
                collection_name="project_items",
                embedding_service=embedding_service,
                source="project",
            )

            user_store = LocalVectorStore(
                storage_path=Path.home() / ".ai" / "vector" / "user",
                collection_name="user_items",
                embedding_service=embedding_service,
                source="user",
            )

            # Setup manager and hybrid search
            self._vector_manager = ThreeTierVectorManager(
                project_store=project_store, user_store=user_store
            )

            self._hybrid_search = HybridSearch(self._vector_manager)

        except ImportError as e:
            self.logger.info(f"Vector search dependencies not available: {e}")
            self._vector_manager = None
            self._hybrid_search = None
        except Exception as e:
            self.logger.warning(f"Failed to setup vector search: {e}")
            self._vector_manager = None
            self._hybrid_search = None

    async def execute(self, arguments: dict) -> str:
        """Execute search with vector search priority and keyword fallback."""
        item_type = arguments.get("item_type")
        query = arguments.get("query")
        source = arguments.get("source", "project")
        limit = arguments.get("limit", 10)
        project_path = arguments.get("project_path")

        self.logger.info(
            f"SearchTool.execute: item_type={item_type}, query={query}, source={source}"
        )

        if not item_type or not query:
            return self._format_response({"error": "item_type and query are required"})

        if not project_path:
            return self._format_response(
                {
                    "error": "project_path is REQUIRED",
                    "message": "Please provide the absolute path to your project root (where .ai/ folder lives).",
                    "hint": "Add project_path parameter. Example: project_path='/home/user/myproject'",
                }
            )

        try:
            # Try vector search first if available
            if self._has_vector_search(project_path):
                return await self._vector_search(item_type, query, source, limit, project_path)

            # Fallback to keyword search
            return await self._keyword_search(item_type, query, source, limit, project_path)

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return self._format_response({"error": str(e)})

    async def _vector_search(
        self, item_type: str, query: str, source: str, limit: int, project_path: str
    ) -> str:
        """Perform vector-based semantic search."""
        try:
            self._setup_vector_search(project_path)

            if self._hybrid_search is None:
                # Fall back to keyword search
                return await self._keyword_search(item_type, query, source, limit, project_path)

            # Perform hybrid search
            results = await self._hybrid_search.search(
                query=query, source=source, item_type=item_type, limit=limit
            )

            # If vector search returns empty, fall back to keyword search
            if not results:
                self.logger.info("Vector search returned empty, falling back to keyword search")
                return await self._keyword_search(item_type, query, source, limit, project_path)

            # Convert to standard format
            items = []
            for result in results:
                items.append(
                    {
                        "id": result.item_id,
                        "type": result.item_type,
                        "score": result.score,
                        "preview": result.content_preview,
                        "metadata": result.metadata,
                        "source": result.source,
                    }
                )

            return self._format_response(
                {
                    "items": items,
                    "total": len(items),
                    "query": query,
                    "search_type": "vector_hybrid",
                    "source": source,
                }
            )

        except Exception as e:
            self.logger.warning(f"Vector search failed, falling back to keyword search: {e}")
            return await self._keyword_search(item_type, query, source, limit, project_path)

    async def _keyword_search(
        self, item_type: str, query: str, source: str, limit: int, project_path: str
    ) -> str:
        """Perform traditional keyword-based search using handler dispatch."""
        # Create handler dynamically with project_path
        from lilux.handlers.directive.handler import DirectiveHandler
        from lilux.handlers.tool.handler import ToolHandler
        from lilux.handlers.knowledge.handler import KnowledgeHandler

        handlers = {
            "directive": DirectiveHandler,
            "tool": ToolHandler,
            "knowledge": KnowledgeHandler,
        }

        handler_class = handlers.get(item_type)
        if not handler_class:
            return self._format_response(
                {
                    "error": f"Unknown item_type: {item_type}",
                    "supported_types": list(handlers.keys()),
                }
            )

        # Dispatch to handler's search method
        handler = handler_class(project_path=project_path)
        result = await handler.search(query, source=source, limit=limit)

        # Add search type and quality indicators to response
        if isinstance(result, dict):
            result["search_type"] = "keyword"
            # Quality indicator: "good" for BM25-based scoring, "basic" for substring matching
            # Handlers use score_relevance which is BM25-inspired
            result["quality"] = "good"

            # Add quality indicator to individual results if present
            if "results" in result and isinstance(result["results"], list):
                for item in result["results"]:
                    item["quality"] = "good"

        self.logger.info(
            f"SearchTool result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}"
        )
        self.logger.info(
            f"SearchTool result total: {result.get('total', 'N/A') if isinstance(result, dict) else 'N/A'}"
        )
        self.logger.info(
            f"SearchTool search_type: {result.get('search_type', 'N/A') if isinstance(result, dict) else 'N/A'}"
        )
        return self._format_response(result)
