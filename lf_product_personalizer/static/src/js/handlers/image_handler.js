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
        this.cropRect = null;
        this.cropTimer = null;
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
     * Apply or update a filter on the image
     * @param {fabric.Image} img - Target image
     * @param {fabric.Image.filters} filter - Fabric.js filter to apply
     */
    applyFilter(img, filter) {
        if (!img || img.type !== 'image') {
            console.warn('Invalid image for filter application');
            return;
        }

        const filters = img.filters || [];
        const idx = filters.findIndex(f => f.type === filter.type);

        if (idx !== -1) {
            filters[idx] = filter;
        } else {
            filters.push(filter);
        }

        img.filters = filters;
        img.applyFilters();
        this.fabricCanvas.requestRenderAll();
    }

    /**
     * Unified method to handle all image operations
     * @param {string} operation - The operation to perform
     * @param {*} value - Optional value for the operation (e.g., brightness level)
     */
    handleImageOperation(operation, value = null) {
        const img = this.fabricCanvas.getActiveObject();
        
        // Validate image selection for most operations (except crop cancel)
        if (!img || img.type !== 'image') {
            alert('Please select an image first');
            return;
        }

        switch (operation) {
            case 'flipX':
                img.toggle('flipX');
                this.fabricCanvas.requestRenderAll();
                break;

            case 'flipY':
                img.toggle('flipY');
                this.fabricCanvas.requestRenderAll();
                break;

            case 'blur':
                this.applyFilter(img, new fabric.Image.filters.Blur({
                    blur: parseFloat(value || 0),
                }));
                break;

            case 'brightness':
                this.applyFilter(img, new fabric.Image.filters.Brightness({
                    brightness: parseFloat(value || 0),
                }));
                break;

            case 'contrast':
                this.applyFilter(img, new fabric.Image.filters.Contrast({
                    contrast: parseFloat(value || 0),
                }));
                break;

            case 'saturation':
                this.applyFilter(img, new fabric.Image.filters.Saturation({
                    saturation: parseFloat(value || 0),
                }));
                break;

            case 'grayscale':
                img.filters = [new fabric.Image.filters.Grayscale()];
                img.applyFilters();
                this.fabricCanvas.requestRenderAll();
                break;

            case 'sepia':
                img.filters = [new fabric.Image.filters.Sepia()];
                img.applyFilters();
                this.fabricCanvas.requestRenderAll();
                break;

            case 'resetFilters':
                img.filters = [];
                img.applyFilters();
                this.fabricCanvas.requestRenderAll();
                break;

            case 'crop':
                this.cropImage();
                break;

        }
        this.syncFiltersToUI(img);
    }

    /**
     * Initiate crop mode for the selected image
     */
    cropImage() {
        const img = this.fabricCanvas.getActiveObject();
    
        if (this.cropRect) {
            this.fabricCanvas.remove(this.cropRect);
            this.cropRect = null;
        }

        if (this.cropTimer) {
            clearTimeout(this.cropTimer);
            this.cropTimer = null;
        }

        // Create crop rectangle
        this.cropRect = new fabric.Rect({
            left: img.left,
            top: img.top,
            width: img.width * img.scaleX * 0.6,
            height: img.height * img.scaleY * 0.6,
            fill: 'rgba(0, 123, 255, 0.2)',
            stroke: 'rgba(0, 123, 255, 0.8)',
            strokeWidth: 2,
            strokeDashArray: [5, 5],
            hasRotatingPoint: false,
            cornerColor: '#007bff',
            cornerSize: 10,
            transparentCorners: false,
            lockRotation: true,
            selectable: true,
            evented: true,
            isCropRect: true,
        });

        this.fabricCanvas.add(this.cropRect);
        this.fabricCanvas.setActiveObject(this.cropRect);
        this.fabricCanvas.requestRenderAll();
        this.cropRect._targetImage = img;

        // Handle crop rectangle modification events
        const resetTimer = function () {
            if (this.cropTimer) {
                clearTimeout(this.cropTimer);
            }

            this.cropTimer = setTimeout(function () {
                this._applyCrop(img, this.cropRect);
            }, 2000);
        };

        // Reset timer on any movement or scaling
        this.cropRect.on('moving', resetTimer);
        this.cropRect.on('scaling', resetTimer);
        this.cropRect.on('modified', resetTimer);

        // Start initial timer
        resetTimer();
    }

    /**
     * Apply the crop based on crop rectangle dimensions
     * @param {fabric.Image} img - Image to crop
     * @param {fabric.Rect} cropRect - Crop rectangle
     * @private
     */
    _applyCrop(img, cropRect) {
        if (!img || !cropRect) return;

        if (this.cropTimer) {
            clearTimeout(this.cropTimer);
            this.cropTimer = null;
        }

        const scaleX = img.scaleX;
        const scaleY = img.scaleY;

        // Calculate crop coordinates relative to image
        const cropX = (cropRect.left - img.left) / scaleX;
        const cropY = (cropRect.top - img.top) / scaleY;
        const cropWidth = (cropRect.width * cropRect.scaleX) / scaleX;
        const cropHeight = (cropRect.height * cropRect.scaleY) / scaleY;

        // Apply crop to image
        img.set({
            cropX: Math.max(0, cropX),
            cropY: Math.max(0, cropY),
            width: Math.max(10, cropWidth),
            height: Math.max(10, cropHeight),
        });

        cropRect.off('moving');
        cropRect.off('scaling');
        cropRect.off('modified');

        this.fabricCanvas.remove(cropRect);
        this.cropRect = null;

        this.fabricCanvas.setActiveObject(img);
        this.fabricCanvas.requestRenderAll();
    }

    /**
     * Sync image filter values with UI sliders
     * @param {fabric.Image} img
     */
    syncFiltersToUI(img) {
        if (!img || img.type !== 'image') return;

        const getFilterValue = (type, key) => {
            const f = (img.filters || []).find(fl => fl.type === type);
            return f ? (f[key] ?? 0) : 0;
        };

        $('#img_blur').val(getFilterValue('Blur', 'blur'));
        $('#img_brightness').val(getFilterValue('Brightness', 'brightness'));
        $('#img_contrast').val(getFilterValue('Contrast', 'contrast'));
        $('#img_saturation').val(getFilterValue('Saturation', 'saturation'));
    }

    /**
     * Update restricted zone reference
     * @param {Object} zone
     */
    updateZone(zone) {
        this.zone = zone;
    }
}