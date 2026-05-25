"""
ComfyUI MixLab Nodes V2
A modern rewrite of comfyui-mixlab-nodes, fully compatible with ComfyUI v0.21.0+
Supports drag-and-drop images/workflows, URL image loading, batch loading, and modern frontend APIs.
"""

import os
from .py.nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

WEB_DIRECTORY = os.path.join(os.path.dirname(__file__), "js")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

print("[MixLab V2] Loaded successfully. Frontend extensions registered.")
