import os
import sys

# 添加模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入节点
from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# 注册节点
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

# 定义JS扩展
WEB_DIRECTORY = "./js"

# 节点类别
CATEGORY = "Mixlab"