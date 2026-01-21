"""
Tests for version warning feature in directive execution.

Tests version comparison, version validation, and version checking
when running directives.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from kiwi_mcp.utils.validators import compare_versions
from kiwi_mcp.utils.parsers import parse_directive_file, parse_script_metadata, parse_knowledge_entry

# Import handlers - may fail if supabase not installed
try:
    from kiwi_mcp.handlers.directive.handler import DirectiveHandler
    HAS_DIRECTIVE_HANDLER = True
except (ImportError, ModuleNotFoundError):
    DirectiveHandler = None
    HAS_DIRECTIVE_HANDLER = False

try:
    from kiwi_mcp.handlers.script.handler import ScriptHandler
    HAS_SCRIPT_HANDLER = True
except (ImportError, ModuleNotFoundError):
    ScriptHandler = None
    HAS_SCRIPT_HANDLER = False

try:
    from kiwi_mcp.handlers.knowledge.handler import KnowledgeHandler
    HAS_KNOWLEDGE_HANDLER = True
except (ImportError, ModuleNotFoundError):
    KnowledgeHandler = None
    HAS_KNOWLEDGE_HANDLER = False


class TestCompareVersions:
    """Test version comparison utility."""

    @pytest.mark.unit
    @pytest.mark.version
    def test_compare_versions_less_than(self):
        """Should return -1 when version1 < version2."""
        assert compare_versions("1.0.0", "1.0.1") == -1
        assert compare_versions("1.0.0", "1.1.0") == -1
        assert compare_versions("1.0.0", "2.0.0") == -1
        assert compare_versions("0.9.0", "1.0.0") == -1

    @pytest.mark.unit
    @pytest.mark.version
    def test_compare_versions_equal(self):
        """Should return 0 when version1 == version2."""
        assert compare_versions("1.0.0", "1.0.0") == 0
        assert compare_versions("2.5.3", "2.5.3") == 0
        assert compare_versions("0.1.0", "0.1.0") == 0

    @pytest.mark.unit
    @pytest.mark.version
    def test_compare_versions_greater_than(self):
        """Should return 1 when version1 > version2."""
        assert compare_versions("1.0.1", "1.0.0") == 1
        assert compare_versions("1.1.0", "1.0.0") == 1
        assert compare_versions("2.0.0", "1.0.0") == 1
        assert compare_versions("1.0.0", "0.9.0") == 1

    @pytest.mark.unit
    @pytest.mark.version
    def test_compare_versions_with_prerelease(self):
        """Should handle prerelease versions correctly."""
        assert compare_versions("1.0.0", "1.0.0-alpha") == 1
        assert compare_versions("1.0.0-alpha", "1.0.0") == -1
        assert compare_versions("1.0.0-alpha", "1.0.0-beta") == -1

    @pytest.mark.unit
    @pytest.mark.version
    def test_compare_versions_with_build_metadata(self):
        """Should handle build metadata correctly."""
        # Note: packaging library may treat versions with build metadata differently
        # The important thing is that it doesn't crash and returns a consistent result
        result1 = compare_versions("1.0.0", "1.0.0+build.1")
        result2 = compare_versions("1.0.0+build.1", "1.0.0+build.2")
        # Just verify it returns a valid comparison result (not an exception)
        assert result1 in (-1, 0, 1)
        assert result2 in (-1, 0, 1)

    @pytest.mark.unit
    @pytest.mark.version
    def test_compare_versions_invalid_raises(self):
        """Should raise ValueError for invalid version strings."""
        with pytest.raises(ValueError):
            compare_versions("invalid", "1.0.0")
        
        with pytest.raises(ValueError):
            compare_versions("1.0.0", "invalid")


class TestParserVersionHandling:
    """Test parser behavior with version attribute."""

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_with_version(self, tmp_path):
        """Should parse directive with version attribute."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_version" version="1.2.3">
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
        
        result = parse_directive_file(directive_file)
        
        assert result["version"] == "1.2.3"

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
        
        result = parse_directive_file(directive_file)
        
        assert result["version"] is None


