"""
Tests for directive, script, and knowledge parsers.
"""

import pytest
from pathlib import Path
from kiwi_mcp.utils.parsers import parse_directive_file


class TestDirectiveParser:
    """Test directive file parsing."""

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_with_greater_than_or_equal_in_text(self, tmp_path):
        """Should parse directive containing >= in text content."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_gte" version="1.0.0">
  <metadata>
    <description>Test directive with >= operator</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="check_version">
      <action>Check if version >= 1.0.0</action>
    </step>
    <step name="compare">
      <action>Compare values: x >= y</action>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_gte.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file)
        
        assert result["name"] == "test_gte"
        assert result["version"] == "1.0.0"
        # Check that >= is preserved in parsed content
        parsed = result["parsed"]
        process = parsed.get("process", {})
        steps = process.get("step", [])
        
        # Find the step with >= in its action
        found_gte = False
        for step in (steps if isinstance(steps, list) else [steps]):
            action = step.get("action", {})
            action_text = action.get("_text", "") if isinstance(action, dict) else str(action)
            if ">=" in action_text:
                found_gte = True
                assert ">=" in action_text
                break
        
        assert found_gte, "Should find >= in action text"

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
        
        result = parse_directive_file(directive_file)
        
        assert result["version"] == "2.3.4"

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_with_greater_than_or_equal_in_cdata(self, tmp_path):
        """Should parse directive containing >= in CDATA section."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_gte_cdata" version="1.0.0">
  <metadata>
    <description>Test directive with >= in CDATA</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="check">
      <action><![CDATA[if version >= 1.0.0 then proceed]]></action>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_gte_cdata.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file)
        
        assert result["name"] == "test_gte_cdata"
        # Check that >= is preserved in CDATA content
        parsed = result["parsed"]
        process = parsed.get("process", {})
        step = process.get("step", {})
        action = step.get("action", {})
        action_text = action.get("_text", "") if isinstance(action, dict) else str(action)
        
        assert ">=" in action_text, "Should preserve >= in CDATA content"

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_with_greater_than_or_equal_in_description(self, tmp_path):
        """Should parse directive containing >= in description text."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_gte_desc" version="1.0.0">
  <metadata>
    <description>This directive requires Python version >= 3.8</description>
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
        directive_file = directive_dir / "test_gte_desc.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file)
        
        assert result["name"] == "test_gte_desc"
        assert ">=" in result["description"], "Should preserve >= in description"

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_with_greater_than_or_equal_in_attribute_value(self, tmp_path):
        """Should parse directive containing >= in attribute values."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_gte_attr" version="1.0.0">
  <metadata>
    <description>Test directive with >= in attributes</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="check" threshold=">= 80%">
      <action>Check if threshold >= 80%</action>
    </step>
    <verification>
      <check>Token reduction >= 80% achieved</check>
    </verification>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_gte_attr.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file)
        
        assert result["name"] == "test_gte_attr"
        # Check that >= is preserved in attribute value
        parsed = result["parsed"]
        process = parsed.get("process", {})
        step = process.get("step", {})
        threshold = step.get("_attrs", {}).get("threshold", "")
        
        assert ">=" in threshold, "Should preserve >= in attribute value"
        assert threshold == ">= 80%", f"Expected '>= 80%', got '{threshold}'"

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_with_greater_than_or_equal_in_verification_check(self, tmp_path):
        """Should parse directive containing >= in verification check text."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_gte_verify" version="1.0.0">
  <metadata>
    <description>Test directive with >= in verification</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="verify">
      <action>Verify results</action>
      <verification>
        <check>Token reduction >= 80% achieved</check>
        <check>Performance improvement >= 50%</check>
      </verification>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_gte_verify.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file)
        
        assert result["name"] == "test_gte_verify"
        # Check that >= is preserved in verification check text
        parsed = result["parsed"]
        process = parsed.get("process", {})
        step = process.get("step", {})
        verification = step.get("verification", {})
        checks = verification.get("check", [])
        
        # Checks can be a list or single item
        check_list = checks if isinstance(checks, list) else [checks]
        check_texts = [
            check.get("_text", "") if isinstance(check, dict) else str(check)
            for check in check_list
        ]
        
        found_gte = any(">=" in text for text in check_texts)
        assert found_gte, "Should preserve >= in verification check text"

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_with_deeply_nested_cdata_placeholders(self, tmp_path):
        """Should parse directive with deeply nested CDATA using placeholders."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_nested_cdata" version="1.0.0">
  <metadata>
    <description>Test directive with deeply nested CDATA placeholders</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="create_template">
      <action><![CDATA[
Create a file with nested CDATA example:

{CDATA_OPEN}
  This is level 1 CDATA
  {CDATA_OPEN}
    This is level 2 CDATA
    {CDATA_OPEN}
      This is level 3 CDATA
      Some content here
    {CDATA_CLOSE}
  {CDATA_CLOSE}
{CDATA_CLOSE}

The placeholders will be expanded when the directive runs.
      ]]></action>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_nested_cdata.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file)
        
        assert result["name"] == "test_nested_cdata"
        # Check that CDATA placeholders are expanded
        parsed = result["parsed"]
        process = parsed.get("process", {})
        step = process.get("step", {})
        action = step.get("action", {})
        action_text = action.get("_text", "") if isinstance(action, dict) else str(action)
        
        # After expansion, placeholders should become actual CDATA markers
        assert "{CDATA_OPEN}" not in action_text, "Placeholders should be expanded"
        assert "<![CDATA[" in action_text, "Should contain expanded CDATA markers"
        assert "{CDATA_CLOSE}" not in action_text, "Placeholders should be expanded"
        assert "]]>" in action_text, "Should contain expanded CDATA closing markers"
        
        # Check that nested structure is preserved
        assert "level 1 CDATA" in action_text
        assert "level 2 CDATA" in action_text
        assert "level 3 CDATA" in action_text

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_with_multiple_nested_cdata_levels(self, tmp_path):
        """Should parse directive with multiple levels of nested CDATA placeholders."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_multi_nested_cdata" version="1.0.0">
  <metadata>
    <description>Test directive with multiple nested CDATA levels</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="complex_template">
      <action><![CDATA[
Template with multiple nesting:

{CDATA_OPEN}
  Outer level
  {CDATA_OPEN}
    Middle level
    {CDATA_OPEN}
      Inner level
      Code: if x >= 5 then do something
    {CDATA_CLOSE}
    More middle content
  {CDATA_CLOSE}
  More outer content
{CDATA_CLOSE}
      ]]></action>
    </step>
    <step name="another_step">
      <action><![CDATA[
Another action with nested CDATA:
{CDATA_OPEN}
  Example: {CDATA_OPEN}nested{CDATA_CLOSE}
{CDATA_CLOSE}
      ]]></action>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_multi_nested_cdata.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file)
        
        assert result["name"] == "test_multi_nested_cdata"
        parsed = result["parsed"]
        process = parsed.get("process", {})
        steps = process.get("step", [])
        if not isinstance(steps, list):
            steps = [steps]
        
        # Check first step
        step1 = steps[0]
        action1 = step1.get("action", {})
        action1_text = action1.get("_text", "") if isinstance(action1, dict) else str(action1)
        
        assert "{CDATA_OPEN}" not in action1_text, "Placeholders should be expanded in step 1"
        assert "<![CDATA[" in action1_text, "Should contain expanded CDATA in step 1"
        assert "Outer level" in action1_text
        assert "Middle level" in action1_text
        assert "Inner level" in action1_text
        assert "x >= 5" in action1_text, "Should preserve >= in nested CDATA"
        
        # Check second step
        if len(steps) > 1:
            step2 = steps[1]
            action2 = step2.get("action", {})
            action2_text = action2.get("_text", "") if isinstance(action2, dict) else str(action2)
            
            assert "{CDATA_OPEN}" not in action2_text, "Placeholders should be expanded in step 2"
            assert "<![CDATA[" in action2_text, "Should contain expanded CDATA in step 2"

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_with_backticks_in_markdown(self, tmp_path):
        """Should parse directive containing backticks in markdown code blocks."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

