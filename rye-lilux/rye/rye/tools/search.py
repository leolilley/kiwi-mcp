"""RYE Search Tool - Intelligent search with content understanding.

Uses Lilux primitives for file search but adds:
- Content type detection (directive/tool/knowledge)
- Title extraction from XML/frontmatter
- Relevance scoring based on metadata
- Filtering by category, tags, source, date ranges
- Vector search if configured
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal
import hashlib
import json

# Import Lilux primitives dynamically
from lilux.schemas.tool_schema import search_items
from lilux.utils.resolvers import DirectiveResolver, ToolResolver, KnowledgeResolver, get_user_space
from lilux.utils.logger import get_logger


class SearchTool:
    """Intelligent search tool with content understanding."""

    def __init__(self, project_path: Optional[str] = None):
        """Initialize search tool with project path."""
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.logger = get_logger("rye_search")

        # Initialize resolvers for each item type
        self.directive_resolver = DirectiveResolver(self.project_path)
        self.tool_resolver = ToolResolver(self.project_path)
        self.knowledge_resolver = KnowledgeResolver(self.project_path)

        # Vector store for semantic search (if configured)
        self._vector_store = None
        self._init_vector_store()

    def _init_vector_store(self):
        """Initialize vector store for semantic search."""
        try:
            from lilux.storage.vector import (
                EmbeddingService,
                LocalVectorStore,
                load_vector_config,
            )

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
            self.logger.debug("Vector store initialized for semantic search")
        except (ValueError, ImportError) as e:
            self.logger.debug(f"Vector store not configured: {e}")
            self._vector_store = None

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute search with RYE intelligence.

        Args:
            arguments: Search parameters
                - item_type: "directive", "tool", or "knowledge"
                - query: Search query (natural language)
                - project_path: Project path (optional, uses current if not provided)
                - source: "project", "user", or "all" (default: "all")
                - limit: Maximum results (default: 10)
                - sort_by: "score", "date", or "name" (default: "score")
                - category: Filter by category (optional)
                - tags: Filter by tags (optional)
                - date_from: Filter by creation date (ISO format, optional)
                - date_to: Filter by creation date (ISO format, optional)

        Returns:
            Dict with search results and RYE-enriched metadata
        """
        try:
            # Extract arguments
            item_type = arguments.get("item_type", "all")
            query = arguments.get("query", "")
            project_path = Path(arguments.get("project_path", self.project_path))
            source = arguments.get("source", "all")
            limit = arguments.get("limit", 10)
            sort_by = arguments.get("sort_by", "score")
            category = arguments.get("category")
            tags = arguments.get("tags")
            date_from = arguments.get("date_from")
            date_to = arguments.get("date_to")

            # Try vector search first (if available and query is semantic)
            results = []
            if self._vector_store and query and len(query.split()) > 2:
                try:
                    vector_results = await self._vector_store.search(
                        query=query,
                        item_type=item_type if item_type != "all" else None,
                        limit=limit,
                    )
                    if vector_results:
                        self.logger.debug(f"Found {len(vector_results)} vector search results")
                        results.extend(self._enrich_vector_results(vector_results))
                except Exception as e:
                    self.logger.warning(f"Vector search failed, falling back to text search: {e}")

            # If no vector results, fall back to text search
            if not results:
                results = await self._text_search(
                    item_type=item_type,
                    query=query,
                    source=source,
                    category=category,
                    tags=tags,
                )

            # Apply date filters (RYE intelligence)
            if date_from or date_to:
                results = self._apply_date_filters(results, date_from, date_to)

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
                        x.get("name", x.get("id", "")).lower(),
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
                "item_type": item_type,
                "query": query,
                "source": source,
                "results": results,
                "total": len(results),
                "search_type": "vector" if self._vector_store and query else "text",
            }
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return {"error": str(e), "message": "Failed to search items"}

    async def _text_search(
        self,
        item_type: str,
        query: str,
        source: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform text search using Lilux's schema-driven extraction.

        RYE Intelligence:
        - Delegates to Lilux's search_items for file discovery
        - Enriches results with titles and content type info
        """
        results = []

        # Build search paths based on source
        search_paths = []
        if source in ("project", "all"):
            search_paths.append(self.project_path / ".ai")
        if source in ("user", "all"):
            search_paths.append(get_user_space())

        # Determine which item types to search
        item_types = [item_type] if item_type != "all" else ["directive", "tool", "knowledge"]

        # Search each item type using Lilux's schema-driven extraction
        for itype in item_types:
            # Build filters
            filters = {}
            if category:
                filters["category"] = category
            if tags:
                filters["tags"] = tags

            try:
                # Use Lilux's search_items (schema-driven extraction)
                itype_results = search_items(itype, query, search_paths, self.project_path, filters)

                # Add RYE intelligence: source field based on path
                for r in itype_results:
                    r["source"] = "project" if ".ai/" in str(r["path"]) else "user"

                results.extend(itype_results)
            except Exception as e:
                self.logger.warning(f"Failed to search {itype}: {e}")

        return results

    def _enrich_vector_results(self, vector_results: List[Dict]) -> List[Dict[str, Any]]:
        """
        Enrich vector search results with RYE intelligence.

        Vector search gives us content and scores, but we need:
        - Extracted titles (from XML/frontmatter)
        - Content type metadata
        - File paths
        """
        enriched = []

        for result in vector_results:
            try:
                item_path = Path(result.get("path"))
                if not item_path.exists():
                    continue

                # Determine item type from path
                item_type = self._detect_item_type(item_path)
                if not item_type:
                    continue

                # Extract title using RYE intelligence
                title = self._extract_title(item_path, item_type)

                # Add RYE-enriched metadata
                enriched_result = {
                    "path": str(item_path),
                    "item_type": item_type,
                    "title": title,
                    "score": result.get("score", 0.0),
                    "content_type": self._get_content_type(item_type),
                }

                # Add metadata from vector result
                for key in ["name", "id", "category", "tags", "created_at", "updated_at"]:
                    if key in result:
                        enriched_result[key] = result[key]

                enriched.append(enriched_result)
            except Exception as e:
                self.logger.warning(f"Failed to enrich vector result: {e}")

        return enriched

    def _detect_item_type(self, file_path: Path) -> Optional[str]:
        """
        Detect item type from file path (RYE intelligence).

        RYE knows:
        - .ai/directives/ -> directive
        - .ai/tools/ -> tool
        - .ai/knowledge/ -> knowledge
        """
        path_str = str(file_path)

        if "/directives/" in path_str or file_path.parent.name == "directives":
            return "directive"
        elif "/tools/" in path_str or file_path.parent.name == "tools":
            return "tool"
        elif "/knowledge/" in path_str or file_path.parent.name == "knowledge":
            return "knowledge"

        return None

    def _extract_title(self, file_path: Path, item_type: str) -> str:
        """
        Extract title from content (RYE intelligence).

        For directives: Parse XML and extract <description> or name
        For tools: Parse metadata and extract description
        For knowledge: Parse frontmatter and extract title
        """
        try:
            content = file_path.read_text()

            if item_type == "directive":
                # Extract title from directive XML
                from lilux.utils.parsers import parse_directive_file

                directive_data = parse_directive_file(file_path)
                return directive_data.get("description", "")

            elif item_type == "tool":
                # Extract title from tool metadata
                from lilux.schemas import extract_tool_metadata

                meta = extract_tool_metadata(file_path, self.project_path)
                return meta.get("description", meta.get("name", "Unnamed Tool"))

            elif item_type == "knowledge":
                # Extract title from frontmatter
                from lilux.utils.parsers import parse_knowledge_entry

                entry_data = parse_knowledge_entry(file_path)
                return entry_data.get("title", entry_data.get("id", "Untitled"))

        except Exception as e:
            self.logger.warning(f"Failed to extract title from {file_path}: {e}")

        # Fallback to filename
        return file_path.stem

    def _get_content_type(self, item_type: str) -> str:
        """
        Get content type description (RYE intelligence).
        """
        content_types = {
            "directive": "XML Workflow",
            "tool": "Python Script",
            "knowledge": "Markdown with Frontmatter",
        }
        return content_types.get(item_type, "Unknown")

    def _apply_date_filters(
        self, results: List[Dict], date_from: Optional[str], date_to: Optional[str]
    ) -> List[Dict]:
        """
        Apply date range filters to results (RYE intelligence).

        Args:
            results: Search results
            date_from: ISO format date string (inclusive)
            date_to: ISO format date string (inclusive)

        Returns:
            Filtered results
        """
        if not date_from and not date_to:
            return results

        filtered = []
        for result in results:
            # Get date from result (check multiple possible fields)
            result_date = result.get("updated_at") or result.get("created_at") or result.get("date")

            if not result_date:
                # No date info, can't filter - include it
                filtered.append(result)
                continue

            # Check if within range
            if date_from and result_date < date_from:
                continue
            if date_to and result_date > date_to:
                continue

            filtered.append(result)

        return filtered
