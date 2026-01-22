# Create Directive Improvements

**Date:** 2026-01-23
**Status:** Implemented
**Version:** 4.0.0

---

## Executive Summary

Review of `create_directive` (v3.0.3) identified several improvements needed:

1. **Reference directive-creation-pattern knowledge entry** - Make it explicit
2. **Enforce metadata in handler code** - Don't rely on directive text alone
3. **Block run/publish for unsigned directives** - Prevent create_file bypass
4. **Normalize complexity → model tier mapping** - Single source of truth

---

## Current Issues

### Issue 1: Agents Bypass create_directive

Agents sometimes use `create_file` to manually create directive files, bypassing:
- XML validation
- Signature generation
- Metadata normalization

**Evidence:** Harness orchestration directives were initially created manually.

### Issue 2: Metadata Enforcement is Documentation-Only

The complexity → model tier mapping exists in directive text but isn't enforced:
```
complexity: orchestrator → tier: reasoning, parallel: true, context_budget required
```

Nothing prevents directives with `complexity: simple` but `tier: expert`.

### Issue 3: Missing Signature Allows Invalid Directives to Run

Current flow:
- `create_file` → directive exists but no signature
- `run` → runs anyway (signature warning ignored)
- Agent thinks it worked, but directive is invalid for publish

---

## Proposed Changes

### A. Directive Updates (create_directive v4.0.0)

#### 1. Add Knowledge Reference (Required)

Add to `<relationships>`:
```xml
<relationships>
  <requires>directive-creation-pattern</requires>
  <suggests>edit_directive</suggests>
  <suggests>sync_directives</suggests>
</relationships>
```

Add early step:
```xml
<step name="load_creation_pattern">
  <description>Load and follow directive creation pattern</description>
  <action><![CDATA[
CRITICAL: Load directive-creation-pattern knowledge entry:

mcp__kiwi_mcp__load(
  item_type="knowledge",
  item_id="directive-creation-pattern",
  source="local",
  project_path="{project_path}"
)

This entry explains why you MUST use this directive (create_directive)
and MUST NOT use create_file to manually create directive files.

If you are about to use create_file for a directive, STOP.
  ]]></action>
</step>
```

#### 2. Explicit Complexity → Metadata Mapping

Add normative table:
```xml
<complexity_mapping>
  <level name="simple">
    <model tier="fast" fallback="balanced" parallel="false" />
    <context_budget estimated_usage="10%" step_count="3" />
  </level>
  <level name="moderate">
    <model tier="balanced" fallback="reasoning" parallel="false" />
    <context_budget estimated_usage="20%" step_count="5" />
  </level>
  <level name="complex">
    <model tier="reasoning" fallback="expert" parallel="false" />
    <context_budget estimated_usage="30%" step_count="8" />
  </level>
  <level name="orchestrator">
    <model tier="reasoning" fallback="expert" parallel="true" />
    <context_budget estimated_usage="40%" step_count="10" spawn_threshold="60%" />
    <requires>deviation_rules</requires>
  </level>
</complexity_mapping>
```

#### 3. Mandatory Post-Create Validation

Update validate_and_sign step to emphasize:
```xml
<step name="validate_and_sign">
  <action><![CDATA[
MANDATORY: After creating the file, validate and sign:

execute(
  item_type="directive",
  action="create",  // or "update" if file exists
  item_id="{name}",
  parameters={"location": "project"},
  project_path="{project_path}"
)

A directive WITHOUT a valid signature:
- ❌ Cannot be published
- ❌ Will show warnings on run
- ❌ Is not considered valid

If validation fails, fix errors and re-run.
  ]]></action>
</step>
```

---

### B. Handler Changes (kiwi_mcp/handlers/directive/handler.py)

#### 1. Block Run/Publish for Unsigned Directives

```python
# In _run_directive()
async def _run_directive(self, directive_name: str, params: dict, ...):
    # Load directive
    file_path = self.resolver.resolve(directive_name)
    
    # CHECK SIGNATURE FIRST
    signature_result = self.metadata_manager.verify_signature(file_path)
    
    if signature_result.status in ["missing", "pending"]:
        return {
            "error": "Directive has no valid signature",
            "status": "invalid",
            "solution": (
                "Run: execute(item_type='directive', action='update', "
                f"item_id='{directive_name}', parameters={{'location': 'project'}}, ...)"
            ),
            "hint": "Directives must be created via create_directive, not create_file"
        }
    
    if signature_result.status == "modified":
        return {
            "error": "Directive content modified since last validation",
            "status": "modified",
            "solution": "Run update action to re-validate and sign"
        }
    
    # Continue with normal execution...
```

#### 2. Add Metadata Schema Validation

