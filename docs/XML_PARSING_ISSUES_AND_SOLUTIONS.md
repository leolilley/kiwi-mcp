# XML Parsing Issues and Solutions in Kiwi MCP Directives

**Date:** 2026-01-23  
**Context:** Issues encountered while creating the `implement_data_driven_validation` directive

## Overview

When creating XML-based directives in Kiwi MCP, certain characters and patterns can cause XML parsing errors. This document outlines the common issues and their solutions.

## Common XML Parsing Issues

### 1. Unescaped Angle Brackets (`<` and `>`)

**Problem:** Using `<` and `>` characters in directive content causes XML parsing errors.

**Error Example (Old):**
```
"error": "Invalid directive XML",
"parse_error": "not well-formed (invalid token): line 392, column 44"
```

**Error Example (Enhanced - New):**
```
"error": "Invalid directive XML",
"parse_error": "Invalid directive XML at line 10, column 25
Error: not well-formed (invalid token): line 10, column 25

Problematic line:
    10 |       <action>Response time must be <100ms</action>

Context (before):
     8 |   <process>
     9 |     <step name="check_latency">

Context (after):
    11 |     </step>
    12 |   </process>

Detected issues and suggestions:
  - Found comparison operator '<100' → use '&lt;100'
  - Found standalone '<' at position 25 → use '&lt;'

Solutions:
  1. Escape special characters: < → &lt;, > → &gt;, & → &amp;
  2. Wrap content in CDATA: <action><![CDATA[content with < > &]]></action>
  3. For arrows: -> → -&gt;

File: /path/to/directive.md"
```

**Common Locations:**
- Method signatures with generic types: `Dict -> List`
- Comparison operators: `>80%`, `<100ms`
- Variable transformations: `script_meta -> tool_meta`

**Solutions:**

#### Option 1: XML Entity Escaping
```xml
<!-- WRONG -->
- Cache hit ratios are high (>80%)
- Validation times are acceptable (<100ms)
- Variable names (script_meta -> tool_meta)

<!-- CORRECT -->
- Cache hit ratios are high (&gt;80%)
- Validation times are acceptable (&lt;100ms)
- Variable names (script_meta -&gt; tool_meta)
```

#### Option 2: CDATA Sections (for complex content)
```xml
<!-- For complex code or content with many special characters -->
<action><![CDATA[
def validate_schema(data: Dict[str, Any]) -> ValidationResult:
    if performance > 80% and latency < 100:
        return success
]]></action>
```

### 2. XML Entity Reference Table

| Character | XML Entity | Usage |
|-----------|------------|-------|
| `<` | `&lt;` | Less than comparisons, generic types |
| `>` | `&gt;` | Greater than comparisons, arrows |
| `&` | `&amp;` | Logical AND, URL parameters |
| `"` | `&quot;` | Quotes in attribute values |
| `'` | `&apos;` | Apostrophes in attribute values |

### 3. Detection Strategy

Use this command to find potential XML issues:
```bash
grep -n "[<>]" directive.md | grep -v "xml\|CDATA\|<step\|</step\|<action\|</action"
```

This finds angle brackets that aren't part of XML tags.

### 4. Common Patterns That Need Escaping

#### Method Signatures
```xml
<!-- WRONG -->
- validate_method(data: Dict) -> Result

<!-- CORRECT -->
- validate_method(data: Dict) -&gt; Result
```

#### Performance Metrics
```xml
<!-- WRONG -->
- Response time <100ms
- Success rate >95%

<!-- CORRECT -->
- Response time &lt;100ms
- Success rate &gt;95%
```

#### Transformations and Arrows
```xml
<!-- WRONG -->
- Convert old_format -> new_format

<!-- CORRECT -->
- Convert old_format -&gt; new_format
```

#### Code Examples in Text
```xml
<!-- WRONG -->
Update the validation call from ValidationManager.validate("script") to use "tool"

<!-- CORRECT (using CDATA) -->
<action><![CDATA[
Update the validation call:
ValidationManager.validate("script") -> ValidationManager.validate("tool")
]]></action>
```

## Best Practices

### 1. Use CDATA for Code Blocks
When including substantial code examples or complex content:
```xml
<action><![CDATA[
# Complex code with <, >, &, etc.
def process_data(input: List[Dict]) -> Dict[str, Any]:
    return {"status": "success", "count": len(input)}
]]></action>
```

