import sys
import subprocess
import shutil
from pathlib import Path

class LanguageModule:
    """
    Python runtime interface for CAL.
    Handles discovery, execution, and plugin loading for Python plugins.
    """

    def __init__(self, core, runtime_path=None, runtime_version=None):
        self.core = core
        self.runtime_path = runtime_path
        self.runtime_version = runtime_version
        self.proc = None
        self.python_exe = self._find_python_executable()
        print(f"[python] Using interpreter: {self.python_exe}")

    # ---------------------------------------------------------------------
    # Runtime management
    # ---------------------------------------------------------------------
    def _find_python_executable(self):
        """Locate Python executable across OSes."""
        # If explicit runtime path given
        if self.runtime_path:
            exe = Path(self.runtime_path)
            if exe.is_dir():
                exe = exe / ("python.exe" if sys.platform.startswith("win") else "python3")
            if exe.exists():
                return str(exe)

        # Otherwise fall back to system Python
        system_python = shutil.which("python3") or shutil.which("python")
        if not system_python:
            raise FileNotFoundError("No Python runtime found on system.")
        return system_python

    # ---------------------------------------------------------------------
    # Plugin loading
    # ---------------------------------------------------------------------
    def load_plugin(self, plugin_data, package_path):
        """
        Loads a plugin written in Python.
        Returns a dict with plugin info and callable path.
        """
        entry = plugin_data.get("entry", "main.py")
        entry_path = Path(package_path) / entry
        if not entry_path.exists():
            raise FileNotFoundError(f"[python] Plugin entry not found: {entry_path}")

        return {"path": str(entry_path)}

    # ---------------------------------------------------------------------
    # Execution
    # ---------------------------------------------------------------------
    def run_code(self, plugin_info):
        """Execute a Python plugin file and return stdout."""
        plugin_path = plugin_info["path"]
        try:
            result = subprocess.run(
                [self.python_exe, plugin_path],
                capture_output=True,
                text=True
            )
            if result.stderr:
                print(f"[python:error] {result.stderr.strip()}")
            return result.stdout.strip()
        except Exception as e:
            return f"[python:exception] {e}"

    # ---------------------------------------------------------------------
    def stop(self):
        """No persistent runtime for Python, so nothing to stop."""
        pass
