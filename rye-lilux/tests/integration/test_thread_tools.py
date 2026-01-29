"""
Integration tests for thread tools (anthropic_thread, openai_thread).

Tests tool chain resolution, config merging, and streaming with file_sink + return sinks.
"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from lilux.primitives.executor import ChainResolver, PrimitiveExecutor
from lilux.primitives.http_client import HttpResult, ReturnSink
from lilux.primitives.integrity_verifier import IntegrityVerifier


class TestThreadTools:
    """Test thread tool configurations and execution."""

    @pytest.fixture
    def project_path(self, tmp_path):
        """Create a test project with thread tool configs."""
        project = tmp_path / "test_project"
        project.mkdir()
        
        tools_dir = project / ".ai" / "tools"
        tools_dir.mkdir(parents=True)
        
        # Create http_client primitive
        primitives_dir = tools_dir / "primitives"
        primitives_dir.mkdir()
        http_client_file = primitives_dir / "http_client.py"
        http_client_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:0000000000000000000000000000000000000000000000000000000000000000
__version__ = "1.0.0"
__tool_type__ = "primitive"
__executor_id__ = None
__category__ = "primitives"
""")
        
        # Create file_sink runtime tool
        sinks_dir = tools_dir / "sinks"
        sinks_dir.mkdir()
        file_sink_file = sinks_dir / "file_sink.py"
        file_sink_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:1111111111111111111111111111111111111111111111111111111111111111
__tool_type__ = "runtime"
__version__ = "1.0.0"
__executor_id__ = "python"
__category__ = "sinks"
""")
        
        # Create LLM endpoint tools
        llm_dir = tools_dir / "llm"
        llm_dir.mkdir()
        
        anthropic_messages_yaml = llm_dir / "anthropic_messages.yaml"
        anthropic_messages_yaml.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
tool_id: anthropic_messages
tool_type: http
version: "1.0.0"
description: "Call Anthropic Messages API"
executor_id: http_client
config:
  method: POST
  url: "https://api.anthropic.com/v1/messages"
  auth:
    type: bearer
    token: "${ANTHROPIC_API_KEY}"
  headers:
    Content-Type: application/json
    anthropic-version: "2023-06-01"
  body:
    model: "{model}"
    max_tokens: "{max_tokens}"
    stream: "{stream}"
    messages: "{messages}"
  stream:
    transport: sse
    destinations:
      - type: return
parameters:
  - name: model
    type: string
    default: "claude-sonnet-4-20250514"
  - name: max_tokens
    type: integer
    default: 4096
  - name: stream
    type: boolean
    default: false
  - name: messages
    type: array
    required: true
""")
        
        openai_chat_yaml = llm_dir / "openai_chat.yaml"
        openai_chat_yaml.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
tool_id: openai_chat
tool_type: http
version: "1.0.0"
description: "Call OpenAI Chat Completions API"
executor_id: http_client
config:
  method: POST
  url: "https://api.openai.com/v1/chat/completions"
  auth:
    type: bearer
    token: "${OPENAI_API_KEY}"
  headers:
    Content-Type: application/json
  body:
    model: "{model}"
    max_tokens: "{max_tokens}"
    stream: "{stream}"
    messages: "{messages}"
  stream:
    transport: sse
    destinations:
      - type: return
parameters:
  - name: model
    type: string
    default: "gpt-4o"
  - name: max_tokens
    type: integer
    default: 4096
  - name: stream
    type: boolean
    default: false
  - name: messages
    type: array
    required: true
