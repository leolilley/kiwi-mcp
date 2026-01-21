"""
Environment Manager for Kiwi MCP

Manages virtual environments for script execution:
- Project-level: .ai/scripts/.venv/ (when project_path provided and it exists)
- User-level: $USER_SPACE/.venv/ or default path ~/.ai/.venv/ (when running from userspace, or when running from project but no project venv exists)

Venv selection:
- Script from userspace -> always use ~/.ai/.venv
- Script from project -> use .ai/scripts/.venv if it exists; else fall back to ~/.ai/.venv
  (caller performs this check; EnvManager does not create a project venv when absent)
"""

import os
import sys
import subprocess
import fcntl
from pathlib import Path
from typing import Optional, List, Dict, Any

from kiwi_mcp.utils.logger import get_logger
from kiwi_mcp.utils.resolvers import get_user_space

logger = get_logger("env_manager")


# Package name to module name mapping for import checks
PACKAGE_TO_MODULE = {
    "beautifulsoup4": "bs4",
    "pillow": "PIL",
    "opencv-python": "cv2",
    "scikit-learn": "sklearn",
    "pyyaml": "yaml",
    "python-dotenv": "dotenv",
    "google-api-python-client": "googleapiclient",
    "google-auth-httplib2": "google_auth_httplib2",
    "google-auth-oauthlib": "google_auth_oauthlib",
    "apify-client": "apify_client",
    "youtube-transcript-api": "youtube_transcript_api",
}


