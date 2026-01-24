"""Local filesystem chain resolution without registry.

Resolves executor chains by walking local files, enabling offline development
and eliminating the requirement to publish tools to a registry before testing.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List
from kiwi_mcp.schemas.tool_schema import extract_tool_metadata
from kiwi_mcp.utils.metadata_manager import MetadataManager
from kiwi_mcp.utils.resolvers import ToolResolver

logger = logging.getLogger(__name__)


class ToolNotFoundError(Exception):
    """Raised when a tool cannot be found locally."""
    pass


class LocalChainResolver:
    """Resolve executor chains from local filesystem only.
    
    Walks the chain of executor dependencies by:
    1. Resolving tool name to file path
    2. Extracting metadata from the file
    3. Following executor_id to next tool
    4. Stopping at primitives (executor_id is None)
    
    Returns the same chain structure as registry for compatibility.
    """

    def __init__(self, project_path: Path):
        """
        Initialize resolver with project path.
        
        Args:
            project_path: Root path to project containing .ai/ folder
        """
        self.project_path = project_path
        self.resolver = ToolResolver(project_path)
        logger.debug(f"LocalChainResolver initialized with project_path={project_path}")

    async def resolve_chain(self, tool_id: str) -> List[Dict[str, Any]]:
        """
        Resolve full executor chain by walking local files.

        Args:
            tool_id: Starting tool ID (e.g., "hello_node")

        Returns:
            Chain from leaf to primitive (same structure as registry)
            
        Raises:
            ToolNotFoundError: If tool is not found locally

        Example:
            >>> resolver = LocalChainResolver(Path("/project"))
            >>> chain = await resolver.resolve_chain("hello_node")
            >>> [link["tool_id"] for link in chain]
            ["hello_node", "node_runtime", "subprocess"]
        """
        chain = []
        visited = set()
        current_id = tool_id

        while current_id:
            # Prevent infinite loops
            if current_id in visited:
                logger.error(f"Circular dependency detected: {current_id}")
                raise ToolNotFoundError(
                    f"Circular dependency in chain for '{tool_id}': {current_id} already visited"
                )
            visited.add(current_id)

            # Resolve file path
            file_path = self.resolver.resolve(current_id)
            if not file_path:
                # Tool not found locally
                if not chain:
                    # Starting tool not found
                    raise ToolNotFoundError(
                        f"Tool '{tool_id}' not found locally. "
                        f"Use 'load' action to copy from registry first."
                    )
                else:
                    # Dependency not found
                    raise ToolNotFoundError(
                        f"Dependency '{current_id}' not found locally for tool '{tool_id}'. "
                        f"Missing executor in chain: {[t['tool_id'] for t in chain]} → {current_id}"
                    )

            logger.debug(f"Resolved {current_id} to {file_path}")

            # Extract metadata
            try:
                metadata = extract_tool_metadata(file_path, self.project_path)
            except Exception as e:
                logger.error(f"Failed to extract metadata for {current_id}: {e}")
                raise ToolNotFoundError(
                    f"Failed to extract metadata from '{file_path}': {e}"
                )

            # Build chain link (same structure as registry)
            chain_link = {
                "tool_id": current_id,
                "tool_type": metadata.get("tool_type"),
                "executor_id": metadata.get("executor_id"),
                "version": metadata.get("version", "0.0.0"),
                "manifest": {
                    "name": metadata.get("name"),
                    "version": metadata.get("version"),
                    "description": metadata.get("description"),
                    "tool_type": metadata.get("tool_type"),
                    "executor_id": metadata.get("executor_id"),
                    "category": metadata.get("category"),
                    "config": metadata.get("config"),
                    "config_schema": metadata.get("config_schema"),
                    "mutates_state": metadata.get("mutates_state", False),
                },
                # Add local-specific metadata
                "file_path": str(file_path),
                "source": "local",
            }
            
            # Extract integrity hash from signature - fail if missing
            file_content = file_path.read_text()
            
            content_hash = MetadataManager.get_signature_hash(
                "tool", file_content, file_path=file_path, project_path=self.project_path
            )
            
            if not content_hash:
                raise ToolNotFoundError(
                    f"Tool '{current_id}' has no signature. "
                    f"Run execute(action='create', item_id='{current_id}', ...) to validate."
                )
            
            chain_link["content_hash"] = content_hash
            logger.debug(f"Using signature hash for {current_id}: {content_hash[:12]}...")

            chain.append(chain_link)
            logger.debug(
                f"Added to chain: {current_id} ({metadata.get('tool_type')}) → {metadata.get('executor_id')}"
            )

            # Move to next executor
            current_id = metadata.get("executor_id")

            # Stop at primitives (executor_id is None)
            if current_id is None:
                logger.debug(f"Reached primitive, chain complete: {len(chain)} steps")
                break

        return chain

    async def resolve_chains_batch(
        self, tool_ids: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Batch resolve multiple chains.
        
        Args:
            tool_ids: List of tool identifiers
            
        Returns:
            Dict mapping tool_id to its chain (or empty list if not found)
        """
        results = {}
        for tool_id in tool_ids:
            try:
                results[tool_id] = await self.resolve_chain(tool_id)
            except ToolNotFoundError as e:
                logger.warning(f"Tool '{tool_id}' not found: {e}")
                results[tool_id] = []
        return results
