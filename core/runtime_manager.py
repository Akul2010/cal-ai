import os
import json
import time
import shutil
import subprocess
import sys
from tools.semver_utils import Version

class RuntimeManager:
    """
    Discovers system runtimes (python/node/go) and otherwise creates a cross-platform simulated runtime.
    Stores installations under base_dir (default /cal_ai/.cal_runtimes).
    """
    def __init__(self, base_dir=None, policy=None):
        # default base dir under workspace root if provided, else /cal_ai
        default_base = base_dir or os.path.join(os.path.abspath(os.sep), 'cal_ai')  # fallback root
        # But prefer environment variable if present
        env_base = os.environ.get('CAL_BASE_DIR')
        self.base_dir = os.path.expanduser(env_base or default_base)
        os.makedirs(self.base_dir, exist_ok=True)
        self.cache_file = os.path.join(self.base_dir, 'runtime_cache.json')
        self.cache = self._load_cache()
        self.policy = policy or {'prefer_reuse': True}
        self.locks_dir = os.path.join(self.base_dir, 'locks')
        os.makedirs(self.locks_dir, exist_ok=True)

    def _load_cache(self):
        try:
            return json.load(open(self.cache_file,'r'))
        except Exception:
            return {}

    def _save_cache(self):
        try:
            json.dump(self.cache, open(self.cache_file,'w'), indent=2)
        except Exception:
            pass

    def discover_system_runtimes(self):
        """
        Probe PATH for common runtimes and record them in cache as language->version->path.
        """
        if self.cache.get('_discovered'):
            return
        candidates = {
            "python": [("python3","--version", r"Python (\d+\.\d+\.\d+)"),
                       ("python","--version", r"Python (\d+\.\d+\.\d+)")],
            "node": [("node","--version", r"v?(\d+\.\d+\.\d+)")],
            "go":   [("go","version", r"go version go(\d+\.\d+\.\d+)")]
        }
        import re
        for lang, bins in candidates.items():
            for bin_name, arg, regex in bins:
                path = shutil.which(bin_name)
                if not path:
                    continue
                try:
                    proc = subprocess.run([path, arg], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=2)
                    m = re.search(regex, proc.stdout or "")
                    if m:
                        ver = m.group(1)
                        # store path to binary's directory
                        self._record_install(lang, ver, os.path.dirname(path))
                        print(f"[CAL][runtime] Found system {lang} {ver} at {path}")
                        break
                except Exception:
                    continue
        self.cache['_discovered'] = True
        self._save_cache()

    def find_installed_versions(self, language):
        return list(self.cache.get(language, {}).keys())

    def _max_version(self, versions):
        if not versions:
            return None
        return max(versions, key=lambda v: Version(v))

    def find_compatible_version(self, installed_versions, version_spec):
        if not version_spec or version_spec in ('latest','*', None):
            return self._max_version(installed_versions)
        if version_spec in installed_versions:
            return version_spec
        if isinstance(version_spec, str) and version_spec.startswith('^'):
            base = Version(version_spec[1:])
            cand = [v for v in installed_versions if Version(v).parts[0] == base.parts[0] and Version(v) >= base]
            return max(cand, key=lambda v: Version(v)) if cand else None
        return None

    def choose_version_to_install(self, language, version_spec):
        defaults = {'python':'3.11.5', 'node':'20.6.0', 'go':'1.21.3'}
        if not version_spec or version_spec in ('latest','*', None):
            return defaults.get(language, '1.0.0')
        return version_spec

    def ensure_runtime(self, language, version_spec):
        # discover system runtimes once
        self.discover_system_runtimes()
        installed = self.find_installed_versions(language)
        found = self.find_compatible_version(installed, version_spec)
        if found:
            return (self.get_runtime_path(language, found), found)
        to_install = self.choose_version_to_install(language, version_spec)
        lockfh = self._acquire_lock(language, to_install)
        try:
            # re-check after lock
            installed = self.find_installed_versions(language)
            found = self.find_compatible_version(installed, version_spec)
            if found:
                return (self.get_runtime_path(language, found), found)
            path = self.download_and_install(language, to_install)
            self._record_install(language, to_install, path)
            return (path, to_install)
        finally:
            self._release_lock(lockfh)

    def _acquire_lock(self, language, version):
        lockfile = os.path.join(self.locks_dir, f"{language}-{version}.lock")
        fh = open(lockfile, 'w')
        try:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX)
        except Exception:
            pass
        return fh

    def _release_lock(self, fh):
        try:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            fh.close()
        except Exception:
            pass

    def _record_install(self, language, version, path):
        self.cache.setdefault(language, {})[version] = path
        self._save_cache()

    def get_runtime_path(self, language, version):
        return self.cache[language][version]

    def download_and_install(self, language, version):
        """
        Create a cross-platform simulated runtime under base_dir/runtimes/<language>/<version>/bin/
        On Windows produce a .bat; on POSIX produce an executable shell script.
        The simulated runtime is intentionally simple for dev/testing: it echoes stdin to stdout.
        """
        target = os.path.join(self.base_dir, 'runtimes', language, version)
        os.makedirs(target, exist_ok=True)
        meta = {'language':language, 'version':version, 'installed_at': time.time()}
        try:
            json.dump(meta, open(os.path.join(target,'meta.json'),'w'), indent=2)
        except Exception:
            pass
        bin_dir = os.path.join(target, 'bin')
        os.makedirs(bin_dir, exist_ok=True)
        import stat
        if sys.platform.startswith("win"):
            exe_name = f"{language}_runtime.bat"
            exe_path = os.path.join(bin_dir, exe_name)
            with open(exe_path, 'w', newline='\r\n') as fh:
                fh.write(f"@echo off\r\n")
                fh.write(f"echo SIMULATED RUNTIME: {language} {version}\r\n")
                # simple echo: read a line and write it back
                fh.write("set /p IN=\r\n")
                fh.write("echo %IN%\r\n")
        else:
            exe_name = f"{language}_runtime"
            exe_path = os.path.join(bin_dir, exe_name)
            with open(exe_path, 'w', newline='\n') as fh:
                fh.write("#!/bin/sh\n")
                fh.write(f'echo "SIMULATED RUNTIME: {language} {version}" >&2\n')
                fh.write("cat -\n")
            st = os.stat(exe_path)
            os.chmod(exe_path, st.st_mode | stat.S_IEXEC)
        return target
