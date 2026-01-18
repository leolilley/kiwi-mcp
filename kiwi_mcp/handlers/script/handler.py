"""
Script handler for kiwi-mcp.

Implements search, load, execute operations for scripts.
Handles LOCAL file operations directly, only uses registry for REMOTE operations.
"""

from typing import Dict, Any, Optional, List, Literal

from kiwi_mcp.handlers import SortBy
import hashlib
import json
import ast
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from kiwi_mcp.api.script_registry import ScriptRegistry
from kiwi_mcp.utils.logger import get_logger
from kiwi_mcp.utils.resolvers import ScriptResolver, get_user_space
from kiwi_mcp.utils.parsers import parse_script_metadata
from kiwi_mcp.utils.file_search import search_python_files, score_relevance
from kiwi_mcp.utils.env_manager import EnvManager
from kiwi_mcp.utils.output_manager import OutputManager, truncate_for_response


class ScriptHandler:
    """Handler for script operations."""

    def __init__(self, project_path: str):
        """Initialize handler with project path."""
        self.project_path = Path(project_path)
        self.resolver = ScriptResolver(project_path=self.project_path)
        self.registry = ScriptRegistry()
        self.logger = get_logger("script_handler")

        # Environment manager for venv-based execution
        self.env_manager = EnvManager(project_path=self.project_path)

        # Output manager for saving large results
        self.output_manager = OutputManager(project_path=self.project_path)

    async def search(
        self, query: str, source: str = "all", limit: int = 10, sort_by: SortBy = "score"
    ) -> Dict[str, Any]:
        """
        Search for scripts.

        Args:
            query: Search query
            source: "local", "registry", or "all"
            limit: Max results
            sort_by: Sort method ("score", "date", "name")

        Returns:
            Dict with search results
        """
        results = []

        # Search local files
        if source in ["local", "all"]:
            local_results = await self._search_local(query, limit)
            results.extend(local_results)

        # Search registry
        if source in ["registry", "all"]:
            registry_results = await self._search_registry(query, limit, sort_by)
            results.extend(registry_results)

        # Sort and limit
        if sort_by == "score":
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
        elif sort_by == "date":
            results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        elif sort_by == "name":
            results.sort(key=lambda x: x.get("name", ""))

        return {"results": results[:limit], "total": len(results), "query": query, "source": source}

    async def _search_local(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search local script files."""
        results = []

        # Search paths
        search_dirs = []
        project_scripts = self.project_path / ".ai" / "scripts"
        if project_scripts.exists():
            search_dirs.append(project_scripts)

        user_scripts = get_user_space() / "scripts"
        if user_scripts.exists():
            search_dirs.append(user_scripts)

        # Search each directory
        for search_dir in search_dirs:
            files = search_python_files(search_dir, query)

            for file_path in files:
                try:
                    script = parse_script_metadata(file_path)

                    # Calculate relevance score
                    searchable_text = f"{script['name']} {script['description']}"
                    score = score_relevance(query, searchable_text)

                    results.append(
                        {
                            "name": script["name"],
                            "description": script["description"],
                            "source": "project" if ".ai/" in str(file_path) else "user",
                            "path": str(file_path),
                            "score": score,
                        }
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to parse {file_path}: {e}")

        return results

    async def _search_registry(
        self, query: str, limit: int, sort_by: SortBy
    ) -> List[Dict[str, Any]]:
        """Search registry for scripts."""
        if not self.registry.is_configured:
            return []

        try:
            results = await self.registry.search(query, limit=limit, sort_by=sort_by)

            # Add source marker
            for result in results:
                result["source"] = "registry"

            return results
        except Exception as e:
            self.logger.error(f"Registry search failed: {e}")
            return []

    async def load(
        self,
        script_name: str,
        source: Literal["project", "user", "registry"],
        destination: Optional[Literal["project", "user"]] = None,
    ) -> Dict[str, Any]:
        """
        Load script from specified source.

        Args:
            script_name: Name of script
            source: Where to load from - "project" | "user" | "registry"
            destination: Where to copy to (optional). If None or same as source, read-only mode.

        Returns:
            Dict with script details
        """
        self.logger.info(
            f"ScriptHandler.load: script={script_name}, source={source}, destination={destination}"
        )

        try:
            # Determine if this is read-only mode (no copy)
            # Read-only when: destination is None OR destination equals source (for non-registry)
            is_read_only = destination is None or (source == destination and source != "registry")
            
            # LOAD FROM REGISTRY
            if source == "registry":
                if not self.registry.is_configured:
                    return {
                        "error": "Registry not configured",
                        "message": "Set SUPABASE_URL and SUPABASE_KEY to load from registry",
                    }

                # Get from registry
                script_data = await self.registry.get(script_name)
                if not script_data:
                    return {"error": f"Script '{script_name}' not found in registry"}

                # For registry, default destination to "project" if not specified
                effective_destination = destination or "project"

                # Determine target path based on destination
                if effective_destination == "user":
                    target_dir = get_user_space() / "scripts"
                else:  # destination == "project"
                    target_dir = self.project_path / ".ai" / "scripts"

                target_dir.mkdir(parents=True, exist_ok=True)

                # Determine category subdirectory
                category = script_data.get("category", "utility")
                category_dir = target_dir / category
                category_dir.mkdir(exist_ok=True)

                # Write script file
                target_file = category_dir / f"{script_name}.py"
                target_file.write_text(script_data["content"])

                self.logger.info(f"Downloaded script from registry to: {target_file}")

                return {
                    "status": "success",
                    "message": f"Downloaded script to {effective_destination}",
                    "path": str(target_file),
                    "source": "registry",
                    "destination": effective_destination,
                    "script": script_data,
                }

            # LOAD FROM PROJECT
            if source == "project":
                search_base = self.project_path / ".ai" / "scripts"
                file_path = self._find_script_in_path(script_name, search_base)
                if not file_path:
                    return {"error": f"Script '{script_name}' not found in project"}

                # If destination differs from source, copy the file
                if destination == "user":
                    # Copy from project to user space
                    content = file_path.read_text()
                    # Determine category from source path
                    relative_path = file_path.relative_to(search_base)
                    target_path = get_user_space() / "scripts" / relative_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(content)
                    self.logger.info(f"Copied script from project to user: {target_path}")

                    script_data = parse_script_metadata(target_path)
                    script_data["source"] = "project"
                    script_data["destination"] = "user"
                    script_data["path"] = str(target_path)
                    return script_data
                else:
                    # Read-only mode: just return project file info (no copy)
                    script_data = parse_script_metadata(file_path)
                    script_data["source"] = "project"
                    script_data["path"] = str(file_path)
                    script_data["mode"] = "read_only"
                    return script_data

            # LOAD FROM USER
            # source == "user" (only remaining option due to Literal typing)
            search_base = get_user_space() / "scripts"
            file_path = self._find_script_in_path(script_name, search_base)
            if not file_path:
                return {"error": f"Script '{script_name}' not found in user space"}

            # If destination differs from source, copy the file
            if destination == "project":
                # Copy from user to project space
                content = file_path.read_text()
                # Determine category from source path
                relative_path = file_path.relative_to(search_base)
                target_path = self.project_path / ".ai" / "scripts" / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content)
                self.logger.info(f"Copied script from user to project: {target_path}")

                script_data = parse_script_metadata(target_path)
                script_data["source"] = "user"
                script_data["destination"] = "project"
                script_data["path"] = str(target_path)
                return script_data
            else:
                # Read-only mode: just return user file info (no copy)
                script_data = parse_script_metadata(file_path)
                script_data["source"] = "user"
                script_data["path"] = str(file_path)
                script_data["mode"] = "read_only"
                return script_data
        except Exception as e:
            self.logger.error(f"Failed to load script: {e}")
            return {"error": str(e)}

    def _find_script_in_path(self, script_name: str, base_path: Path) -> Optional[Path]:
        """Find script file in specified path."""
        if not base_path.exists():
            return None

        # Search recursively for the script
        for py_file in base_path.rglob(f"{script_name}.py"):
            return py_file

        # Also try with wildcards in case of naming variations
        for py_file in base_path.rglob("*.py"):
            if script_name in py_file.stem:
                return py_file

        return None

    def _extract_lib_dependencies(self, script_path: Path) -> List[Dict[str, Any]]:
        """
        Extract dependencies from lib modules imported by the script.

        Scans for 'from lib.X import' statements and parses those lib files
        to get their dependencies.
        """
        deps = []

        try:
            content = script_path.read_text()
            tree = ast.parse(content)

            # Find lib imports
            lib_imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("lib."):
                        lib_name = node.module.split(".")[1]  # lib.http_session -> http_session
                        lib_imports.add(lib_name)

            # For each lib import, find the lib file and parse its dependencies
            for lib_name in lib_imports:
                lib_file = self._find_lib_file(lib_name)
                if lib_file:
                    lib_meta = parse_script_metadata(lib_file)
                    deps.extend(lib_meta.get("dependencies", []))

        except Exception as e:
            self.logger.warning(f"Failed to extract lib dependencies: {e}")

        # Deduplicate by name
        seen = set()
        unique_deps = []
        for dep in deps:
            name = dep.get("name")
            if name and name not in seen:
                seen.add(name)
                unique_deps.append(dep)

        return unique_deps

    def _find_lib_file(self, lib_name: str) -> Optional[Path]:
        """Find a lib file in project or user space."""
        # Check project lib/
        project_lib = self.project_path / ".ai" / "scripts" / "lib" / f"{lib_name}.py"
        if project_lib.exists():
            return project_lib

        # Check user lib/
        user_lib = get_user_space() / "scripts" / "lib" / f"{lib_name}.py"
        if user_lib.exists():
            return user_lib

        return None

    def _verify_script_signature(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Verify script signature if present.

        Returns None if no signature, or a dict with status:
        - "valid": hash matches
        - "modified": hash doesn't match
        - "invalid": signature format is wrong
        """
        content = file_path.read_text()

        # Look for signature comment (after optional shebang)
        # Format: # kiwi-mcp:validated:TIMESTAMP:HASH
        sig_pattern = r"^(?:#!/[^\n]*\n)?# kiwi-mcp:validated:(.*?):([a-f0-9]{12})"
        sig_match = re.match(sig_pattern, content)

        if not sig_match:
            return None  # No signature - might be legacy or unvalidated

        stored_timestamp = sig_match.group(1)
        stored_hash = sig_match.group(2)

        # Remove signature line to compute current hash
        content_without_sig = re.sub(r"^#!/[^\n]*\n", "", content)  # Remove shebang if present
        content_without_sig = re.sub(r"^# kiwi-mcp:validated:[^\n]+\n", "", content_without_sig)

        # Compute current hash
        current_hash = hashlib.sha256(content_without_sig.encode()).hexdigest()[:12]

        if current_hash == stored_hash:
            return {"status": "valid", "validated_at": stored_timestamp, "hash": stored_hash}
        else:
            return {
                "status": "modified",
                "validated_at": stored_timestamp,
                "original_hash": stored_hash,
                "current_hash": current_hash,
                "warning": "Content modified since last validation. Consider running 'update' to re-validate.",
            }

    def _build_search_paths(self, script_path: Path, storage_location: str) -> List[Path]:
        """
        Build PYTHONPATH entries for script execution context.

        Includes:
        - Script's own directory
        - Project scripts root (.ai/scripts/)
        - Project lib (.ai/scripts/lib/)
        - User scripts root (~/.ai/scripts/)
        - User lib (~/.ai/scripts/lib/)

        Both user space and project space are included for lib imports.
        """
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

    async def _run_script(
        self, script_name: str, params: Dict[str, Any], dry_run: bool
    ) -> Dict[str, Any]:
        """Execute a script from local file."""
        start_time = time.time()

        # Find local script file
        file_path = self.resolver.resolve(script_name)
        if not file_path:
            return {
                "error": f"Script '{script_name}' not found locally",
                "suggestion": "Use load() to download from registry first",
            }

        # ENFORCE hash validation - ALWAYS check, never skip
        signature_status = self._verify_script_signature(file_path)

        # Block execution if signature is invalid or modified
        if signature_status:
            if signature_status.get("status") == "modified":
                return {
                    "status": "error",
                    "error": "Script content has been modified since last validation",
                    "signature": signature_status,
                    "path": str(file_path),
                    "solution": "Use execute action 'update' or 'create' to re-validate the script",
                }
            elif signature_status.get("status") == "invalid":
                return {
                    "status": "error",
                    "error": "Script signature is invalid",
                    "signature": signature_status,
                    "path": str(file_path),
                    "solution": "Use execute action 'update' or 'create' to re-validate the script",
                }

        # Parse script metadata for dependencies
        script_meta = parse_script_metadata(file_path)
        dependencies = script_meta.get("dependencies", [])

        # Determine storage location (project or user)
        is_project_script = str(file_path).startswith(str(self.project_path / ".ai"))
        storage_location = "project" if is_project_script else "user"

        # Update env_manager based on script location
        if storage_location == "project":
            self.env_manager = EnvManager(project_path=self.project_path)
        else:
            self.env_manager = EnvManager(project_path=None)

        # Check and install script dependencies
        if dependencies:
            self.logger.info(f"Checking {len(dependencies)} script dependencies...")
            missing_deps = self.env_manager.check_packages(dependencies)
            if missing_deps:
                self.logger.info(f"Installing {len(missing_deps)} missing dependencies...")
                install_result = self.env_manager.install_packages(missing_deps)
                if install_result.get("failed"):
                    return {
                        "status": "error",
                        "error": "Failed to install script dependencies",
                        "details": {
                            "installed": install_result.get("installed", []),
                            "failed": install_result.get("failed", []),
                        },
                    }

        # Also check lib dependencies (scan lib imports and install their deps)
        lib_deps = self._extract_lib_dependencies(file_path)
        if lib_deps:
            self.logger.info(f"Checking {len(lib_deps)} lib dependencies...")
            missing_lib_deps = self.env_manager.check_packages(lib_deps)

            if missing_lib_deps:
                self.logger.info(f"Installing {len(missing_lib_deps)} missing lib dependencies...")
                install_result = self.env_manager.install_packages(missing_lib_deps)

                if install_result.get("failed"):
                    return {
                        "status": "error",
                        "error": "Failed to install lib dependencies",
                        "details": {
                            "installed": install_result.get("installed", []),
                            "failed": install_result.get("failed", []),
                        },
                    }

        if dry_run:
            env_info = self.env_manager.get_info()
            return {
                "status": "validation_passed",
                "message": "Script is ready to execute",
                "path": str(file_path),
                "venv": env_info["venv_dir"],
                "dependencies": dependencies,
                "lib_dependencies": lib_deps,
            }

        # Build execution context
        search_paths = self._build_search_paths(file_path, storage_location)

        # Extract output control parameters
        save_output = params.pop("_save_output", True)  # Default: save outputs
        output_file = params.pop("_output_file", None)  # Custom output path
        timeout = params.pop("_timeout", 300)  # 5 min default

        # Execute the script via subprocess
        try:
            result = self._execute_subprocess(
                script_path=file_path,
                script_name=script_name,
                params=params,
                search_paths=search_paths,
                timeout=timeout,
            )

            duration = time.time() - start_time

            # Add metadata
            if isinstance(result, dict):
                if "metadata" not in result:
                    result["metadata"] = {}
                result["metadata"]["duration_sec"] = round(duration, 3)
                result["metadata"]["venv"] = self.env_manager.env_type

            # Handle output saving and response truncation
            if isinstance(result, dict) and result.get("status") == "success":
                result_data = result.get("data", {})

                # Save output if enabled
                if save_output:
                    output_info = self.output_manager.save_output(
                        script_name=script_name,
                        data=result_data,
                        force_save=(output_file is not None),
                    )
                    output_path = output_info.get("path") if output_info else None
                    if output_path:
                        if "metadata" not in result:
                            result["metadata"] = {}
                        result["metadata"]["output_file"] = str(output_path)
                        result["metadata"]["output_saved"] = True

                # Truncate response if too large
                truncated_data, was_truncated = truncate_for_response(result_data)
                if was_truncated:
                    result["data"] = truncated_data
                    if "metadata" not in result:
                        result["metadata"] = {}
                    result["metadata"]["response_truncated"] = True
                    result["metadata"]["truncation_note"] = (
                        "Large response truncated. Full results saved to output file."
                    )

            return result

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": f"Script execution timed out after {timeout} seconds",
                "error_type": "timeout",
            }
        except Exception as e:
            self.logger.error(f"Script execution failed: {e}")
            return {"status": "error", "error": str(e), "error_type": type(e).__name__}

    def _execute_subprocess(
        self,
        script_path: Path,
        script_name: str,
        params: Dict[str, Any],
        search_paths: List[Path],
        timeout: int,
    ) -> Dict[str, Any]:
        """
        Execute script as subprocess with venv Python.

        Converts params dict to command-line args and runs script in isolated venv.
        """
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

    async def execute(
        self,
        action: str,
        script_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute a script or perform script operation.

        Args:
            action: "run", "publish", "delete", "create", "update", "link"
            script_name: Name of script to execute
            parameters: Script parameters (for run action)
            dry_run: If True, validate without executing

        Returns:
            Dict with execution result
        """
        # Extract dry_run from parameters if present
        if parameters and "dry_run" in parameters:
            dry_run = parameters.pop("dry_run")

        try:
            if action == "run":
                return await self._run_script(script_name, parameters or {}, dry_run)

            elif action == "publish":
                return await self._publish_script(script_name, kwargs.get("version"))

            elif action == "delete":
                return await self._delete_script(script_name, kwargs.get("confirm", False))

            elif action == "create":
                return await self._create_script(
                    script_name,
                    kwargs.get("content"),
                    kwargs.get("location", "project"),
                    kwargs.get("category"),
                )

            elif action == "update":
                return await self._update_script(script_name, kwargs.get("updates", {}))

            else:
                return {"error": f"Unknown action: {action}"}

        except Exception as e:
            self.logger.error(f"Execute failed: {e}")
            return {"error": str(e)}

    async def _publish_script(self, script_name: str, version: Optional[str]) -> Dict[str, Any]:
        """Publish script to registry."""
        if not self.registry.is_configured:
            return {"error": "Registry not configured"}

        # Find local script
        file_path = self.resolver.resolve(script_name)
        if not file_path:
            return {"error": f"Script '{script_name}' not found locally"}

        # ENFORCE hash validation - ALWAYS check, never skip
        signature_status = self._verify_script_signature(file_path)

        # Block publishing if signature is invalid or modified
        if signature_status:
            if signature_status.get("status") == "modified":
                return {
                    "error": "Script content has been modified since last validation",
                    "signature": signature_status,
                    "path": str(file_path),
                    "solution": "Use execute action 'update' or 'create' to re-validate the script before publishing",
                }
            elif signature_status.get("status") == "invalid":
                return {
                    "error": "Script signature is invalid",
                    "signature": signature_status,
                    "path": str(file_path),
                    "solution": "Use execute action 'update' or 'create' to re-validate the script before publishing",
                }

        # Parse script to get content and metadata
        script_data = parse_script_metadata(file_path)
        content = file_path.read_text()

        # Use registry publish method
        try:
            result = await self.registry.publish(
                name=script_name,
                content=content,
                version=version,
                description=script_data.get("description", ""),
                category=script_data.get("category", "utility"),
                dependencies=script_data.get("dependencies", []),
                tech_stack=script_data.get("tech_stack", []),
            )
            return result
        except Exception as e:
            self.logger.error(f"Publish failed: {e}")
            return {"error": str(e)}

    async def _delete_script(self, script_name: str, confirm: bool) -> Dict[str, Any]:
        """Delete script from local storage."""
        if not confirm:
            return {"error": "Must set confirm=true to delete"}

        file_path = self.resolver.resolve(script_name)
        if not file_path:
            return {"error": f"Script '{script_name}' not found"}

        try:
            file_path.unlink()
            return {"status": "success", "message": f"Deleted script '{script_name}'"}
        except Exception as e:
            return {"error": str(e)}

    async def _create_script(
        self, script_name: str, content: str, location: str, category: Optional[str]
    ) -> Dict[str, Any]:
        """Create new script file."""
        # Determine target directory
        if location == "project":
            base_dir = self.project_path / ".ai" / "scripts"
        else:
            base_dir = get_user_space() / "scripts"

        # Add category subdirectory if provided
        if category:
            target_dir = base_dir / category
        else:
            target_dir = base_dir

        target_dir.mkdir(parents=True, exist_ok=True)

        # Write file
        target_file = target_dir / f"{script_name}.py"
        if target_file.exists():
            return {"error": f"Script '{script_name}' already exists"}

        # Generate signature for validated content
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        signature_line = f"# kiwi-mcp:validated:{timestamp}:{content_hash}\n"

        # Prepend signature to content (after shebang if present)
        if content.startswith("#!/"):
            lines = content.split("\n", 1)
            signed_content = lines[0] + "\n" + signature_line + (lines[1] if len(lines) > 1 else "")
        else:
            signed_content = signature_line + content

        target_file.write_text(signed_content)

        return {
            "status": "success",
            "message": f"Created script at {location}",
            "path": str(target_file),
            "signature": {"hash": content_hash, "timestamp": timestamp},
        }

    async def _update_script(self, script_name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update script file."""
        file_path = self.resolver.resolve(script_name)
        if not file_path:
            return {"error": f"Script '{script_name}' not found"}

        # For now, only support content updates
        if "content" in updates:
            content = updates["content"]

            # Generate new signature for validated content
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            signature_line = f"# kiwi-mcp:validated:{timestamp}:{content_hash}\n"

            # Remove old signature if present
            content_clean = re.sub(r"^(#!/[^\n]*\n)?# kiwi-mcp:validated:[^\n]+\n", r"\1", content)

            # Prepend new signature (after shebang if present)
            if content_clean.startswith("#!/"):
                lines = content_clean.split("\n", 1)
                signed_content = (
                    lines[0] + "\n" + signature_line + (lines[1] if len(lines) > 1 else "")
                )
            else:
                signed_content = signature_line + content_clean

            file_path.write_text(signed_content)
            return {
                "status": "success",
                "message": f"Updated script '{script_name}'",
                "signature": {"hash": content_hash, "timestamp": timestamp},
            }

        return {"error": "No updates provided"}
