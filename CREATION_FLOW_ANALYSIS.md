# Creation Flow Analysis

## Summary

**All three item types now follow the same pattern:**

- **Knowledge, Tools, and Directives**: File must exist first, then validate, then sign

This unified approach ensures consistency and allows the `create` action to focus solely on validation and signing, while file creation is handled by directives (create_knowledge, create_script, create_directive) or manual file operations.

## Detailed Flow Comparison

### 1. Knowledge Creation (`_create_knowledge`)

**Location**: `kiwi_mcp/handlers/knowledge/handler.py:787-931`

**Flow**:
1. ✅ **Accepts content via parameters** (`title`, `content`, `entry_type`, etc.)
2. ✅ **Creates file first** (line 840: `file_path.write_text(temp_content)`)
   - Writes temporary content with frontmatter (no signature yet)
3. ✅ **Then validates** (lines 843-865)
   - Parses the file: `parse_knowledge_entry(file_path)`
   - Validates: `ValidationManager.validate_and_embed()`
   - **If validation fails**: Deletes file (`file_path.unlink()`)
4. ✅ **Then signs** (lines 867-889)
   - Generates hash and timestamp
   - Rewrites file with signature in frontmatter

**Pattern**: `Create → Validate → Sign`

---

### 2. Tool Creation (`_create_tool`)

**Location**: `kiwi_mcp/handlers/tool/handler.py:662-753`

**Flow**:
1. ✅ **Accepts content via parameters** (`content` parameter)
2. ✅ **Creates file first** (line 710: `file_path.write_text(content)`)
   - Writes content without signature
3. ✅ **Then validates** (lines 712-737)
   - Parses the file: `parse_script_metadata(file_path)`
   - Validates: `ValidationManager.validate_and_embed()`
   - **If validation fails**: Deletes file (`file_path.unlink()`)
4. ✅ **Then signs** (lines 739-741)
   - Signs content: `MetadataManager.sign_content("tool", content)`
   - Rewrites file with signature

**Pattern**: `Create → Validate → Sign`

---

### 3. Directive Creation (`_create_directive`)

**Location**: `kiwi_mcp/handlers/directive/handler.py:1177-1381`

**Flow**:
1. ❌ **Does NOT accept content via parameters**
   - Only accepts `location` and `category` parameters
2. ❌ **Expects file to already exist** (lines 1212-1221)
   - Searches for file: `rglob(f"*{directive_name}.md")`
   - **If file not found**: Returns error with hint to create file first
3. ✅ **Then validates** (lines 1223-1345)
   - Reads existing file: `file_path.read_text()`
   - Validates XML syntax
   - Parses: `parse_directive_file(file_path)`
   - Validates: `ValidationManager.validate_and_embed()`
   - **If validation fails**: Returns error (does NOT delete file)
4. ✅ **Then signs** (lines 1347-1351)
   - Signs content: `MetadataManager.sign_content("directive", content)`
   - Rewrites file with signature

**Pattern**: `File Must Exist → Validate → Sign`

---

## Key Differences

| Aspect | Knowledge | Tools | Directives |
|--------|-----------|-------|------------|
| **Content Parameter** | ✅ Yes (`title`, `content`) | ✅ Yes (`content`) | ❌ No |
| **Creates File** | ✅ Yes | ✅ Yes | ❌ No (must exist) |
| **Validation After Create** | ✅ Yes | ✅ Yes | ✅ Yes (on existing) |
| **Cleanup on Failure** | ✅ Deletes file | ✅ Deletes file | ❌ Returns error |
| **Signature Added** | ✅ Yes | ✅ Yes | ✅ Yes |

## Code Evidence

### Knowledge - Creates File First
```python
# Line 840: Create file with temporary content
file_path.write_text(temp_content)

# Line 844-851: Then validate
entry_data = parse_knowledge_entry(file_path)
validation_result = await ValidationManager.validate_and_embed(...)

# Line 853: Cleanup on failure
if not validation_result["valid"]:
    file_path.unlink()  # Clean up invalid file
```

### Tools - Creates File First
```python
# Line 710: Create file with content
file_path.write_text(content)

# Line 714-727: Then validate
tool_meta = parse_script_metadata(file_path)
validation_result = await ValidationManager.validate_and_embed(...)

# Line 729: Cleanup on failure
if not validation_result["valid"]:
    file_path.unlink()  # Clean up invalid file
```

### Directives - File Must Exist
```python
# Line 1212-1221: Check if file exists
if not file_path or not file_path.exists():
    return {
        "error": f"Directive file not found: {directive_name}",
        "hint": f"Create the file first at .ai/directives/{{category}}/{directive_name}.md",
    }

# Line 1224: Read existing file
content = file_path.read_text()

# Line 1261-1332: Then validate
directive_data = parse_directive_file(file_path)
validation_result = await ValidationManager.validate_and_embed(...)

# No cleanup - just returns error if validation fails
```

## Current Unified Pattern

**All three handlers now follow the same pattern:**

1. **File must exist first** (created via directive or manually)
2. **Validate the existing file**
3. **Sign if validation succeeds**
4. **Return error if validation fails** (file left intact for fixing)

This ensures consistency across all three item types. The `create` action is now purely for validation and signing, not file creation.
