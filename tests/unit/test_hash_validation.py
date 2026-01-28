"""
Unit tests for hash validation enforcement in handlers.

Tests that directives, scripts, and knowledge entries enforce hash validation
during run actions and properly block execution when content is modified.

These tests verify that handlers use the centralized MetadataManager
for all signature verification operations.
"""

import pytest
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime, timezone

from kiwi_mcp.handlers.directive.handler import DirectiveHandler
from kiwi_mcp.handlers.tool.handler import ToolHandler
from kiwi_mcp.handlers.knowledge.handler import KnowledgeHandler
from kiwi_mcp.utils.metadata_manager import MetadataManager


class TestDirectiveHashValidation:
    """Test directive hash validation enforcement."""

    @pytest.mark.asyncio
    async def test_directive_run_blocks_on_modified_hash(self, tmp_path):
        """Test directive run action blocks when content hash doesn't match."""
        # Create a directive file with signature
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)

        # Create valid XML content (include model tag for validation)
        xml_content = """<directive name="test_directive" version="1.0.0">
  <metadata>
    <description>Test directive</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="test">
      <action>Test action</action>
    </step>
  </process>
</directive>"""

        # Generate correct hash for original content using centralized method
        original_hash = MetadataManager.compute_hash(
            "directive",
            f"""# Test Directive

```xml
{xml_content}
```
""",
        )
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Create file with signature
        file_content = f"""<!-- kiwi-mcp:validated:{timestamp}:{original_hash} -->

# Test Directive

```xml
{xml_content}
```
"""
        directive_file = directive_dir / "test_directive.md"
        directive_file.write_text(file_content)

        # Now modify the XML content (this should invalidate the hash)
        modified_xml = xml_content.replace("Test action", "Modified action")
        modified_content = f"""<!-- kiwi-mcp:validated:{timestamp}:{original_hash} -->

# Test Directive

```xml
{modified_xml}
```
"""
        directive_file.write_text(modified_content)

        # Try to run - should be blocked
        handler = DirectiveHandler(project_path=str(tmp_path))
        result = await handler.execute("test_directive", {})

        # Should return error about modified content
        assert "error" in result
        # Error message should mention modification
        error_msg = result["error"].lower()
        assert "modified" in error_msg or "invalid" in error_msg or "signature" in error_msg
        assert "signature" in result
        assert result["signature"]["status"] == "modified"

    @pytest.mark.asyncio
    async def test_directive_run_allows_valid_hash(self, tmp_path):
        """Test directive run action allows execution when hash is valid."""
        # Create a directive file with correct signature
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)

        xml_content = """<directive name="test_directive" version="1.0.0">
  <metadata>
    <description>Test directive</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="test">
      <action>Test action</action>
    </step>
  </process>
</directive>"""

        # Generate correct hash using centralized method
        content_hash = MetadataManager.compute_hash(
            "directive",
            f"""# Test Directive

```xml
{xml_content}
```
""",
        )
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Create file with correct signature
        file_content = f"""<!-- kiwi-mcp:validated:{timestamp}:{content_hash} -->

# Test Directive

```xml
{xml_content}
```
"""
        directive_file = directive_dir / "test_directive.md"
        directive_file.write_text(file_content)

        # Run should succeed (no signature error)
        handler = DirectiveHandler(project_path=str(tmp_path))
        result = await handler.execute("test_directive", {})

        # Should NOT have signature error
        assert result.get("status") == "ready"
        # Handler returns directive data with name, description, etc., not a "directive" key
        assert "name" in result
        assert result["name"] == "test_directive"


