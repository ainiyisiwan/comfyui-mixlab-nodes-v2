/**
 * MixLab V2 - Modern ComfyUI Frontend Extension
 * Fully compatible with ComfyUI v0.21.0+ frontend architecture
 */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const MIXLAB_V2_VERSION = "2.0.0";

/**
 * Extract workflow from PNG blob by parsing tEXt chunks
 */
async function extractWorkflowFromBlob(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const arrayBuffer = e.target.result;
            const uint8Array = new Uint8Array(arrayBuffer);

            if (blob.type === "image/png" || blob.name?.endsWith(".png")) {
                let offset = 8; // Skip PNG signature
                while (offset < uint8Array.length) {
                    const length = 
                        (uint8Array[offset] << 24) |
                        (uint8Array[offset + 1] << 16) |
                        (uint8Array[offset + 2] << 8) |
                        uint8Array[offset + 3];

                    const type = String.fromCharCode(...uint8Array.slice(offset + 4, offset + 8));

                    if (type === "tEXt") {
                        const textData = uint8Array.slice(offset + 8, offset + 8 + length);
                        const nullIndex = textData.indexOf(0);
                        if (nullIndex > 0) {
                            const keyword = String.fromCharCode(...textData.slice(0, nullIndex));
                            const value = String.fromCharCode(...textData.slice(nullIndex + 1));

                            if (keyword === "workflow") {
                                try {
                                    resolve(JSON.parse(value));
                                    return;
                                } catch (err) {
                                    console.warn("[MixLab V2] Failed to parse workflow JSON:", err);
                                }
                            }
                        }
                    }

                    if (type === "IEND") break;
                    offset += 12 + length;
                }
            }
            resolve(null);
        };
        reader.onerror = reject;
        reader.readAsArrayBuffer(blob);
    });
}

/**
 * Upload file to ComfyUI server
 */
async function uploadFileToServer(file) {
    const formData = new FormData();
    formData.append("image", file);
    formData.append("type", "input");
    formData.append("subfolder", "mixlab-v2");

    try {
        const resp = await api.fetchApi("/upload/image", {
            method: "POST",
            body: formData,
        });

        if (resp.status === 200) {
            const data = await resp.json();
            return data.name || file.name;
        }
    } catch (e) {
        console.error("[MixLab V2] Upload failed:", e);
    }
    return null;
}

app.registerExtension({
    name: "MixLab.V2",
    version: MIXLAB_V2_VERSION,

    async init() {
        console.log(`[MixLab V2] Extension v${MIXLAB_V2_VERSION} initialized`);
        this.setupCanvasDragDrop();
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "LoadImageFromPath_MixLabV2") {
            this.setupLoadImageNode(nodeType);
        }
        if (nodeData.name === "LoadImageFromURL_MixLabV2") {
            this.setupURLLoaderNode(nodeType);
        }
    },

    async nodeCreated(node) {
        if (node.comfyClass?.includes("MixLabV2")) {
            node.color = "#2d3a4a";
            node.bgcolor = "#1a2332";
        }
    },

    setupCanvasDragDrop() {
        const canvas = app.canvas;

        canvas.canvas.ondragover = (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = "copy";
            canvas.canvas.style.boxShadow = "inset 0 0 50px rgba(100, 200, 255, 0.2)";
        };

        canvas.canvas.ondragleave = (e) => {
            canvas.canvas.style.boxShadow = "";
        };

        canvas.canvas.ondrop = async (e) => {
            e.preventDefault();
            canvas.canvas.style.boxShadow = "";

            const files = Array.from(e.dataTransfer.files);
            if (files.length === 0) return;

            const file = files[0];
            const isImage = file.type.startsWith("image/") || 
                           file.name.match(/\.(png|jpg|jpeg|webp|gif|bmp)$/i);
            const isJson = file.name.endsWith(".json");

            // Handle JSON workflow files
            if (isJson) {
                const text = await file.text();
                try {
                    const workflow = JSON.parse(text);
                    await app.loadGraphData(workflow);
                    app.ui.dialog.show("Workflow loaded successfully!");
                    return;
                } catch (err) {
                    app.ui.dialog.show("Error loading workflow: " + err.message);
                    return;
                }
            }

            // Handle images
            if (isImage) {
                const workflow = await extractWorkflowFromBlob(file);

                if (workflow) {
                    await app.loadGraphData(workflow);
                    app.ui.dialog.show("Workflow loaded from image!");
                    return;
                } else {
                    const uploadedPath = await uploadFileToServer(file);
                    if (uploadedPath) {
                        const node = LiteGraph.createNode("LoadImageFromPath_MixLabV2");
                        if (node) {
                            node.pos = [e.canvasX - 150, e.canvasY - 50];
                            app.graph.add(node);

                            const pathWidget = node.widgets?.find(w => w.name === "image_path");
                            if (pathWidget) {
                                pathWidget.value = uploadedPath;
                            }

                            node.setDirtyCanvas(true, true);
                            app.ui.dialog.show(`Image loaded: ${file.name}`);
                        }
                    }
                    return;
                }
            }
        };
    },

    setupLoadImageNode(nodeType) {
        nodeType.prototype.onDragOver = function(e) {
            if (e.dataTransfer.files?.length > 0) {
                const file = e.dataTransfer.files[0];
                if (file.type.startsWith("image/") || file.name.match(/\.(png|jpg|jpeg|webp)$/i)) {
                    this.boxcolor = "#4CAF50";
                    this.setDirtyCanvas(true, false);
                    return true;
                }
            }
            return false;
        };

        nodeType.prototype.onDragDrop = async function(e) {
            if (e.dataTransfer.files?.length > 0) {
                const file = e.dataTransfer.files[0];

                if (file.type.startsWith("image/") || file.name.match(/\.(png|jpg|jpeg|webp)$/i)) {
                    const uploadedPath = await uploadFileToServer(file);

                    if (uploadedPath) {
                        const pathWidget = this.widgets?.find(w => w.name === "image_path");
                        if (pathWidget) {
                            pathWidget.value = uploadedPath;
                            this.setDirtyCanvas(true, true);
                        }
                    }

                    this.boxcolor = "#333";
                    return true;
                }
            }
            return false;
        };
    },

    setupURLLoaderNode(nodeType) {
        // Add URL paste support
        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            originalOnNodeCreated?.apply(this, arguments);

            // Enhance URL widget
            const urlWidget = this.widgets?.find(w => w.name === "url");
            if (urlWidget) {
                urlWidget.placeholder = "https://example.com/image.png";
            }
        };
    }
});

console.log("[MixLab V2] Extension script loaded");
