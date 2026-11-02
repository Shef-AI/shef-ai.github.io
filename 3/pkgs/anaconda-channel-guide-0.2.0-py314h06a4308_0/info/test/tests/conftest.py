from __future__ import annotations

from conda.base.context import context

# Load plugins before test modules are imported.
# This ensures that context.plugins.anaconda_channel_guide exists
# when tests try to patch it.
context.plugin_manager.load_plugins()
