"""
ComfyUI MixLab Nodes V2
A modern rewrite of comfyui-mixlab-nodes, fully compatible with ComfyUI v0.21.0+
Supports drag-and-drop images/workflows, batch loading, and modern frontend APIs.
No popups, no extra UI elements - clean and minimal.
"""

import os
import sys
import json
import folder_paths
from .py.nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from .py.server import add_routes

# Register web directory for frontend extensions
WEB_DIRECTORY = os.path.join(os.path.dirname(__file__), "js")

# Node registration
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

print("[MixLab V2 v2.0.1] Loaded. Clean mode - no popups.")
