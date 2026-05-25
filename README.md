# ComfyUI MixLab Nodes V2

A modern, fully-compatible rewrite of [comfyui-mixlab-nodes](https://github.com/MixLabPro/comfyui-mixlab-nodes) that works with **ComfyUI v0.21.0+** and the latest frontend architecture.

> The original MixLab plugin has a known bug where drag-and-drop of images and workflows stopped working after ComfyUI v0.21.0. This V2 version fixes all compatibility issues.

---

## Features

| Feature | Description |
|---------|-------------|
| Drag & Drop Images | Drop images directly onto nodes or the canvas |
| Drag & Drop Workflows | Drop PNG/WebP with embedded workflow metadata |
| Load Image from URL | Load images directly from http/https URLs |
| Batch Image Loading | Load entire folders of images as batched tensors |
| Metadata Extraction | Extract embedded ComfyUI workflow/prompt from images |
| Text to Image | Render text strings as images for prompts/watermarks |
| Masked Composite | Overlay images with alpha mask blending |
| Save + Workflow | Save images with embedded workflow metadata |

---

## Installation

### Method 1: ComfyUI Manager (Recommended)
1. Open ComfyUI Manager
2. Search for `MixLab V2`
3. Click Install
4. Restart ComfyUI

### Method 2: Git Clone
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/YOUR_USERNAME/comfyui-mixlab-nodes-v2.git
```

---

## Nodes

### Image Loading
- **Load Image From Path** - Load single image with drag-and-drop
- **Load Image From URL** - Load image from http/https URL
- **Load Images To Batch** - Load directory of images as batch tensor

### Workflow Tools
- **Extract Workflow From Image** - Extract embedded JSON from generated images
- **Save Image + Workflow** - Save with embedded metadata for sharing

### Image Processing
- **Text To Image** - Render text as RGB image
- **Image Composite Masked** - Blend foreground onto background using mask

---

## License

MIT License
