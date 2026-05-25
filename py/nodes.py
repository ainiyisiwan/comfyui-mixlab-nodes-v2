"""
Backend nodes for MixLab V2
"""

import os
import io
import json
import base64
import urllib.request
import urllib.parse
import torch
import numpy as np
from PIL import Image, PngImagePlugin
import folder_paths
import comfy.utils
from comfy.comfy_types import IO, ComfyNodeABC, InputTypeDict


class LoadImageFromPath(ComfyNodeABC):
    """Load image from absolute path with drag-and-drop support"""

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "image_path": ("STRING", {"default": "", "multiline": False, "tooltip": "Absolute path to image file"}),
            },
            "optional": {
                "width": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 1, "tooltip": "Resize width (0=original)"}),
                "height": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 1, "tooltip": "Resize height (0=original)"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING")
    RETURN_NAMES = ("image", "mask", "metadata")
    FUNCTION = "load_image"
    CATEGORY = "MixLab V2/Image"
    DESCRIPTION = "Load image from file path. Supports drag-and-drop from frontend."

    def load_image(self, image_path: str, width: int = 0, height: int = 0):
        if not image_path or not os.path.exists(image_path):
            empty = torch.zeros(1, 64, 64, 3)
            return (empty, torch.zeros(1, 64, 64), "")

        img = Image.open(image_path)
        img = img.convert("RGB") if img.mode != "RGBA" else img.convert("RGBA")

        # Extract metadata
        metadata = ""
        try:
            if hasattr(img, 'info') and 'workflow' in img.info:
                metadata = img.info['workflow']
            elif hasattr(img, 'info') and 'prompt' in img.info:
                metadata = img.info['prompt']
        except:
            pass

        # Resize if requested
        if width > 0 or height > 0:
            w, h = img.size
            if width == 0:
                width = int(w * height / h)
            if height == 0:
                height = int(h * width / w)
            img = img.resize((width, height), Image.LANCZOS)

        # Convert to tensor
        img_array = np.array(img).astype(np.float32) / 255.0

        if img.mode == "RGBA":
            image = torch.from_numpy(img_array[:, :, :3])[None,]
            mask = torch.from_numpy(img_array[:, :, 3])[None,]
        else:
            image = torch.from_numpy(img_array)[None,]
            mask = torch.zeros((1, img.size[1], img.size[0]), dtype=torch.float32)

        return (image, mask, metadata)