```python
# New file: kiwi_mcp/validation/directive_schema.py

from dataclasses import dataclass
from typing import Optional
from enum import Enum

class Complexity(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ORCHESTRATOR = "orchestrator"

@dataclass
class ModelConfig:
    tier: str
    fallback: str
    parallel: bool

@dataclass
class ContextBudget:
    estimated_usage: str  # percentage
    step_count: int
    spawn_threshold: Optional[str] = None

# Mapping from complexity to required metadata
COMPLEXITY_DEFAULTS = {
    Complexity.SIMPLE: {
        "model": ModelConfig(tier="fast", fallback="balanced", parallel=False),
        "context_budget": ContextBudget(estimated_usage="10%", step_count=3),
    },
    Complexity.MODERATE: {
        "model": ModelConfig(tier="balanced", fallback="reasoning", parallel=False),
        "context_budget": ContextBudget(estimated_usage="20%", step_count=5),
    },
    Complexity.COMPLEX: {
        "model": ModelConfig(tier="reasoning", fallback="expert", parallel=False),
        "context_budget": ContextBudget(estimated_usage="30%", step_count=8),
    },
    Complexity.ORCHESTRATOR: {
        "model": ModelConfig(tier="reasoning", fallback="expert", parallel=True),
        "context_budget": ContextBudget(
            estimated_usage="40%", step_count=10, spawn_threshold="60%"
        ),
        "requires_deviation_rules": True,
    },
}

def validate_directive_metadata(parsed: dict) -> tuple[dict, list[str]]:
    """Validate and normalize directive metadata.
    
    Returns (normalized_metadata, errors).
    """
    errors = []
    metadata = parsed.get("metadata", {})
    
    # Required fields
    required = ["description", "category", "author"]
    for field in required:
        if field not in metadata:
            errors.append(f"Missing required metadata field: {field}")
    
    # Version format (must be semver)
    version = parsed.get("_attrs", {}).get("version", "")
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        errors.append(f"Invalid version format: {version}. Must be semver (e.g., 1.0.0)")
    
    # Name must match file (checked elsewhere, but validate format)
    name = parsed.get("_attrs", {}).get("name", "")
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        errors.append(f"Invalid directive name: {name}. Must be snake_case")
    
    # Complexity validation
    complexity_str = metadata.get("complexity")
    if complexity_str:
        try:
            complexity = Complexity(complexity_str)
        except ValueError:
            errors.append(f"Invalid complexity: {complexity_str}. Must be one of: {[c.value for c in Complexity]}")
    
    # If orchestrator, require deviation_rules
    if complexity_str == "orchestrator":
        if "deviation_rules" not in metadata:
            errors.append("Orchestrator directives require deviation_rules")
    
    # Model tier validation
    model = metadata.get("model", {})
    if isinstance(model, dict):
        tier = model.get("_attrs", {}).get("tier")
        valid_tiers = ["fast", "balanced", "general", "reasoning", "expert", "orchestrator"]
        if tier and tier not in valid_tiers:
            errors.append(f"Invalid model tier: {tier}. Must be one of: {valid_tiers}")
    
    return metadata, errors
```

#### 3. Wire Validation into Create/Update Actions

```python
# In handler.py _create_directive() and _update_directive()

async def _create_directive(self, directive_name: str, params: dict, ...):
    file_path = self.resolver.resolve(directive_name)
    
    if not file_path.exists():
        return {"error": "Directive file not found", "hint": "Create the file first"}
    
    # Parse and validate
    parsed = parse_directive_file(file_path)
    
    # Schema validation
    _, errors = validate_directive_metadata(parsed)
    if errors:
        return {
            "error": "Invalid directive metadata",
            "validation_errors": errors,
            "hint": "Fix the listed errors and retry"
        }
    
    # Validate XML structure
    validation_result = await self.validation_manager.validate(file_path)
    if not validation_result.valid:
        return {"error": validation_result.error, ...}
    
    # Sign
    signature = self.metadata_manager.sign_content(file_path)
    ...
```

#### 4. Add Directive Name/Filename Match Check

```python
def _validate_name_matches_file(self, file_path: Path, parsed: dict) -> Optional[str]:
    """Ensure directive name matches filename."""
    file_stem = file_path.stem
    directive_name = parsed.get("_attrs", {}).get("name", "")
    
    if file_stem != directive_name:
        return (
            f"Directive name '{directive_name}' does not match filename '{file_stem}'. "
            "These must match to prevent rename drift."
        )
    return None
```

---

### C. Success Metrics

After implementation:

- [ ] `run` action blocks directives without valid signature
- [ ] `publish` action blocks directives without valid signature
- [ ] `create/update` validates metadata schema
- [ ] Complexity enum enforced (only 4 values allowed)
- [ ] Orchestrator directives require deviation_rules
- [ ] Directive name must match filename
- [ ] Version must be semver format

---

### D. Migration Path

1. **Existing directives**: Run `execute(action="update")` to revalidate
2. **Grace period**: Add warnings before blocking (1 week)
3. **Batch tool**: Add `kiwi validate-all-directives` CLI command

---

## Implementation Status

| Change | Impact | Status |
|--------|--------|--------|
| Block run for unsigned | High | ✅ Implemented |
| Block publish for unsigned | High | ✅ Implemented |
| Add metadata schema validation | High | ✅ Implemented |
| Reference knowledge entry | Medium | ✅ Implemented |
| Name format validation (snake_case) | Medium | ✅ Implemented |
| Version format validation (semver) | Medium | ✅ Implemented |
| Model tier validation | Medium | ✅ Implemented |
| Complexity → tier normalization | Medium | 🔄 Future (P2) |

### Files Changed

1. **kiwi_mcp/handlers/directive/handler.py**
   - `_run_directive()`: Block on missing signature
   - `_publish_directive()`: Block on missing signature

2. **kiwi_mcp/utils/validators.py**
   - `DirectiveValidator.validate_filename_match()`: Add snake_case name validation
   - `DirectiveValidator.validate_metadata()`: Add tier enum validation, semver validation

3. **.ai/directives/core/create_directive.md**
   - Version bumped to 4.0.0
   - Added `<requires>directive-creation-pattern</requires>`
   - Added `load_creation_pattern` step

4. **.ai/knowledge/patterns/anti-patterns/directive-creation-pattern.md**
   - New knowledge entry documenting the pattern

---

## Related Documents

- [directive-creation-pattern](../.ai/knowledge/patterns/anti-patterns/directive-creation-pattern.md)
- [PERMISSION_ENFORCEMENT.md](./PERMISSION_ENFORCEMENT.md)
- [DIRECTIVE_AUTHORING.md](./DIRECTIVE_AUTHORING.md)
