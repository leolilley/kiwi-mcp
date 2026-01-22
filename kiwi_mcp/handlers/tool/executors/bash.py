"""
Bash Executor for Tool Harness

Executes bash scripts with environment variable injection and timeout handling.
"""

import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any

from .base import ToolExecutor, ExecutionResult


class BashExecutor(ToolExecutor):
    """Executor for bash script tools."""

    async def execute(self, manifest, params: Dict[str, Any]) -> ExecutionResult:
        """Execute a bash script with the given parameters."""
        config = manifest.executor_config
        script_path = self._resolve_script(manifest)

        # Validate allowed commands if specified
        if "requires" in config:
            for cmd in config["requires"].get("commands", []):
                if not shutil.which(cmd):
                    return ExecutionResult(
                        success=False, output="", error=f"Required command not found: {cmd}"
                    )

        # Build environment with params
        env = os.environ.copy()
        for key, value in params.items():
            env[f"KIWI_{key.upper()}"] = str(value)

        # Execute with timeout
        timeout = config.get("timeout", 60)
        try:
            result = await asyncio.wait_for(self._run_script(script_path, env), timeout=timeout)
            return result
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False, output="", error=f"Script timed out after {timeout}s"
            )

    def _resolve_script(self, manifest) -> Path:
        """Resolve the path to the script file."""
        tool_dir = Path(manifest.file_path).parent
        entrypoint = manifest.executor_config.get("entrypoint", "script.sh")
        return tool_dir / entrypoint

    async def _run_script(self, script_path: Path, env: Dict[str, str]) -> ExecutionResult:
        """Run the bash script subprocess."""
        try:
            # Make script executable
            script_path.chmod(0o755)

            # Run script
            process = await asyncio.create_subprocess_exec(
                str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            stdout, stderr = await process.communicate()

            return ExecutionResult(
                success=process.returncode == 0,
                output=stdout.decode(),
                error=stderr.decode() if process.returncode != 0 else None,
            )
        except Exception as e:
            return ExecutionResult(
                success=False, output="", error=f"Script execution failed: {str(e)}"
            )

    def can_execute(self, manifest) -> bool:
        """Check if this executor can handle the given manifest."""
        return manifest.tool_type == "bash"
