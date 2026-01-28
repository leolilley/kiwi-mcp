"""Tests for the expression evaluator."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".ai" / "tools" / "threads"))

from expression_evaluator import (
    evaluate_expression,
    substitute_templates,
    resolve_path,
    tokenize,
    Parser,
    ExpressionError,
)


class TestTokenizer:
    """Test tokenization of expressions."""

    @pytest.mark.unit
    def test_tokenize_simple_comparison(self):
        tokens = tokenize('event.code == "permission_denied"')
        assert len(tokens) == 5
        assert tokens[0] == ("IDENT", "event")
        assert tokens[1] == ("DOT", ".")
        assert tokens[2] == ("IDENT", "code")
        assert tokens[3] == ("OP_COMP", "==")
        assert tokens[4] == ("STRING", '"permission_denied"')

    @pytest.mark.unit
    def test_tokenize_arithmetic(self):
        tokens = tokenize("cost.turns > limits.turns * 0.9")
        assert ("OP_ARITH", "*") in tokens
        assert ("NUMBER", "0.9") in tokens

    @pytest.mark.unit
    def test_tokenize_logical(self):
        tokens = tokenize("a and b or not c")
        assert ("OP_LOGIC", "and") in tokens
        assert ("OP_LOGIC", "or") in tokens
        assert ("OP_LOGIC", "not") in tokens

    @pytest.mark.unit
    def test_tokenize_membership(self):
        tokens = tokenize('"fs.write" in permissions.required')
        token_values = [t[1] for t in tokens]
        assert "in" in token_values


class TestParser:
    """Test parsing expressions to AST."""

    @pytest.mark.unit
    def test_parse_simple_comparison(self):
        tokens = tokenize("a == 1")
        parser = Parser(tokens)
        ast = parser.parse()
        assert ast[0] == "=="
        assert ast[1] == ("path", ["a"])
        assert ast[2] == ("literal", 1)

    @pytest.mark.unit
    def test_parse_path(self):
        tokens = tokenize("event.detail.missing")
        parser = Parser(tokens)
        ast = parser.parse()
        assert ast == ("path", ["event", "detail", "missing"])

    @pytest.mark.unit
    def test_parse_parentheses(self):
        tokens = tokenize("(a or b) and c")
        parser = Parser(tokens)
        ast = parser.parse()
        assert ast[0] == "and"

    @pytest.mark.unit
    def test_parse_not(self):
        tokens = tokenize("not active")
        parser = Parser(tokens)
        ast = parser.parse()
        assert ast[0] == "not"


class TestResolvePath:
    """Test path resolution in context."""

    @pytest.mark.unit
    def test_resolve_simple(self):
        context = {"event": {"code": "error"}}
        assert resolve_path(["event", "code"], context) == "error"

    @pytest.mark.unit
    def test_resolve_nested(self):
        context = {"event": {"detail": {"missing": "fs.write"}}}
        assert resolve_path(["event", "detail", "missing"], context) == "fs.write"

    @pytest.mark.unit
    def test_resolve_missing_returns_none(self):
        context = {"event": {"code": "error"}}
        assert resolve_path(["event", "nonexistent"], context) is None

    @pytest.mark.unit
    def test_resolve_top_level(self):
        context = {"name": "test"}
        assert resolve_path(["name"], context) == "test"


class TestEvaluateExpression:
    """Test full expression evaluation."""

    @pytest.mark.unit
    def test_string_equality(self):
        context = {"event": {"code": "permission_denied"}}
        assert evaluate_expression('event.code == "permission_denied"', context) is True
        assert evaluate_expression('event.code == "other"', context) is False

    @pytest.mark.unit
    def test_numeric_comparison(self):
        context = {"cost": {"turns": 5}, "limits": {"turns": 10}}
        assert evaluate_expression("cost.turns > limits.turns", context) is False
        assert evaluate_expression("cost.turns < limits.turns", context) is True
        assert evaluate_expression("cost.turns <= 5", context) is True

    @pytest.mark.unit
    def test_arithmetic(self):
        context = {"cost": {"turns": 9}, "limits": {"turns": 10}}
        assert evaluate_expression("cost.turns > limits.turns * 0.9", context) is False
        context["cost"]["turns"] = 10
        assert evaluate_expression("cost.turns > limits.turns * 0.9", context) is True

    @pytest.mark.unit
    def test_logical_and(self):
        context = {"event": {"name": "error", "code": "timeout"}}
        assert evaluate_expression('event.name == "error" and event.code == "timeout"', context) is True
        assert evaluate_expression('event.name == "error" and event.code == "other"', context) is False

    @pytest.mark.unit
    def test_logical_or(self):
        context = {"event": {"code": "timeout"}}
        assert evaluate_expression('event.code == "timeout" or event.code == "rate_limit"', context) is True
        assert evaluate_expression('event.code == "network" or event.code == "rate_limit"', context) is False

    @pytest.mark.unit
    def test_logical_not(self):
        context = {"active": False}
        assert evaluate_expression("not active", context) is True
        context["active"] = True
        assert evaluate_expression("not active", context) is False

    @pytest.mark.unit
    def test_membership_in(self):
        context = {"permissions": {"required": ["fs.read", "fs.write"]}}
        assert evaluate_expression('"fs.write" in permissions.required', context) is True
        assert evaluate_expression('"fs.delete" in permissions.required', context) is False

    @pytest.mark.unit
    def test_membership_not_in(self):
        context = {"permissions": {"granted": ["fs.read"]}}
        assert evaluate_expression('"fs.write" not in permissions.granted', context) is True
        assert evaluate_expression('"fs.read" not in permissions.granted', context) is False

    @pytest.mark.unit
    def test_complex_expression(self):
        context = {
            "event": {"name": "error", "code": "permission_denied"},
            "cost": {"turns": 5},
            "limits": {"turns": 10}
        }
        expr = 'event.name == "error" and (event.code == "permission_denied" or event.code == "quota_exceeded")'
        assert evaluate_expression(expr, context) is True

    @pytest.mark.unit
    def test_boolean_literals(self):
        context = {}
        assert evaluate_expression("true", context) is True
        assert evaluate_expression("false", context) is False

    @pytest.mark.unit
    def test_null_literal(self):
        context = {"value": None}
        assert evaluate_expression("value == null", context) is True

    @pytest.mark.unit
    def test_missing_path_is_none(self):
        context = {}
        assert evaluate_expression("missing == null", context) is True


class TestSubstituteTemplates:
    """Test template substitution."""

    @pytest.mark.unit
    def test_substitute_simple(self):
        context = {"directive": {"name": "deploy_staging"}}
        result = substitute_templates("${directive.name}", context)
        assert result == "deploy_staging"

    @pytest.mark.unit
    def test_substitute_in_dict(self):
        context = {"directive": {"name": "deploy"}, "event": {"detail": {"missing": "fs.write"}}}
        obj = {
            "original_directive": "${directive.name}",
            "missing_cap": "${event.detail.missing}"
        }
        result = substitute_templates(obj, context)
        assert result["original_directive"] == "deploy"
        assert result["missing_cap"] == "fs.write"

    @pytest.mark.unit
    def test_substitute_missing_leaves_template(self):
        context = {}
        result = substitute_templates("${missing.path}", context)
        assert result == "${missing.path}"

    @pytest.mark.unit
    def test_substitute_in_list(self):
        context = {"name": "test"}
        obj = ["${name}", "static"]
        result = substitute_templates(obj, context)
        assert result == ["test", "static"]

    @pytest.mark.unit
    def test_substitute_nested(self):
        context = {"a": "x", "b": "y"}
        obj = {"outer": {"inner": "${a}"}, "list": ["${b}"]}
        result = substitute_templates(obj, context)
        assert result["outer"]["inner"] == "x"
        assert result["list"][0] == "y"

    @pytest.mark.unit
    def test_substitute_non_string_passthrough(self):
        context = {}
        assert substitute_templates(123, context) == 123
        assert substitute_templates(True, context) is True
        assert substitute_templates(None, context) is None


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.unit
    def test_empty_expression_raises(self):
        with pytest.raises(ExpressionError):
            evaluate_expression("", {})

    @pytest.mark.unit
    def test_division_by_zero(self):
        context = {"a": 10, "b": 0}
        result = evaluate_expression("a / b", context)
        assert result == 0

    @pytest.mark.unit
    def test_comparison_with_none(self):
        context = {"value": None}
        assert evaluate_expression("value < 10", context) is False
        assert evaluate_expression("value > 10", context) is False

    @pytest.mark.unit
    def test_arithmetic_with_none(self):
        context = {"a": None, "b": 5}
        # Note: evaluate_expression returns bool, so 5 becomes True
        # This is expected - expressions are for conditions, not calculations
        result = evaluate_expression("a + b", context)
        assert result is True  # 5 is truthy
