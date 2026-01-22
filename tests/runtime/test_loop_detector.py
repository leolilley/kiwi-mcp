"""Tests for loop detection."""

import pytest
from kiwi_mcp.runtime.loop_detector import LoopDetector, StuckSignal


class TestLoopDetector:
    """Test LoopDetector functionality."""

    def test_no_stuck_pattern_initially(self):
        """Test that no stuck pattern is detected initially."""
        detector = LoopDetector(repeat_threshold=3)

        result = detector.record_call("tool1", {"param": "value"})
        assert result is None

    def test_exact_repeat_detection(self):
        """Test detection of exact repeated calls."""
        detector = LoopDetector(repeat_threshold=3)

        # Call same tool with same params 3 times
        params = {"param": "value"}
        detector.record_call("tool1", params)
        detector.record_call("tool1", params)
        result = detector.record_call("tool1", params)

        assert result is not None
        assert result.pattern_type == "exact_repeat"
        assert "tool1" in result.reason
        assert "3 times" in result.reason
        assert "different parameters" in result.suggestion

    def test_alternating_pattern_detection(self):
        """Test detection of A-B-A-B alternating patterns."""
        detector = LoopDetector()

        # Create A-B-A-B pattern
        detector.record_call("tool1", {"param": "a"})
        detector.record_call("tool2", {"param": "b"})
        detector.record_call("tool1", {"param": "a"})
        result = detector.record_call("tool2", {"param": "b"})

        assert result is not None
        assert result.pattern_type == "alternating"
        assert "Alternating pattern" in result.reason
        assert "Break the cycle" in result.suggestion

    def test_spiral_pattern_detection(self):
        """Test detection of spiral patterns (similar but different calls)."""
        detector = LoopDetector()

        # Call same tool with similar but different parameters
        detector.record_call("search", {"query": "test1"})
        detector.record_call("search", {"query": "test2"})
        detector.record_call("search", {"query": "test3"})
        result = detector.record_call("search", {"query": "test4"})

        assert result is not None
        assert result.pattern_type == "spiral"
        assert "Spiral pattern" in result.reason
        assert "fundamentally different approach" in result.suggestion

    def test_parameter_normalization(self):
        """Test parameter normalization for comparison."""
        detector = LoopDetector(repeat_threshold=2)

        # These should be considered the same after normalization
        params1 = {"path": "src/file.py", "timestamp": "2023-01-01"}
        params2 = {
            "path": "src\\file.py",
            "timestamp": "2023-01-02",
        }  # Different timestamp, different path separator

        detector.record_call("tool1", params1)
        result = detector.record_call("tool1", params2)

        # Should detect as repeat because timestamp is ignored and path is normalized
        assert result is not None
        assert result.pattern_type == "exact_repeat"

    def test_reset_detector(self):
        """Test resetting the detector state."""
        detector = LoopDetector(repeat_threshold=2)

        # Build up some history
        detector.record_call("tool1", {"param": "value"})
        detector.record_call("tool1", {"param": "value"})

        # Reset
        detector.reset()

        # Should not detect pattern after reset
        result = detector.record_call("tool1", {"param": "value"})
        assert result is None

    def test_window_size_limit(self):
        """Test that detector respects window size limit."""
        detector = LoopDetector(window_size=3, repeat_threshold=2)

        # Fill window beyond capacity
        detector.record_call("tool1", {"param": "1"})
        detector.record_call("tool2", {"param": "2"})
        detector.record_call("tool3", {"param": "3"})
        detector.record_call("tool4", {"param": "4"})  # Should push out tool1

        # Now calling tool1 again shouldn't trigger repeat detection
        # because it was pushed out of the window
        result = detector.record_call("tool1", {"param": "1"})
        assert result is None

    def test_progress_call_detection(self):
        """Test detection of progress-making calls."""
        detector = LoopDetector()

        # Progress calls should be recognized
        assert detector._is_progress_call("write_file")
        assert detector._is_progress_call("create_document")
        assert detector._is_progress_call("git_commit")
        assert detector._is_progress_call("deploy_app")

        # Non-progress calls
        assert not detector._is_progress_call("read_file")
        assert not detector._is_progress_call("search_data")
        assert not detector._is_progress_call("get_status")

    def test_similar_but_different_params(self):
        """Test detection of similar but different parameters."""
        detector = LoopDetector()

        # Same structure, different values
        params_list = [
            {"query": "test1", "limit": 10},
            {"query": "test2", "limit": 10},
            {"query": "test3", "limit": 10},
            {"query": "test4", "limit": 10},
        ]

        assert detector._params_are_similar_but_different(params_list)

        # Identical parameters
        identical_params = [{"query": "test", "limit": 10}, {"query": "test", "limit": 10}]

        assert not detector._params_are_similar_but_different(identical_params)

        # Different structures
        different_structure = [{"query": "test"}, {"search": "test", "limit": 10}]

        assert not detector._params_are_similar_but_different(different_structure)

    def test_no_false_positives_with_different_tools(self):
        """Test that different tools don't trigger false positives."""
        detector = LoopDetector(repeat_threshold=2)

        # Different tools with same parameters shouldn't trigger repeat detection
        params = {"param": "value"}
        detector.record_call("tool1", params)
        result = detector.record_call("tool2", params)

        assert result is None

    def test_alternating_requires_four_calls(self):
        """Test that alternating pattern requires at least 4 calls."""
        detector = LoopDetector()

        # Only 3 calls - shouldn't detect alternating
        detector.record_call("tool1", {"param": "a"})
        detector.record_call("tool2", {"param": "b"})
        result = detector.record_call("tool1", {"param": "a"})

        assert result is None

    def test_spiral_requires_four_calls(self):
        """Test that spiral pattern requires at least 4 calls of same tool."""
        detector = LoopDetector()

        # Only 3 calls - shouldn't detect spiral yet
        detector.record_call("search", {"query": "test1"})
        detector.record_call("search", {"query": "test2"})
        result = detector.record_call("search", {"query": "test3"})
        assert result is None

        # Should detect spiral on 4th call of same tool
        result = detector.record_call("search", {"query": "test4"})
        assert result is not None
        assert result.pattern_type == "spiral"
