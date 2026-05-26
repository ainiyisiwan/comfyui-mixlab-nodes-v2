import os
import json
import hashlib
import glob
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import numpy as np
import requests
from io import BytesIO
import torch
import comfy.utils

class ImageUploadNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE", {}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")
    FUNCTION = "process"
    CATEGORY = "Mixlab/图片"

    def process(self, image):
        if isinstance(image, np.ndarray):
            image = torch.from_numpy(image)
        
        mask = None
        if len(image.shape) == 4 and image.shape[3] == 4:
            mask = image[:, :, :, 3:]
            image = image[:, :, :, :3]
        else:
            mask = torch.ones((image.shape[0], image.shape[1], image.shape[2], 1), dtype=torch.float32)
        return (image, mask)

class LoadImageFromURL:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "url": ("STRING", {"default": "https://example.com/image.jpg", "multiline": True}),
                "timeout": ("INT", {"default": 10, "min": 1, "max": 60}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")
    FUNCTION = "load_image"
    CATEGORY = "Mixlab/图片"

    def load_image(self, url, timeout=10):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert("RGBA")
            image = np.array(image).astype(np.float32) / 255.0
            image = np.expand_dims(image, axis=0)
            
            mask = image[:, :, :, 3:]
            image = image[:, :, :, :3]
            
            image = torch.from_numpy(image)
            mask = torch.from_numpy(mask)
            
            return (image, mask)
        except Exception as e:
            raise RuntimeError(f"从URL加载图片失败: {str(e)}")

class LoadImageFromPath:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image_path": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")
    FUNCTION = "load_image"
    CATEGORY = "Mixlab/图片"

    def load_image(self, image_path):
        if not image_path or not os.path.exists(image_path):
            raise RuntimeError(f"图片路径不存在: {image_path}")
        
        image = Image.open(image_path).convert("RGBA")
        image = np.array(image).astype(np.float32) / 255.0
        image = np.expand_dims(image, axis=0)
        
        mask = image[:, :, :, 3:]
        image = image[:, :, :, :3]
        
        image = torch.from_numpy(image)
        mask = torch.from_numpy(mask)
        
        return (image, mask)

