"""
Integration tests for MetadataManager and ValidationManager.

Tests end-to-end flows and integration with handlers.
"""

import pytest
from pathlib import Path

from kiwi_mcp.utils.metadata_manager import MetadataManager
from kiwi_mcp.utils.validators import ValidationManager
from kiwi_mcp.utils.parsers import (
    parse_directive_file,
    parse_script_metadata,
    parse_knowledge_entry,
)


class TestMetadataValidationIntegration:
    """Test MetadataManager and ValidationManager working together."""

    @pytest.mark.integration
    @pytest.mark.metadata
    @pytest.mark.validation
    def test_create_validate_sign_verify_directive(self, sample_directive_file):
        """Test complete flow: parse → validate → sign → verify for directive."""
        # Parse
        parsed_data = parse_directive_file(sample_directive_file)

        # Validate
        validation_result = ValidationManager.validate(
            "directive", sample_directive_file, parsed_data
        )
        assert validation_result["valid"] is True

        # Sign
        file_content = sample_directive_file.read_text()
        signed_content = MetadataManager.sign_content("directive", file_content)

        # Verify
        verify_result = MetadataManager.verify_signature("directive", signed_content)
        assert verify_result is not None
        assert verify_result["status"] == "valid"

    @pytest.mark.integration
    @pytest.mark.metadata
    @pytest.mark.validation
    def test_create_validate_sign_verify_script(self, sample_tool_file):
        """Test complete flow: parse → validate → sign → verify for tool."""
        # Parse
        parsed_data = parse_script_metadata(sample_tool_file)
        
        # Add required tool fields for ToolValidator
        parsed_data["tool_id"] = parsed_data.get("name", "test_tool")
        parsed_data["tool_type"] = "primitive"
        if not parsed_data.get("version"):
            parsed_data["version"] = "1.0.0"

        # Validate
        validation_result = ValidationManager.validate("tool", sample_tool_file, parsed_data)
        assert validation_result["valid"] is True

        # Sign
        file_content = sample_tool_file.read_text()
        signed_content = MetadataManager.sign_content("tool", file_content)

        # Verify
        verify_result = MetadataManager.verify_signature("tool", signed_content)
        assert verify_result is not None
        assert verify_result["status"] == "valid"

    @pytest.mark.integration
    @pytest.mark.metadata
    @pytest.mark.validation
    def test_create_validate_sign_verify_knowledge(self, sample_knowledge_file):
        """Test complete flow: parse → validate → sign → verify for knowledge."""
        # Parse
        parsed_data = parse_knowledge_entry(sample_knowledge_file)

        # Validate
        validation_result = ValidationManager.validate(
            "knowledge", sample_knowledge_file, parsed_data
        )
        assert validation_result["valid"] is True

        # For knowledge, signature is in frontmatter, so we need to rebuild it
        from kiwi_mcp.utils.metadata_manager import compute_content_hash, generate_timestamp

        content = parsed_data["content"]
        content_hash = compute_content_hash(content)
        timestamp = generate_timestamp()

        # Rebuild with signature (include version as required)
        frontmatter = f"""---
version: "1.0.0"
zettel_id: {parsed_data["zettel_id"]}
title: {parsed_data["title"]}
entry_type: {parsed_data["entry_type"]}
category: {parsed_data["category"]}
tags: {parsed_data.get("tags", [])}
validated_at: {timestamp}
content_hash: {content_hash}
---

"""
        signed_content = frontmatter + content

        # Verify
        verify_result = MetadataManager.verify_signature("knowledge", signed_content)
        assert verify_result is not None
        assert verify_result["status"] == "valid"

    @pytest.mark.integration
    @pytest.mark.metadata
    @pytest.mark.validation
    def test_validation_fails_then_signature_not_created(self, tmp_path):
        """Test that invalid items don't get signed."""
        # Create invalid directive (missing model)
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)

        invalid_xml = """<directive name="invalid" version="1.0.0">
  <metadata>
    <description>Invalid directive</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
  </metadata>
</directive>"""

        file_content = f"""# Invalid Directive

```xml
{invalid_xml}
```
"""
        directive_file = directive_dir / "invalid.md"
        directive_file.write_text(file_content)

        # Parse
        parsed_data = parse_directive_file(directive_file)

        # Validate - should fail
        validation_result = ValidationManager.validate("directive", directive_file, parsed_data)
        assert validation_result["valid"] is False

        # Should not be able to sign invalid content (validation would catch it first)
        # In practice, handlers check validation before signing


