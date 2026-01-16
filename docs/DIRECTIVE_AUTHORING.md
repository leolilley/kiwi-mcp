# Directive Authoring Guide

**Purpose:** Guidelines for writing directives in the Kiwi MCP system.

---

## Table of Contents

1. [Directive Structure](#directive-structure)
2. [XML Requirements](#xml-requirements)
3. [Inline Relationships](#inline-relationships)
4. [CDATA Usage](#cdata-usage)
5. [Permissions](#permissions)
6. [Best Practices](#best-practices)

---

## Directive Structure

A directive is a markdown file containing:
1. **Markdown content**: Description, examples, usage notes
2. **XML block**: The actual directive specification

Basic template:

```markdown
# Directive Name

Description of what this directive does.

```xml
<directive name="directive_name" version="1.0.0">
  <metadata>
    <description>Brief description</description>
    <category>category_name</category>
    <author>author_name</author>
    <permissions>
      <read resource="filesystem" path="**/*.py" />
      <write resource="filesystem" path="**/*.py" />
    </permissions>
  </metadata>
  
  <context>
    <tech_stack>python</tech_stack>
    <project_path>/path/to/project</project_path>
  </context>
  
  <inputs>
    <input name="param1" type="string" required="true">
      Description of parameter
    </input>
  </inputs>
  
  <process>
    <step name="step1">
      <description>What this step does</description>
      <action>
Detailed instructions for this step
      </action>
    </step>
  </process>
  
  <outputs>
    <success>What success looks like</success>
    <failure>What to do on failure</failure>
  </outputs>
</directive>
\```
```

---

## XML Requirements

### Required Elements

Every directive MUST include:

1. **`<metadata>`**: Contains description, category, author, and **`<permissions>`** (REQUIRED even if empty)
2. **`<process>`**: Contains the steps to execute
3. **`<outputs>`**: Defines success/failure outcomes

### Optional Elements

- **`<context>`**: Tech stack, project paths, environment info
- **`<inputs>`**: Parameters the directive accepts

---

## Inline Relationships

Directives can declare relationships to other directives using the `<relationships>` element. This helps organize and discover related directives.

### Relationships Element

Add the `<relationships>` element after `<metadata>` in your directive XML:

```xml
<directive name="my_directive" version="1.0.0">
  <metadata>
    <description>My directive description</description>
    <category>development</category>
    <author>your_name</author>
  </metadata>

  <relationships>
    <requires directive="base_setup" />
    <suggests directive="advanced_config" />
    <extends directive="parent_directive" />
    <related directive="similar_directive" />
  </relationships>

  <!-- rest of directive -->
</directive>
```

### Relationship Types

| Type | Description | Example |
|------|-------------|---------|
| `requires` | This directive depends on another directive being executed first | A deployment directive requires a build directive |
| `suggests` | This directive works well when combined with another | A testing directive suggests a code coverage directive |
| `extends` | This directive builds upon or modifies another directive | A custom build directive extends a standard build directive |
| `related` | This directive is conceptually related to another | Two different approaches to the same problem |

### Best Practices for Relationships

- Use `requires` sparingly - only when execution order is critical
- Use `suggests` to recommend complementary directives
- Use `extends` when your directive modifies or enhances another
- Use `related` for loose connections or alternative approaches
- Keep relationship chains short to avoid complexity

---

## CDATA Usage

### The Problem: Nested CDATA Limitation

**CRITICAL:** XML does not support nested CDATA sections. The sequence `]]>` **always** closes a CDATA section, even inside another CDATA.

This creates a problem when:
- A directive needs to show CDATA examples in its action content
- Template directives need to output CDATA-wrapped content
- Documentation includes CDATA syntax examples

### The Solution: Placeholder Tokens

Use these special placeholders in your directive content:

| Placeholder | Expands To | Use Case |
|------------|-----------|----------|
| `{CDATA_OPEN}` | `<![CDATA[` | Show CDATA opening in examples |
| `{CDATA_CLOSE}` | `]]>` | Show CDATA closing in examples |

The parser automatically expands these placeholders **after** parsing the XML, so they won't interfere with XML parsing.

### Example: Template Directive

**Problem** (this breaks):
```xml
<step name="create_file">
  <action>
<![CDATA[
Create a file with this content:
<![CDATA[
  Some content here
]]>
]]>
  </action>
</step>
```

The inner `]]>` closes the outer CDATA prematurely, breaking the XML.

**Solution** (this works):
```xml
<step name="create_file">
  <action>
<![CDATA[
Create a file with this content:
{CDATA_OPEN}
  Some content here
{CDATA_CLOSE}
]]>
  </action>
</step>
```

When the directive runs, the placeholders are expanded to actual CDATA markers in the output.

### When to Use CDATA vs Placeholders

| Situation | Use This |
|-----------|----------|
| Normal action content with `<`, `>`, `&` | CDATA: `<![CDATA[content]]>` |
| Content that shows CDATA examples | Placeholders: `{CDATA_OPEN}` and `{CDATA_CLOSE}` |
| Template output with CDATA | Placeholders in the template |
| Documentation examples | Placeholders if inside CDATA, real CDATA if not |

### Alternative: Escape Special Characters

If you don't need CDATA, you can use XML escaping:
- `&lt;` for `<`
- `&gt;` for `>`
- `&amp;` for `&`
- `&quot;` for `"`
- `&apos;` for `'`

This is cleaner for short content but harder to read for large blocks.

---

## Permissions

### Permission Format

Permissions declare what resources a directive needs to access. The `<permissions>` section **must be placed inside `<metadata>`**:

```xml
<metadata>
  <description>...</description>
  <category>...</category>
  <permissions>
    <!-- File system access -->
    <read resource="filesystem" path="src/**/*.ts" />
    <write resource="filesystem" path="dist/**/*" />
    
    <!-- Network access -->
    <read resource="network" endpoint="https://api.example.com" />
    <write resource="network" endpoint="https://api.example.com" />
    
    <!-- Environment variables -->
    <read resource="env" var="API_KEY" />
    <write resource="env" var="CONFIG_VALUE" />
    
    <!-- Execution -->
    <execute resource="shell" command="npm" />
    <execute resource="python" module="requests" />
  </permissions>
</metadata>
```

### Permission Types

| Tag | Resource | Attributes | Description |
|-----|----------|-----------|-------------|
| `<read>` | `filesystem` | `path` (glob pattern) | Read file access |
| `<write>` | `filesystem` | `path` (glob pattern) | Write file access |
| `<read>` | `network` | `endpoint` (URL pattern) | HTTP GET requests |
| `<write>` | `network` | `endpoint` (URL pattern) | HTTP POST/PUT requests |
| `<read>` | `env` | `var` (variable name) | Read environment variable |
| `<write>` | `env` | `var` (variable name) | Write environment variable |
| `<execute>` | `shell` | `command` (binary name) | Execute shell command |
| `<execute>` | `python` | `module` (import name) | Import Python module |

### Glob Patterns in Permissions

Use glob patterns to specify file paths:
- `**/*.py` - All Python files recursively
- `src/**/*` - All files under src/
- `*.json` - JSON files in current directory
- `config/*.yaml` - YAML files in config/

### Empty Permissions

If a directive doesn't need any special permissions (e.g., it only provides guidance), include an empty permissions section inside `<metadata>`:

```xml
<metadata>
  <description>...</description>
  <category>...</category>
  <permissions>
    <!-- No special permissions required -->
  </permissions>
</metadata>
```

**IMPORTANT:** The `<permissions>` section is REQUIRED inside `<metadata>` even if empty. The parser will reject directives without it.

---

## Best Practices

### 1. Clear Step Names

Use descriptive step names that indicate what the step does:

**Good:**
```xml
<step name="install_dependencies">
<step name="create_config_file">
<step name="verify_api_connection">
```

**Bad:**
```xml
<step name="step1">
<step name="do_stuff">
<step name="handle">
```

### 2. Atomic Steps

Each step should do ONE thing. If a step has multiple sub-actions, consider breaking it into multiple steps:

**Instead of:**
```xml
<step name="setup_and_configure">
  <action>
1. Install dependencies
2. Create config file
3. Validate configuration
4. Test connection
  </action>
</step>
```

**Do this:**
```xml
<step name="install_dependencies">...</step>
<step name="create_config">...</step>
<step name="validate_config">...</step>
<step name="test_connection">...</step>
```

### 3. Use CDATA for Complex Content

Wrap action content in CDATA if it contains:
- Code examples with `<`, `>`, `&`
- Command-line arguments with special characters
- JSON/XML/HTML snippets
- URLs with query parameters

```xml
<action>
<![CDATA[
Run this command:
  curl -X POST https://api.example.com?key=value&foo=bar
  
Response format:
  {"status": "success", "data": {...}}
]]>
</action>
```

### 4. Document Inputs Clearly

For each input parameter, specify:
- **Type**: string, integer, boolean, array, object
- **Required**: true/false
- **Default**: What value is used if not provided
- **Description**: What the parameter does and expected format

```xml
<input name="api_endpoint" type="string" required="true">
  API endpoint URL (must start with https://)
</input>

<input name="timeout" type="integer" required="false" default="30">
  Request timeout in seconds (1-300)
</input>
```

### 5. Provide Clear Success/Failure Messages

Outputs should describe:
- **Success**: What was accomplished, what files were created/modified, next steps
- **Failure**: Common error causes, troubleshooting steps, fallback options

```xml
<outputs>
  <success>
API configuration complete:
- Config file created at .env
- Connection test passed
- API key validated

Next steps:
1. Run the application
2. Monitor logs for API calls
  </success>
  
  <failure>
API setup failed. Common issues:
- Invalid API key (check .env file)
- Network connectivity (test with: curl https://api.example.com)
- Firewall blocking requests (check firewall rules)

Fallback: Use mock API mode with MOCK_API=true
  </failure>
</outputs>
```

### 6. Version Your Directives

Use semantic versioning:
- **Major** (1.0.0 → 2.0.0): Breaking changes to inputs or behavior
- **Minor** (1.0.0 → 1.1.0): New features, backward compatible
- **Patch** (1.0.0 → 1.0.1): Bug fixes, clarifications

### 7. Test Your Directives

Before publishing:
1. Run the directive end-to-end
2. Test with different input combinations
3. Verify permissions are sufficient
4. Check that CDATA sections parse correctly
5. Validate XML syntax (parser will catch this)

---

## Additional Resources

- [API Reference](./API.md) - Complete API documentation
- [Architecture](./ARCHITECTURE.md) - System architecture overview
- [Directive-Driven Build](./DIRECTIVE_DRIVEN_BUILD.md) - Using directives to build the system

---

**Questions or Issues?**

If you encounter problems or have suggestions for this guide, please:
1. Check existing directives in `.ai/directives/` for examples
2. Search the knowledge base for related topics
3. Create an issue describing the problem