class LoadWorkflowImage:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE", {}),
            },
            "optional": {
                "extract_metadata": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("image", "mask", "positive_prompt", "negative_prompt", "model_name")
    FUNCTION = "process"
    CATEGORY = "Mixlab/图片"

    def process(self, image, extract_metadata=True):
        if isinstance(image, np.ndarray):
            image = torch.from_numpy(image)
        
        mask = None
        if len(image.shape) == 4 and image.shape[3] == 4:
            mask = image[:, :, :, 3:]
            image = image[:, :, :, :3]
        else:
            mask = torch.ones((image.shape[0], image.shape[1], image.shape[2], 1), dtype=torch.float32)
        
        positive_prompt = ""
        negative_prompt = ""
        model_name = ""
        
        return (image, mask, positive_prompt, negative_prompt, model_name)


class ImageResize:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE", {}),
                "width": ("INT", {"default": 512, "min": 1, "max": 16384}),
                "height": ("INT", {"default": 512, "min": 1, "max": 16384}),
                "mode": (["bilinear", "nearest", "bicubic", "lanczos"], {"default": "bilinear"}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "resize"
    CATEGORY = "Mixlab/图像处理"

    def resize(self, image, width, height, mode="bilinear"):
        if isinstance(image, torch.Tensor):
            image = image.cpu().numpy()
        
        resized_images = []
        for img in image:
            img_pil = Image.fromarray((img * 255).astype(np.uint8))
            img_resized = img_pil.resize((width, height), Image.Resampling[mode.upper()])
            resized_images.append(np.array(img_resized).astype(np.float32) / 255.0)
        
        result = np.stack(resized_images, axis=0)
        return (torch.from_numpy(result),)


class ImageCrop:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE", {}),
                "x": ("INT", {"default": 0, "min": 0}),
                "y": ("INT", {"default": 0, "min": 0}),
                "width": ("INT", {"default": 512, "min": 1}),
                "height": ("INT", {"default": 512, "min": 1}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "crop"
    CATEGORY = "Mixlab/图像处理"

    def crop(self, image, x, y, width, height):
        if isinstance(image, torch.Tensor):
            image = image.cpu().numpy()
        
        cropped_images = []
        for img in image:
            img_pil = Image.fromarray((img * 255).astype(np.uint8))
            img_cropped = img_pil.crop((x, y, x + width, y + height))
            cropped_images.append(np.array(img_cropped).astype(np.float32) / 255.0)
        
        result = np.stack(cropped_images, axis=0)
        return (torch.from_numpy(result),)


class ImageFlip:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE", {}),
                "direction": (["horizontal", "vertical", "both"], {"default": "horizontal"}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "flip"
    CATEGORY = "Mixlab/图像处理"

    def flip(self, image, direction="horizontal"):
        if isinstance(image, torch.Tensor):
            image = image.cpu().numpy()
        
        flipped_images = []
        for img in image:
            img_pil = Image.fromarray((img * 255).astype(np.uint8))
            if direction == "horizontal":
                img_flipped = ImageOps.mirror(img_pil)
            elif direction == "vertical":
                img_flipped = ImageOps.flip(img_pil)
            else:
                img_flipped = ImageOps.mirror(ImageOps.flip(img_pil))
            flipped_images.append(np.array(img_flipped).astype(np.float32) / 255.0)
        
        result = np.stack(flipped_images, axis=0)
        return (torch.from_numpy(result),)


class ImageRotate:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE", {}),
                "angle": ("FLOAT", {"default": 90.0, "min": -360.0, "max": 360.0, "step": 0.1}),
                "expand": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "rotate"
    CATEGORY = "Mixlab/图像处理"

    def rotate(self, image, angle, expand=False):
        if isinstance(image, torch.Tensor):
            image = image.cpu().numpy()
        
        rotated_images = []
        for img in image:
            img_pil = Image.fromarray((img * 255).astype(np.uint8))
            img_rotated = img_pil.rotate(angle, expand=expand)
            rotated_images.append(np.array(img_rotated).astype(np.float32) / 255.0)
        
        result = np.stack(rotated_images, axis=0)
        return (torch.from_numpy(result),)


class ImageAdjust:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE", {}),
                "brightness": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.01}),
                "contrast": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.01}),
                "saturation": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.01}),
                "sharpness": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.01}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "adjust"
    CATEGORY = "Mixlab/图像处理"

    def adjust(self, image, brightness, contrast, saturation, sharpness):
        if isinstance(image, torch.Tensor):
            image = image.cpu().numpy()
        
        adjusted_images = []
        for img in image:
            img_pil = Image.fromarray((img * 255).astype(np.uint8))
            
            if brightness != 1.0:
                enhancer = ImageEnhance.Brightness(img_pil)
                img_pil = enhancer.enhance(brightness)
            if contrast != 1.0:
                enhancer = ImageEnhance.Contrast(img_pil)
                img_pil = enhancer.enhance(contrast)
            if saturation != 1.0:
                enhancer = ImageEnhance.Color(img_pil)
                img_pil = enhancer.enhance(saturation)
            if sharpness != 1.0:
                enhancer = ImageEnhance.Sharpness(img_pil)
                img_pil = enhancer.enhance(sharpness)
            
            adjusted_images.append(np.array(img_pil).astype(np.float32) / 255.0)
        
        result = np.stack(adjusted_images, axis=0)
        return (torch.from_numpy(result),)


