"""Integration tests for the Safety Harness system."""

import pytest
import sys
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

# Load modules from rye/.ai/tools/core/threads or .ai/tools/threads
_repo = Path(__file__).resolve().parent.parent.parent
_tools_path = _repo / "rye" / ".ai" / "tools" / "core" / "threads"
if not _tools_path.exists():
    _tools_path = _repo / ".ai" / "tools" / "threads"
if not _tools_path.exists():
    import pytest
    pytest.skip("No rye/.ai or .ai/tools/threads", allow_module_level=True)

def _load_module(name):
    path = _tools_path / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

_harness_module = _load_module("safety_harness")
_expr_module = _load_module("expression_evaluator")
_directive_module = _load_module("thread_directive")

SafetyHarness = _harness_module.SafetyHarness
HarnessAction = _harness_module.HarnessAction
evaluate_expression = _expr_module.evaluate_expression
substitute_templates = _expr_module.substitute_templates


@pytest.fixture
def project_with_hooks(tmp_path):
    """Create a project with hook directives and pricing config."""
    # Create pricing config
    llm_dir = tmp_path / ".ai" / "tools" / "llm"
    llm_dir.mkdir(parents=True)
    (llm_dir / "pricing.yaml").write_text("""
models:
  gpt-4o:
    input_per_million: 2.50
    output_per_million: 10.00
default:
  input_per_million: 5.00
  output_per_million: 15.00
""")
    
    # Create hook directives
    hooks_dir = tmp_path / ".ai" / "directives" / "hooks"
    hooks_dir.mkdir(parents=True)
    
    (hooks_dir / "request_elevated_permissions.md").write_text("""# Request Elevated Permissions

```xml
<directive name="request_elevated_permissions" version="1.0.0">
  <metadata>
    <description>Request elevated permissions</description>
    <category>hooks</category>
    <author>system</author>
    <model tier="fast">Simple interaction</model>
    <limits>
      <turns>5</turns>
      <tokens>5000</tokens>
      <spawns>0</spawns>
      <duration>60</duration>
      <spend currency="USD">0.10</spend>
    </limits>
    <permissions></permissions>
  </metadata>
  <inputs>
    <input name="original_directive" type="string" required="true">Original directive</input>
    <input name="missing_cap" type="string" required="true">Missing capability</input>
  </inputs>
  <process>
    <step name="request">Ask user for permission</step>
  </process>
</directive>
```
""")
    
    return tmp_path


class TestPermissionDeniedTriggersHook:
    """Test that permission denied errors trigger the appropriate hook."""

    @pytest.mark.unit
    def test_permission_denied_matches_hook(self, project_with_hooks):
        hooks = [
            {
                "when": 'event.code == "permission_denied"',
                "directive": "request_elevated_permissions",
                "inputs": {
                    "original_directive": "${directive.name}",
                    "missing_cap": "${event.detail.missing}"
                }
            }
        ]
        
        harness = SafetyHarness(
            project_path=project_with_hooks,
            hooks=hooks,
            directive_name="deploy_staging"
        )
        
        result = harness.checkpoint_on_error(
            "permission_denied",
            {"missing": "fs.write"}
        )
        
        assert result.context is not None
        assert result.context["hook_directive"] == "request_elevated_permissions"
        assert result.context["hook_inputs"]["original_directive"] == "deploy_staging"
        assert result.context["hook_inputs"]["missing_cap"] == "fs.write"


class TestTurnsExceededTriggersHook:
    """Test that turn limit exceeded triggers the appropriate hook."""

    @pytest.mark.unit
    def test_turns_exceeded_at_checkpoint(self, project_with_hooks):
        hooks = [
            {
                "when": 'event.code == "turns_exceeded"',
                "directive": "handle_turns_exceeded",
            }
        ]
        
        harness = SafetyHarness(
            project_path=project_with_hooks,
            hooks=hooks,
            limits={"turns": 10}
        )
        harness.cost.turns = 10
        
        result = harness.checkpoint_before_step("next_step")
        
        assert result.context is not None
        assert result.context["hook_directive"] == "handle_turns_exceeded"


class TestFirstHookWins:
    """Test that only the first matching hook executes."""

    @pytest.mark.unit
    def test_first_matching_hook_executes(self, project_with_hooks):
        hooks = [
            {
                "when": 'event.name == "error"',
                "directive": "generic_error_handler",
            },
            {
                "when": 'event.code == "permission_denied"',
                "directive": "permission_handler",
            }
        ]
        
        harness = SafetyHarness(
            project_path=project_with_hooks,
            hooks=hooks
        )
        
        result = harness.checkpoint_on_error("permission_denied", {})
        
        # First hook matches (event.name == "error")
        assert result.context["hook_directive"] == "generic_error_handler"


class TestNoHookMatchesContinues:
    """Test that execution continues when no hook matches."""

    @pytest.mark.unit
    def test_no_match_returns_continue(self, project_with_hooks):
        hooks = [
            {
                "when": 'event.code == "timeout"',
                "directive": "handle_timeout",
            }
        ]
        
        harness = SafetyHarness(
            project_path=project_with_hooks,
            hooks=hooks
        )
        
        result = harness.checkpoint_on_error("permission_denied", {})
        
        assert result.action == HarnessAction.CONTINUE
        assert result.context is None