class TestToolHashValidation:
    """Test tool hash validation enforcement."""

    @pytest.mark.asyncio
    async def test_tool_run_blocks_on_modified_hash(self, tmp_path):
        """Test tool run action blocks when content hash doesn't match."""
        # Create a tool file with signature
        tool_dir = tmp_path / ".ai" / "scripts" / "test"
        tool_dir.mkdir(parents=True)

        # Original tool content
        tool_content = '''"""Test tool"""
import sys

def main():
    print("Original")

if __name__ == "__main__":
    main()
'''

        # Generate hash for original using centralized method
        original_hash = MetadataManager.compute_hash("tool", tool_content)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        signature_line = f"# kiwi-mcp:validated:{timestamp}:{original_hash}\n"

        tool_file = tool_dir / "test_tool.py"
        tool_file.write_text(signature_line + tool_content)

        # Modify the content (invalidate hash)
        modified_content = tool_content.replace("Original", "Modified")
        tool_file.write_text(signature_line + modified_content)

        # Try to run - should be blocked
        handler = ToolHandler(project_path=str(tmp_path))
        result = await handler.execute("test_tool", {})

        # Should return error about modified content
        assert result.get("status") == "error"
        assert "modified" in result["error"].lower()
        assert "signature" in result
        assert result["signature"]["status"] == "modified"

    @pytest.mark.asyncio
    async def test_tool_run_allows_valid_hash(self, tmp_path):
        """Test tool run action allows execution when hash is valid."""
        # Create a tool file with correct signature
        tool_dir = tmp_path / ".ai" / "scripts" / "test"
        tool_dir.mkdir(parents=True)

        tool_content = '''"""Test tool"""
import sys
import json

def main():
    result = {"status": "success", "data": {"message": "test"}}
    print(json.dumps(result))

if __name__ == "__main__":
    main()
'''

        # Generate correct hash using centralized method
        content_hash = MetadataManager.compute_hash("tool", tool_content)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        signature_line = f"# kiwi-mcp:validated:{timestamp}:{content_hash}\n"

        tool_file = tool_dir / "test_tool.py"
        tool_file.write_text(signature_line + tool_content)

        # Run should succeed (hash is valid)
        handler = ToolHandler(project_path=str(tmp_path))
        result = await handler.execute("test_tool", {})

        # Should NOT have signature error
        # Note: actual execution might fail for other reasons, but NOT signature
        if "error" in result:
            assert "signature" not in result["error"].lower()
            assert "modified" not in result["error"].lower()


class TestKnowledgeHashValidation:
    """Test knowledge entry hash validation enforcement."""

    @pytest.mark.asyncio
    async def test_knowledge_run_blocks_on_modified_hash(self, tmp_path):
        """Test knowledge run action blocks when content hash doesn't match."""
        # Create a knowledge entry with signature
        knowledge_dir = tmp_path / ".ai" / "knowledge" / "test"
        knowledge_dir.mkdir(parents=True)

        # Original content
        entry_content = "This is the original knowledge content."

        # Generate hash for original using centralized method
        original_hash = MetadataManager.compute_hash("knowledge", entry_content)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Create frontmatter with signature (include version)
        file_content = f"""---
version: "1.0.0"
id: 001-test
title: Test Entry
entry_type: learning
category: test
tags: []
validated_at: {timestamp}
content_hash: {original_hash}
---

{entry_content}
"""
        knowledge_file = knowledge_dir / "001-test.md"
        knowledge_file.write_text(file_content)

        # Modify the content (invalidate hash)
        modified_content = "This is the MODIFIED knowledge content."
        modified_file = f"""---
version: "1.0.0"
id: 001-test
title: Test Entry
entry_type: learning
category: test
tags: []
validated_at: {timestamp}
content_hash: {original_hash}
---

{modified_content}
"""
        knowledge_file.write_text(modified_file)

        # Try to run - should be blocked
        handler = KnowledgeHandler(project_path=str(tmp_path))
        result = await handler.execute("001-test", {})

        # Should return error about modified content
        assert result.get("status") == "error"
        assert "modified" in result["error"].lower()
        assert "signature" in result
        assert result["signature"]["status"] == "modified"

    @pytest.mark.asyncio
    async def test_knowledge_run_allows_valid_hash(self, tmp_path):
        """Test knowledge run action allows execution when hash is valid."""
        # Create a knowledge entry with correct signature
        knowledge_dir = tmp_path / ".ai" / "knowledge" / "test"
        knowledge_dir.mkdir(parents=True)

        entry_content = "This is valid knowledge content."

        # Create frontmatter first (without signature fields)
        # Use proper YAML format: tags as array, version as string (quoted for YAML to parse as string)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        file_content_without_sig = f"""---