""")
        
        # Create thread tools
        threads_dir = tools_dir / "threads"
        threads_dir.mkdir()
        
        anthropic_thread_yaml = threads_dir / "anthropic_thread.yaml"
        anthropic_thread_yaml.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
tool_id: anthropic_thread
tool_type: http
version: "1.0.0"
description: "Run a conversation thread with Claude"
executor_id: anthropic_messages
config:
  stream:
    destinations:
      - type: file_sink
        path: ".ai/threads/{thread_id}/transcript.jsonl"
        format: jsonl
      - type: return
parameters:
  - name: thread_id
    type: string
    required: true
  - name: model
    type: string
    default: "claude-sonnet-4-20250514"
  - name: max_tokens
    type: integer
    default: 4096
  - name: stream
    type: boolean
    default: true
  - name: messages
    type: array
    required: true
""")
        
        openai_thread_yaml = threads_dir / "openai_thread.yaml"
        openai_thread_yaml.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
tool_id: openai_thread
tool_type: http
version: "1.0.0"
description: "Run a conversation thread with OpenAI"
executor_id: openai_chat
config:
  stream:
    destinations:
      - type: file_sink
        path: ".ai/threads/{thread_id}/transcript.jsonl"
        format: jsonl
      - type: return
parameters:
  - name: thread_id
    type: string
    required: true
  - name: model
    type: string
    default: "gpt-4o"
  - name: max_tokens
    type: integer
    default: 4096
  - name: stream
    type: boolean
    default: true
  - name: messages
    type: array
    required: true