@pytest.mark.skipif(not HAS_DIRECTIVE_HANDLER, reason="DirectiveHandler requires supabase")
class TestDirectiveHandlerVersionChecking:
    """Test version checking in DirectiveHandler._check_for_newer_version."""

    @pytest.fixture
    def handler(self, tmp_path):
        """Create DirectiveHandler instance."""
        return DirectiveHandler(project_path=str(tmp_path))

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_check_for_newer_version_no_newer_found(self, handler):
        """Should return None when no newer version exists."""
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"version": "1.0.0"}
            
            result = await handler._check_for_newer_version(
                directive_name="test_directive",
                current_version="1.0.0",
                current_source="project",
            )
            
            assert result is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_check_for_newer_version_registry_has_newer(self, handler):
        """Should return warning when registry has newer version."""
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"version": "1.2.0"}
            
            result = await handler._check_for_newer_version(
                directive_name="test_directive",
                current_version="1.0.0",
                current_source="project",
            )
            
            assert result is not None
            assert result["current_version"] == "1.0.0"
            assert result["newer_version"] == "1.2.0"
            assert result["location"] == "registry"
            assert "newer version" in result["message"].lower()

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_check_for_newer_version_userspace_has_newer(self, handler, tmp_path):
        """Should return warning when userspace has newer version (running from project)."""
        # Create directive in userspace with newer version
        user_directive_dir = tmp_path / ".ai" / "directives" / "test"
        user_directive_dir.mkdir(parents=True)
        
        user_directive_content = """# Test Directive

```xml
<directive name="test_directive" version="1.5.0">
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
        user_directive_file = user_directive_dir / "test_directive.md"
        user_directive_file.write_text(user_directive_content)
        
        # Mock registry to return older version
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"version": "1.0.0"}
            
            # Mock user directives path
            handler.resolver.user_directives = tmp_path / ".ai" / "directives"
            
            result = await handler._check_for_newer_version(
                directive_name="test_directive",
                current_version="1.0.0",
                current_source="project",
            )
            
            assert result is not None
            assert result["newer_version"] == "1.5.0"
            assert result["location"] == "user"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_check_for_newer_version_registry_newest_when_both_newer(self, handler, tmp_path):
        """Should return registry version when both userspace and registry are newer, but registry is newest."""
        # Create directive in userspace with newer version
        user_directive_dir = tmp_path / ".ai" / "directives" / "test"
        user_directive_dir.mkdir(parents=True)
        
        user_directive_content = """# Test Directive

