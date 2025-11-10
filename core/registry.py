class Registry:
    """
    Simple registry: stores plugin instances and callables (exports).
    """
    def __init__(self):
        self.plugins = {}   # plugin_name -> { instance, manifest }
        self.exports = {}   # "plugin:export" -> callable

    def register_plugin(self, name, instance, manifest):
        self.plugins[name] = {'instance': instance, 'manifest': manifest}

    def register_export(self, plugin_name, export_name, callable_handle):
        key = f"{plugin_name}:{export_name}"
        self.exports[key] = callable_handle

    def call_export(self, plugin_name, export_name, *args, **kwargs):
        key = f"{plugin_name}:{export_name}"
        if key not in self.exports:
            raise KeyError(f"Export not found: {key}")
        return self.exports[key](*args, **kwargs)

    def get_manifest(self, plugin_name):
        p = self.plugins.get(plugin_name)
        return p['manifest'] if p else None