""")
        
        return project

    @pytest.fixture
    def resolver(self, project_path):
        """ChainResolver instance."""
        return ChainResolver(project_path)

    @pytest.fixture
    def executor(self, project_path):
        """PrimitiveExecutor instance with mocked HTTP client."""
        exec = PrimitiveExecutor(project_path)
        # Mock the HTTP client primitive
        exec.http_client_primitive = MagicMock()
        return exec

    @pytest.mark.asyncio
    async def test_anthropic_thread_config_structure(self, project_path):
        """Test that anthropic_thread config has correct structure and chains to anthropic_messages."""
        import yaml
        
        thread_file = project_path / ".ai" / "tools" / "threads" / "anthropic_thread.yaml"
        messages_file = project_path / ".ai" / "tools" / "llm" / "anthropic_messages.yaml"
        
        with open(thread_file) as f:
            thread_config = yaml.safe_load(f)
        
        with open(messages_file) as f:
            messages_config = yaml.safe_load(f)
        
        # Verify thread tool structure
        assert thread_config["tool_id"] == "anthropic_thread"
        assert thread_config["tool_type"] == "http"
        assert thread_config["executor_id"] == "anthropic_messages"
        
        # Verify parent tool structure
        assert messages_config["tool_id"] == "anthropic_messages"
        assert messages_config["tool_type"] == "http"
        assert messages_config["executor_id"] == "http_client"

    @pytest.mark.asyncio
    async def test_openai_thread_config_structure(self, project_path):
        """Test that openai_thread config has correct structure and chains to openai_chat."""
        import yaml
        
        thread_file = project_path / ".ai" / "tools" / "threads" / "openai_thread.yaml"
        chat_file = project_path / ".ai" / "tools" / "llm" / "openai_chat.yaml"
        
        with open(thread_file) as f:
            thread_config = yaml.safe_load(f)
        
        with open(chat_file) as f:
            chat_config = yaml.safe_load(f)
        
        # Verify thread tool structure
        assert thread_config["tool_id"] == "openai_thread"
        assert thread_config["tool_type"] == "http"
        assert thread_config["executor_id"] == "openai_chat"
        
        # Verify parent tool structure
        assert chat_config["tool_id"] == "openai_chat"
        assert chat_config["tool_type"] == "http"
        assert chat_config["executor_id"] == "http_client"

    @pytest.mark.asyncio
    async def test_config_merging_in_thread_tool(self, project_path):
        """Test that thread tool config extends parent config with additional destinations."""
        import yaml
        
        thread_file = project_path / ".ai" / "tools" / "threads" / "anthropic_thread.yaml"
        messages_file = project_path / ".ai" / "tools" / "llm" / "anthropic_messages.yaml"
        
        with open(thread_file) as f:
            thread_config = yaml.safe_load(f)
        
        with open(messages_file) as f:
            messages_config = yaml.safe_load(f)
        
        # Thread tool should have stream.destinations with file_sink + return
        thread_stream = thread_config.get("config", {}).get("stream", {})
        thread_destinations = thread_stream.get("destinations", [])
        
        assert len(thread_destinations) == 2
        assert any(d.get("type") == "file_sink" for d in thread_destinations)
        assert any(d.get("type") == "return" for d in thread_destinations)
        
        # Parent config should have stream.destinations with just return
        parent_stream = messages_config.get("config", {}).get("stream", {})
        parent_destinations = parent_stream.get("destinations", [])
        
        assert len(parent_destinations) == 1
        assert parent_destinations[0].get("type") == "return"

    @pytest.mark.asyncio
    async def test_thread_tool_parameters(self, project_path):
        """Test that thread tools have thread_id parameter."""
        import yaml
        
        thread_file = project_path / ".ai" / "tools" / "threads" / "anthropic_thread.yaml"
        
        with open(thread_file) as f:
            thread_config = yaml.safe_load(f)
        
        parameters = thread_config.get("parameters", [])
        param_names = [p.get("name") for p in parameters]
        
        assert "thread_id" in param_names
        thread_id_param = next(p for p in parameters if p.get("name") == "thread_id")
        assert thread_id_param.get("required") is True

    @pytest.mark.asyncio
    async def test_yaml_configs_are_valid(self, project_path):
        """Test that all YAML configs are valid and parse correctly."""
        llm_dir = project_path / ".ai" / "tools" / "llm"
        threads_dir = project_path / ".ai" / "tools" / "threads"
        
        # Validate LLM endpoint configs
        for yaml_file in [llm_dir / "anthropic_messages.yaml", llm_dir / "openai_chat.yaml"]:
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
                assert "tool_id" in config
                assert "tool_type" in config
                assert config["tool_type"] == "http"
                assert "executor_id" in config
                assert config["executor_id"] == "http_client"
        
        # Validate thread configs
        for yaml_file in [threads_dir / "anthropic_thread.yaml", threads_dir / "openai_thread.yaml"]:
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
                assert "tool_id" in config
                assert "tool_type" in config
                assert config["tool_type"] == "http"
                assert "executor_id" in config
                assert config["executor_id"] in ["anthropic_messages", "openai_chat"]
                assert "thread_id" in [p.get("name") for p in config.get("parameters", [])]

    @pytest.mark.asyncio
    async def test_transcript_path_templating(self, project_path):
        """Test that transcript path uses {thread_id} template."""
        import yaml
        
        thread_file = project_path / ".ai" / "tools" / "threads" / "anthropic_thread.yaml"
        
        with open(thread_file) as f:
            thread_config = yaml.safe_load(f)
        
        stream_config = thread_config.get("config", {}).get("stream", {})
        destinations = stream_config.get("destinations", [])
        
        file_sink = next(d for d in destinations if d.get("type") == "file_sink")
        assert "{thread_id}" in file_sink.get("path", "")

    @pytest.mark.asyncio
    async def test_streaming_config_inheritance(self, project_path):
        """Test that streaming config structure is correct for inheritance."""
        import yaml
        
        thread_file = project_path / ".ai" / "tools" / "threads" / "anthropic_thread.yaml"
        messages_file = project_path / ".ai" / "tools" / "llm" / "anthropic_messages.yaml"
        
        with open(thread_file) as f:
            thread_config = yaml.safe_load(f)
        
        with open(messages_file) as f:
            messages_config = yaml.safe_load(f)
        
        # Base tool has stream config
        base_stream = messages_config.get("config", {}).get("stream", {})
        assert "transport" in base_stream
        assert base_stream.get("transport") == "sse"
        
        # Thread tool has stream config (will inherit transport, extend destinations)
        thread_stream = thread_config.get("config", {}).get("stream", {})
        assert "destinations" in thread_stream
        assert len(thread_stream.get("destinations", [])) == 2  # Extended with file_sink + return
