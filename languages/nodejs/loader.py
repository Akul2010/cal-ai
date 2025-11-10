import sys
import subprocess
import shutil
from pathlib import Path

class LanguageModule:
    """
    Node.js runtime interface for CAL.
    Handles discovery, execution, and plugin loading for Node.js plugins.
    """

    def __init__(self, core, runtime_path=None, runtime_version=None):
        self.core = core
        self.runtime_path = runtime_path
        self.runtime_version = runtime_version
        self.proc = None
        self.node_exe = self._find_node_executable()
        print(f"[nodejs] Using interpreter: {self.node_exe}")

    # ---------------------------------------------------------------------
    # Runtime management
    # ---------------------------------------------------------------------
    def _find_node_executable(self):
        """Locate Node.js executable across OSes."""
        # If explicit runtime path given
        if self.runtime_path:
            exe = Path(self.runtime_path)
            if exe.is_dir():
                exe = exe / ("node.exe" if sys.platform.startswith("win") else "node")
            if exe.exists():
                return str(exe)

        # Otherwise fall back to system Node.js
        system_node = shutil.which("node")
        if not system_node:
            raise FileNotFoundError("No Node.js runtime found on system.")
        return system_node

    # ---------------------------------------------------------------------
    # Plugin loading
    # ---------------------------------------------------------------------
    def load_plugin(self, plugin_data, package_path):
        """
        Loads a plugin written in Node.js.
        Returns a dict with plugin info and callable path.
        """
        entry = plugin_data.get("entry", "main.js")
        entry_path = Path(package_path) / entry
        if not entry_path.exists():
            raise FileNotFoundError(f"[nodejs] Plugin entry not found: {entry_path}")

        return {"path": str(entry_path)}

    # ---------------------------------------------------------------------
    # Execution
    # ---------------------------------------------------------------------
    def run_code(self, plugin_info):
        """Execute a Node.js plugin file and return stdout."""
        plugin_path = plugin_info["path"]
        try:
            result = subprocess.run(
                [self.node_exe, plugin_path],
                capture_output=True,
                text=True
            )
            if result.stderr:
                print(f"[nodejs:error] {result.stderr.strip()}")
            return result.stdout.strip()
        except Exception as e:
            return f"[nodejs:exception] {e}"

    # ---------------------------------------------------------------------
    def stop(self):
        """No persistent runtime for Node.js, so nothing to stop."""
        pass
