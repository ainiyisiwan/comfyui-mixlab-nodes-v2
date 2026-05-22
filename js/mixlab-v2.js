/**
 * MixLab V2 - Modern ComfyUI Frontend Extension
 * Fully compatible with ComfyUI v0.21.0+ frontend architecture
 * 
 * Features:
 * - Drag-and-drop images to LoadImageFromPath node
 * - Drag-and-drop workflow JSON/PNG to canvas
 * - No popups, no extra UI elements - clean and minimal
 */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const MIXLAB_V2_VERSION = "2.0.1";

// ============================================
// Utility Functions
// ============================================

/**
 * Extract workflow from PNG/WebP blob
 */
async function extractWorkflowFromBlob(blob) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const arrayBuffer = e.target.result;
            const uint8Array = new Uint8Array(arrayBuffer);

            // Look for tEXt chunks in PNG
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
                            if (keyword === "prompt") {
                                try {
                                    resolve(JSON.parse(value));
                                    return;
                                } catch (err) {
                                    // Continue searching for workflow
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
        reader.onerror = () => resolve(null);
        reader.readAsArrayBuffer(blob);
    });
}

/**
 * Upload file to server and return path
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

// ============================================
// Extension Registration
// ============================================

app.registerExtension({
    name: "MixLab.V2",
    version: MIXLAB_V2_VERSION,

    // ============================================
    // Initialization
    // ============================================
    async init() {
        console.log(`[MixLab V2] Extension v${MIXLAB_V2_VERSION} initialized`);
        this.setupCanvasDragDrop();
    },

    // ============================================
    // Node Type Registration Hooks
    // ============================================
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "LoadImageFromPath_MixLabV2") {
            this.setupLoadImageNode(nodeType);
        }
    },

    // ============================================
    // Setup Methods
    // ============================================

    /**
     * Setup canvas-level drag-and-drop
     * No popups, no extra UI elements
     */
    setupCanvasDragDrop() {
        const canvas = app.canvas;

        canvas.canvas.ondragover = (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = "copy";
        };

        canvas.canvas.ondrop = async (e) => {
            e.preventDefault();

            const files = Array.from(e.dataTransfer.files);
            if (files.length === 0) return;

            const file = files[0];
            const isImage = file.type.startsWith("image/") || 
                           file.name.match(/\.(png|jpg|jpeg|webp|gif)$/i);
            const isJson = file.name.endsWith(".json");

            // Handle JSON workflow files - silent load
            if (isJson) {
                try {
                    const text = await file.text();
                    const workflow = JSON.parse(text);
                    await app.loadGraphData(workflow);
                } catch (err) {
                    console.error("[MixLab V2] Failed to load workflow:", err);
                }
                return;
            }

            // Handle images
            if (isImage) {
                const workflow = await extractWorkflowFromBlob(file);

                if (workflow) {
                    // Image has embedded workflow - load silently
                    await app.loadGraphData(workflow);
                    return;
                } else {
                    // No workflow in image - create LoadImageFromPath node silently
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
                        }
                    }
                    return;
                }
            }
        };

        console.log("[MixLab V2] Canvas drag-and-drop handler registered (no popups)");
    },

    /**
     * Setup LoadImageFromPath node with drag-and-drop support
     * No popups, no extra UI elements
     */
    setupLoadImageNode(nodeType) {
        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function() {
            originalOnNodeCreated?.apply(this, arguments);
        };

        // Handle drag over - simple visual feedback only
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

        // Handle drop - silent operation
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

        // Add file browser to context menu (optional, no popup)
        const originalGetExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
        nodeType.prototype.getExtraMenuOptions = function(_, options) {
            options.push({
                content: "Browse Input Folder",
                callback: async () => {
                    try {
                        const resp = await api.fetchApi("/mixlabv2/list-inputs");
                        const data = await resp.json();

                        if (data.files?.length > 0) {
                            const dialog = document.createElement("dialog");
                            dialog.innerHTML = `
                                <div style="padding: 20px; min-width: 300px;">
                                    <h3>Select Image</h3>
                                    <select id="mixlab-file-select" style="width: 100%; margin: 10px 0;">
                                        ${data.files.map(f => `<option value="${f}">${f}</option>`).join("")}
                                    </select>
                                    <div style="text-align: right; margin-top: 10px;">
                                        <button id="mixlab-cancel">Cancel</button>
                                        <button id="mixlab-confirm" style="margin-left: 5px;">Select</button>
                                    </div>
                                </div>
                            `;

                            document.body.appendChild(dialog);
                            dialog.showModal();

                            dialog.querySelector("#mixlab-cancel").onclick = () => dialog.close();
                            dialog.querySelector("#mixlab-confirm").onclick = () => {
                                const select = dialog.querySelector("#mixlab-file-select");
                                const pathWidget = this.widgets?.find(w => w.name === "image_path");
                                if (pathWidget) {
                                    pathWidget.value = select.value;
                                    this.setDirtyCanvas(true, true);
                                }
                                dialog.close();
                            };

                            dialog.onclose = () => dialog.remove();
                        }
                    } catch (e) {
                        console.error("[MixLab V2] Failed to list inputs:", e);
                    }
                }
            });

            return originalGetExtraMenuOptions?.apply(this, arguments);
        };
    }
});

console.log("[MixLab V2] Extension loaded - no popups mode");
