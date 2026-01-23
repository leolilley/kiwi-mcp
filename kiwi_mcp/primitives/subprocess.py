"""
SubprocessPrimitive for executing shell commands and scripts.
"""

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class SubprocessResult:
    """Result of subprocess execution."""

    success: bool
    stdout: str
    stderr: str
    return_code: int
    duration_ms: int


class SubprocessPrimitive:
    """Primitive for executing subprocess commands."""

    async def execute(self, config: Dict[str, Any], params: Dict[str, Any]) -> SubprocessResult:
        """
        Execute a subprocess command.

        Args:
            config: Configuration from tool definition
            params: Runtime parameters

        Returns:
            SubprocessResult with execution details
        """
        start_time = time.time()

        try:
            # Extract configuration
            command = config.get("command")
            if not command:
                raise ValueError("command is required in config")

            args = config.get("args", [])
            env_vars = config.get("env", {})
            cwd = config.get("cwd")
            timeout = config.get("timeout", 300)
            capture_output = config.get("capture_output", True)
            input_data = config.get("input_data")

            # Resolve environment variables in command and args
            command = self._resolve_env_var(command)
            args = [self._resolve_env_var(arg) for arg in args]

            # Prepare environment
            env = os.environ.copy()
            for key, value in env_vars.items():
                env[key] = self._resolve_env_var(str(value))

            # Resolve cwd if provided
            if cwd:
                cwd = self._resolve_env_var(cwd)

            # Create subprocess
            if capture_output:
                process = await asyncio.create_subprocess_exec(
                    command,
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.PIPE if input_data else None,
                    env=env,
                    cwd=cwd,
                )
            else:
                process = await asyncio.create_subprocess_exec(command, *args, env=env, cwd=cwd)

            # Execute with timeout
            try:
                if input_data:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(input_data.encode()), timeout=timeout
                    )
                else:
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

                return_code = process.returncode or 0

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                duration_ms = int((time.time() - start_time) * 1000)
                return SubprocessResult(
                    success=False,
                    stdout="",
                    stderr=f"Command timed out after {timeout} seconds",
                    return_code=-1,
                    duration_ms=duration_ms,
                )

            # Process results
            stdout_str = stdout.decode() if stdout else ""
            stderr_str = stderr.decode() if stderr else ""
            success = return_code == 0

            duration_ms = int((time.time() - start_time) * 1000)

            return SubprocessResult(
                success=success,
                stdout=stdout_str,
                stderr=stderr_str,
                return_code=return_code,
                duration_ms=duration_ms,
            )

        except FileNotFoundError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return SubprocessResult(
                success=False,
                stdout="",
                stderr=f"Command not found: {e}",
                return_code=-1,
                duration_ms=duration_ms,
            )

        except PermissionError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return SubprocessResult(
                success=False,
                stdout="",
                stderr=f"Permission denied: {e}",
                return_code=-1,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return SubprocessResult(
                success=False,
                stdout="",
                stderr=f"Unexpected error: {e}",
                return_code=-1,
                duration_ms=duration_ms,
            )

    def _resolve_env_var(self, value: str) -> str:
        """
        Resolve environment variables with default syntax: ${VAR:-default}

        Args:
            value: String that may contain environment variable references

        Returns:
            String with environment variables resolved
        """
        if not isinstance(value, str):
            return str(value)

        import re

        # Pattern for ${VAR:-default} syntax
        pattern = r"\$\{([^}]+)\}"

        def replace_var(match):
            var_expr = match.group(1)

            # Check for default value syntax
            if ":-" in var_expr:
                var_name, default_value = var_expr.split(":-", 1)
                return os.environ.get(var_name.strip(), default_value)
            else:
                return os.environ.get(var_expr, "")

        return re.sub(pattern, replace_var, value)
