"""
Output Manager for Kiwi MCP

Manages tool execution outputs:
- Hybrid storage: project space (.ai/outputs/tools/) or user space (~/.ai/outputs/tools/)
- Auto-cleanup: keeps last N outputs per tool
- Size-aware: only saves outputs above threshold
- Response truncation: caps large responses for MCP messages
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from kiwi_mcp.utils.logger import get_logger
from kiwi_mcp.utils.resolvers import get_user_space

logger = get_logger("output_manager")

# Configuration
MIN_SAVE_SIZE_BYTES = 10 * 1024  # 10KB - don't save tiny results
MAX_RESPONSE_SIZE_BYTES = 1_000_000  # 1MB - truncate MCP responses above this
MAX_OUTPUTS_PER_TOOL = 10  # Keep last N outputs per tool
MAX_ARRAY_ITEMS = 500  # Max items in arrays before truncation
MAX_STRING_LENGTH = 5_000  # Max string length before truncation


class OutputManager:
    """Manages tool output storage and cleanup."""

    def __init__(self, project_path: Optional[Path] = None):
        """
        Initialize output manager.

        Args:
            project_path: If provided, prefer project outputs at .ai/outputs/tools/
                         Otherwise, use user outputs at ~/.ai/outputs/tools/
        """
        self.project_path = Path(project_path) if project_path else None
        self.user_space = get_user_space()

        if self.project_path:
            self.project_outputs = self.project_path / ".ai" / "outputs" / "tools"
            self.primary_outputs = self.project_outputs
        else:
            self.project_outputs = None
            self.primary_outputs = self.user_space / "outputs" / "tools"

        self.user_outputs = self.user_space / "outputs" / "tools"

    def save_output(
        self,
        tool_name: str,
        data: Any,
        execution_id: Optional[str] = None,
        force_save: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Save tool output to file if it meets size threshold.

        Args:
            tool_name: Name of the tool
            data: Output data to save
            execution_id: Optional execution ID for filename
            force_save: Save regardless of size

        Returns:
            Dict with file info if saved, None if skipped
        """
        # Serialize to measure size
        try:
            json_data = json.dumps(data, indent=2, default=str)
            size_bytes = len(json_data.encode('utf-8'))
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize output: {e}")
            return None

        # Check size threshold
        if not force_save and size_bytes < MIN_SAVE_SIZE_BYTES:
            logger.info(f"Skipping save for {tool_name}: {size_bytes} bytes < {MIN_SAVE_SIZE_BYTES} threshold")
            return None

        # Determine output directory
        output_dir = self.primary_outputs / tool_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = int(time.time())
        if execution_id:
            filename = f"{timestamp}_{execution_id[:8]}_results.json"
        else:
            filename = f"{timestamp}_results.json"

        output_path = output_dir / filename

        # Write file
        try:
            output_path.write_text(json_data, encoding='utf-8')
            logger.info(f"Saved output to {output_path} ({size_bytes:,} bytes)")

            # Run cleanup after save
            self._cleanup_old_outputs(tool_name)

            return {
                "path": str(output_path),
                "size_bytes": size_bytes,
                "timestamp": timestamp,
                "tool_name": tool_name
            }
        except Exception as e:
            logger.error(f"Failed to save output: {e}")
            return None

    def _cleanup_old_outputs(self, tool_name: str) -> int:
        """
        Remove old outputs, keeping only the last N.

        Args:
            tool_name: Name of the tool

        Returns:
            Number of files removed
        """
        output_dir = self.primary_outputs / tool_name
        if not output_dir.exists():
            return 0

        # Get all result files sorted by modification time (newest first)
        result_files = sorted(
            output_dir.glob("*_results.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        # Remove files beyond the limit
        removed = 0
        for old_file in result_files[MAX_OUTPUTS_PER_TOOL:]:
            try:
                old_file.unlink()
                removed += 1
                logger.info(f"Cleaned up old output: {old_file.name}")
            except Exception as e:
                logger.warning(f"Failed to remove {old_file}: {e}")

        return removed

    def list_outputs(self, tool_name: str) -> List[Dict[str, Any]]:
        """
        List all outputs for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            List of output info dicts, newest first
        """
        outputs = []

        # Check project outputs
        if self.project_outputs:
            outputs.extend(self._list_dir_outputs(self.project_outputs / tool_name, "project"))

        # Check user outputs
        outputs.extend(self._list_dir_outputs(self.user_outputs / tool_name, "user"))

        # Sort by timestamp (newest first)
        outputs.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return outputs

    def _list_dir_outputs(self, output_dir: Path, location: str) -> List[Dict[str, Any]]:
        """List outputs in a directory."""
        if not output_dir.exists():
            return []

        outputs = []
        for file_path in output_dir.glob("*_results.json"):
            try:
                stat = file_path.stat()
                outputs.append({
                    "path": str(file_path),
                    "filename": file_path.name,
                    "size_bytes": stat.st_size,
                    "timestamp": int(stat.st_mtime),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "location": location
                })
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")

        return outputs

    def get_latest_output(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent output for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Output info dict with 'data' key containing parsed content
        """
        outputs = self.list_outputs(tool_name)
        if not outputs:
            return None

        latest = outputs[0]
        try:
            data = json.loads(Path(latest["path"]).read_text())
            latest["data"] = data
            return latest
        except Exception as e:
            logger.warning(f"Failed to read output: {e}")
            return latest

    def cleanup_all(self, tool_name: Optional[str] = None) -> Dict[str, int]:
        """
        Clean up outputs, keeping only last N per tool.

        Args:
            tool_name: If provided, only clean this tool. Otherwise clean all.

        Returns:
            Dict mapping tool names to number of files removed
        """
        results = {}
        
        if tool_name:
            removed = self._cleanup_old_outputs(tool_name)
            if removed > 0:
                results[tool_name] = removed
        else:
            # Clean all scripts
            for output_dir in [self.project_outputs, self.user_outputs]:
                if output_dir and output_dir.exists():
                    for script_dir in output_dir.iterdir():
                        if script_dir.is_dir():
                            removed = self._cleanup_script_dir(script_dir)
                            if removed > 0:
                                results[script_dir.name] = results.get(script_dir.name, 0) + removed

        return results

    def _cleanup_script_dir(self, script_dir: Path) -> int:
        """Clean up a specific script directory."""
        result_files = sorted(
            script_dir.glob("*_results.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        removed = 0
        for old_file in result_files[MAX_OUTPUTS_PER_TOOL:]:
            try:
                old_file.unlink()
                removed += 1
            except Exception:
                pass

        return removed


def truncate_for_response(
    data: Any,
    max_size: int = MAX_RESPONSE_SIZE_BYTES,
    max_array_items: int = MAX_ARRAY_ITEMS,
    max_string_length: int = MAX_STRING_LENGTH
) -> Tuple[Any, Dict[str, Any]]:
    """
    Truncate data to fit within MCP response limits.

    Args:
        data: Data to truncate
        max_size: Maximum size in bytes
        max_array_items: Maximum items in arrays
        max_string_length: Maximum string length

    Returns:
        Tuple of (truncated_data, truncation_info)
    """
    truncation_info = {}

    def _truncate_value(value: Any, path: str = "") -> Any:
        if isinstance(value, dict):
            return {k: _truncate_value(v, f"{path}.{k}" if path else k) for k, v in value.items()}

        elif isinstance(value, list):
            if len(value) > max_array_items:
                truncation_info[path or "root"] = {
                    "type": "array",
                    "original_count": len(value),
                    "truncated_to": max_array_items,
                    "message": f"Array truncated from {len(value)} to {max_array_items} items"
                }
                return [_truncate_value(item, f"{path}[{i}]") for i, item in enumerate(value[:max_array_items])]
            else:
                return [_truncate_value(item, f"{path}[{i}]") for i, item in enumerate(value)]

        elif isinstance(value, str):
            if len(value) > max_string_length:
                truncation_info[path or "root"] = {
                    "type": "string",
                    "original_length": len(value),
                    "truncated_to": max_string_length,
                    "message": f"String truncated from {len(value)} to {max_string_length} characters"
                }
                return value[:max_string_length] + f"... (truncated {len(value) - max_string_length} chars)"

        return value

    truncated = _truncate_value(data)

    # Check final size
    try:
        final_json = json.dumps(truncated, default=str)
        final_size = len(final_json.encode('utf-8'))
        if final_size > max_size:
            # Still too big - create summary instead
            truncation_info["_final_size_exceeded"] = {
                "size_bytes": final_size,
                "max_bytes": max_size,
                "message": "Result still too large after truncation, returning summary only"
            }
            return _create_summary(data), truncation_info
    except Exception:
        pass

    return truncated, truncation_info


def _create_summary(data: Any, max_depth: int = 2, current_depth: int = 0) -> Dict[str, Any]:
    """Create a summary of large data structures."""
    if current_depth >= max_depth:
        return {"_type": type(data).__name__, "_summary": "..."}

    if isinstance(data, dict):
        summary = {}
        items = list(data.items())[:10]
        for key, value in items:
            if isinstance(value, (dict, list)):
                summary[key] = _create_summary(value, max_depth, current_depth + 1)
            elif isinstance(value, str):
                summary[key] = value[:100] + "..." if len(value) > 100 else value
            else:
                summary[key] = value
        if len(data) > 10:
            summary["_more_keys"] = len(data) - 10
        return summary

    elif isinstance(data, list):
        if len(data) == 0:
            return []
        summary = []
        for item in data[:5]:
            if isinstance(item, (dict, list)):
                summary.append(_create_summary(item, max_depth, current_depth + 1))
            elif isinstance(item, str):
                summary.append(item[:100] + "..." if len(item) > 100 else item)
            else:
                summary.append(item)
        if len(data) > 5:
            summary.append(f"... and {len(data) - 5} more items")
        return summary

    elif isinstance(data, str):
        return data[:200] + "..." if len(data) > 200 else data

    return data