class EnvManager:
    """Manages virtual environments for script execution."""

    def __init__(self, project_path: Optional[Path] = None):
        """
        Initialize environment manager.

        Args:
            project_path: If provided, use project-level venv at .ai/scripts/.venv/
                         Otherwise, use user-level venv at $USER_SPACE/.venv/
        """
        self.project_path = Path(project_path) if project_path else None
        self.user_space = get_user_space()

        # Determine environment root based on project_path
        if self.project_path:
            # Project-level env at .ai/scripts/.venv
            self.env_root = self.project_path / ".ai" / "scripts"
            self.env_type = "project"
        else:
            # User-level env at $USER_SPACE/.venv
            self.env_root = self.user_space
            self.env_type = "user"

        self.venv_dir = self.env_root / ".venv"
        self._lock_file: Optional[int] = None

    @staticmethod
    def venv_has_python(venv_dir: Path) -> bool:
        """Return True if venv_dir exists and contains a python executable."""
        if not venv_dir.exists():
            return False
        if os.name == "nt":
            return (venv_dir / "Scripts" / "python.exe").exists()
        return (venv_dir / "bin" / "python").exists()

    def _acquire_lock(self) -> bool:
        """
        Acquire a file lock to prevent concurrent venv operations.

        Returns:
            True if lock acquired, False otherwise
        """
        lock_path = self.venv_dir.parent / ".venv.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._lock_file = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
            fcntl.flock(self._lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (OSError, BlockingIOError):
            if self._lock_file is not None:
                os.close(self._lock_file)
                self._lock_file = None
            return False

    def _release_lock(self) -> None:
        """Release the file lock."""
        if self._lock_file is not None:
            try:
                fcntl.flock(self._lock_file, fcntl.LOCK_UN)
                os.close(self._lock_file)
            except OSError:
                pass
            finally:
                self._lock_file = None

    def ensure_venv(self) -> Path:
        """
        Create venv lazily if it doesn't exist.

        Returns:
            Path to the venv directory
        """
        if self.venv_dir.exists() and (self.venv_dir / "bin" / "python").exists():
            return self.venv_dir

        # Try to acquire lock for venv creation
        lock_acquired = self._acquire_lock()
        try:
            # Double-check after acquiring lock (another process may have created it)
            if self.venv_dir.exists() and (self.venv_dir / "bin" / "python").exists():
                return self.venv_dir

            logger.info(f"Creating {self.env_type} venv at {self.venv_dir}")
            self.venv_dir.parent.mkdir(parents=True, exist_ok=True)

            # Create venv using current Python
            result = subprocess.run(
                [sys.executable, "-m", "venv", str(self.venv_dir)],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"Failed to create venv: {result.stderr or result.stdout}"
                )

            # Upgrade pip in the new venv
            venv_python = self._get_python_path()
            pip_upgrade = subprocess.run(
                [venv_python, "-m", "pip", "install", "--upgrade", "pip"],
                capture_output=True,
                text=True,
            )
            if pip_upgrade.returncode != 0:
                logger.warning(f"Failed to upgrade pip: {pip_upgrade.stderr}")

            logger.info(f"Created {self.env_type} venv at {self.venv_dir}")
            return self.venv_dir
        finally:
            if lock_acquired:
                self._release_lock()

    def _get_python_path(self) -> str:
        """
        Get path to the venv's Python executable without ensuring venv exists.
        Internal helper to avoid recursion in ensure_venv.
        """
        if os.name == "nt":
            return str(self.venv_dir / "Scripts" / "python.exe")
        else:
            return str(self.venv_dir / "bin" / "python")

    def get_python(self) -> str:
        """
        Get path to the venv's Python executable.
        Ensures the venv exists first.

        Returns:
            Absolute path to python executable in the venv
        """
        self.ensure_venv()
        return self._get_python_path()

    def get_pip(self) -> str:
        """
        Get path to the venv's pip executable.

        Returns:
            Absolute path to pip executable in the venv
        """
        venv = self.ensure_venv()
        if os.name == "nt":
            return str(venv / "Scripts" / "pip.exe")
        else:
            return str(venv / "bin" / "pip")

    def build_subprocess_env(
        self, 
        search_paths: List[Path],
        extra_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Build environment variables for subprocess execution.

        Sets up PYTHONPATH, PATH, VIRTUAL_ENV, and loads .env files so scripts run
        in the venv with access to lib/ directories and environment variables.

        .env Loading Order (later overrides earlier):
        1. ~/.ai/.env (userspace defaults)
        2. .ai/.env (project-specific overrides)
        3. os.environ (runtime environment)
        4. extra_vars (passed in programmatically)

        Args:
            search_paths: List of paths to add to PYTHONPATH
            extra_vars: Additional environment variables to set

        Returns:
            Environment dict for subprocess.run()
        """
        from kiwi_mcp.utils.env_loader import build_script_env
        
        # Build base environment from .env files + os.environ
        env = build_script_env(
            project_path=self.project_path,
            search_paths=search_paths,
            extra_vars=extra_vars
        )

        # Activate venv for subprocess
        venv = self.ensure_venv()
        bin_dir = venv / ("Scripts" if os.name == "nt" else "bin")
        env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
        env["VIRTUAL_ENV"] = str(venv)

        # Remove PYTHONHOME if set (can interfere with venv)
        env.pop("PYTHONHOME", None)

        return env

    def install_packages(
        self, packages: List[Dict[str, str]], timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Install pip packages into the venv.

        Args:
            packages: List of dicts with 'name' and optional 'version' keys
            timeout: Timeout in seconds for each install

        Returns:
            Dict with 'installed', 'failed', and 'status' keys
        """
        if not packages:
            return {"status": "success", "installed": [], "failed": []}

        python = self.get_python()
        installed = []
        failed = []

        for pkg in packages:
            pkg_name = pkg.get("name")
            pkg_version = pkg.get("version")

            if not pkg_name:
                continue

            try:
                # Build package spec
                if pkg_version:
                    if pkg_version.startswith((">=", "<=", "==", "~=", "!=")):
                        package_spec = f"{pkg_name}{pkg_version}"
                    else:
                        package_spec = f"{pkg_name}=={pkg_version}"
                else:
                    package_spec = pkg_name

                logger.info(f"Installing {package_spec} into {self.env_type} venv")

                result = subprocess.run(
                    [python, "-m", "pip", "install", package_spec],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                if result.returncode == 0:
                    installed.append({"name": pkg_name, "version": pkg_version})
                    logger.info(f"Installed: {package_spec}")
                else:
                    error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                    failed.append({"name": pkg_name, "error": error_msg})
                    logger.warning(f"Failed to install {package_spec}: {error_msg}")

            except subprocess.TimeoutExpired:
                failed.append({"name": pkg_name, "error": "Installation timed out"})
                logger.warning(f"Timeout installing {pkg_name}")
            except Exception as e:
                failed.append({"name": pkg_name, "error": str(e)})
                logger.warning(f"Error installing {pkg_name}: {e}")

        if failed:
            status = "partial" if installed else "error"
        else:
            status = "success"

        return {"status": status, "installed": installed, "failed": failed}

    def check_packages(self, packages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Check which packages are missing from the venv.

        Runs import checks in the venv's Python to get accurate results.

        Args:
            packages: List of dicts with 'name' and optional 'version' keys

        Returns:
            List of missing packages with install commands
        """
        if not packages:
            return []

        # Internal modules to skip (local lib imports)
        internal_prefixes = ("lib", "lib.")

        # Build a script to check imports in the venv
        check_script = """
import sys
import json

packages = json.loads(sys.argv[1])
missing = []

for pkg in packages:
    name = pkg.get('name', '')
    module = pkg.get('module', name.replace('-', '_'))
    try:
        __import__(module)
    except ImportError:
        try:
            __import__(name)
        except ImportError:
            missing.append(name)

print(json.dumps(missing))
"""

        # Prepare package list with module names
        packages_with_modules = []
        for pkg in packages:
            pkg_name = pkg.get("name") if isinstance(pkg, dict) else str(pkg)

            # Skip internal lib modules
            if pkg_name.startswith(internal_prefixes):
                continue

            module_name = PACKAGE_TO_MODULE.get(pkg_name, pkg_name.replace("-", "_"))
            packages_with_modules.append({"name": pkg_name, "module": module_name})

        if not packages_with_modules:
            return []

        import json

        python = self.get_python()

        try:
            result = subprocess.run(
                [python, "-c", check_script, json.dumps(packages_with_modules)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                missing_names = json.loads(result.stdout.strip())
            else:
                logger.warning(f"Import check failed: {result.stderr}")
                missing_names = [p["name"] for p in packages_with_modules]
        except Exception as e:
            logger.warning(f"Error checking packages: {e}")
            missing_names = [p["name"] for p in packages_with_modules]

        # Build missing packages list with install commands
        missing = []
        pkg_lookup = {p.get("name"): p for p in packages if isinstance(p, dict)}

        for name in missing_names:
            pkg = pkg_lookup.get(name, {"name": name})
            version = pkg.get("version")
            install_cmd = (
                f"pip install '{name}{version}'" if version else f"pip install '{name}'"
            )
            missing.append({
                "name": name,
                "version": version,
                "install_cmd": install_cmd,
            })

        return missing

    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the current environment.

        Returns:
            Dict with env_type, venv_dir, exists, python_path
        """
        exists = self.venv_dir.exists() and (self.venv_dir / "bin" / "python").exists()
        return {
            "env_type": self.env_type,
            "venv_dir": str(self.venv_dir),
            "exists": exists,
            "python_path": self.get_python() if exists else None,
            "project_path": str(self.project_path) if self.project_path else None,
        }