class ImageBlur:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE", {}),
                "blur_type": (["gaussian", "box", "median"], {"default": "gaussian"}),
                "radius": ("FLOAT", {"default": 2.0, "min": 0.0, "max": 50.0, "step": 0.1}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "blur"
    CATEGORY = "Mixlab/图像处理"

    def blur(self, image, blur_type="gaussian", radius=2.0):
        if isinstance(image, torch.Tensor):
            image = image.cpu().numpy()
        
        blurred_images = []
        for img in image:
            img_pil = Image.fromarray((img * 255).astype(np.uint8))
            if blur_type == "gaussian":
                img_blurred = img_pil.filter(ImageFilter.GaussianBlur(radius=radius))
            elif blur_type == "box":
                img_blurred = img_pil.filter(ImageFilter.BoxBlur(radius=int(radius)))
            else:
                img_blurred = img_pil.filter(ImageFilter.MedianFilter(size=int(radius) * 2 + 1))
            blurred_images.append(np.array(img_blurred).astype(np.float32) / 255.0)
        
        result = np.stack(blurred_images, axis=0)
        return (torch.from_numpy(result),)


class ImageComposite:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "background": ("IMAGE", {}),
                "foreground": ("IMAGE", {}),
                "x": ("INT", {"default": 0}),
                "y": ("INT", {"default": 0}),
            },
            "optional": {
                "mask": ("MASK", {}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "composite"
    CATEGORY = "Mixlab/图像处理"

    def composite(self, background, foreground, x, y, mask=None):
        if isinstance(background, torch.Tensor):
            background = background.cpu().numpy()
        if isinstance(foreground, torch.Tensor):
            foreground = foreground.cpu().numpy()
        if mask is not None and isinstance(mask, torch.Tensor):
            mask = mask.cpu().numpy()
        
        bg_pil = Image.fromarray((background[0] * 255).astype(np.uint8))
        fg_pil = Image.fromarray((foreground[0] * 255).astype(np.uint8))
        
        if mask is not None:
            mask_pil = Image.fromarray((mask[0, :, :, 0] * 255).astype(np.uint8))
            fg_pil.putalpha(mask_pil)
        
        bg_pil.paste(fg_pil, (x, y), fg_pil if mask is not None else None)
        
        result = np.array(bg_pil).astype(np.float32) / 255.0
        result = np.expand_dims(result, axis=0)
        return (torch.from_numpy(result),)


class LoadImagesFromFolder:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input_path": ("STRING", {"default": "./input"}),
                "start_index": ("INT", {"default": 0, "min": 0}),
                "max_images": ("INT", {"default": 1, "min": 1, "max": 1000}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "INT", "STRING", "INT", "INT", "INT")
    RETURN_NAMES = ("图像", "遮罩", "索引", "文件名", "宽度", "高度", "列表长度")
    FUNCTION = "load_images"
    CATEGORY = "Mixlab/批处理"

    def load_images(self, input_path, start_index=0, max_images=1):
        if not os.path.exists(input_path):
            raise RuntimeError(f"路径不存在: {input_path}")
        
        # 支持的图片格式
        extensions = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.webp']
        image_files = []
        
        for ext in extensions:
            pattern = os.path.join(input_path, ext)
            image_files.extend(glob.glob(pattern))
            # 也检查大写扩展名
            pattern_upper = os.path.join(input_path, ext.upper())
            image_files.extend(glob.glob(pattern_upper))
        
        # 去重并排序
        image_files = sorted(list(set(image_files)))
        
        if not image_files:
            raise RuntimeError(f"在路径中未找到图片: {input_path}")
        
        list_length = len(image_files)
        
        # 限制加载数量
        end_index = min(start_index + max_images, list_length)
        selected_files = image_files[start_index:end_index]
        
        if not selected_files:
            raise RuntimeError(f"索引超出范围: {start_index}")
        
        loaded_images = []
        loaded_masks = []
        filenames = []
        
        for file_path in selected_files:
            image = Image.open(file_path).convert("RGBA")
            img_array = np.array(image).astype(np.float32) / 255.0
            
            mask = img_array[:, :, 3:]
            img_rgb = img_array[:, :, :3]
            
            loaded_images.append(img_rgb)
            loaded_masks.append(mask)
            filenames.append(os.path.basename(file_path))
        
        # 转换为张量
        images_tensor = torch.from_numpy(np.stack(loaded_images, axis=0))
        masks_tensor = torch.from_numpy(np.stack(loaded_masks, axis=0))
        
        # 获取第一张图片的信息
        first_image = loaded_images[0]
        height, width = first_image.shape[:2]
        
        # 返回第一张图片的详细信息
        return (
            images_tensor[0:1],      # 图像
            masks_tensor[0:1],       # 遮罩
            start_index,             # 索引
            filenames[0],            # 文件名
            width,                   # 宽度
            height,                  # 高度
            list_length,             # 列表长度
        )


class ImageBatch:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "图像1": ("IMAGE", {}),
            },
            "optional": {
                "图像2": ("IMAGE", {}),
                "图像3": ("IMAGE", {}),
                "图像4": ("IMAGE", {}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("图像批次",)
    FUNCTION = "batch"
    CATEGORY = "Mixlab/批处理"

    def batch(self, 图像1, 图像2=None, 图像3=None, 图像4=None):
        images = [图像1]
        if 图像2 is not None:
            images.append(图像2)
        if 图像3 is not None:
            images.append(图像3)
        if 图像4 is not None:
            images.append(图像4)
        
        if isinstance(images[0], torch.Tensor):
            return (torch.cat(images, dim=0),)
        else:
            return (np.concatenate(images, axis=0),)


class ImageSplit:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "图像批次": ("IMAGE", {}),
            },
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "IMAGE")
    RETURN_NAMES = ("图像1", "图像2", "图像3", "图像4")
    FUNCTION = "split"
    CATEGORY = "Mixlab/批处理"

    def split(self, 图像批次):
        if isinstance(图像批次, torch.Tensor):
            batch_size = 图像批次.shape[0]
        else:
            batch_size = 图像批次.shape[0]
        
        outputs = []
        for i in range(4):
            if i < batch_size:
                if isinstance(图像批次, torch.Tensor):
                    outputs.append(图像批次[i:i+1])
                else:
                    outputs.append(图像批次[i:i+1])
            else:
                if isinstance(图像批次, torch.Tensor):
                    outputs.append(torch.zeros_like(图像批次[0:1]))
                else:
                    outputs.append(np.zeros_like(图像批次[0:1]))
        
        return tuple(outputs)


class PromptText:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "get_text"
    CATEGORY = "Mixlab/文本"

    def get_text(self, text):
        return (text,)


class PromptCombine:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text1": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
                "text2": ("STRING", {"default": "", "multiline": True}),
                "separator": ("STRING", {"default": ", "}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "combine"
    CATEGORY = "Mixlab/文本"

    def combine(self, text1, text2="", separator=", "):
        if text2:
            return (text1 + separator + text2,)
        return (text1,)


class SaveImageToPath:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", {}),
                "output_path": ("STRING", {"default": "./output.png"}),
                "filename_prefix": ("STRING", {"default": "Mixlab"}),
            },
            "optional": {
                "quality": ("INT", {"default": 95, "min": 1, "max": 100}),
            },
        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "save_images"
    CATEGORY = "Mixlab/输出"

    def save_images(self, images, output_path, filename_prefix, quality=95):
        if isinstance(images, torch.Tensor):
            images = images.cpu().numpy()
        
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        for i, img in enumerate(images):
            img_pil = Image.fromarray((img * 255).astype(np.uint8))
            filename = f"{filename_prefix}_{i:05d}.png"
            filepath = os.path.join(output_dir, filename) if output_dir else filename
            img_pil.save(filepath, "PNG", quality=quality)
        
        return {}


class PreviewImage:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", {}),
            },
        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "preview"
    CATEGORY = "Mixlab/输出"

    def preview(self, images):
        if isinstance(images, torch.Tensor):
            images = images.cpu().numpy()
        
        results = []
        for img in images:
            img_pil = Image.fromarray((img * 255).astype(np.uint8))
            results.append({"filename": "preview", "subfolder": "", "type": "temp"})
        
        return {"ui": {"images": results}}


