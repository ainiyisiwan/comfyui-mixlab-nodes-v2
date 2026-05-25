"""
MixLab V2 后端节点 - 中文版
"""

import os
import io
import json
import urllib.request
import torch
import numpy as np
from PIL import Image, PngImagePlugin
import folder_paths
from comfy.comfy_types import IO, ComfyNodeABC, InputTypeDict


class LoadImageFromPath(ComfyNodeABC):
    """从本地路径加载图像"""

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "图像路径": ("STRING", {"default": "", "multiline": False, "tooltip": "图像文件的绝对路径"}),
            },
            "optional": {
                "宽度": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 1, "tooltip": "调整宽度（0=保持原尺寸）"}),
                "高度": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 1, "tooltip": "调整高度（0=保持原尺寸）"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING")
    RETURN_NAMES = ("图像", "遮罩", "元数据")
    FUNCTION = "load_image"
    CATEGORY = "MixLab V2/图像"
    DESCRIPTION = "从本地路径加载图像文件，支持前端拖放导入"

    def load_image(self, 图像路径: str, 宽度: int = 0, 高度: int = 0):
        if not 图像路径 or not os.path.exists(图像路径):
            empty = torch.zeros(1, 64, 64, 3)
            return (empty, torch.zeros(1, 64, 64), "")

        img = Image.open(图像路径)
        img = img.convert("RGB") if img.mode != "RGBA" else img.convert("RGBA")

        # 提取元数据
        元数据 = ""
        try:
            if hasattr(img, 'info') and 'workflow' in img.info:
                元数据 = img.info['workflow']
            elif hasattr(img, 'info') and 'prompt' in img.info:
                元数据 = img.info['prompt']
        except:
            pass

        # 调整尺寸
        if 宽度 > 0 or 高度 > 0:
            w, h = img.size
            if 宽度 == 0:
                宽度 = int(w * 高度 / h)
            if 高度 == 0:
                高度 = int(h * 宽度 / w)
            img = img.resize((宽度, 高度), Image.LANCZOS)

        # 转为张量
        img_array = np.array(img).astype(np.float32) / 255.0

        if img.mode == "RGBA":
            图像 = torch.from_numpy(img_array[:, :, :3])[None,]
            遮罩 = torch.from_numpy(img_array[:, :, 3])[None,]
        else:
            图像 = torch.from_numpy(img_array)[None,]
            遮罩 = torch.zeros((1, img.size[1], img.size[0]), dtype=torch.float32)

        return (图像, 遮罩, 元数据)