class LoadImageFromURL(ComfyNodeABC):
    """Load image from URL (http/https)"""

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "url": ("STRING", {"default": "https://", "multiline": False, "tooltip": "Image URL (http/https)"}),
            },
            "optional": {
                "timeout": ("INT", {"default": 30, "min": 5, "max": 300, "step": 5, "tooltip": "Download timeout in seconds"}),
                "user_agent": ("STRING", {"default": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "multiline": False, "tooltip": "User-Agent header"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING")
    RETURN_NAMES = ("image", "mask", "metadata")
    FUNCTION = "load_from_url"
    CATEGORY = "MixLab V2/Image"
    DESCRIPTION = "Load image from URL. Supports http/https with custom headers."

    def load_from_url(self, url: str, timeout: int = 30, user_agent: str = ""):
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            empty = torch.zeros(1, 64, 64, 3)
            return (empty, torch.zeros(1, 64, 64), "Invalid URL")

        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            req.add_header("Accept", "image/*,*/*")

            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = response.read()
                img = Image.open(io.BytesIO(data))

                # Convert to RGB/RGBA
                if img.mode in ("P", "L", "LA"):
                    img = img.convert("RGBA") if "A" in img.mode or "a" in img.mode else img.convert("RGB")
                elif img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")

                # Extract metadata
                metadata = ""
                try:
                    if hasattr(img, 'info') and 'workflow' in img.info:
                        metadata = img.info['workflow']
                except:
                    pass

                # Convert to tensor
                img_array = np.array(img).astype(np.float32) / 255.0

                if img.mode == "RGBA":
                    image = torch.from_numpy(img_array[:, :, :3])[None,]
                    mask = torch.from_numpy(img_array[:, :, 3])[None,]
                else:
                    image = torch.from_numpy(img_array)[None,]
                    mask = torch.zeros((1, img.size[1], img.size[0]), dtype=torch.float32)

                return (image, mask, metadata)

        except Exception as e:
            print(f"[MixLab V2] Failed to load image from URL: {e}")
            empty = torch.zeros(1, 64, 64, 3)
            return (empty, torch.zeros(1, 64, 64), str(e))


class LoadImagesToBatch(ComfyNodeABC):
    """Load multiple images from directory and batch them"""

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "directory": ("STRING", {"default": "", "multiline": False, "tooltip": "Directory containing images"}),
                "pattern": ("STRING", {"default": "*.png", "tooltip": "File glob pattern (e.g. *.png, *.jpg)"}),
            },
            "optional": {
                "max_images": ("INT", {"default": 10, "min": 1, "max": 100, "step": 1}),
                "sort_by": (["name", "date", "size"], {"default": "name"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("images", "count")
    FUNCTION = "load_batch"
    CATEGORY = "MixLab V2/Image"
    DESCRIPTION = "Load multiple images from directory as a batch tensor"

    def load_batch(self, directory: str, pattern: str, max_images: int = 10, sort_by: str = "name"):
        import glob

        if not directory or not os.path.exists(directory):
            empty = torch.zeros(1, 64, 64, 3)
            return (empty, 0)

        files = glob.glob(os.path.join(directory, pattern))

        # Sort files
        if sort_by == "date":
            files.sort(key=lambda x: os.path.getmtime(x))
        elif sort_by == "size":
            files.sort(key=lambda x: os.path.getsize(x))
        else:
            files.sort()

        files = files[:max_images]

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
                print(f"[MixLab V2] Skip invalid image: {f} - {e}")
                continue

        if not images:
            empty = torch.zeros(1, 64, 64, 3)
            return (empty, 0)

        batch = torch.stack(images, dim=0)
        return (batch, len(images))


class ExtractWorkflowFromImage(ComfyNodeABC):
    """Extract workflow JSON from PNG/WebP metadata"""

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "Input image containing workflow metadata"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("workflow_json", "prompt_json")
    FUNCTION = "extract"
    CATEGORY = "MixLab V2/Workflow"
    DESCRIPTION = "Extract embedded ComfyUI workflow and prompt from generated image"

    def extract(self, image):
        # Frontend extension handles actual extraction via server API
        # This node serves as a passthrough trigger
        return ("", "")


class TextImage(ComfyNodeABC):
    """Render text as image for prompts/watermarks"""

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "text": ("STRING", {"default": "Hello World", "multiline": True}),
                "width": ("INT", {"default": 512, "min": 64, "max": 4096, "step": 64}),
                "height": ("INT", {"default": 64, "min": 64, "max": 4096, "step": 64}),
                "font_size": ("INT", {"default": 32, "min": 8, "max": 256, "step": 1}),
            },
            "optional": {
                "font_color": ("STRING", {"default": "#FFFFFF", "tooltip": "Hex color code"}),
                "background_color": ("STRING", {"default": "#000000", "tooltip": "Hex color code"}),
                "align": (["left", "center", "right"], {"default": "center"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "render_text"
    CATEGORY = "MixLab V2/Image"
    DESCRIPTION = "Render text string as an RGB image"

    def render_text(self, text: str, width: int, height: int, font_size: int, 
                    font_color: str = "#FFFFFF", background_color: str = "#000000",
                    align: str = "center"):
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (width, height), background_color)
        draw = ImageDraw.Draw(img)

        # Load font
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
                    font = ImageFont.truetype(fp, font_size)
                    break
                except:
                    continue

        if font is None:
            font = ImageFont.load_default()

        # Calculate text position
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        if align == "center":
            x = (width - text_width) // 2
        elif align == "right":
            x = width - text_width
        else:
            x = 0

        y = (height - text_height) // 2

        draw.text((x, y), text, fill=font_color, font=font)

        img_array = np.array(img).astype(np.float32) / 255.0
        tensor = torch.from_numpy(img_array)[None,]

        return (tensor,)


class ImageCompositeMasked(ComfyNodeABC):
    """Composite two images with mask blending"""

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "background": ("IMAGE",),
                "foreground": ("IMAGE",),
                "mask": ("MASK",),
                "x": ("INT", {"default": 0, "min": -4096, "max": 4096}),
                "y": ("INT", {"default": 0, "min": -4096, "max": 4096}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "composite"
    CATEGORY = "MixLab V2/Image"
    DESCRIPTION = "Overlay foreground onto background using alpha mask"

    def composite(self, background, foreground, mask, x, y):
        bg = background[0].cpu().numpy()
        fg = foreground[0].cpu().numpy()
        m = mask[0].cpu().numpy()

        h, w = bg.shape[:2]
        fh, fw = fg.shape[:2]

        result = bg.copy()

        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(w, x + fw), min(h, y + fh)

        if x2 > x1 and y2 > y1:
            fx1, fy1 = x1 - x, y1 - y
            fx2, fy2 = fx1 + (x2 - x1), fy1 + (y2 - y1)

            fg_region = fg[fy1:fy2, fx1:fx2]
            m_region = m[fy1:fy2, fx1:fx2]
            m_region = np.expand_dims(m_region, axis=-1)

            result[y1:y2, x1:x2] = fg_region * m_region + result[y1:y2, x1:x2] * (1 - m_region)

        tensor = torch.from_numpy(result)[None,].to(background.device)
        return (tensor,)


class SaveImageWithWorkflow(ComfyNodeABC):
    """Save image with embedded workflow metadata"""

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "Images to save"}),
                "filename_prefix": ("STRING", {"default": "MixLab"}),
            },
            "optional": {
                "embed_workflow": ("BOOLEAN", {"default": True}),
                "compress_level": ("INT", {"default": 4, "min": 0, "max": 9}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "MixLab V2/Image"
    DESCRIPTION = "Save image with embedded workflow metadata for drag-and-drop loading"

    def save(self, images, filename_prefix="MixLab", embed_workflow=True, compress_level=4, prompt=None, extra_pnginfo=None):
        output_dir = folder_paths.get_output_directory()

        for idx, image in enumerate(images):
            img = Image.fromarray(np.clip(255. * image.cpu().numpy(), 0, 255).astype(np.uint8))

            metadata = PngImagePlugin.PngInfo()
            if embed_workflow and extra_pnginfo:
                if "workflow" in extra_pnginfo:
                    metadata.add_text("workflow", json.dumps(extra_pnginfo["workflow"]))
                if "prompt" in extra_pnginfo:
                    metadata.add_text("prompt", json.dumps(extra_pnginfo["prompt"]))

            filename = f"{filename_prefix}_{idx:05d}.png"
            filepath = os.path.join(output_dir, filename)
            img.save(filepath, pnginfo=metadata, compress_level=compress_level)

        return {}


# Node registration
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
    "LoadImageFromPath_MixLabV2": "📁 Load Image From Path (MixLab V2)",
    "LoadImageFromURL_MixLabV2": "🌐 Load Image From URL (MixLab V2)",
    "LoadImagesToBatch_MixLabV2": "📂 Load Images To Batch (MixLab V2)",
    "ExtractWorkflowFromImage_MixLabV2": "🔍 Extract Workflow From Image (MixLab V2)",
    "TextImage_MixLabV2": "📝 Text To Image (MixLab V2)",
    "ImageCompositeMasked_MixLabV2": "🎭 Image Composite Masked (MixLab V2)",
    "SaveImageWithWorkflow_MixLabV2": "💾 Save Image + Workflow (MixLab V2)",
}
