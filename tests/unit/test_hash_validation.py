"""
Unit tests for hash validation enforcement in handlers.

Tests that directives, scripts, and knowledge entries enforce hash validation
during run actions and properly block execution when content is modified.
"""

import pytest
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime, timezone

from kiwi_mcp.handlers.directive.handler import DirectiveHandler
from kiwi_mcp.handlers.script.handler import ScriptHandler
from kiwi_mcp.handlers.knowledge.handler import KnowledgeHandler


class TestDirectiveHashValidation:
    """Test directive hash validation enforcement."""
    
    @pytest.mark.asyncio
    async def test_directive_run_blocks_on_modified_hash(self, tmp_path):
        """Test directive run action blocks when content hash doesn't match."""
        # Create a directive file with signature
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        # Create valid XML content
        xml_content = """<directive name="test_directive" version="1.0.0">
  <metadata>
    <description>Test directive</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
  </metadata>
  <process>
    <step name="test">
      <action>Test action</action>
    </step>
  </process>
</directive>"""
        
        # Generate correct hash for original content
        original_hash = hashlib.sha256(xml_content.encode()).hexdigest()[:12]
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
        result = await handler.execute("run", "test_directive", {})
        
        # Should return error about modified content
        assert "error" in result
        assert "modified" in result["error"].lower()
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
  </metadata>
  <process>
    <step name="test">
      <action>Test action</action>
    </step>
  </process>
</directive>"""
        
        # Generate correct hash
        content_hash = hashlib.sha256(xml_content.encode()).hexdigest()[:12]
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
        result = await handler.execute("run", "test_directive", {})
        
        # Should NOT have signature error
        assert result.get("status") == "ready"
        assert "directive" in result


class TestScriptHashValidation:
    """Test script hash validation enforcement."""
    
    @pytest.mark.asyncio
    async def test_script_run_blocks_on_modified_hash(self, tmp_path):
        """Test script run action blocks when content hash doesn't match."""
        # Create a script file with signature
        script_dir = tmp_path / ".ai" / "scripts" / "test"
        script_dir.mkdir(parents=True)
        
        # Original script content
        script_content = '''"""Test script"""
import sys

def main():
    print("Original")

if __name__ == "__main__":
    main()
'''
        
        # Generate hash for original
        original_hash = hashlib.sha256(script_content.encode()).hexdigest()[:12]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        signature_line = f"# kiwi-mcp:validated:{timestamp}:{original_hash}\n"
        
        script_file = script_dir / "test_script.py"
        script_file.write_text(signature_line + script_content)
        
        # Modify the content (invalidate hash)
        modified_content = script_content.replace("Original", "Modified")
        script_file.write_text(signature_line + modified_content)
        
        # Try to run - should be blocked
        handler = ScriptHandler(project_path=str(tmp_path))
        result = await handler.execute("run", "test_script", {}, dry_run=False)
        
        # Should return error about modified content
        assert result.get("status") == "error"
        assert "modified" in result["error"].lower()
        assert "signature" in result
        assert result["signature"]["status"] == "modified"
    
    @pytest.mark.asyncio
    async def test_script_run_allows_valid_hash(self, tmp_path):
        """Test script run action allows execution when hash is valid."""
        # Create a script file with correct signature
        script_dir = tmp_path / ".ai" / "scripts" / "test"
        script_dir.mkdir(parents=True)
        
        script_content = '''"""Test script"""
import sys
import json

def main():
    result = {"status": "success", "data": {"message": "test"}}
    print(json.dumps(result))

if __name__ == "__main__":
    main()
'''
        
        # Generate correct hash
        content_hash = hashlib.sha256(script_content.encode()).hexdigest()[:12]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        signature_line = f"# kiwi-mcp:validated:{timestamp}:{content_hash}\n"
        
        script_file = script_dir / "test_script.py"
        script_file.write_text(signature_line + script_content)
        
        # Run should succeed (hash is valid)
        handler = ScriptHandler(project_path=str(tmp_path))
        result = await handler.execute("run", "test_script", {}, dry_run=False)
        
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
        
        # Generate hash for original
        original_hash = hashlib.sha256(entry_content.encode()).hexdigest()[:12]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Create frontmatter with signature
        file_content = f"""---
zettel_id: 001-test
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
zettel_id: 001-test
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
        result = await handler.execute("run", "001-test", {})
        
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
        
        # Generate correct hash
        content_hash = hashlib.sha256(entry_content.encode()).hexdigest()[:12]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Create frontmatter with correct signature
        file_content = f"""---
zettel_id: 001-test
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
        result = await handler.execute("run", "001-test", {})
        
        # Should NOT have signature error
        assert result.get("status") == "ready"
        assert "content" in result
        assert result["content"] == entry_content
    
    @pytest.mark.asyncio
    async def test_knowledge_run_allows_missing_signature(self, tmp_path):
        """Test knowledge run action allows entries without signature (legacy)."""
        # Create a knowledge entry WITHOUT signature (legacy format)
        knowledge_dir = tmp_path / ".ai" / "knowledge" / "test"
        knowledge_dir.mkdir(parents=True)
        
        # No signature fields
        file_content = """---
zettel_id: 002-legacy
title: Legacy Entry
entry_type: learning
category: test
tags: []
---

This is legacy content without signature.
"""
        knowledge_file = knowledge_dir / "002-legacy.md"
        knowledge_file.write_text(file_content)
        
        # Run should succeed (no signature = legacy, allowed)
        handler = KnowledgeHandler(project_path=str(tmp_path))
        result = await handler.execute("run", "002-legacy", {})
        
        # Should succeed (legacy format)
        assert result.get("status") == "ready"
        assert "content" in result


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
        result = await handler.execute("run", "test", {"skip_validation": True})
        
        # Should STILL be blocked (skip_validation is ignored)
        assert "error" in result
        assert "modified" in result["error"].lower() or "invalid" in result["error"].lower()
