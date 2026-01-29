"""
Test configuration and fixtures for rye-lilux.
"""

import sys
import pytest
import os
from unittest.mock import Mock, AsyncMock, MagicMock
from pathlib import Path

# Add rye tools to path for tests that import user-space tools (e.g. harness, expression_evaluator)
_repo_root = Path(__file__).resolve().parent.parent
_rye_tools = _repo_root / "rye" / ".ai" / "tools"
if _rye_tools.exists():
    core = _rye_tools / "core"
    if core.exists():
        sys.path.insert(0, str(core))
    threads = _rye_tools / "core" / "threads"
    if threads.exists():
        sys.path.insert(0, str(threads))

# Set up test environment
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")


def pytest_configure(config):
    """Register custom marks."""
    config.addinivalue_line("markers", "unit: unit tests")
    config.addinivalue_line("markers", "parser: parser tests")
    config.addinivalue_line("markers", "metadata: metadata manager tests")
    config.addinivalue_line("markers", "requires_extractors: requires .ai/extractors (rye or user-space)")


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    client = MagicMock()
    client.table = MagicMock(return_value=MagicMock())
    client.rpc = MagicMock(return_value=MagicMock())
    return client


@pytest.fixture
def parsing_project_path():
    """Project path that has .ai/extractors (for parser tests). Skip if none."""
    root = Path(__file__).resolve().parent.parent
    for p in [root / "rye", root]:
        if (p / ".ai" / "extractors" / "directive").exists():
            return p
    pytest.skip("No .ai/extractors/directive (need rye/.ai or user-space)")


@pytest.fixture
def mock_filesystem(tmp_path):
    """Create a mock filesystem for testing."""
    ai_dir = tmp_path / ".ai"
    (ai_dir / "directives" / "core").mkdir(parents=True)
    (ai_dir / "tools" / "core").mkdir(parents=True)
    (ai_dir / "knowledge" / "lilux").mkdir(parents=True)
    
    return {
        "project_root": tmp_path,
        "ai_dir": ai_dir,
        "directives_dir": ai_dir / "directives",
        "tools_dir": ai_dir / "tools",
        "knowledge_dir": ai_dir / "knowledge",
    }


@pytest.fixture
def sample_directive_content():
    """Sample directive XML content for testing."""
    return """<directive name="test_directive" version="1.0.0">
  <metadata>
    <description>Test directive for unit testing</description>
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


@pytest.fixture
def sample_directive_file(tmp_path, sample_directive_content):
    """Create a sample directive file for testing."""
    directive_dir = tmp_path / ".ai" / "directives" / "test"
    directive_dir.mkdir(parents=True)

    file_content = f"""# Test Directive

```xml
{sample_directive_content}
```
"""
    directive_file = directive_dir / "test_directive.md"
    directive_file.write_text(file_content)
    return directive_file


@pytest.fixture
def sample_tool_content():
    """Sample tool content for testing."""
    return '''"""Test tool for unit testing"""
__version__ = "1.0.0"

import sys
import json

def main():
    result = {"status": "success", "data": {"message": "test"}}
    print(json.dumps(result))

if __name__ == "__main__":
    main()
'''


@pytest.fixture
def sample_tool_file(tmp_path, sample_tool_content):
    """Create a sample tool file for testing."""
    tool_dir = tmp_path / ".ai" / "tools" / "test"
    tool_dir.mkdir(parents=True)

    tool_file = tool_dir / "test_tool.py"
    tool_file.write_text(sample_tool_content)
    return tool_file


@pytest.fixture
def sample_knowledge_content():
    """Sample knowledge entry content for testing."""
    return "This is test knowledge content for unit testing."


@pytest.fixture
def sample_knowledge_file(tmp_path, sample_knowledge_content):
    """Create a sample knowledge entry file for testing."""
    knowledge_dir = tmp_path / ".ai" / "knowledge" / "test"
    knowledge_dir.mkdir(parents=True)

    file_content = f"""---
version: "1.0.0"
id: 001-test
title: Test Knowledge Entry
entry_type: learning
category: test
tags: []
---

{sample_knowledge_content}
"""
    knowledge_file = knowledge_dir / "001-test.md"
    knowledge_file.write_text(file_content)
    return knowledge_file
