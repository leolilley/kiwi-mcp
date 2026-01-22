"""Loop detection for Kiwi Agent Harness.

Detects stuck patterns in tool calls to prevent infinite loops.
"""

import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from collections import deque


@dataclass
class StuckSignal:
    """Signal indicating a stuck pattern was detected."""

    reason: str
    suggestion: str
    pattern_type: str  # "exact_repeat", "alternating", "spiral"
    calls_involved: List[Tuple[str, Dict[str, Any]]]


class LoopDetector:
    """Detects stuck patterns in tool call sequences."""

    def __init__(self, window_size: int = 20, repeat_threshold: int = 3):
        self.window_size = window_size
        self.repeat_threshold = repeat_threshold
        self.call_history: deque = deque(maxlen=window_size)
        self.last_progress_time = time.time()

    def record_call(self, tool_id: str, params: Dict[str, Any]) -> Optional[StuckSignal]:
        """Record a tool call and check for stuck patterns.

        Returns StuckSignal if a stuck pattern is detected.
        """
        call = (tool_id, self._normalize_params(params))
        self.call_history.append((call, time.time()))

        # Check for various stuck patterns
        stuck = (
            self._check_exact_repeat()
            or self._check_alternating_pattern()
            or self._check_spiral_pattern()
        )

        if stuck:
            return stuck

        # Update progress time if this looks like meaningful progress
        if self._is_progress_call(tool_id):
            self.last_progress_time = time.time()

        return None

    def reset(self):
        """Reset the detector state."""
        self.call_history.clear()
        self.last_progress_time = time.time()

    def _normalize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize parameters for comparison, removing timestamps etc."""
        normalized = {}

        for key, value in params.items():
            # Skip time-based parameters that naturally vary
            if key.lower() in ["timestamp", "session_id", "request_id"]:
                continue

            # Normalize file paths
            if key.lower() in ["path", "file_path", "filepath"]:
                normalized[key] = str(value).replace("\\", "/")
            else:
                normalized[key] = value

        return normalized

    def _check_exact_repeat(self) -> Optional[StuckSignal]:
        """Check for exact repeated calls."""
        if len(self.call_history) < self.repeat_threshold:
            return None

        recent_calls = [call for call, _ in list(self.call_history)[-self.repeat_threshold :]]

        if len(set(str(call) for call in recent_calls)) == 1:
            # All recent calls are identical
            tool_id, params = recent_calls[0]
            return StuckSignal(
                reason=f"Tool '{tool_id}' called {self.repeat_threshold} times with identical parameters",
                suggestion=f"Try different parameters or a different approach. Consider using help tool with action='stuck'",
                pattern_type="exact_repeat",
                calls_involved=recent_calls,
            )

        return None

    def _check_alternating_pattern(self) -> Optional[StuckSignal]:
        """Check for A-B-A-B alternating patterns."""
        if len(self.call_history) < 4:
            return None

        recent_calls = [call for call, _ in list(self.call_history)[-4:]]

        # Check if pattern is A-B-A-B
        if (
            recent_calls[0] == recent_calls[2]
            and recent_calls[1] == recent_calls[3]
            and recent_calls[0] != recent_calls[1]
        ):
            return StuckSignal(
                reason="Alternating pattern detected: same two operations repeating",
                suggestion="Break the cycle by trying a different tool or approach",
                pattern_type="alternating",
                calls_involved=recent_calls,
            )

        return None

    def _check_spiral_pattern(self) -> Optional[StuckSignal]:
        """Check for spiral patterns (similar calls with slight variations)."""
        if len(self.call_history) < 4:
            return None

        recent_calls = [call for call, _ in list(self.call_history)[-5:]]

        # Group by tool_id
        tool_groups = {}
        for tool_id, params in recent_calls:
            if tool_id not in tool_groups:
                tool_groups[tool_id] = []
            tool_groups[tool_id].append(params)

        # Check if one tool dominates with similar parameters
        for tool_id, param_list in tool_groups.items():
            if len(param_list) >= 4:  # Same tool called 4+ times recently
                # Check if parameters are similar but not identical
                if self._params_are_similar_but_different(param_list):
                    return StuckSignal(
                        reason=f"Spiral pattern detected: '{tool_id}' called repeatedly with similar parameters",
                        suggestion="Parameters are converging but not making progress. Try a fundamentally different approach",
                        pattern_type="spiral",
                        calls_involved=[(tool_id, params) for params in param_list],
                    )

        return None

        recent_calls = [call for call, _ in list(self.call_history)[-5:]]

        # Group by tool_id
        tool_groups = {}
        for tool_id, params in recent_calls:
            if tool_id not in tool_groups:
                tool_groups[tool_id] = []
            tool_groups[tool_id].append(params)

        # Check if one tool dominates with similar parameters
        for tool_id, param_list in tool_groups.items():
            if len(param_list) >= 4:  # Same tool called 4+ times recently
                # Check if parameters are similar but not identical
                if self._params_are_similar_but_different(param_list):
                    return StuckSignal(
                        reason=f"Spiral pattern detected: '{tool_id}' called repeatedly with similar parameters",
                        suggestion="Parameters are converging but not making progress. Try a fundamentally different approach",
                        pattern_type="spiral",
                        calls_involved=[(tool_id, params) for params in param_list],
                    )

        return None

    def _params_are_similar_but_different(self, param_list: List[Dict[str, Any]]) -> bool:
        """Check if parameters are similar but not identical."""
        if len(param_list) < 2:
            return False

        # Convert to strings for comparison
        param_strings = [str(sorted(params.items())) for params in param_list]

        # All different (not exact repeats)
        if len(set(param_strings)) != len(param_strings):
            return False  # Some are identical

        # But similar structure (same keys)
        key_sets = [set(params.keys()) for params in param_list]
        if len(set(frozenset(keys) for keys in key_sets)) > 1:
            return False  # Different key structures

        return True

    def _is_progress_call(self, tool_id: str) -> bool:
        """Determine if a tool call represents meaningful progress."""
        progress_tools = [
            "write",
            "edit",
            "create",
            "delete",
            "commit",
            "push",
            "install",
            "build",
            "test",
            "deploy",
        ]

        return any(indicator in tool_id.lower() for indicator in progress_tools)