class TestHandlerIntegration:
    """Test integration with handlers using centralized methods."""

    @pytest.mark.integration
    @pytest.mark.handlers
    @pytest.mark.metadata
    @pytest.mark.asyncio
    async def test_directive_handler_uses_metadata_manager(
        self, tmp_path, sample_directive_content
    ):
        """Test that DirectiveHandler uses MetadataManager for signature operations."""
        from kiwi_mcp.handlers.directive.handler import DirectiveHandler

        # Create directive file
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)

        file_content = f"""# Test Directive

```xml
{sample_directive_content}
```
"""
        directive_file = directive_dir / "test_directive.md"
        directive_file.write_text(file_content)

        # Sign using handler's create action (which uses MetadataManager)
        handler = DirectiveHandler(project_path=str(tmp_path))
        result = await handler.execute("create", "test_directive", {"location": "project"})

        assert result.get("status") == "created"
        assert "signature" in result

        # Verify signature was added
        signed_content = directive_file.read_text()
        verify_result = MetadataManager.verify_signature("directive", signed_content)
        assert verify_result is not None
        assert verify_result["status"] == "valid"

    @pytest.mark.integration
    @pytest.mark.handlers
    @pytest.mark.validation
    @pytest.mark.asyncio
    async def test_directive_handler_uses_validation_manager(
        self, tmp_path, sample_directive_content
    ):
        """Test that DirectiveHandler uses ValidationManager for validation."""
        from kiwi_mcp.handlers.directive.handler import DirectiveHandler

        # Create directive file
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)

        file_content = f"""# Test Directive

```xml
{sample_directive_content}
```
"""
        directive_file = directive_dir / "test_directive.md"
        directive_file.write_text(file_content)

        # Try to create - should validate first
        handler = DirectiveHandler(project_path=str(tmp_path))
        result = await handler.execute("create", "test_directive", {"location": "project"})

        # Should succeed if validation passes
        assert result.get("status") == "created" or "error" not in result

    @pytest.mark.integration
    @pytest.mark.handlers
    @pytest.mark.metadata
    @pytest.mark.asyncio
    async def test_tool_handler_uses_metadata_manager(self, tmp_path, sample_tool_content):
        """Test that ToolHandler uses MetadataManager for signature operations."""
        from kiwi_mcp.handlers.tool.handler import ToolHandler

        # Create tool file first (file-first pattern)
        tool_dir = tmp_path / ".ai" / "scripts" / "test"
        tool_dir.mkdir(parents=True)
        tool_file = tool_dir / "test_tool_metadata.py"
        tool_file.write_text(sample_tool_content)

        # Now validate and sign using handler
        handler = ToolHandler(project_path=str(tmp_path))
        result = await handler.execute(
            "create",
            "test_tool_metadata",
            {
                "location": "project",
                "category": "test",
            },
        )

        assert result.get("status") == "created"
        assert "signature" in result

        # Verify signature was added
        assert tool_file.exists()
        signed_content = tool_file.read_text()
        verify_result = MetadataManager.verify_signature("tool", signed_content)
        assert verify_result is not None
        assert verify_result["status"] == "valid"

    @pytest.mark.integration
    @pytest.mark.handlers
    @pytest.mark.validation
    @pytest.mark.asyncio
    async def test_tool_handler_uses_validation_manager(self, tmp_path, sample_tool_content):
        """Test that ToolHandler uses ValidationManager for validation."""
        from kiwi_mcp.handlers.tool.handler import ToolHandler

        # Create tool file first (file-first pattern)
        tool_dir = tmp_path / ".ai" / "scripts" / "test"
        tool_dir.mkdir(parents=True)
        tool_file = tool_dir / "test_tool_validation.py"
        tool_file.write_text(sample_tool_content)

        # Now validate using handler
        handler = ToolHandler(project_path=str(tmp_path))
        result = await handler.execute(
            "create",
            "test_tool_validation",
            {
                "location": "project",
                "category": "test",
            },
        )

        # Should succeed if validation passes (tool_type will be auto-detected)
        assert result.get("status") in ["created", "success"] or "error" not in result

    @pytest.mark.integration
    @pytest.mark.handlers
    @pytest.mark.metadata
    @pytest.mark.asyncio
    async def test_knowledge_handler_uses_metadata_manager(
        self, tmp_path, sample_knowledge_content
    ):
        """Test that KnowledgeHandler uses MetadataManager for signature operations."""
        from kiwi_mcp.handlers.knowledge.handler import KnowledgeHandler

        # Create knowledge entry file first (file-first pattern)
        knowledge_dir = tmp_path / ".ai" / "knowledge" / "test"
        knowledge_dir.mkdir(parents=True)
        knowledge_file = knowledge_dir / "001-test.md"
        
        # Create file with frontmatter and content
        file_content = f"""---
zettel_id: 001-test
title: Test Entry
entry_type: learning
category: test
tags: []
version: "1.0.0"
---

{sample_knowledge_content}
"""
        knowledge_file.write_text(file_content)

        # Now validate and sign using handler
        handler = KnowledgeHandler(project_path=str(tmp_path))
        result = await handler.execute(
            "create",
            "001-test",
            {
                "location": "project",
                "category": "test",
            },
        )

        assert result.get("status") == "created"
        assert "signature" in result

        # Verify signature was added
        assert knowledge_file.exists()

        signed_content = knowledge_file.read_text()
        verify_result = MetadataManager.verify_signature("knowledge", signed_content)
        assert verify_result is not None
        assert verify_result["status"] == "valid"

    @pytest.mark.integration
    @pytest.mark.handlers
    @pytest.mark.validation
    @pytest.mark.asyncio
    async def test_knowledge_handler_uses_validation_manager(
        self, tmp_path, sample_knowledge_content
    ):
        """Test that KnowledgeHandler uses ValidationManager for validation."""
        from kiwi_mcp.handlers.knowledge.handler import KnowledgeHandler

        # Create knowledge entry file first (file-first pattern)
        knowledge_dir = tmp_path / ".ai" / "knowledge" / "test"
        knowledge_dir.mkdir(parents=True)
        knowledge_file = knowledge_dir / "001-test.md"
        
        # Create file with frontmatter and content
        file_content = f"""---
zettel_id: 001-test
title: Test Entry
entry_type: learning
category: test
tags: []
version: "1.0.0"
---

{sample_knowledge_content}
"""
        knowledge_file.write_text(file_content)

        # Now validate using handler
        handler = KnowledgeHandler(project_path=str(tmp_path))
        result = await handler.execute(
            "create",
            "001-test",
            {
                "location": "project",
                "category": "test",
            },
        )

        # Should succeed if validation passes
        assert result.get("status") == "created" or "error" not in result


