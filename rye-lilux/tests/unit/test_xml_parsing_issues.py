"""
Tests for XML parsing issues in directives.

These tests demonstrate the problems that occur when directives contain
unescaped special characters (<, >, &) in text content.
"""

import pytest
from lilux.utils.parsers import parse_directive_file


class TestXMLParsingIssues:
    """Test cases that demonstrate XML parsing failures with unescaped characters."""

    @pytest.mark.unit
    @pytest.mark.parser
    def test_unescaped_less_than_in_action_text(self, tmp_path):
        """Parser auto-escapes < in flexible sections (process/action)."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_lt_action" version="1.0.0">
  <metadata>
    <description>Test directive with unescaped &lt; in action</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="check_latency">
      <action>Response time must be <100ms</action>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_lt_action.md"
        directive_file.write_text(directive_content)
        
        # Parser now auto-escapes < followed by digits in flexible sections
        result = parse_directive_file(directive_file)
        assert result["name"] == "test_lt_action"

    @pytest.mark.unit
    @pytest.mark.parser
    def test_unescaped_less_than_in_description(self, tmp_path):
        """Should fail when < character appears unescaped in description."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_lt_desc" version="1.0.0">
  <metadata>
    <description>Requires Python version < 3.12</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
</directive>
```
"""
        directive_file = directive_dir / "test_lt_desc.md"
        directive_file.write_text(directive_content)
        
        with pytest.raises(ValueError) as exc_info:
            parse_directive_file(directive_file)
        
        error_msg = str(exc_info.value)
        assert "Invalid directive XML" in error_msg or "ParseError" in error_msg

    @pytest.mark.unit
    @pytest.mark.parser
    def test_unescaped_greater_than_in_verification(self, tmp_path):
        """Note: > in text is actually valid XML, but we test with < to ensure error."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_gt_verify" version="1.0.0">
  <metadata>
    <description>Test directive with unescaped < in verification</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="verify">
      <action>Check performance</action>
      <verification>
        <check>Cache hit ratio <80%</check>
      </verification>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_gt_verify.md"
        directive_file.write_text(directive_content)
        
        with pytest.raises(ValueError) as exc_info:
            parse_directive_file(directive_file)
        
        error_msg = str(exc_info.value)
        assert "Invalid directive XML" in error_msg or "ParseError" in error_msg

    @pytest.mark.unit
    @pytest.mark.parser
    def test_unescaped_greater_than_in_action(self, tmp_path):
        """Note: >= is valid XML, but we test with < to ensure error."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_gt_action" version="1.0.0">
  <metadata>
    <description>Test directive with unescaped < in action</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="check_version">
      <action>Ensure version < 1.0.0</action>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_gt_action.md"
        directive_file.write_text(directive_content)
        
        with pytest.raises(ValueError) as exc_info:
            parse_directive_file(directive_file)
        
        error_msg = str(exc_info.value)
        assert "Invalid directive XML" in error_msg or "ParseError" in error_msg

    @pytest.mark.unit
    @pytest.mark.parser
    def test_unescaped_arrow_in_text(self, tmp_path):
        """Note: -> is valid XML, but we test with < to ensure error."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_arrow" version="1.0.0">
  <metadata>
    <description>Test directive with unescaped < in arrow-like pattern</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="transform">
      <action>Convert script_meta <- tool_meta</action>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_arrow.md"
        directive_file.write_text(directive_content)
        
        with pytest.raises(ValueError) as exc_info:
            parse_directive_file(directive_file)
        
        error_msg = str(exc_info.value)
        assert "Invalid directive XML" in error_msg or "ParseError" in error_msg

    @pytest.mark.unit
    @pytest.mark.parser
    def test_unescaped_arrow_in_method_signature(self, tmp_path):
        """Parser auto-escapes < followed by space in flexible sections."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_method_sig" version="1.0.0">
  <metadata>
    <description>Test directive with method signature</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="validate">
      <action>Update validate(data: Dict) < Result method</action>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_method_sig.md"
        directive_file.write_text(directive_content)
        
        # Parser now auto-escapes < followed by space in flexible sections
        result = parse_directive_file(directive_file)
        assert result["name"] == "test_method_sig"

    @pytest.mark.unit
    @pytest.mark.parser
    def test_unescaped_ampersand_in_text(self, tmp_path):
        """Should fail when & character appears unescaped in text."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_ampersand" version="1.0.0">
  <metadata>
    <description>Test directive with unescaped & character</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="check">
      <action>Verify foo & bar condition</action>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_ampersand.md"
        directive_file.write_text(directive_content)
        
        with pytest.raises(ValueError) as exc_info:
            parse_directive_file(directive_file)
        
        error_msg = str(exc_info.value)
        assert "Invalid directive XML" in error_msg or "ParseError" in error_msg

    @pytest.mark.unit
    @pytest.mark.parser
    def test_unescaped_ampersand_in_url(self, tmp_path):
        """Should fail when & appears in URL query string."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_url_amp" version="1.0.0">
  <metadata>
    <description>Test directive with URL containing &</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="call_api">
      <action>Call https://api.com?key=value&foo=bar</action>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_url_amp.md"
        directive_file.write_text(directive_content)
        
        with pytest.raises(ValueError) as exc_info:
            parse_directive_file(directive_file)
        
        error_msg = str(exc_info.value)
        assert "Invalid directive XML" in error_msg or "ParseError" in error_msg

    @pytest.mark.unit
    @pytest.mark.parser
    def test_mixed_unescaped_characters(self, tmp_path):
        """Should fail when multiple unescaped < characters appear in different locations."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_mixed" version="1.0.0">
  <metadata>
    <description>Performance <80% and latency <100ms</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="transform">
      <action>Convert old format with Dict[str, Any]</action>
    </step>
    <step name="verify">
      <verification>
        <check>Success rate <95% & errors <5%</check>
      </verification>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_mixed.md"
        directive_file.write_text(directive_content)
        
        with pytest.raises(ValueError) as exc_info:
            parse_directive_file(directive_file)
        
        error_msg = str(exc_info.value)
        assert "Invalid directive XML" in error_msg or "ParseError" in error_msg

    @pytest.mark.unit
    @pytest.mark.parser
    def test_generic_type_syntax(self, tmp_path):
        """Should fail when < appears in generic type syntax like List<T>."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_generic" version="1.0.0">
  <metadata>
    <description>Test directive with generic type syntax</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="validate">
      <action>Use validate(data: List<String>) method</action>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_generic.md"
        directive_file.write_text(directive_content)
        
        with pytest.raises(ValueError) as exc_info:
            parse_directive_file(directive_file)
        
        error_msg = str(exc_info.value)
        assert "Invalid directive XML" in error_msg or "ParseError" in error_msg
