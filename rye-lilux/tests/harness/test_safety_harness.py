"""Tests for the Safety Harness."""

import pytest
import sys
import time
import importlib.util
from pathlib import Path
from unittest.mock import patch

# Load safety_harness from rye/.ai/tools/core/threads or .ai/tools/threads
_repo = Path(__file__).resolve().parent.parent.parent
_harness_path = _repo / "rye" / ".ai" / "tools" / "core" / "threads" / "safety_harness.py"
if not _harness_path.exists():
    _harness_path = _repo / ".ai" / "tools" / "threads" / "safety_harness.py"
if not _harness_path.exists():
    pytest.skip("No rye/.ai or .ai/tools/threads/safety_harness.py", allow_module_level=True)
_spec = importlib.util.spec_from_file_location("thread_safety_harness", _harness_path)
_harness_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_harness_module)

SafetyHarness = _harness_module.SafetyHarness
HarnessAction = _harness_module.HarnessAction
HarnessResult = _harness_module.HarnessResult
CostTracker = _harness_module.CostTracker


@pytest.fixture
def project_path(tmp_path):
    """Create a temporary project with pricing config."""
    ai_dir = tmp_path / ".ai" / "tools" / "llm"
    ai_dir.mkdir(parents=True)
    
    pricing_yaml = ai_dir / "pricing.yaml"
    pricing_yaml.write_text("""
models:
  gpt-4o:
    input_per_million: 2.50
    output_per_million: 10.00
  gpt-4o-mini:
    input_per_million: 0.15
    output_per_million: 0.60
  claude-sonnet-4-20250514:
    input_per_million: 3.00
    output_per_million: 15.00

default:
  input_per_million: 5.00
  output_per_million: 15.00
""")
    
    return tmp_path


class TestCostTracker:
    """Test the CostTracker dataclass."""

    @pytest.mark.unit
    def test_initial_values(self):
        tracker = CostTracker()
        assert tracker.turns == 0
        assert tracker.tokens == 0
        assert tracker.spawns == 0
        assert tracker.spend == 0.0

    @pytest.mark.unit
    def test_duration_tracking(self):
        tracker = CostTracker()
        time.sleep(0.01)
        assert tracker.duration_seconds > 0

    @pytest.mark.unit
    def test_to_dict(self):
        tracker = CostTracker()
        tracker.turns = 5
        tracker.tokens = 1000
        d = tracker.to_dict()
        assert d["turns"] == 5
        assert d["tokens"] == 1000
        assert "duration_seconds" in d


class TestSafetyHarnessInit:
    """Test SafetyHarness initialization."""

    @pytest.mark.unit
    def test_init_with_defaults(self, project_path):
        harness = SafetyHarness(project_path=project_path)
        assert harness.limits == {}
        assert harness.hooks == []
        assert harness.cost.turns == 0

    @pytest.mark.unit
    def test_init_with_limits(self, project_path):
        limits = {"turns": 10, "tokens": 5000}
        harness = SafetyHarness(project_path=project_path, limits=limits)
        assert harness.limits["turns"] == 10
        assert harness.limits["tokens"] == 5000


class TestUsageExtraction:
    """Test LLM usage extraction."""

    @pytest.mark.unit
    def test_extract_openai_format(self, project_path):
        harness = SafetyHarness(project_path=project_path)
        response = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            }
        }
        usage = harness._extract_usage(response)
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50
        assert usage["total_tokens"] == 150
        assert usage["estimated"] is False

    @pytest.mark.unit
    def test_extract_anthropic_format(self, project_path):
        harness = SafetyHarness(project_path=project_path)
        response = {
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            }
        }
        usage = harness._extract_usage(response)
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50
        assert usage["total_tokens"] == 150
        assert usage["estimated"] is False

    @pytest.mark.unit
    def test_extract_missing_usage_estimates(self, project_path):
        harness = SafetyHarness(project_path=project_path)
        response = {"content": "Hello world!"}  # 12 chars ≈ 3 tokens
        usage = harness._extract_usage(response)
        assert usage["estimated"] is True
        assert usage["output_tokens"] == 3