class LoadImageFromURL(ComfyNodeABC):
    """从网络地址加载图像"""

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "网络地址": ("STRING", {"default": "https://", "multiline": False, "tooltip": "图像网络地址 (http/https)"}),
            },
            "optional": {
                "超时时间": ("INT", {"default": 30, "min": 5, "max": 300, "step": 5, "tooltip": "下载超时时间（秒）"}),
                "浏览器标识": ("STRING", {"default": "Mozilla/5.0", "multiline": False, "tooltip": "浏览器标识请求头"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING")
    RETURN_NAMES = ("图像", "遮罩", "元数据")
    FUNCTION = "load_from_url"
    CATEGORY = "MixLab V2/图像"
    DESCRIPTION = "从网络地址加载图像，支持 http/https 自定义请求头"

    def load_from_url(self, 网络地址: str, 超时时间: int = 30, 浏览器标识: str = ""):
        if not 网络地址 or not (网络地址.startswith("http://") or 网络地址.startswith("https://")):
            empty = torch.zeros(1, 64, 64, 3)
            return (empty, torch.zeros(1, 64, 64), "无效地址")

        try:
            req = urllib.request.Request(网络地址)
            req.add_header("User-Agent", 浏览器标识 or "Mozilla/5.0")
            req.add_header("Accept", "image/*,*/*")

            with urllib.request.urlopen(req, timeout=超时时间) as response:
                data = response.read()
                img = Image.open(io.BytesIO(data))

                if img.mode in ("P", "L", "LA"):
                    img = img.convert("RGBA") if "A" in img.mode else img.convert("RGB")
                elif img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")

                # 提取元数据
                元数据 = ""
                try:
                    if hasattr(img, 'info') and 'workflow' in img.info:
                        元数据 = img.info['workflow']
                except:
                    pass

                # 转为张量
                img_array = np.array(img).astype(np.float32) / 255.0

                if img.mode == "RGBA":
                    图像 = torch.from_numpy(img_array[:, :, :3])[None,]
                    遮罩 = torch.from_numpy(img_array[:, :, 3])[None,]
                else:
                    图像 = torch.from_numpy(img_array)[None,]
                    遮罩 = torch.zeros((1, img.size[1], img.size[0]), dtype=torch.float32)

                return (图像, 遮罩, 元数据)

        except Exception as e:
            print(f"[MixLab V2] 网络图像加载失败: {e}")
            empty = torch.zeros(1, 64, 64, 3)
            return (empty, torch.zeros(1, 64, 64), str(e))


class LoadImagesToBatch(ComfyNodeABC):
    """批量加载目录图像"""

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "目录路径": ("STRING", {"default": "", "multiline": False, "tooltip": "包含图像文件的目录路径"}),
                "匹配模式": ("STRING", {"default": "*.png", "tooltip": "文件匹配模式（如 *.png, *.jpg）"}),
            },
            "optional": {
                "最大数量": ("INT", {"default": 10, "min": 1, "max": 100, "step": 1}),
                "排序方式": (["名称", "日期", "大小"], {"default": "名称"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("图像批次", "数量")
    FUNCTION = "load_batch"
    CATEGORY = "MixLab V2/图像"
    DESCRIPTION = "从目录批量加载多张图像为张量批次"

    def load_batch(self, 目录路径: str, 匹配模式: str, 最大数量: int = 10, 排序方式: str = "名称"):
        import glob

        if not 目录路径 or not os.path.exists(目录路径):
            empty = torch.zeros(1, 64, 64, 3)
            return (empty, 0)

        files = glob.glob(os.path.join(目录路径, 匹配模式))

        if 排序方式 == "日期":
            files.sort(key=lambda x: os.path.getmtime(x))
        elif 排序方式 == "大小":
            files.sort(key=lambda x: os.path.getsize(x))
        else:
            files.sort()

        files = files[:最大数量]

        if not files:
            empty = torch.zeros(1, 64, 64, 3)
            return (empty, 0)

        images = []
        for f in files:
            try:
                img = Image.open(f).convert("RGB")
                img_array = np.array(img).astype(np.float32) / 255.0
                images.append(torch.from_numpy(img_array))
            except Exception as e:
                print(f"[MixLab V2] 跳过无效图像: {f} - {e}")
                continue

        if not images:
            empty = torch.zeros(1, 64, 64, 3)
            return (empty, 0)

        batch = torch.stack(images, dim=0)
        return (batch, len(images))


class ExtractWorkflowFromImage(ComfyNodeABC):
    """提取图像工作流"""

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "图像": ("IMAGE", {"tooltip": "包含工作流元数据的输入图像"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("工作流JSON", "提示词JSON")
    FUNCTION = "extract"
    CATEGORY = "MixLab V2/工作流"
    DESCRIPTION = "从生成的图像中提取嵌入的 ComfyUI 工作流和提示词"

    def extract(self, 图像):
        return ("", "")


class TextImage(ComfyNodeABC):
    """文字转图像"""

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "文字": ("STRING", {"default": "你好世界", "multiline": True}),
                "宽度": ("INT", {"default": 512, "min": 64, "max": 4096, "step": 64}),
                "高度": ("INT", {"default": 64, "min": 64, "max": 4096, "step": 64}),
                "字体大小": ("INT", {"default": 32, "min": 8, "max": 256, "step": 1}),
            },
            "optional": {
                "字体颜色": ("STRING", {"default": "#FFFFFF", "tooltip": "十六进制颜色代码"}),
                "背景颜色": ("STRING", {"default": "#000000", "tooltip": "十六进制颜色代码"}),
                "对齐方式": (["左对齐", "居中", "右对齐"], {"default": "居中"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("图像",)
    FUNCTION = "render_text"
    CATEGORY = "MixLab V2/图像"
    DESCRIPTION = "将文字字符串渲染为 RGB 图像，可用于水印或提示词"

    def render_text(self, 文字: str, 宽度: int, 高度: int, 字体大小: int, 
                    字体颜色: str = "#FFFFFF", 背景颜色: str = "#000000",
                    对齐方式: str = "居中"):
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (宽度, 高度), 背景颜色)
        draw = ImageDraw.Draw(img)

        # 加载字体
        font = None
        font_paths = [
            os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "NotoSansCJK-Regular.ttc"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]

        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    font = ImageFont.truetype(fp, 字体大小)
                    break
                except:
                    continue

        if font is None:
            font = ImageFont.load_default()

        # 计算文字位置
        bbox = draw.textbbox((0, 0), 文字, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        if 对齐方式 == "居中":
            x = (宽度 - text_width) // 2
        elif 对齐方式 == "右对齐":
            x = 宽度 - text_width
        else:
            x = 0

        y = (高度 - text_height) // 2

        draw.text((x, y), 文字, fill=字体颜色, font=font)

        img_array = np.array(img).astype(np.float32) / 255.0
        tensor = torch.from_numpy(img_array)[None,]

        return (tensor,)


class ImageCompositeMasked(ComfyNodeABC):
    """图像遮罩合成"""

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "背景": ("IMAGE",),
                "前景": ("IMAGE",),
                "遮罩": ("MASK",),
                "X坐标": ("INT", {"default": 0, "min": -4096, "max": 4096}),
                "Y坐标": ("INT", {"default": 0, "min": -4096, "max": 4096}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("合成图像",)
    FUNCTION = "composite"
    CATEGORY = "MixLab V2/图像"
    DESCRIPTION = "使用透明度遮罩将前景图像叠加到背景图像上"

    def composite(self, 背景, 前景, 遮罩, X坐标, Y坐标):
        bg = 背景[0].cpu().numpy()
        fg = 前景[0].cpu().numpy()
        m = 遮罩[0].cpu().numpy()

        h, w = bg.shape[:2]
        fh, fw = fg.shape[:2]

        result = bg.copy()

        x1, y1 = max(0, X坐标), max(0, Y坐标)
        x2, y2 = min(w, X坐标 + fw), min(h, Y坐标 + fh)

        if x2 > x1 and y2 > y1:
            fx1, fy1 = x1 - X坐标, y1 - Y坐标
            fx2, fy2 = fx1 + (x2 - x1), fy1 + (y2 - y1)

            fg_region = fg[fy1:fy2, fx1:fx2]
            m_region = m[fy1:fy2, fx1:fx2]
            m_region = np.expand_dims(m_region, axis=-1)

            result[y1:y2, x1:x2] = fg_region * m_region + result[y1:y2, x1:x2] * (1 - m_region)

        tensor = torch.from_numpy(result)[None,].to(背景.device)
        return (tensor,)


class SaveImageWithWorkflow(ComfyNodeABC):
    """保存图像+工作流"""

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "图像": ("IMAGE", {"tooltip": "要保存的图像"}),
                "文件名前缀": ("STRING", {"default": "MixLab"}),
            },
            "optional": {
                "嵌入工作流": ("BOOLEAN", {"default": True}),
                "压缩级别": ("INT", {"default": 4, "min": 0, "max": 9}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "MixLab V2/图像"
    DESCRIPTION = "保存图像并嵌入工作流元数据，支持拖放重新加载"

    def save(self, 图像, 文件名前缀="MixLab", 嵌入工作流=True, 压缩级别=4, prompt=None, extra_pnginfo=None):
        output_dir = folder_paths.get_output_directory()

        for idx, image in enumerate(图像):
            img = Image.fromarray(np.clip(255. * image.cpu().numpy(), 0, 255).astype(np.uint8))

            metadata = PngImagePlugin.PngInfo()
            if 嵌入工作流 and extra_pnginfo:
                if "workflow" in extra_pnginfo:
                    metadata.add_text("workflow", json.dumps(extra_pnginfo["workflow"]))
                if "prompt" in extra_pnginfo:
                    metadata.add_text("prompt", json.dumps(extra_pnginfo["prompt"]))

            filename = f"{文件名前缀}_{idx:05d}.png"
            filepath = os.path.join(output_dir, filename)
            img.save(filepath, pnginfo=metadata, compress_level=压缩级别)

        return {}


# 节点注册映射
NODE_CLASS_MAPPINGS = {
    "LoadImageFromPath_MixLabV2": LoadImageFromPath,
    "LoadImageFromURL_MixLabV2": LoadImageFromURL,
    "LoadImagesToBatch_MixLabV2": LoadImagesToBatch,
    "ExtractWorkflowFromImage_MixLabV2": ExtractWorkflowFromImage,
    "TextImage_MixLabV2": TextImage,
    "ImageCompositeMasked_MixLabV2": ImageCompositeMasked,
    "SaveImageWithWorkflow_MixLabV2": SaveImageWithWorkflow,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageFromPath_MixLabV2": "📁 加载图像路径 (MixLab V2)",
    "LoadImageFromURL_MixLabV2": "🌐 加载网络图像 (MixLab V2)",
    "LoadImagesToBatch_MixLabV2": "📂 批量加载图像 (MixLab V2)",
    "ExtractWorkflowFromImage_MixLabV2": "🔍 提取图像工作流 (MixLab V2)",
    "TextImage_MixLabV2": "📝 文字转图像 (MixLab V2)",
    "ImageCompositeMasked_MixLabV2": "🎭 图像遮罩合成 (MixLab V2)",
    "SaveImageWithWorkflow_MixLabV2": "💾 保存图像+工作流 (MixLab V2)",
}