class ImageInfo:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE", {}),
            },
        }

    RETURN_TYPES = ("INT", "INT", "INT", "STRING")
    RETURN_NAMES = ("width", "height", "batch_size", "info")
    FUNCTION = "get_info"
    CATEGORY = "Mixlab/工具"

    def get_info(self, image):
        if isinstance(image, torch.Tensor):
            shape = image.shape
        else:
            shape = image.shape
        
        batch_size = shape[0]
        height = shape[1]
        width = shape[2]
        info = f"尺寸: {width}x{height}, 批次: {batch_size}"
        
        return (width, height, batch_size, info)


class ColorPicker:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "color": ("STRING", {"default": "#FFFFFF"}),
            },
        }

    RETURN_TYPES = ("STRING", "INT", "INT", "INT")
    RETURN_NAMES = ("hex", "r", "g", "b")
    FUNCTION = "get_color"
    CATEGORY = "Mixlab/工具"

    def get_color(self, color):
        color = color.lstrip('#')
        if len(color) == 3:
            color = ''.join([c*2 for c in color])
        
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
        
        return (f"#{color}", r, g, b)


NODE_CLASS_MAPPINGS = {
    "MixlabImageUpload": ImageUploadNode,
    "MixlabLoadImageFromURL": LoadImageFromURL,
    "MixlabLoadImageFromPath": LoadImageFromPath,
    "MixlabLoadWorkflowImage": LoadWorkflowImage,
    "MixlabImageResize": ImageResize,
    "MixlabImageCrop": ImageCrop,
    "MixlabImageFlip": ImageFlip,
    "MixlabImageRotate": ImageRotate,
    "MixlabImageAdjust": ImageAdjust,
    "MixlabImageBlur": ImageBlur,
    "MixlabImageComposite": ImageComposite,
    "MixlabLoadImagesFromFolder": LoadImagesFromFolder,
    "MixlabImageBatch": ImageBatch,
    "MixlabImageSplit": ImageSplit,
    "MixlabPromptText": PromptText,
    "MixlabPromptCombine": PromptCombine,
    "MixlabSaveImageToPath": SaveImageToPath,
    "MixlabPreviewImage": PreviewImage,
    "MixlabImageInfo": ImageInfo,
    "MixlabColorPicker": ColorPicker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MixlabImageUpload": "图片上传",
    "MixlabLoadImageFromURL": "从URL加载图片",
    "MixlabLoadImageFromPath": "从路径加载图片",
    "MixlabLoadWorkflowImage": "加载工作流图片",
    "MixlabImageResize": "调整图片大小",
    "MixlabImageCrop": "裁剪图片",
    "MixlabImageFlip": "翻转图片",
    "MixlabImageRotate": "旋转图片",
    "MixlabImageAdjust": "调整图片参数",
    "MixlabImageBlur": "模糊图片",
    "MixlabImageComposite": "图片合成",
    "MixlabLoadImagesFromFolder": "从文件夹加载图片",
    "MixlabImageBatch": "图片批次合并",
    "MixlabImageSplit": "图片批次拆分",
    "MixlabPromptText": "提示词文本",
    "MixlabPromptCombine": "提示词合并",
    "MixlabSaveImageToPath": "保存图片到路径",
    "MixlabImageInfo": "图片信息",
    "MixlabColorPicker": "颜色选择器",
}