class TestTemplateSubstitution:
    """Test that template substitution works correctly."""

    @pytest.mark.unit
    def test_directive_name_substitution(self, project_with_hooks):
        hooks = [
            {
                "when": "true",
                "directive": "test_hook",
                "inputs": {
                    "directive_name": "${directive.name}",
                    "input_value": "${directive.inputs.env}"
                }
            }
        ]
        
        harness = SafetyHarness(
            project_path=project_with_hooks,
            hooks=hooks,
            directive_name="deploy",
            directive_inputs={"env": "production"}
        )
        
        result = harness.evaluate_hooks({"name": "test"})
        
        assert result.context["hook_inputs"]["directive_name"] == "deploy"
        assert result.context["hook_inputs"]["input_value"] == "production"

    @pytest.mark.unit
    def test_event_detail_substitution(self, project_with_hooks):
        hooks = [
            {
                "when": "true",
                "directive": "test_hook",
                "inputs": {
                    "error_code": "${event.code}",
                    "missing": "${event.detail.missing}"
                }
            }
        ]
        
        harness = SafetyHarness(
            project_path=project_with_hooks,
            hooks=hooks
        )
        
        event = {
            "name": "error",
            "code": "permission_denied",
            "detail": {"missing": "fs.write"}
        }
        result = harness.evaluate_hooks(event)
        
        assert result.context["hook_inputs"]["error_code"] == "permission_denied"
        assert result.context["hook_inputs"]["missing"] == "fs.write"


class TestArithmeticExpressions:
    """Test that arithmetic expressions evaluate correctly."""

    @pytest.mark.unit
    def test_percentage_threshold(self, project_with_hooks):
        hooks = [
            {
                "when": "cost.turns >= limits.turns * 0.9",
                "directive": "warn_approaching_limit",
            }
        ]
        
        harness = SafetyHarness(
            project_path=project_with_hooks,
            hooks=hooks,
            limits={"turns": 10}
        )
        
        # At 80% - should not match
        harness.cost.turns = 8
        result = harness.evaluate_hooks({"name": "check"})
        assert result.context is None
        
        # At 90% - should match
        harness.cost.turns = 9
        result = harness.evaluate_hooks({"name": "check"})
        assert result.context["hook_directive"] == "warn_approaching_limit"

    @pytest.mark.unit
    def test_complex_arithmetic(self, project_with_hooks):
        context = {
            "cost": {"tokens": 4500, "spend": 0.08},
            "limits": {"tokens": 5000, "spend": 0.10}
        }
        
        # tokens at 90%
        assert evaluate_expression("cost.tokens >= limits.tokens * 0.9", context) is True
        
        # spend at 80%
        assert evaluate_expression("cost.spend >= limits.spend * 0.9", context) is False


class TestRecursiveHarness:
    """Test that hook directives get their own harness."""

    @pytest.mark.unit
    def test_child_harness_independent(self, project_with_hooks):
        # Parent harness
        parent = SafetyHarness(
            project_path=project_with_hooks,
            limits={"turns": 10, "spawns": 3},
            directive_name="parent_directive"
        )
        parent.cost.turns = 5
        parent.cost.spawns = 1
        
        # Child harness (simulating what would happen when hook directive runs)
        child = SafetyHarness(
            project_path=project_with_hooks,
            limits={"turns": 5, "spawns": 0},  # Hook's own limits
            directive_name="handle_error"
        )
        
        # Child starts fresh
        assert child.cost.turns == 0
        assert child.cost.spawns == 0
        
        # Child has different limits
        assert child.limits["turns"] == 5
        assert parent.limits["turns"] == 10


class TestCostAccumulation:
    """Test end-to-end cost tracking."""

    @pytest.mark.unit
    def test_multi_turn_cost_tracking(self, project_with_hooks):
        harness = SafetyHarness(
            project_path=project_with_hooks,
            limits={"turns": 10, "tokens": 10000, "spend": 1.0}
        )
        
        # Simulate 3 turns
        responses = [
            {"usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}},
            {"usage": {"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300}},
            {"usage": {"prompt_tokens": 150, "completion_tokens": 75, "total_tokens": 225}},
        ]
        
        for response in responses:
            harness.update_cost_after_turn(response, "gpt-4o")
        
        assert harness.cost.turns == 3
        assert harness.cost.tokens == 675  # 150 + 300 + 225
        assert harness.cost.input_tokens == 450  # 100 + 200 + 150
        assert harness.cost.output_tokens == 225  # 50 + 100 + 75
        assert harness.cost.spend > 0


class TestComplexHookConditions:
    """Test complex hook expression conditions."""

    @pytest.mark.unit
    def test_compound_conditions(self, project_with_hooks):
        hooks = [
            {
                "when": 'event.name == "error" and (event.code == "permission_denied" or event.code == "quota_exceeded")',
                "directive": "handle_access_error",
            }
        ]
        
        harness = SafetyHarness(
            project_path=project_with_hooks,
            hooks=hooks
        )
        
        # permission_denied - should match
        result = harness.checkpoint_on_error("permission_denied", {})
        assert result.context["hook_directive"] == "handle_access_error"
        
        # quota_exceeded - should match
        result = harness.checkpoint_on_error("quota_exceeded", {})
        assert result.context["hook_directive"] == "handle_access_error"
        
        # timeout - should not match
        result = harness.checkpoint_on_error("timeout", {})
        assert result.context is None

    @pytest.mark.unit
    def test_membership_conditions(self, project_with_hooks):
        context = {
            "event": {"code": "permission_denied"},
            "permissions": {
                "required": ["fs.read", "fs.write"],
                "granted": ["fs.read"]
            }
        }
        
        assert evaluate_expression('"fs.write" in permissions.required', context) is True
        assert evaluate_expression('"fs.write" not in permissions.granted', context) is True
        assert evaluate_expression('"fs.read" in permissions.granted', context) is True