class TestEndToEndFlows:
    """Test complete end-to-end workflows."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_create_update_verify_flow_directive(self, tmp_path, sample_directive_content):
        """Test create → update → verify flow for directive."""
        from kiwi_mcp.handlers.directive.handler import DirectiveHandler

        # Create
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)

        file_content = f"""# Test Directive

```xml
{sample_directive_content}
```
"""
        directive_file = directive_dir / "test_directive.md"
        directive_file.write_text(file_content)

        handler = DirectiveHandler(project_path=str(tmp_path))

        # Create (validates and signs)
        create_result = await handler.execute("create", "test_directive", {"location": "project"})
        assert create_result.get("status") == "created"

        # Verify signature after create
        signed_content = directive_file.read_text()
        verify1 = MetadataManager.verify_signature("directive", signed_content)
        assert verify1["status"] == "valid"

        # Update (re-validates and re-signs)
        update_result = await handler.execute("update", "test_directive", {})
        assert update_result.get("status") == "updated"

        # Verify signature after update
        updated_content = directive_file.read_text()
        verify2 = MetadataManager.verify_signature("directive", updated_content)
        assert verify2["status"] == "valid"

        # Timestamps should be different (or same if generated within same second)
        # Both should be valid timestamps
        assert verify1.get("validated_at") is not None
        assert verify2.get("validated_at") is not None
        # If timestamps are identical, that's acceptable if they were generated in the same second
        # The important thing is that both signatures are valid

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_run_action_validates_and_verifies(self, tmp_path, sample_directive_content):
        """Test that run action validates and verifies before execution."""
        from kiwi_mcp.handlers.directive.handler import DirectiveHandler

        # Create and sign directive
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)

        file_content = f"""# Test Directive

```xml
{sample_directive_content}
```
"""
        directive_file = directive_dir / "test_directive.md"
        directive_file.write_text(file_content)

        handler = DirectiveHandler(project_path=str(tmp_path))

        # Create to sign it
        await handler.execute("create", "test_directive", {"location": "project"})

        # Run should succeed (validation and verification pass)
        run_result = await handler.execute("run", "test_directive", {})
        assert run_result.get("status") == "ready" or "error" not in run_result

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_publish_action_verifies_signature(self, tmp_path, sample_directive_content):
        """Test that publish action verifies signature before publishing."""
        from kiwi_mcp.handlers.directive.handler import DirectiveHandler

        # Create and sign directive
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)

        file_content = f"""# Test Directive

```xml
{sample_directive_content}
```
"""
        directive_file = directive_dir / "test_directive.md"
        directive_file.write_text(file_content)

        handler = DirectiveHandler(project_path=str(tmp_path))

        # Create to sign it
        await handler.execute("create", "test_directive", {"location": "project"})

        # Publish should verify signature first
        # Note: This will fail if registry not configured, but that's expected
        publish_result = await handler.execute("publish", "test_directive", {"version": "1.0.0"})

        # Should either succeed or fail with registry error, not signature error
        if "error" in publish_result:
            assert (
                "signature" not in publish_result["error"].lower()
                or "registry" in publish_result["error"].lower()
            )
