# languages/python3/wrapper.py

import sys
import json
import importlib.util
from pathlib import Path

def run_plugin(plugin_path, export_name, slots):
    try:
        # Load the plugin module
        spec = importlib.util.spec_from_file_location("plugin", plugin_path)
        plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin)

        # Get the function to call
        func = getattr(plugin, export_name, None)
        if not func or not callable(func):
            raise AttributeError(f"Export '{export_name}' not found or not a function in plugin.")

        # Call the function
        result = func(slots)

        # Output the result
        if isinstance(result, dict) or isinstance(result, list):
            print(json.dumps(result))
        else:
            print(result)

    except Exception as e:
        print(f"Error executing plugin: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python wrapper.py <plugin_path> <export_name> [slots_json]", file=sys.stderr)
        sys.exit(1)

    plugin_path = sys.argv[1]
    export_name = sys.argv[2]
    slots_json = sys.argv[3] if len(sys.argv) > 3 else '{}'

    try:
        slots = json.loads(slots_json)
    except json.JSONDecodeError:
        print("Error: Invalid JSON for slots.", file=sys.stderr)
        sys.exit(1)

    run_plugin(plugin_path, export_name, slots)
