/** @odoo-module **/

// Preview Generator - Produces preview thumbnails for personalized designs

export class PreviewGenerator {
    /**
     * Generate preview image for a design type
     * @param {string} designType
     * @param {Object} designData
     * @param {Object} productData
     * @returns {Promise<string>} Data URL of preview image
     */
    static generatePreview(designType, designData, productData) {
        const savedData = designData[designType];

        // No customization — return default design image
        if (!savedData || !savedData.json || !savedData.json.objects || savedData.json.objects.length === 0) {
            const cfg = productData.designs[designType];
            return Promise.resolve(cfg ? cfg.image_url : productData.fallback_image_url);
        }

        try {
            const tempCanvas = new fabric.Canvas(document.createElement("canvas"));
            tempCanvas.setWidth(800);
            tempCanvas.setHeight(800);

            const cfg = productData.designs[designType];
            const bgUrl = cfg ? cfg.image_url : productData.fallback_image_url;

            return new Promise(resolve => {
                let json = savedData.json;

                if (typeof json === "string") {
                    try {
                        json = JSON.parse(json);
                    } catch (e) {
                        console.error("Error parsing preview JSON:", e);
                        json = { objects: [] };
                    }
                }

                const loadObjects = () => {
                    const filtered = {
                        objects: (json.objects || []).filter(
                            o => !o.isZoneRect && o.name !== "zoneRect"
                        )
                    };

                    fabric.util.enlivenObjects(filtered.objects, objs => {
                        objs.forEach(o => tempCanvas.add(o));
                        tempCanvas.renderAll();

                        const dataURL = tempCanvas.toDataURL({ format: "png", quality: 0.8 });
                        tempCanvas.dispose();
                        resolve(dataURL);
                    });
                };

                // Load background (if any)
                if (bgUrl) {
                    fabric.Image.fromURL(
                        bgUrl,
                        img => {
                            if (img) {
                                const w = tempCanvas.getWidth();
                                const h = tempCanvas.getHeight();
                                const scale = Math.min(w / img.width, h / img.height);

                                img.set({
                                    left: (w - img.width * scale) / 2,
                                    top: (h - img.height * scale) / 2,
                                    scaleX: scale,
                                    scaleY: scale,
                                    selectable: false,
                                    evented: false
                                });

                                tempCanvas.setBackgroundImage(img, loadObjects);
                            } else {
                                console.warn("Preview: Failed to load background:", bgUrl);
                                loadObjects();
                            }
                        },
                        null,
                        { crossOrigin: "anonymous" }
                    );
                } else {
                    loadObjects();
                }
            });
        } catch (e) {
            console.error("Preview generation failed:", e);
            const cfg = productData.designs[designType];
            return Promise.resolve(cfg ? cfg.image_url : productData.fallback_image_url);
        }
    }

    /**
     * Download preview image in specified format
     * @param {string} imageUrl
     * @param {string} designType
     * @param {string} format - png | jpeg | webp
     * @returns {Promise<void>}
     */
    static downloadImageAs(imageUrl, designType, format) {
        return new Promise((resolve, reject) => {
            const tempCanvas = document.createElement("canvas");
            const tempImg = new Image();

            tempImg.onload = () => {
                tempCanvas.width = tempImg.width;
                tempCanvas.height = tempImg.height;

                const ctx = tempCanvas.getContext("2d");
                ctx.drawImage(tempImg, 0, 0);

                let mime = "image/png";
                let ext = "png";

                if (format === "jpeg") {
                    mime = "image/jpeg";
                    ext = "jpg";
                } else if (format === "webp") {
                    mime = "image/webp";
                    ext = "webp";
                }

                tempCanvas.toBlob(
                    blob => {
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        const filename = designType.replace(/_/g, "-") + "." + ext;

                        a.href = url;
                        a.download = filename;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);

                        URL.revokeObjectURL(url);
                        resolve();
                    },
                    mime,
                    0.95
                );
            };

            tempImg.onerror = () => reject(new Error("Failed to load image"));
            tempImg.crossOrigin = "anonymous";
            tempImg.src = imageUrl;
        });
    }
}