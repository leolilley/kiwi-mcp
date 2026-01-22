"""Python tool executor - extracted from ScriptHandler."""

import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List

from .base import ToolExecutor, ExecutionResult
from ..manifest import ToolManifest
from kiwi_mcp.utils.env_manager import EnvManager
from kiwi_mcp.utils.resolvers import get_user_space
from kiwi_mcp.utils.parsers import parse_script_metadata
from kiwi_mcp.utils.logger import get_logger


class PythonExecutor(ToolExecutor):
    """Executor for Python tools/scripts."""

    def __init__(self, project_path: Path):
        """Initialize with project path."""
        self.project_path = project_path
        self.logger = get_logger("python_executor")
        # Note: env_manager will be set dynamically based on script location
        self.env_manager = None

    def can_execute(self, manifest: ToolManifest) -> bool:
        """Check if this executor can handle Python tools."""
        return manifest.tool_type == "python"

    async def execute(self, manifest: ToolManifest, params: dict) -> ExecutionResult:
        """Execute Python tool/script."""
        start_time = time.time()

        try:
            # For legacy scripts, we need to find the actual file
            # For true tools, the path would be in executor_config
            script_path = self._resolve_script_path(manifest)
            if not script_path:
                return ExecutionResult(
                    success=False,
                    error=f"Could not find Python file for tool '{manifest.tool_id}'",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # Setup environment manager based on script location
            self._setup_env_manager(script_path)

            # Handle dependencies
            await self._handle_dependencies(script_path, manifest)

            # Build execution context
            search_paths = self._build_search_paths(script_path)

            # Extract execution parameters
            timeout = params.pop("_timeout", 300)  # 5 min default

            # Execute the script
            result_data = self._execute_subprocess(
                script_path=script_path, params=params, search_paths=search_paths, timeout=timeout
            )

            duration = (time.time() - start_time) * 1000

            # Convert script result to ExecutionResult format
            if isinstance(result_data, dict) and result_data.get("status") == "success":
                return ExecutionResult(
                    success=True, output=json.dumps(result_data, indent=2), duration_ms=duration
                )
            else:
                error_msg = (
                    result_data.get("error", "Unknown execution error")
                    if isinstance(result_data, dict)
                    else str(result_data)
                )
                return ExecutionResult(
                    success=False,
                    output=json.dumps(result_data, indent=2)
                    if isinstance(result_data, dict)
                    else str(result_data),
                    error=error_msg,
                    duration_ms=duration,
                )

        except subprocess.TimeoutExpired:
            duration = (time.time() - start_time) * 1000
            return ExecutionResult(
                success=False,
                error=f"Python tool execution timed out after {timeout} seconds",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.logger.error(f"Python tool execution failed: {e}")
            return ExecutionResult(success=False, error=str(e), duration_ms=duration)

    def _resolve_script_path(self, manifest: ToolManifest) -> Path:
        """Resolve the actual Python file path for the tool."""
        # For legacy compatibility, look for .py file with tool_id name
        script_name = manifest.tool_id

        # Check project scripts first
        project_scripts = self.project_path / ".ai" / "scripts"
        if project_scripts.exists():
            # Look in root and all subdirectories
            for py_file in project_scripts.rglob(f"{script_name}.py"):
                return py_file

        # Check user scripts
        user_scripts = get_user_space() / "scripts"
        if user_scripts.exists():
            for py_file in user_scripts.rglob(f"{script_name}.py"):
                return py_file

        return None

    def _setup_env_manager(self, script_path: Path):
        """Setup environment manager based on script location."""
        # Determine storage location (project or user)
        is_project_script = str(script_path).startswith(str(self.project_path / ".ai" / "scripts"))

        if is_project_script:
            project_venv = self.project_path / ".ai" / "scripts" / ".venv"
            if EnvManager.venv_has_python(project_venv):
                self.env_manager = EnvManager(project_path=self.project_path)
            else:
                self.env_manager = EnvManager(project_path=None)  # Fallback to user venv
        else:
            self.env_manager = EnvManager(project_path=None)  # User venv

    async def _handle_dependencies(self, script_path: Path, manifest: ToolManifest):
        """Handle script and lib dependencies."""
        # Get script dependencies from metadata
        script_meta = parse_script_metadata(script_path)
        dependencies = script_meta.get("dependencies", [])

        # Install script dependencies
        if dependencies:
            self.logger.info(f"Checking {len(dependencies)} script dependencies...")
            missing_deps = self.env_manager.check_packages(dependencies)
            if missing_deps:
                self.logger.info(f"Installing {len(missing_deps)} missing dependencies...")
                install_result = self.env_manager.install_packages(missing_deps)
                if install_result.get("failed"):
                    raise RuntimeError(
                        f"Failed to install dependencies: {install_result.get('failed')}"
                    )

        # Handle lib dependencies (from imports)
        lib_deps = self._extract_lib_dependencies(script_path)
        if lib_deps:
            self.logger.info(f"Checking {len(lib_deps)} lib dependencies...")
            missing_lib_deps = self.env_manager.check_packages(lib_deps)
            if missing_lib_deps:
                self.logger.info(f"Installing {len(missing_lib_deps)} missing lib dependencies...")
                install_result = self.env_manager.install_packages(missing_lib_deps)
                if install_result.get("failed"):
                    raise RuntimeError(
                        f"Failed to install lib dependencies: {install_result.get('failed')}"
                    )

    def _extract_lib_dependencies(self, script_path: Path) -> List[Dict[str, Any]]:
        """Extract lib dependencies by scanning imports."""
        # This is a simplified version - full implementation would scan lib/ folders
        # For now, return empty list
        return []

    def _build_search_paths(self, script_path: Path) -> List[Path]:
        """Build PYTHONPATH entries for script execution context."""
        paths = []

        # Script's own directory (for relative imports)
        if script_path.parent not in paths:
            paths.append(script_path.parent)

        # Project space scripts (if available)
        project_scripts = self.project_path / ".ai" / "scripts"
        if project_scripts.exists() and project_scripts not in paths:
            paths.insert(0, project_scripts)  # Project takes priority

        # User space scripts (always included)
        user_scripts = get_user_space() / "scripts"
        if user_scripts.exists() and user_scripts not in paths:
            paths.append(user_scripts)

        return paths

    def _execute_subprocess(
        self,
        script_path: Path,
        params: Dict[str, Any],
        search_paths: List[Path],
        timeout: int,
    ) -> Dict[str, Any]:
        """Execute script as subprocess with venv Python."""
        # Get venv Python
        venv_python = self.env_manager.get_python()

        # Build command
        cmd = [venv_python, str(script_path.absolute())]

        # Convert params to CLI args
        for key, value in params.items():
            if value is None or key.startswith("_"):
                continue

            # Convert snake_case to --kebab-case
            flag = f"--{key.replace('_', '-')}"

            if isinstance(value, bool):
                if value:  # Only add flag if True
                    cmd.append(flag)
            elif isinstance(value, list):
                for item in value:
                    cmd.extend([flag, str(item)])
            else:
                cmd.extend([flag, str(value)])

        # Build environment
        env = self.env_manager.build_subprocess_env(search_paths)

        # Execute
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, env=env, cwd=script_path.parent
        )

        # Parse output
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # Try to parse JSON from stdout
        if stdout:
            try:
                parsed = json.loads(stdout)

                # If script returned structured output, use it
                if isinstance(parsed, dict):
                    if "status" not in parsed:
                        parsed["status"] = "success" if result.returncode == 0 else "error"

                    # Add logs from stderr
                    if stderr:
                        parsed["logs"] = stderr.split("\n")

                    return parsed
            except json.JSONDecodeError:
                pass

        # Fallback: return raw output
        if result.returncode != 0:
            return {
                "status": "error",
                "error": stderr or stdout or f"Script exited with code {result.returncode}",
                "error_type": "execution_error",
                "exit_code": result.returncode,
            }

        return {
            "status": "success",
            "data": {"output": stdout},
            "logs": stderr.split("\n") if stderr else [],
        }
