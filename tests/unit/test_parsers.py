"""
Tests for directive and knowledge parsers.

Tests the new Universal Extractor architecture with flat output structure.
"""

import pytest
from pathlib import Path
from kiwi_mcp.utils.parsers import parse_directive_file, parse_knowledge_file


class TestDirectiveParser:
    """Test directive file parsing with new flat structure."""

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_basic(self, tmp_path):
        """Should parse basic directive and return flat structure."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_basic" version="1.0.0">
  <metadata>
    <description>A basic test directive</description>
    <category>test</category>
    <author>tester</author>
    <permissions>
      <read resource="fs" path="*" />
    </permissions>
    <model tier="fast" fallback_id="gpt-4o-mini">Model context</model>
  </metadata>
  <inputs>
    <input name="foo" type="string" required="true">A foo param</input>
  </inputs>
  <process>
    <step name="do_thing">
      <action>Do the thing</action>
    </step>
  </process>
  <outputs>
    <success>Done</success>
  </outputs>
</directive>
```
"""
        directive_file = directive_dir / "test_basic.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file, tmp_path)
        
        # Check flat structure
        assert result["name"] == "test_basic"
        assert result["version"] == "1.0.0"
        assert result["description"] == "A basic test directive"
        assert result["category"] == "test"
        assert result["author"] == "tester"
        
        # Check model
        assert result["model"]["tier"] == "fast"
        assert result["model"]["fallback_id"] == "gpt-4o-mini"
        
        # Check permissions
        assert len(result["permissions"]) == 1
        assert result["permissions"][0]["tag"] == "read"
        
        # Check inputs
        assert len(result["inputs"]) == 1
        assert result["inputs"][0]["name"] == "foo"
        assert result["inputs"][0]["required"] is True

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_without_version_returns_none(self, tmp_path):
        """Should return None when version attribute is missing."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_no_version">
  <metadata>
    <description>Test directive</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
</directive>
```
"""
        directive_file = directive_dir / "test_no_version.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file, tmp_path)
        
        assert result["version"] is None

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_with_version_attribute(self, tmp_path):
        """Should parse version attribute correctly."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_version" version="2.3.4">
  <metadata>
    <description>Test directive</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
</directive>
```
"""
        directive_file = directive_dir / "test_version.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file, tmp_path)
        
        assert result["version"] == "2.3.4"

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_with_cdata(self, tmp_path):
        """Should parse directive with CDATA sections correctly."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_cdata" version="1.0.0">
  <metadata>
    <description>Test with CDATA</description>
    <permissions>
      <read resource="fs" path="*" />
    </permissions>
    <model tier="fast" />
  </metadata>
  <process>
    <step name="check">
      <action><![CDATA[if version >= 1.0.0 && x < 10 then proceed]]></action>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_cdata.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file, tmp_path)
        
        assert result["name"] == "test_cdata"
        assert result["version"] == "1.0.0"
        # Content should contain the process XML
        assert "process" in result.get("content", "")

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_invalid_xml_raises_error(self, tmp_path):
        """Should raise ValueError for invalid XML."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_invalid" version="1.0.0">
  <metadata>
    <description>Test with unescaped < character</description>
    <permissions>
      <read resource="fs" path="*" />
    </permissions>
  </metadata>
  <process>
    <step>
      <action>if x < 10 then fail</action>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_invalid.md"
        directive_file.write_text(directive_content)
        
        with pytest.raises(ValueError) as exc_info:
            parse_directive_file(directive_file, tmp_path)
        
        assert "Invalid directive XML" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_with_limits(self, tmp_path):
        """Should parse limits structure correctly."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_limits" version="1.0.0">
  <metadata>
    <description>Test with limits</description>
    <category>test</category>
    <author>tester</author>
    <permissions>
      <read resource="fs" path="*" />
    </permissions>
    <model tier="fast" />
    <limits>
      <turns>10</turns>
      <tokens>5000</tokens>
      <spawns>3</spawns>
      <duration>300</duration>
      <spend currency="USD">10.00</spend>
    </limits>
  </metadata>
</directive>
```
"""
        directive_file = directive_dir / "test_limits.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file, tmp_path)
        
        assert result["name"] == "test_limits"
        assert result["limits"] is not None
        assert result["limits"]["turns"] == 10
        assert result["limits"]["tokens"] == 5000
        assert result["limits"]["spawns"] == 3
        assert result["limits"]["duration"] == 300
        assert result["limits"]["spend"] == 10.0
        assert result["limits"]["spend_currency"] == "USD"

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_with_hooks(self, tmp_path):
        """Should parse hooks structure correctly."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_hooks" version="1.0.0">
  <metadata>
    <description>Test with hooks</description>
    <category>test</category>
    <author>tester</author>
    <permissions>
      <read resource="fs" path="*" />
    </permissions>
    <model tier="fast" />
    <hooks>
      <hook>
        <when>event.code == "permission_denied"</when>
        <directive>request_elevated_permissions</directive>
        <inputs>
          <original_directive>${directive.name}</original_directive>
          <missing_cap>${event.detail.missing}</missing_cap>
        </inputs>
      </hook>
      <hook>
        <when>cost.turns > limits.turns</when>
        <directive>handle_turns_exceeded</directive>
      </hook>
    </hooks>
  </metadata>
</directive>
```
"""
        directive_file = directive_dir / "test_hooks.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file, tmp_path)
        
        assert result["name"] == "test_hooks"
        assert result["hooks"] is not None
        assert len(result["hooks"]) == 2
        
        # First hook
        assert result["hooks"][0]["when"] == 'event.code == "permission_denied"'
        assert result["hooks"][0]["directive"] == "request_elevated_permissions"
        assert result["hooks"][0]["inputs"]["original_directive"] == "${directive.name}"
        assert result["hooks"][0]["inputs"]["missing_cap"] == "${event.detail.missing}"
        
        # Second hook (no inputs)
        assert result["hooks"][1]["when"] == "cost.turns > limits.turns"
        assert result["hooks"][1]["directive"] == "handle_turns_exceeded"
        assert "inputs" not in result["hooks"][1]