version: "1.0.0"
id: 001-test
title: Test Entry
entry_type: learning
category: test
tags: []
---

{entry_content}
"""
        # Compute hash - extract_content_for_hash extracts content after frontmatter
        # So we need to compute hash for the full file, and it will extract just the content part
        content_hash = MetadataManager.compute_hash("knowledge", file_content_without_sig)
        
        # Now create file with signature fields (use proper YAML format)
        file_content = f"""---
version: 1.0.0
id: 001-test
title: Test Entry
entry_type: learning
category: test
tags: []
validated_at: {timestamp}
content_hash: {content_hash}
---

{entry_content}
"""
        knowledge_file = knowledge_dir / "001-test.md"
        knowledge_file.write_text(file_content)

        # Run should succeed (hash is valid)
        handler = KnowledgeHandler(project_path=str(tmp_path))
        # Mock registry to avoid connection errors
        from unittest.mock import patch, AsyncMock
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None  # No newer version in registry
            result = await handler.execute("001-test", {})

        # Should NOT have signature error
        assert result.get("status") == "ready"
        assert "content" in result
        assert result["content"] == entry_content

    @pytest.mark.asyncio
    async def test_knowledge_run_blocks_missing_signature(self, tmp_path):
        """Test knowledge run action blocks entries without signature."""
        # Create a knowledge entry WITHOUT signature
        knowledge_dir = tmp_path / ".ai" / "knowledge" / "test"
        knowledge_dir.mkdir(parents=True)

        # No signature fields (but include version for validation)
        # Use proper YAML format: version as string (quoted), tags as array
        file_content = """---
version: "1.0.0"
id: 002-no-sig
title: Entry Without Signature
entry_type: learning
category: test
tags: []
---

This is content without signature.
"""
        knowledge_file = knowledge_dir / "002-no-sig.md"
        knowledge_file.write_text(file_content)

        # Run should fail (missing signature is now blocked)
        handler = KnowledgeHandler(project_path=str(tmp_path))
        # Mock registry to avoid connection errors
        from unittest.mock import patch, AsyncMock
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None  # No newer version in registry
            result = await handler.execute("002-no-sig", {})

        # Should fail with signature error
        assert result.get("status") == "error"
        assert "no valid signature" in result.get("error", "").lower()
        assert "path" in result
        assert "solution" in result


class TestHashValidationNoBypass:
    """Test that hash validation cannot be bypassed."""

    @pytest.mark.asyncio
    async def test_directive_run_no_skip_validation_param(self, tmp_path):
        """Test directive run does not accept skip_validation parameter."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)

        xml_content = """<directive name="test" version="1.0.0">
  <metadata>
    <description>Test</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process><step name="s"><action>a</action></step></process>
</directive>"""

        # Wrong hash intentionally
        wrong_hash = "000000000000"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        file_content = f"""<!-- kiwi-mcp:validated:{timestamp}:{wrong_hash} -->
```xml
{xml_content}
```
"""
        (directive_dir / "test.md").write_text(file_content)

        # Try to run with skip_validation - should still be blocked
        handler = DirectiveHandler(project_path=str(tmp_path))
        result = await handler.execute("test", {"skip_validation": True})

        # Should STILL be blocked (skip_validation is ignored)
        assert "error" in result
        assert "modified" in result["error"].lower() or "invalid" in result["error"].lower()