### 2. Escape Individual Characters
For simple comparisons or arrows in text:
```xml
<verification>
- Performance is &gt;80%
- Latency is &lt;100ms
- Migration path: old -&gt; new
</verification>
```

### 3. Validation Workflow
1. **Write directive content**
2. **Check for unescaped characters** using grep
3. **Escape or wrap in CDATA** as appropriate
4. **Validate with create action** to catch parsing errors
5. **Fix any remaining issues** and re-validate

### 4. Testing Your Directive
Always test directive creation:
```python
kiwi_mcp_execute(
    item_type="directive",
    action="create",
    item_id="your_directive_name",
    parameters={"category": "your_category", "location": "project"}
)
```

If you get parsing errors, the enhanced error message will:
- Show the exact line and column where the error occurred
- Display the problematic line with context
- Automatically detect common patterns (comparisons, arrows, etc.)
- Suggest specific fixes for each detected issue

The error message format has been improved to make it much easier to identify and fix XML parsing issues.

## Error Recovery

### Enhanced Error Messages

The XML parser now provides detailed error messages that include:

1. **Exact line and column numbers** where the error occurred
2. **Problematic line** with the issue highlighted
3. **Context lines** (before and after) to help locate the problem
4. **Automatic pattern detection** that identifies common issues:
   - Comparison operators (`>80%`, `<100ms`)
   - Arrow operators (`->`, `=>`)
   - Method signatures with return types
   - Unescaped ampersands (`&`)
5. **Specific suggestions** for fixing each detected issue
6. **Multiple solution options** (escaping vs CDATA)

### Error Recovery Workflow

If you encounter XML parsing errors:

1. **Read the enhanced error message** - it now includes line numbers and context
2. **Check the "Detected issues and suggestions" section** - it identifies specific problems
3. **Apply the suggested fixes** - either escape characters or use CDATA
4. **Re-run the create/update action** to validate
5. **Repeat until validation succeeds**

The error message will guide you to the exact location and suggest the appropriate fix.

## Example: Before and After

### Before (Causes Parsing Error)
```xml
<verification>
- Cache hit ratio >80%
- Response time <100ms
- Transform: old_data -> new_data
</verification>
```

### After (Parses Successfully)
```xml
<verification>
- Cache hit ratio &gt;80%
- Response time &lt;100ms
- Transform: old_data -&gt; new_data
</verification>
```

## Related Documentation

- [XML 1.0 Specification](https://www.w3.org/TR/xml/)
- [XML Entity References](https://www.w3.org/TR/xml/#sec-predefined-ent)
- [CDATA Sections](https://www.w3.org/TR/xml/#sec-cdata-sect)

## Improved Error Handling

The XML parser has been enhanced to provide much better error messages:

### What's New

- **Line and column numbers**: Errors now show exactly where the problem is
- **Context display**: Shows the problematic line with surrounding context
- **Pattern detection**: Automatically identifies common issues:
  - Comparison operators: `>80%` → suggests `&gt;80%`
  - Arrows: `->` → suggests `-&gt;`
  - Method signatures: `->` in return types
  - Unescaped ampersands: `&` → suggests `&amp;`
- **Specific suggestions**: Each detected issue gets a specific fix suggestion
- **Multiple solutions**: Suggests both escaping and CDATA options

### Example Enhanced Error

When you have an unescaped character, instead of a generic error, you'll see:

```
Invalid directive XML at line 10, column 25
Error: not well-formed (invalid token): line 10, column 25

Problematic line:
    10 |       <action>Response time must be <100ms</action>

Detected issues and suggestions:
  - Found comparison operator '<100' → use '&lt;100'

Solutions:
  1. Escape special characters: < → &lt;, > → &gt;, & → &amp;
  2. Wrap content in CDATA: <action><![CDATA[content with < > &]]></action>
```

This makes it much easier to identify and fix XML parsing issues.

## Conclusion

XML parsing issues in Kiwi MCP directives are easily preventable by:
1. **Being aware** of special characters (`<`, `>`, `&`)
2. **Using proper escaping** for simple cases
3. **Using CDATA sections** for complex code blocks
4. **Testing early and often** with the create action
5. **Reading enhanced error messages** that now provide detailed guidance

Following these practices ensures your directives validate successfully and are ready for execution. The enhanced error messages make it much easier to identify and fix issues when they occur.