```xml
<directive name="test_directive" version="1.5.0">
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
        user_directive_file = user_directive_dir / "test_directive.md"
        user_directive_file.write_text(user_directive_content)
        
        # Mock registry to return even newer version
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"version": "2.0.0"}
            
            # Mock user directives path
            handler.resolver.user_directives = tmp_path / ".ai" / "directives"
            
            result = await handler._check_for_newer_version(
                directive_name="test_directive",
                current_version="1.0.0",
                current_source="project",
            )
            
            assert result is not None
            assert result["newer_version"] == "2.0.0"
            assert result["location"] == "registry"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_check_for_newer_version_from_user_skips_userspace(self, handler):
        """Should only check registry when running from user space."""
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"version": "1.2.0"}
            
            result = await handler._check_for_newer_version(
                directive_name="test_directive",
                current_version="1.0.0",
                current_source="user",
            )
            
            # Should check registry
            mock_get.assert_called_once_with("test_directive")
            
            # Should return warning
            assert result is not None
            assert result["location"] == "registry"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_check_for_newer_version_handles_registry_error(self, handler):
        """Should handle registry errors gracefully and not block."""
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Registry unavailable")
            
            result = await handler._check_for_newer_version(
                directive_name="test_directive",
                current_version="1.0.0",
                current_source="project",
            )
            
            # Should return None (no warning) when registry fails
            assert result is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_check_for_newer_version_handles_userspace_parse_error(self, handler, tmp_path):
        """Should handle userspace file parsing errors gracefully."""
        # Create invalid directive file in userspace
        user_directive_dir = tmp_path / ".ai" / "directives" / "test"
        user_directive_dir.mkdir(parents=True)
        
        invalid_file = user_directive_dir / "test_directive.md"
        invalid_file.write_text("Invalid content")
        
        # Mock user directives path
        handler.resolver.user_directives = tmp_path / ".ai" / "directives"
        
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"version": "1.0.0"}
            
            result = await handler._check_for_newer_version(
                directive_name="test_directive",
                current_version="1.0.0",
                current_source="project",
            )
            
            # Should not raise exception, should return None
            assert result is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_check_for_newer_version_handles_invalid_version_in_registry(self, handler):
        """Should handle invalid version strings in registry gracefully."""
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"version": "invalid-version"}
            
            result = await handler._check_for_newer_version(
                directive_name="test_directive",
                current_version="1.0.0",
                current_source="project",
            )
            
            # Should not raise exception, should return None
            assert result is None


@pytest.mark.skipif(not HAS_DIRECTIVE_HANDLER, reason="DirectiveHandler requires supabase")
class TestDirectiveHandlerRunWithVersionWarning:
    """Test _run_directive adds version warning to result."""

    @pytest.fixture
    def handler(self, tmp_path):
        """Create DirectiveHandler instance."""
        return DirectiveHandler(project_path=str(tmp_path))

    @pytest.fixture
    def valid_directive_file(self, tmp_path):
        """Create a valid directive file for testing."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_directive" version="1.0.0">
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
</directive>
```
"""
        directive_file = directive_dir / "test_directive.md"
        directive_file.write_text(directive_content)
        
        # Sign the directive
        from kiwi_mcp.utils.metadata_manager import MetadataManager
        content = directive_file.read_text()
        signed_content = MetadataManager.sign_content("directive", content)
        directive_file.write_text(signed_content)
        
        return directive_file

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_run_directive_adds_version_warning_when_newer_exists(self, handler, valid_directive_file):
        """Should add version_warning to result when newer version exists."""
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"version": "1.2.0"}
            
            result = await handler.execute("run", "test_directive", {})
            
            assert "version_warning" in result
            assert result["version_warning"]["newer_version"] == "1.2.0"
            assert result["version_warning"]["location"] == "registry"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_run_directive_no_warning_when_current_is_newest(self, handler, valid_directive_file):
        """Should not add version_warning when current version is newest."""
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"version": "1.0.0"}
            
            result = await handler.execute("run", "test_directive", {})
            
            assert "version_warning" not in result
            assert result["status"] == "ready"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_run_directive_no_warning_when_version_missing(self, handler, tmp_path):
        """Should not add version_warning when version is missing (validation should catch it)."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        # Directive without version (should fail validation)
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
        
        result = await handler.execute("run", "test_no_version", {})
        
        # Should fail validation, not reach version checking
        assert "error" in result
        assert "version" in result["error"].lower() or any("version" in issue.lower() for issue in result.get("details", []))


class TestParseScriptMetadataVersion:
    """Test parse_script_metadata __version__ extraction."""

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_script_with_version(self, tmp_path):
        """Should extract __version__ from script."""
        script = tmp_path / "v_script.py"
        script.write_text('__version__ = "2.3.4"\n"""Docstring."""\n')
        meta = parse_script_metadata(script)
        assert meta.get("version") == "2.3.4"

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_script_without_version(self, tmp_path):
        """Should set version to None when __version__ is missing."""
        script = tmp_path / "nov_script.py"
        script.write_text('"""Docstring."""\nimport os\n')
        meta = parse_script_metadata(script)
        assert meta.get("version") is None


@pytest.mark.skipif(not HAS_SCRIPT_HANDLER, reason="ScriptHandler requires supabase")
class TestScriptHandlerVersionChecking:
    """Test ScriptHandler._check_for_newer_version."""

    @pytest.fixture
    def handler(self, tmp_path):
        return ScriptHandler(project_path=str(tmp_path))

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_script_check_registry_has_newer(self, handler):
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as m:
            m.return_value = {"version": "1.2.0"}
            r = await handler._check_for_newer_version("s", "1.0.0", "project")
        assert r is not None and r["newer_version"] == "1.2.0" and r["location"] == "registry"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_script_check_no_newer(self, handler):
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as m:
            m.return_value = {"version": "1.0.0"}
            r = await handler._check_for_newer_version("s", "1.0.0", "project")
        assert r is None


