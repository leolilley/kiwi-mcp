"""RYE Sign Tool - Intelligent signing with validation.

Uses Lilux primitives for file I/O but adds:
- Signature format validation
- Hash computation (unified integrity)
- Keychain access for signing keys
- Re-signing support (existing signatures included in validation chain)
- Vector store embedding
"""

import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
import re

# Import Lilux primitives dynamically
from lilux.utils.resolvers import DirectiveResolver, ToolResolver, KnowledgeResolver
from lilux.utils.logger import get_logger


class SignTool:
    """Intelligent sign tool with hash computation."""

    # Signature format (RYE knowledge)
    SIGNATURE_PATTERN = re.compile(r"<!-- kiwi-mcp:valid:([^:]+):([a-f0-9]+):(.+?) -->")
    SIGNATURE_TEMPLATE = "<!-- kiwi-mcp:valid:{hash}:{signature}:{item_id} -->"

    def __init__(self, project_path: Optional[str] = None):
        """Initialize sign tool with project path."""
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.logger = get_logger("rye_sign")

        # Initialize resolvers for each item type
        self.directive_resolver = DirectiveResolver(self.project_path)
        self.tool_resolver = ToolResolver(self.project_path)
        self.knowledge_resolver = KnowledgeResolver(self.project_path)

        # Vector store for embedding (if configured)
        self._vector_store = None
        self._init_vector_store()

    def _init_vector_store(self):
        """Initialize vector store for automatic embedding."""
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
            self.logger.debug("Vector store initialized for embedding")
        except (ValueError, ImportError) as e:
            self.logger.debug(f"Vector store not configured: {e}")
            self._vector_store = None

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute sign with RYE intelligence.

        Args:
            arguments: Sign parameters
                - item_type: "directive", "tool", or "knowledge"
                - item_id: ID/name of item to sign
                - project_path: Project path (optional, uses current if not provided)
                - location: "project" or "user" (default: "project")
                - category: Category for new items (optional)
                - embed: Auto-embed in vector store (default: True)

        Returns:
            Dict with sign result and signature info
        """
        try:
            # Extract arguments
            item_type = arguments.get("item_type")
            item_id = arguments.get("item_id")
            project_path = Path(arguments.get("project_path", self.project_path))
            location = arguments.get("location", "project")
            category = arguments.get("category")
            embed = arguments.get("embed", True)

            if not item_type or not item_id:
                return {"error": "item_type and item_id are required"}

            # Update project path if changed
            self.project_path = project_path
            self.directive_resolver = DirectiveResolver(project_path)
            self.tool_resolver = ToolResolver(project_path)
            self.knowledge_resolver = KnowledgeResolver(project_path)

            # Route to appropriate signer
            if item_type == "directive":
                return await self._sign_directive(item_id, location, category, embed)
            elif item_type == "tool":
                return await self._sign_tool(item_id, location, category, embed)
            elif item_type == "knowledge":
                return await self._sign_knowledge(item_id, location, category, embed)
            else:
                return {
                    "error": f"Unknown item_type: {item_type}",
                    "valid_types": ["directive", "tool", "knowledge"],
                }
        except Exception as e:
            self.logger.error(f"Sign failed: {e}")
            return {"error": str(e), "message": f"Failed to sign {item_id}"}

    async def _sign_directive(
        self, directive_name: str, location: str, category: Optional[str], embed: bool
    ) -> Dict[str, Any]:
        """Sign directive with RYE intelligence."""
        # Find directive file
        file_path = self.directive_resolver.resolve(directive_name)

        if not file_path or not file_path.exists():
            return {
                "error": f"Directive file not found: {directive_name}",
                "hint": f"Create file first at .ai/directives/{{category}}/{directive_name}.md",
            }

        # Parse directive XML (RYE intelligence)
        from lilux.utils.parsers import parse_directive_file

        directive_data = parse_directive_file(file_path)

        # Validate structure (RYE intelligence)
        validation = self._validate_directive_structure(directive_data)
        if not validation["valid"]:
            return {
                "error": "Directive validation failed",
                "details": validation["issues"],
                "path": str(file_path),
            }

        # Get version (required for hash)
        version = directive_data.get("version", "0.0.0")
        if version == "0.0.0":
            return {
                "error": "Directive validation failed",
                "details": ["Directive is missing required 'version' attribute"],
                "solution": 'Add version: <directive name="..." version="1.0.0">',
            }

        # Read content
        content = file_path.read_text()

        # Compute unified integrity hash (RYE intelligence)
        # Remove existing signature before hashing (re-signing support)
        content_without_sig = self.remove_signature(content)

        content_hash = self.compute_directive_integrity(
            directive_name,
            version,
            content_without_sig,
            directive_data,
        )

        # Generate signature block (RYE intelligence)
        signature_block = self.SIGNATURE_TEMPLATE.format(
            hash=content_hash, signature="", item_id=directive_name
        )

        # Add signature to content
        signed_content = content_without_sig + "\n" + signature_block

        # Write file
        file_path.write_text(signed_content)

        # Embed in vector store if configured (RYE intelligence)
        if embed and self._vector_store:
            await self._embed_item(
                "directive",
                directive_name,
                directive_data.get("description", ""),
            )

        return {
            "status": "signed",
            "item_type": "directive",
            "item_id": directive_name,
            "path": str(file_path),
            "integrity": content_hash,
            "integrity_short": content_hash[:12],
            "location": location,
        }

    async def _sign_tool(
        self, tool_name: str, location: str, category: Optional[str], embed: bool
    ) -> Dict[str, Any]:
        """Sign tool with RYE intelligence."""
        # Find tool file
        file_path = self.tool_resolver.resolve(tool_name)

        if not file_path or not file_path.exists():
            return {
                "error": f"Tool file not found: {tool_name}",
                "hint": f"Create file first at .ai/tools/{{category}}/{tool_name}.py",
            }

        # Extract tool metadata (RYE intelligence)
        from lilux.schemas import extract_tool_metadata, validate_tool_metadata

        tool_meta = extract_tool_metadata(file_path, self.project_path)

        # Validate structure (RYE intelligence)
        validation = validate_tool_metadata(tool_meta)
        if not validation["valid"]:
            return {
                "error": "Tool validation failed",
                "details": validation["issues"],
                "warnings": validation.get("warnings", []),
                "path": str(file_path),
            }

        # Get version (required for hash)
        version = tool_meta.get("version", "0.0.0")
        if version == "0.0.0":
            return {
                "error": "Tool validation failed",
                "details": ['Tool is missing required version. Add: __version__ = "1.0.0"'],
                "path": str(file_path),
            }

        # Read content
        content = file_path.read_text()

        # Compute unified integrity hash (RYE intelligence)
        # Remove existing signature before hashing (re-signing support)
        content_without_sig = self.remove_signature(content)

        content_hash = self.compute_tool_integrity(
            tool_name,
            version,
            content_without_sig,
            tool_meta,
        )

        # Generate signature block (RYE intelligence)
        signature_block = self.SIGNATURE_TEMPLATE.format(
            hash=content_hash, signature="", item_id=tool_name
        )

        # Add signature to content
        signed_content = content_without_sig + "\n" + signature_block

        # Write file
        file_path.write_text(signed_content)

        # Generate lockfile (RYE intelligence - delegates to Lilux)
        lockfile_info = await self._generate_lockfile(tool_name, version, category or "utility")

        # Embed in vector store if configured (RYE intelligence)
        if embed and self._vector_store:
            await self._embed_item(
                "tool",
                tool_name,
                tool_meta.get("description", ""),
            )

        return {
            "status": "signed",
            "item_type": "tool",
            "item_id": tool_name,
            "path": str(file_path),
            "integrity": content_hash,
            "integrity_short": content_hash[:12],
            "location": location,
            "lockfile": lockfile_info,
        }

    async def _sign_knowledge(
        self, knowledge_id: str, location: str, category: Optional[str], embed: bool
    ) -> Dict[str, Any]:
        """Sign knowledge entry with RYE intelligence."""
        # Find knowledge file
        file_path = self.knowledge_resolver.resolve(knowledge_id)

        if not file_path or not file_path.exists():
            return {
                "error": f"Knowledge entry file not found: {knowledge_id}",
                "hint": f"Create file first at .ai/knowledge/{{category}}/{knowledge_id}.md",
            }

        # Parse knowledge frontmatter (RYE intelligence)
        from lilux.utils.parsers import parse_knowledge_entry

        entry_data = parse_knowledge_entry(file_path)

        # Validate structure (RYE intelligence)
        validation = self._validate_knowledge_structure(entry_data)
        if not validation["valid"]:
            return {
                "error": "Knowledge entry validation failed",
                "details": validation["issues"],
                "path": str(file_path),
            }

        # Get version (required for hash)
        version = entry_data.get("version", "1.0.0")

        # Read content
        content = file_path.read_text()

        # Compute unified integrity hash (RYE intelligence)
        # Remove existing signature before hashing (re-signing support)
        content_without_sig = self.remove_signature(content)

        content_hash = self.compute_knowledge_integrity(
            knowledge_id,
            version,
            content_without_sig,
            entry_data,
        )

        # Generate signature block (RYE intelligence)
        signature_block = self.SIGNATURE_TEMPLATE.format(
            hash=content_hash, signature="", item_id=knowledge_id
        )

        # Add signature to content
        signed_content = content_without_sig + "\n" + signature_block

        # Write file
        file_path.write_text(signed_content)

        # Embed in vector store if configured (RYE intelligence)
        if embed and self._vector_store:
            await self._embed_item(
                "knowledge",
                knowledge_id,
                entry_data.get("title", ""),
            )

        return {
            "status": "signed",
            "item_type": "knowledge",
            "item_id": knowledge_id,
            "path": str(file_path),
            "integrity": content_hash,
            "integrity_short": content_hash[:12],
            "location": location,
        }

    def compute_directive_integrity(
        self, name: str, version: str, content: str, metadata: Dict[str, Any]
    ) -> str:
        """
        Compute unified integrity hash for directive (RYE intelligence).

        Hash algorithm: SHA256
        """
        # Build canonical content string
        canonical_parts = [
            f"name:{name}",
            f"version:{version}",
        ]

        # Add optional metadata fields
        for field in ["category", "description"]:
            if field in metadata and metadata[field]:
                canonical_parts.append(f"{field}:{metadata[field]}")

        canonical = "\n".join(canonical_parts) + "\n" + content

        return hashlib.sha256(canonical.encode()).hexdigest()

    def compute_tool_integrity(
        self, name: str, version: str, content: str, metadata: Dict[str, Any]
    ) -> str:
        """
        Compute unified integrity hash for tool (RYE intelligence).

        Hash algorithm: SHA256
        """
        # Build canonical content string
        canonical_parts = [
            f"name:{name}",
            f"version:{version}",
        ]

        # Add optional metadata fields
        for field in ["description", "tool_type"]:
            if field in metadata and metadata[field]:
                canonical_parts.append(f"{field}:{metadata[field]}")

        canonical = "\n".join(canonical_parts) + "\n" + content

        return hashlib.sha256(canonical.encode()).hexdigest()

    def compute_knowledge_integrity(
        self, id: str, version: str, content: str, metadata: Dict[str, Any]
    ) -> str:
        """
        Compute unified integrity hash for knowledge (RYE intelligence).

        Hash algorithm: SHA256
        """
        # Build canonical content string
        canonical_parts = [
            f"id:{id}",
            f"version:{version}",
        ]

        # Add optional metadata fields
        for field in ["title", "entry_type", "category"]:
            if field in metadata and metadata[field]:
                canonical_parts.append(f"{field}:{metadata[field]}")

        # Add tags (sorted for consistency)
        if "tags" in metadata and metadata["tags"]:
            tags = sorted(metadata["tags"])
            canonical_parts.append(f"tags:{','.join(tags)}")

        canonical = "\n".join(canonical_parts) + "\n" + content

        return hashlib.sha256(canonical.encode()).hexdigest()

    def remove_signature(self, content: str) -> str:
        """
        Remove existing signature from content (RYE intelligence).

        Supports re-signing by removing old signature.
        """
        # Remove signature block if present
        signature_pattern = r"\n?<!-- kiwi-mcp:valid:[^:]+:[a-f0-9]+:.+? -->\n?$"
        content_without_sig = re.sub(signature_pattern, "", content)

        return content_without_sig.strip()

    def extract_signature_info(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract signature information from content (RYE intelligence).

        Returns:
            Dict with hash, signature, item_id, or None if not signed
        """
        match = self.SIGNATURE_PATTERN.search(content)
        if not match:
            return None

        return {
            "hash": match.group(1),
            "signature": match.group(2),
            "item_id": match.group(3),
        }

    def _validate_directive_structure(self, directive_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate directive structure (RYE intelligence)."""
        issues = []

        # Required fields
        if "name" not in directive_data or not directive_data["name"]:
            issues.append("Directive must have a 'name' attribute")

        if "version" not in directive_data or not directive_data["version"]:
            issues.append("Directive must have a 'version' attribute")

        if "description" not in directive_data:
            issues.append("Directive must have <description> element")

        # Process structure
        if "process" not in directive_data:
            issues.append("Directive must have <process> element")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }

    def _validate_knowledge_structure(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate knowledge structure (RYE intelligence)."""
        issues = []

        # Required fields
        if "id" not in entry_data or not entry_data["id"]:
            issues.append("Knowledge entry must have 'id' in frontmatter")

        if "title" not in entry_data or not entry_data["title"]:
            issues.append("Knowledge entry must have 'title' in frontmatter")

        if "entry_type" not in entry_data or not entry_data["entry_type"]:
            issues.append("Knowledge entry must have 'entry_type' in frontmatter")

        # Content
        if "content" not in entry_data:
            issues.append("Knowledge entry must have markdown content")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }

    async def _generate_lockfile(
        self, tool_name: str, version: str, category: str
    ) -> Dict[str, Any]:
        """
        Generate lockfile for tool (RYE intelligence, delegates to Lilux).

        Uses Lilux's ChainResolver to freeze dependencies.
        """
        try:
            from lilux.primitives.executor import ChainResolver
            from lilux.runtime.lockfile_store import LockfileStore

            # Resolve tool's chain
            resolver = ChainResolver(self.project_path)
            chain = await resolver.resolve(tool_name)

            if not chain:
                return {
                    "status": "skipped",
                    "reason": "No chain to freeze (tool has no dependencies)",
                }

            # Get lockfile store
            lockfile_store = LockfileStore(project_root=self.project_path)

            # Freeze chain
            lockfile = lockfile_store.freeze(
                tool_id=tool_name, version=version, category=category, chain=chain
            )

            # Save to project scope
            lockfile_path = lockfile_store.save(lockfile, category=category, scope="project")

            return {
                "status": "generated",
                "path": str(lockfile_path),
                "chain_length": len(chain),
            }
        except Exception as e:
            self.logger.warning(f"Lockfile generation failed for {tool_name}: {e}")
            return {"status": "failed", "error": str(e)}

    async def _embed_item(self, item_type: str, item_id: str, text: str):
        """Embed item in vector store (RYE intelligence)."""
        try:
            if not self._vector_store:
                return

            await self._vector_store.add(
                item_type=item_type,
                item_id=item_id,
                content=text,
            )

            self.logger.debug(f"Embedded {item_type}/{item_id} in vector store")
        except Exception as e:
            self.logger.warning(f"Failed to embed {item_type}/{item_id}: {e}")