class TestSpendCalculation:
    """Test spend calculation."""

    @pytest.mark.unit
    def test_calculate_spend_known_model(self, project_path):
        harness = SafetyHarness(project_path=project_path)
        usage = {"input_tokens": 1000, "output_tokens": 500}
        spend = harness._calculate_spend(usage, "gpt-4o")
        # 1000/1M * 2.50 + 500/1M * 10.00 = 0.0025 + 0.005 = 0.0075
        assert abs(spend - 0.0075) < 0.0001

    @pytest.mark.unit
    def test_calculate_spend_unknown_model_uses_default(self, project_path):
        harness = SafetyHarness(project_path=project_path)
        usage = {"input_tokens": 1000, "output_tokens": 500}
        spend = harness._calculate_spend(usage, "unknown-model-xyz")
        # Default: 5.00 input, 15.00 output
        # 1000/1M * 5.00 + 500/1M * 15.00 = 0.005 + 0.0075 = 0.0125
        assert abs(spend - 0.0125) < 0.0001


class TestCostTracking:
    """Test cost accumulation."""

    @pytest.mark.unit
    def test_update_cost_after_turn(self, project_path):
        harness = SafetyHarness(project_path=project_path)
        response = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            }
        }
        harness.update_cost_after_turn(response, "gpt-4o")
        
        assert harness.cost.turns == 1
        assert harness.cost.tokens == 150
        assert harness.cost.input_tokens == 100
        assert harness.cost.output_tokens == 50
        assert harness.cost.spend > 0

    @pytest.mark.unit
    def test_cost_accumulates(self, project_path):
        harness = SafetyHarness(project_path=project_path)
        response = {"usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}}
        
        harness.update_cost_after_turn(response, "gpt-4o")
        harness.update_cost_after_turn(response, "gpt-4o")
        
        assert harness.cost.turns == 2
        assert harness.cost.tokens == 300

    @pytest.mark.unit
    def test_increment_spawn_count(self, project_path):
        harness = SafetyHarness(project_path=project_path)
        assert harness.cost.spawns == 0
        harness.increment_spawn_count()
        assert harness.cost.spawns == 1


class TestLimitEnforcement:
    """Test limit checking."""

    @pytest.mark.unit
    def test_check_limits_none_when_under(self, project_path):
        harness = SafetyHarness(
            project_path=project_path,
            limits={"turns": 10, "tokens": 5000}
        )
        harness.cost.turns = 5
        harness.cost.tokens = 2000
        
        assert harness.check_limits() is None

    @pytest.mark.unit
    def test_check_limits_turns_exceeded(self, project_path):
        harness = SafetyHarness(
            project_path=project_path,
            limits={"turns": 10}
        )
        harness.cost.turns = 10
        
        event = harness.check_limits()
        assert event is not None
        assert event["code"] == "turns_exceeded"
        assert event["current"] == 10
        assert event["max"] == 10

    @pytest.mark.unit
    def test_check_limits_tokens_exceeded(self, project_path):
        harness = SafetyHarness(
            project_path=project_path,
            limits={"tokens": 5000}
        )
        harness.cost.tokens = 5500
        
        event = harness.check_limits()
        assert event["code"] == "tokens_exceeded"

    @pytest.mark.unit
    def test_check_limits_spawns_exceeded(self, project_path):
        harness = SafetyHarness(
            project_path=project_path,
            limits={"spawns": 3}
        )
        harness.cost.spawns = 3
        
        event = harness.check_limits()
        assert event["code"] == "spawns_exceeded"


class TestContextBuilding:
    """Test context building for hook evaluation."""

    @pytest.mark.unit
    def test_build_context(self, project_path):
        harness = SafetyHarness(
            project_path=project_path,
            limits={"turns": 10},
            directive_name="deploy_staging",
            directive_inputs={"env": "staging"}
        )
        harness.cost.turns = 5
        
        event = {"name": "error", "code": "permission_denied"}
        context = harness.build_context(event)
        
        assert context["event"] == event
        assert context["directive"]["name"] == "deploy_staging"
        assert context["directive"]["inputs"]["env"] == "staging"
        assert context["cost"]["turns"] == 5
        assert context["limits"]["turns"] == 10


class TestHookEvaluation:
    """Test hook matching and evaluation."""

    @pytest.mark.unit
    def test_no_hooks_returns_continue(self, project_path):
        harness = SafetyHarness(project_path=project_path, hooks=[])
        event = {"name": "error", "code": "permission_denied"}
        result = harness.evaluate_hooks(event)
        assert result.action == HarnessAction.CONTINUE

    @pytest.mark.unit
    def test_matching_hook_returns_hook_context(self, project_path):
        hooks = [
            {
                "when": 'event.code == "permission_denied"',
                "directive": "request_elevated_permissions",
                "inputs": {"original_directive": "${directive.name}"}
            }
        ]
        harness = SafetyHarness(
            project_path=project_path,
            hooks=hooks,
            directive_name="deploy_staging"
        )
        
        event = {"name": "error", "code": "permission_denied"}
        result = harness.evaluate_hooks(event)
        
        assert result.context is not None
        assert result.context["hook_directive"] == "request_elevated_permissions"
        assert result.context["hook_inputs"]["original_directive"] == "deploy_staging"

    @pytest.mark.unit
    def test_first_matching_hook_wins(self, project_path):
        hooks = [
            {
                "when": 'event.code == "permission_denied"',
                "directive": "first_handler",
            },
            {
                "when": 'event.code == "permission_denied"',
                "directive": "second_handler",
            }
        ]
        harness = SafetyHarness(project_path=project_path, hooks=hooks)
        
        event = {"name": "error", "code": "permission_denied"}
        result = harness.evaluate_hooks(event)
        
        assert result.context["hook_directive"] == "first_handler"

    @pytest.mark.unit
    def test_no_matching_hook_continues(self, project_path):
        hooks = [
            {
                "when": 'event.code == "timeout"',
                "directive": "handle_timeout",
            }
        ]
        harness = SafetyHarness(project_path=project_path, hooks=hooks)
        
        event = {"name": "error", "code": "permission_denied"}
        result = harness.evaluate_hooks(event)
        
        assert result.action == HarnessAction.CONTINUE
        assert result.context is None

    @pytest.mark.unit
    def test_cost_based_hook(self, project_path):
        hooks = [
            {
                "when": "cost.turns >= limits.turns * 0.9",
                "directive": "warn_approaching_limit",
            }
        ]
        harness = SafetyHarness(
            project_path=project_path,
            hooks=hooks,
            limits={"turns": 10}
        )
        harness.cost.turns = 9  # 9 >= 10 * 0.9 = 9 >= 9 = True
        
        event = {"name": "after_step", "step": "deploy"}
        result = harness.evaluate_hooks(event)
        
        assert result.context is not None
        assert result.context["hook_directive"] == "warn_approaching_limit"


class TestCheckpoints:
    """Test checkpoint methods."""

    @pytest.mark.unit
    def test_checkpoint_before_step(self, project_path):
        harness = SafetyHarness(project_path=project_path)
        result = harness.checkpoint_before_step("deploy")
        assert result.action == HarnessAction.CONTINUE

    @pytest.mark.unit
    def test_checkpoint_before_step_checks_limits_first(self, project_path):
        hooks = [
            {
                "when": 'event.code == "turns_exceeded"',
                "directive": "handle_turns_exceeded",
            }
        ]
        harness = SafetyHarness(
            project_path=project_path,
            hooks=hooks,
            limits={"turns": 10}
        )
        harness.cost.turns = 10
        
        result = harness.checkpoint_before_step("deploy")
        assert result.context["hook_directive"] == "handle_turns_exceeded"

    @pytest.mark.unit
    def test_checkpoint_after_step(self, project_path):
        harness = SafetyHarness(project_path=project_path)
        result = harness.checkpoint_after_step("deploy", {"status": "success"})
        assert result.action == HarnessAction.CONTINUE

    @pytest.mark.unit
    def test_checkpoint_on_error(self, project_path):
        hooks = [
            {
                "when": 'event.code == "permission_denied"',
                "directive": "request_elevated_permissions",
            }
        ]
        harness = SafetyHarness(project_path=project_path, hooks=hooks)
        
        result = harness.checkpoint_on_error(
            "permission_denied",
            {"missing": "fs.write"}
        )
        assert result.context["hook_directive"] == "request_elevated_permissions"


class TestStatus:
    """Test status reporting."""

    @pytest.mark.unit
    def test_get_status(self, project_path):
        harness = SafetyHarness(
            project_path=project_path,
            limits={"turns": 10},
            hooks=[{"when": "true", "directive": "test"}],
            directive_name="test_directive"
        )
        harness.cost.turns = 5
        
        status = harness.get_status()
        assert status["directive"] == "test_directive"
        assert status["cost"]["turns"] == 5
        assert status["limits"]["turns"] == 10
        assert status["hooks_count"] == 1
