import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

function setupDragAndDrop() {
    const canvas = document.querySelector(".comfy-canvas");
    if (!canvas) return;

    canvas.addEventListener("dragover", (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "copy";
        canvas.style.border = "2px dashed #4CAF50";
    });

    canvas.addEventListener("dragleave", () => {
        canvas.style.border = "none";
    });

    canvas.addEventListener("drop", async (e) => {
        e.preventDefault();
        canvas.style.border = "none";

        const files = Array.from(e.dataTransfer.files);
        const imageFiles = files.filter(f => f.type.startsWith("image/"));

        if (imageFiles.length === 0) {
            alert("请拖放图片文件");
            return;
        }

        for (const file of imageFiles) {
            await handleImageDrop(file);
        }
    });
}

async function handleImageDrop(file) {
    try {
        const reader = new FileReader();
        
        reader.onload = async (e) => {
            const img = new Image();
            img.onload = async () => {
                const canvas = document.createElement("canvas");
                canvas.width = img.width;
                canvas.height = img.height;
                const ctx = canvas.getContext("2d");
                ctx.drawImage(img, 0, 0);
                
                const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                const pixels = imageData.data;
                
                let hasAlpha = false;
                for (let i = 3; i < pixels.length; i += 4) {
                    if (pixels[i] !== 255) {
                        hasAlpha = true;
                        break;
                    }
                }
                
                const node = app.graph.addNode(
                    hasAlpha ? "MixlabLoadWorkflowImage" : "MixlabImageUpload",
                    app.canvas.width / 2 - 150,
                    app.canvas.height / 2 - 100
                );
                
                const blob = await fetch(e.target.result).then(r => r.blob());
                const formData = new FormData();
                formData.append("image", blob, file.name);
                
                const response = await api.fetchApi("/upload/image", {
                    method: "POST",
                    body: formData
                });
                
                if (response.ok) {
                    const result = await response.json();
                    if (node.widgets) {
                        node.widgets.forEach(w => {
                            if (w.name === "image" || w.name === "image_path") {
                                w.value = result.name;
                            }
                        });
                    }
                    app.canvas.setDirty(true);
                }
            };
            img.src = e.target.result;
        };
        
        reader.readAsDataURL(file);
    } catch (error) {
        console.error("Error handling dropped image:", error);
        alert("处理图片时出错: " + error.message);
    }
}

app.registerExtension({
    name: "Mixlab.DragDrop",
    init() {
        setupDragAndDrop();
    },
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeType.name === "MixlabImageUpload" || 
            nodeType.name === "MixlabLoadWorkflowImage") {
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(message) {
                if (onExecuted) onExecuted.call(this, message);
                console.log("Node executed successfully:", this.title);
            };
        }
    },
});