This directive contains backticks in markdown.

```xml
<directive name="test_backticks" version="1.0.0">
  <metadata>
    <description>Test directive with backticks</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="code_example">
      <action><![CDATA[
Run this command:
  `python script.py --arg value`

Or use inline code: `print("hello")`

Code block example:
```
def example():
    return "test"
```
      ]]></action>
    </step>
  </process>
</directive>
```

More markdown with `inline code` here.
"""
        directive_file = directive_dir / "test_backticks.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file)
        
        assert result["name"] == "test_backticks"
        # Check that backticks are preserved in action content
        parsed = result["parsed"]
        process = parsed.get("process", {})
        step = process.get("step", {})
        action = step.get("action", {})
        action_text = action.get("_text", "") if isinstance(action, dict) else str(action)
        
        assert "`python script.py" in action_text, "Should preserve backticks in action"
        assert "`print(" in action_text, "Should preserve inline code backticks"
        assert "```" in action_text, "Should preserve code block backticks"

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_with_backticks_and_cdata_nested(self, tmp_path):
        """Should parse directive with backticks inside nested CDATA placeholders."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_backticks_cdata" version="1.0.0">
  <metadata>
    <description>Test directive with backticks in nested CDATA</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="complex_example">
      <action><![CDATA[
Example showing code in nested CDATA:

{CDATA_OPEN}
  Here's some code:
  `python -c "print('test')"`
  
  And a code block:
  ```
  def func():
      return True
  ```
{CDATA_CLOSE}
      ]]></action>
    </step>
  </process>
</directive>
```
"""
        directive_file = directive_dir / "test_backticks_cdata.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file)
        
        assert result["name"] == "test_backticks_cdata"
        parsed = result["parsed"]
        process = parsed.get("process", {})
        step = process.get("step", {})
        action = step.get("action", {})
        action_text = action.get("_text", "") if isinstance(action, dict) else str(action)
        
        # CDATA placeholders should be expanded
        assert "{CDATA_OPEN}" not in action_text, "Placeholders should be expanded"
        assert "<![CDATA[" in action_text, "Should contain expanded CDATA"
        
        # Backticks should be preserved
        assert "`python -c" in action_text, "Should preserve backticks after CDATA expansion"
        assert "```" in action_text, "Should preserve code block backticks"

    @pytest.mark.unit
    @pytest.mark.parser
    def test_parse_directive_with_backticks_in_description(self, tmp_path):
        """Should parse directive with backticks in description and other metadata."""
        directive_dir = tmp_path / ".ai" / "directives" / "test"
        directive_dir.mkdir(parents=True)
        
        directive_content = """# Test Directive

```xml
<directive name="test_backticks_meta" version="1.0.0">
  <metadata>
    <description>This directive uses `code` and ```code blocks``` in description</description>
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
        directive_file = directive_dir / "test_backticks_meta.md"
        directive_file.write_text(directive_content)
        
        result = parse_directive_file(directive_file)
        
        assert result["name"] == "test_backticks_meta"
        # Check that backticks are preserved in description
        assert "`code`" in result["description"], "Should preserve inline code backticks"
        assert "```code blocks```" in result["description"], "Should preserve code block backticks"
