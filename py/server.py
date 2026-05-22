"""
FastAPI routes for MixLab V2 frontend communication
"""

import os
import json
from aiohttp import web
from PIL import Image
import numpy as np

routes = web.RouteTableDef()

@routes.get("/mixlabv2/health")
async def health_check(request):
    """Health check endpoint"""
    return web.json_response({"status": "ok", "version": "2.0.0"})

@routes.post("/mixlabv2/extract-metadata")
async def extract_metadata(request):
    """Extract workflow metadata from uploaded image"""
    try:
        data = await request.post()
        file_field = data.get("file")

        if not file_field:
            return web.json_response({"error": "No file provided"}, status=400)

        # Read uploaded file
        content = file_field.file.read()
        from io import BytesIO
        img = Image.open(BytesIO(content))

        metadata = {}

        # Extract PNG metadata
        if hasattr(img, 'info'):
            if 'workflow' in img.info:
                try:
                    metadata['workflow'] = json.loads(img.info['workflow'])
                except:
                    metadata['workflow'] = img.info['workflow']

            if 'prompt' in img.info:
                try:
                    metadata['prompt'] = json.loads(img.info['prompt'])
                except:
                    metadata['prompt'] = img.info['prompt']

        # Try EXIF for other formats
        try:
            exif = img._getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag = Image.ExifTags.TAGS.get(tag_id, tag_id)
                    if 'UserComment' in str(tag) or 'ImageDescription' in str(tag):
                        try:
                            metadata['exif_workflow'] = json.loads(value)
                        except:
                            metadata['exif_comment'] = str(value)
        except:
            pass

        return web.json_response({
            "success": True,
            "format": img.format,
            "size": img.size,
            "metadata": metadata
        })

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

@routes.get("/mixlabv2/list-inputs")
async def list_inputs(request):
    """List files in ComfyUI input directory"""
    try:
        input_dir = request.app["input_directory"]
        files = []

        for root, dirs, filenames in os.walk(input_dir):
            for fname in filenames:
                if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                    rel_path = os.path.relpath(os.path.join(root, fname), input_dir)
                    files.append(rel_path)

        return web.json_response({"files": sorted(files)})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

def add_routes(app, input_directory):
    """Register routes with ComfyUI server"""
    app.router.add_routes(routes)
    app["input_directory"] = input_directory
    print("[MixLab V2] Server routes registered")
