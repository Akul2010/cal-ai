// languages/nodejs/wrapper.js

const fs = require('fs');
const path = require('path');

// Get command line arguments
const pluginPath = process.argv[2];
const exportName = process.argv[3];
const slotsJson = process.argv[4];

if (!pluginPath || !exportName) {
    console.error("Usage: node wrapper.js <plugin_path> <export_name> [slots_json]");
    process.exit(1);
}

try {
    // Load the plugin module
    const plugin = require(path.resolve(pluginPath));

    // Get the function to call
    const func = plugin[exportName];
    if (typeof func !== 'function') {
        throw new Error(`Export '${exportName}' not found or not a function in plugin.`);
    }

    // Parse slots
    let slots = {};
    if (slotsJson) {
        slots = JSON.parse(slotsJson);
    }

    // Call the function
    const result = func(slots);

    // Output the result
    if (typeof result === 'object') {
        console.log(JSON.stringify(result));
    } else {
        console.log(result);
    }

} catch (e) {
    console.error(`Error executing plugin: ${e.message}`);
    process.exit(1);
}