class TestKnowledgeParser:
    """Test knowledge file parsing with new flat structure."""

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_knowledge_basic(self, tmp_path):
        """Should parse basic knowledge entry."""
        knowledge_dir = tmp_path / ".ai" / "knowledge"
        knowledge_dir.mkdir(parents=True)
        
        knowledge_content = """---
id: test-entry
title: Test Knowledge Entry
entry_type: concept
version: "1.0.0"
category: test
tags:
  - testing
  - example
---

# Test Knowledge

This is a test knowledge entry.

It references [[other-entry]] and [[another-one]].
"""
        knowledge_file = knowledge_dir / "test-entry.md"
        knowledge_file.write_text(knowledge_content)
        
        result = parse_knowledge_file(knowledge_file, tmp_path)
        
        assert result["id"] == "test-entry"
        assert result["title"] == "Test Knowledge Entry"
        assert result["entry_type"] == "concept"
        assert result["version"] == "1.0.0"
        assert result["backlinks"] == ["other-entry", "another-one"]

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_knowledge_with_signature(self, tmp_path):
        """Should parse knowledge entry with signature comment."""
        knowledge_dir = tmp_path / ".ai" / "knowledge"
        knowledge_dir.mkdir(parents=True)
        
        knowledge_content = """<!-- kiwi-mcp:validated:2026-01-28T00:00:00Z:abc123 -->
---
id: signed-entry
title: Signed Entry
entry_type: learning
version: "1.0.0"
---

# Signed Knowledge

This entry has a signature.
"""
        knowledge_file = knowledge_dir / "signed-entry.md"
        knowledge_file.write_text(knowledge_content)
        
        result = parse_knowledge_file(knowledge_file, tmp_path)
        
        assert result["id"] == "signed-entry"
        assert result["title"] == "Signed Entry"

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_knowledge_body_extraction(self, tmp_path):
        """Should extract body content correctly."""
        knowledge_dir = tmp_path / ".ai" / "knowledge"
        knowledge_dir.mkdir(parents=True)
        
        knowledge_content = """---
id: body-test
title: Body Test
entry_type: concept
version: "1.0.0"
---

# Main Content

This is the body content.

## Section 2

More content here.
"""
        knowledge_file = knowledge_dir / "body-test.md"
        knowledge_file.write_text(knowledge_content)
        
        result = parse_knowledge_file(knowledge_file, tmp_path)
        
        assert result["body"] is not None
        assert "Main Content" in result["body"]
        assert "Section 2" in result["body"]
