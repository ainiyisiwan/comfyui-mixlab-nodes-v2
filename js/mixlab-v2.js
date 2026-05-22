/**
 * MixLab V2 Frontend Extension
 * ComfyUI v0.21.0+ compatible
 */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const MIXLAB_V2_NODE_TYPES = [
    "LoadImageFromPath_MixLabV2",
    "LoadImagesToBatch_MixLabV2",
    "ExtractWorkflowFromImage_MixLabV2",
    "TextImage_MixLabV2",
    "ImageCompositeMasked_MixLabV2",
    "SaveImageWithWorkflow_MixLabV2",
];

app.registerExtension({
    name: "ComfyUI.MixLabV2",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (!MIXLAB_V2_NODE_TYPES.includes(nodeData.name)) {
            return;
        }

        // ============================================
        // LoadImageFromPath: Drag & Drop support
        // ============================================
        if (nodeData.name === "LoadImageFromPath_MixLabV2") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                // 可选：添加一个视觉提示（不会显示文件名）
                this.addWidget("text", "🖱️ Drop image here", "", () => {}, {
                    disabled: true,
                    serialize: false,
                });

                return r;
            };

            // Handle drag over
            const onDragOver = nodeType.prototype.onDragOver;
            nodeType.prototype.onDragOver = function (e) {
                if (e.dataTransfer && e.dataTransfer.types) {
                    const types = Array.from(e.dataTransfer.types);
                    if (types.includes("Files") || types.includes("text/uri-list")) {
                        return true;
                    }
                }
                return onDragOver ? onDragOver.apply(this, arguments) : false;
            };

            // Handle drop
            const onDragDrop = nodeType.prototype.onDragDrop;
            nodeType.prototype.onDragDrop = function (e) {
                let handled = false;

                // Handle file drop
                if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    const file = e.dataTransfer.files[0];
                    if (file.type.startsWith("image/")) {
                        const path = file.path || file.name;

                        // 只更新 image_path widget，不要设置 this.title 或其他显示属性
                        const imagePathWidget = this.widgets?.find(w => w.name === "image_path");
                        if (imagePathWidget) {
                            imagePathWidget.value = path;
                        }

                        handled = true;
                    }
                }

                // Handle URL drop
                if (!handled && e.dataTransfer && e.dataTransfer.getData) {
                    const url = e.dataTransfer.getData("text/uri-list") || e.dataTransfer.getData("text/plain");
                    if (url && (url.startsWith("http") || url.startsWith("file://"))) {
                        const imagePathWidget = this.widgets?.find(w => w.name === "image_path");
                        if (imagePathWidget) {
                            imagePathWidget.value = url;
                        }
                        handled = true;
                    }
                }

                if (handled) {
                    // 关键：不要设置 this.title 或任何会显示在节点上的属性
                    // 只更新 widget 值即可

                    if (this.setDirtyCanvas) {
                        this.setDirtyCanvas(true, true);
                    }
                    return true;
                }

                return onDragDrop ? onDragDrop.apply(this, arguments) : false;
            };
        }

        // ============================================
        // LoadImagesToBatch: Directory drop support
        // ============================================
        if (nodeData.name === "LoadImagesToBatch_MixLabV2") {
            const onDragDrop = nodeType.prototype.onDragDrop;
            nodeType.prototype.onDragDrop = function (e) {
                if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    const file = e.dataTransfer.files[0];
                    const path = file.path || "";
                    const dir = path.substring(0, path.lastIndexOf("/") + 1) || path.substring(0, path.lastIndexOf("\\") + 1);

                    if (dir) {
                        const dirWidget = this.widgets?.find(w => w.name === "directory");
                        if (dirWidget) {
                            dirWidget.value = dir;
                        }
                        if (this.setDirtyCanvas) {
                            this.setDirtyCanvas(true, true);
                        }
                        return true;
                    }
                }
                return onDragDrop ? onDragDrop.apply(this, arguments) : false;
            };
        }
    },

    // ============================================
    // Canvas-level drag & drop for workflow restore
    // ============================================
    async setup() {
        const originalOnDrop = app.canvas.ondrop;
        app.canvas.ondrop = async function (e) {
            const files = e.dataTransfer?.files;
            if (files && files.length > 0) {
                const file = files[0];
                if (file.type === "image/png" || file.type === "image/webp") {
                    try {
                        const arrayBuffer = await file.arrayBuffer();
                        const workflow = await extractWorkflowFromImage(arrayBuffer, file.type);

                        if (workflow) {
                            await app.loadGraphData(workflow);
                            e.preventDefault();
                            e.stopPropagation();
                            return false;
                        }
                    } catch (err) {
                        console.warn("[MixLab V2] Failed to extract workflow from image:", err);
                    }
                }

                if (file.type === "application/json" || file.name.endsWith(".json")) {
                    try {
                        const text = await file.text();
                        const workflow = JSON.parse(text);
                        await app.loadGraphData(workflow);
                        e.preventDefault();
                        e.stopPropagation();
                        return false;
                    } catch (err) {
                        console.warn("[MixLab V2] Failed to load JSON workflow:", err);
                    }
                }
            }

            if (originalOnDrop) {
                return originalOnDrop.apply(this, arguments);
            }
        };
    },
});

// ============================================
// Helper: Extract workflow from PNG/WebP metadata
// ============================================
async function extractWorkflowFromImage(arrayBuffer, mimeType) {
    if (mimeType === "image/webp") {
        const blob = new Blob([arrayBuffer], { type: mimeType });
        const formData = new FormData();
        formData.append("image", blob, "image.webp");

        try {
            const resp = await api.fetchApi("/mixlab/extract_workflow", {
                method: "POST",
                body: formData,
            });
            const data = await resp.json();
            return data.workflow || null;
        } catch (e) {
            return null;
        }
    }

    const dataView = new DataView(arrayBuffer);
    const decoder = new TextDecoder();
    let offset = 8;

    while (offset < arrayBuffer.byteLength) {
        const length = dataView.getUint32(offset);
        const type = decoder.decode(new Uint8Array(arrayBuffer, offset + 4, 4));
        const chunkData = new Uint8Array(arrayBuffer, offset + 8, length);

        if (type === "tEXt") {
            const text = decoder.decode(chunkData);
            const [key, ...valueParts] = text.split("\0");
            const value = valueParts.join("\0");

            if (key === "workflow") {
                try {
                    return JSON.parse(value);
                } catch (e) {
                    return value;
                }
            }
        }

        offset += 12 + length;
    }

    return null;
}