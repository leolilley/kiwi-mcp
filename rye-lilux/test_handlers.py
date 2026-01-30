"""
Test RYE Content Handlers
"""

from pathlib import Path
import sys
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from rye.handlers.directive.handler import DirectiveHandler
from rye.handlers.tool.handler import ToolHandler
from rye.handlers.knowledge.handler import KnowledgeHandler


def test_directive_handler():
    """Test directive handler."""
    print("Testing Directive Handler...")

    # Create test content
    test_content = """# Test Directive

```xml
<directive name="test" version="1.0.0">
  <metadata>
    <description>Test directive for validation</description>
    <category>test</category>
  </metadata>
  <inputs>
    <input name="test_input" type="string" required="true">Test input</input>
  </inputs>
  <process>
    <step name="test_step">
      <description>Test step</description>
      <action>echo "test"</action>
    </step>
  </process>
</directive>
```
"""

    # Write test file
    test_file = Path("/tmp/test_directive.md")
    test_file.write_text(test_content)

    # Test parsing
    handler = DirectiveHandler("/tmp")
    parsed = handler.parse(test_file)

    print(f"Parsed name: {parsed.get('name')}")
    print(f"Parsed version: {parsed.get('version')}")
    print(f"Parsed description: {parsed.get('description')}")

    # Test validation
    validation = handler.validate(parsed, test_file)
    print(f"Validation valid: {validation['valid']}")
    if validation["issues"]:
        print(f"Issues: {validation['issues']}")

    # Test integrity
    integrity = handler.compute_integrity(parsed, test_content)
    print(f"Integrity hash: {integrity}")

    # Test signature
    signed = handler.add_signature(test_content, integrity)
    print(f"Signed content length: {len(signed)}")

    print("Directive handler test complete!\n")


def test_tool_handler():
    """Test tool handler."""
    print("Testing Tool Handler...")

    # Create test content
    test_content = '''"""Test tool for validation."""

__version__ = "1.0.0"
__description__ = "Test tool"
__tool_type__ = "subprocess"

def execute(params):
    """Execute test tool."""
    return {"result": "test"}
'''

    # Write test file
    test_file = Path("/tmp/test_tool.py")
    test_file.write_text(test_content)

    # Test parsing
    handler = ToolHandler("/tmp")
    parsed = handler.parse(test_file)

    print(f"Parsed name: {parsed.get('name')}")
    print(f"Parsed version: {parsed.get('version')}")
    print(f"Parsed description: {parsed.get('description')}")
    print(f"Parsed tool_type: {parsed.get('tool_type')}")

    # Test validation
    validation = handler.validate(parsed, test_file)
    print(f"Validation valid: {validation['valid']}")
    if validation["issues"]:
        print(f"Issues: {validation['issues']}")

    # Test integrity
    integrity = handler.compute_integrity(parsed, test_content)
    print(f"Integrity hash: {integrity}")

    # Test signature
    signed = handler.add_signature(test_content, integrity)
    print(f"Signed content length: {len(signed)}")

    print("Tool handler test complete!\n")


def test_knowledge_handler():
    """Test knowledge handler."""
    print("Testing Knowledge Handler...")

    # Create test content
    test_content = """---
id: test-knowledge
title: Test Knowledge Entry
entry_type: learning
category: test
version: 1.0.0
author: Test Author
tags: [test, validation]
---

# Test Knowledge Entry

This is a test knowledge entry for validating the RYE knowledge handler.

## Content

The knowledge handler should parse frontmatter and validate the structure.
"""

    # Write test file
    test_file = Path("/tmp/test_knowledge.md")
    test_file.write_text(test_content)

    # Test parsing
    handler = KnowledgeHandler("/tmp")
    parsed = handler.parse(test_file)

    print(f"Parsed ID: {parsed.get('id')}")
    print(f"Parsed title: {parsed.get('title')}")
    print(f"Parsed entry_type: {parsed.get('entry_type')}")
    print(f"Parsed version: {parsed.get('version')}")

    # Test validation
    validation = handler.validate(parsed, test_file)
    print(f"Validation valid: {validation['valid']}")
    if validation["issues"]:
        print(f"Issues: {validation['issues']}")
    if validation["warnings"]:
        print(f"Warnings: {validation['warnings']}")

    # Test integrity
    integrity = handler.compute_integrity(parsed, test_content)
    print(f"Integrity hash: {integrity}")

    # Test signature
    signed = handler.add_signature(test_content, integrity)
    print(f"Signed content length: {len(signed)}")

    print("Knowledge handler test complete!\n")


if __name__ == "__main__":
    print("=" * 50)
    print("RYE Content Handlers Test")
    print("=" * 50)

    test_directive_handler()
    test_tool_handler()
    test_knowledge_handler()

    print("=" * 50)
    print("All tests completed successfully!")
    print("=" * 50)

    # Cleanup
    for f in ["/tmp/test_directive.md", "/tmp/test_tool.py", "/tmp/test_knowledge.md"]:
        if os.path.exists(f):
            os.remove(f)
