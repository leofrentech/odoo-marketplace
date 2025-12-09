/** @odoo-module **/

// Image Handler - Handles image upload and placement on the canvas

export class ImageHandler {
    /**
     * @param {fabric.Canvas} fabricCanvas - Fabric.js canvas instance
     * @param {Object|null} zone - Optional restricted zone object
     */
    constructor(fabricCanvas, zone) {
        this.fabricCanvas = fabricCanvas;
        this.zone = zone;
    }

    /**
     * Add uploaded images to the canvas
     * @param {FileList} files - Selected image files
     */
    addImages(files) {
        if (!files || !files.length) {
            alert("Please select an image file");
            return;
        }

        const self = this;

        Array.from(files).forEach(function (file, i) {
            const reader = new FileReader();

            reader.onload = function (e) {
                fabric.Image.fromURL(e.target.result, function (img) {
                    if (!img) return;

                    img.scaleToWidth(150);

                    // Default placement
                    let left = 100 + i * 20;
                    let top = 100 + i * 20;

                    // If zone exists, center inside zone
                    if (self.zone) {
                        left = self.zone.bound_x + self.zone.width / 2 + i * 10;
                        top = self.zone.bound_y + self.zone.height / 2 + i * 10;
                    }

                    img.set({ left: left, top: top });

                    // Store file name for later referencing
                    try { if (img._element) img._element.name = file.name; } catch (e) {}
                    try { img.__label = file.name; } catch (e) {}

                    self.fabricCanvas.add(img);
                    self.fabricCanvas.setActiveObject(img);
                    self.fabricCanvas.renderAll();
                });
            };

            reader.readAsDataURL(file);
        });
    }

    /**
     * Update restricted zone reference
     * @param {Object} zone
     */
    updateZone(zone) {
        this.zone = zone;
    }
}