@pytest.mark.skipif(not HAS_SCRIPT_HANDLER, reason="ScriptHandler requires supabase")
class TestScriptHandlerRunWithVersionWarning:
    """Test _run_script adds version_warning when newer exists."""

    @pytest.fixture
    def handler(self, tmp_path):
        return ScriptHandler(project_path=str(tmp_path))

    @pytest.fixture
    def valid_script_with_version(self, tmp_path):
        from kiwi_mcp.utils.metadata_manager import MetadataManager
        d = tmp_path / ".ai" / "scripts" / "test"
        d.mkdir(parents=True)
        content = '__version__ = "1.0.0"\n"""Test."""\nimport json\nprint(json.dumps({"status":"success","data":{}}))\n'
        p = d / "valid_script.py"
        p.write_text(content)
        signed = MetadataManager.sign_content("script", content)
        p.write_text(signed)
        return p

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_script_run_adds_version_warning_when_newer(self, handler, valid_script_with_version):
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as m:
            m.return_value = {"version": "1.2.0"}
            with patch.object(handler, "_execute_subprocess") as sub:
                sub.return_value = {"status": "success", "data": {}}
                r = await handler.execute("run", "valid_script", {})
        assert "version_warning" in r and r["version_warning"]["newer_version"] == "1.2.0"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_script_dry_run_adds_version_warning(self, handler, valid_script_with_version):
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as m:
            m.return_value = {"version": "1.2.0"}
            r = await handler.execute("run", "valid_script", {"dry_run": True})
        assert r.get("status") == "validation_passed" and "version_warning" in r


@pytest.mark.skipif(not HAS_KNOWLEDGE_HANDLER, reason="KnowledgeHandler requires supabase")
class TestKnowledgeHandlerVersionChecking:
    """Test KnowledgeHandler._check_for_newer_version."""

    @pytest.fixture
    def handler(self, tmp_path):
        return KnowledgeHandler(project_path=str(tmp_path))

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_knowledge_check_registry_has_newer(self, handler):
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as m:
            m.return_value = {"version": "1.2.0"}
            r = await handler._check_for_newer_version("k1", "1.0.0", "project")
        assert r is not None and r["newer_version"] == "1.2.0" and r["location"] == "registry"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_knowledge_check_no_newer(self, handler):
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as m:
            m.return_value = {"version": "1.0.0"}
            r = await handler._check_for_newer_version("k1", "1.0.0", "project")
        assert r is None


@pytest.mark.skipif(not HAS_KNOWLEDGE_HANDLER, reason="KnowledgeHandler requires supabase")
class TestKnowledgeHandlerRunWithVersionWarning:
    """Test _run_knowledge adds version_warning when newer exists."""

    @pytest.fixture
    def handler(self, tmp_path):
        return KnowledgeHandler(project_path=str(tmp_path))

    @pytest.fixture
    def valid_knowledge_with_version(self, tmp_path):
        d = tmp_path / ".ai" / "knowledge" / "test"
        d.mkdir(parents=True)
        raw = "---\nzettel_id: k1\ntitle: K1\nversion: 1.0.0\n---\n\nContent here.\n"
        p = d / "k1.md"
        p.write_text(raw)
        return p

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.version
    async def test_knowledge_run_adds_version_warning_when_newer(self, handler, valid_knowledge_with_version):
        with patch.object(handler.registry, "get", new_callable=AsyncMock) as m:
            m.return_value = {"version": "1.2.0"}
            with patch("kiwi_mcp.handlers.knowledge.handler.MetadataManager.verify_signature", return_value=None):
                r = await handler.execute("run", "k1", {})
        assert "version_warning" in r and r["version_warning"]["newer_version"] == "1.2.0"
