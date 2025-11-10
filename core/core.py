import json
import importlib
from pathlib import Path


class Core:
    """
    CAL Core System
    ----------------
    Responsible for:
      - Discovering and loading plugins
      - Managing language runtimes
      - Coordinating with assistant + NLU layer
    """

    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.languages_dir = self.base_dir / "languages"
        self.plugins_dir = self.base_dir / "plugins"
        self.runtime_dir = self.base_dir / ".cal_ai" / "runtimes"
        self.language_modules = {}
        self.plugins = {}
        print("[core] initialized")

    # ---------------------------------------------------------------------
    # Discovery and loading
    # ---------------------------------------------------------------------
    def resolve_and_load(self):
        """Discover runtimes, load languages, then load all plugins."""
        print("[core] discovering languages and plugins...")

        for lang_dir in self.languages_dir.iterdir():
            if not lang_dir.is_dir():
                continue
            lang_name = lang_dir.name.lower()
            loader_path = lang_dir / "loader.py"

            if not loader_path.exists():
                print(f"[core:warn] No loader for language {lang_name}")
                continue

            mod_name = f"languages.{lang_name}.loader"
            try:
                mod = importlib.import_module(mod_name)
                runtime_path = self.find_runtime_path(lang_name)
                runtime_version = self.detect_runtime_version(lang_name, runtime_path)

                lm = mod.LanguageModule(
                    core=self,
                    runtime_path=runtime_path,
                    runtime_version=runtime_version
                )
                self.language_modules[lang_name] = lm
                print(f"[core] Loaded language module: {lang_name}")

            except Exception as e:
                print(f"[core:error] Failed to load {lang_name}: {e}")

        # Load all plugins
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            plugin_meta = plugin_dir / "plugin.json"
            if not plugin_meta.exists():
                print(f"[core:warn] Plugin missing metadata: {plugin_dir.name}")
                continue

            try:
                with open(plugin_meta, "r", encoding="utf-8") as f:
                    data = json.load(f)

                lang = data.get("language", "python").lower()
                if lang not in self.language_modules:
                    print(f"[core:warn] No runtime for {lang}, skipping {plugin_dir.name}")
                    continue

                lm = self.language_modules[lang]
                plugin_info = lm.load_plugin(data, plugin_dir)
                self.plugins[plugin_dir.name] = {
                    "lang": lang,
                    "meta": data,
                    "info": plugin_info
                }
                print(f"[core] Registered plugin: {plugin_dir.name} ({lang})")

            except Exception as e:
                print(f"[core:error] Failed to load plugin {plugin_dir.name}: {e}")

    # ---------------------------------------------------------------------
    # Runtime helpers
    # ---------------------------------------------------------------------
    def find_runtime_path(self, language):
        """Locate or create runtime directory for a given language."""
        lang_dir = self.runtime_dir / language
        lang_dir.mkdir(parents=True, exist_ok=True)
        return str(lang_dir)

    def detect_runtime_version(self, language, runtime_path):
        """Detect runtime version if available."""
        if language == "python":
            import sys
            return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        elif language == "nodejs":
            import subprocess, shutil
            node_bin = shutil.which("node")
            if node_bin:
                try:
                    out = subprocess.check_output([node_bin, "--version"], text=True).strip()
                    return out.lstrip("v")
                except Exception:
                    pass
        return "unknown"

    # ---------------------------------------------------------------------
    # Plugin execution
    # ---------------------------------------------------------------------
    def run_plugin(self, name):
        """Run a plugin by name and return its output."""
        if name not in self.plugins:
            return f"[core:error] Plugin '{name}' not found."

        plugin = self.plugins[name]
        lang = plugin["lang"]
        lm = self.language_modules.get(lang)
        if not lm:
            return f"[core:error] Language module '{lang}' missing."

        try:
            return lm.run_code(plugin["info"])
        except Exception as e:
            return f"[core:error] Failed to run plugin '{name}': {e}"

    # ---------------------------------------------------------------------
    def list_plugins(self):
        """Return all loaded plugins."""
        return list(self.plugins.keys())

    def stop_all(self):
        """Gracefully stop all runtimes."""
        for lang, lm in self.language_modules.items():
            try:
                lm.stop()
                print(f"[core] stopped runtime {lang}")
            except Exception as e:
                print(f"[core:warn] Failed to stop {lang}: {e}")
