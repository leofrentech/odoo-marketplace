/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ObjectUtils, isImage } from "../utils/object_utils";
import { EDITOR_SIZE } from "../utils/fabric_loader";
import { imageSize, readFileAsDataUrl } from "../utils/dom_utils";

const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp"];
const FILTERS = {
    brightness: (value) => new window.fabric.Image.filters.Brightness({ brightness: value }),
    contrast: (value) => new window.fabric.Image.filters.Contrast({ contrast: value }),
    saturation: (value) => new window.fabric.Image.filters.Saturation({ saturation: value }),
};
const FILTER_TYPES = { brightness: "Brightness", contrast: "Contrast", saturation: "Saturation" };

export class ImageHandler {
    constructor(editor) {
        this.editor = editor;
        this.cropRect = null;
        this.cropTarget = null;
    }

    get canvas() {
        return this.editor.canvasManager.canvas;
    }

    get isCropping() {
        return Boolean(this.cropRect);
    }

    async addFiles(files) {
        const { min_image_px: minPx } = this.editor.state.settings;
        const maxBytes = (this.editor.state.data.max_upload_mb || 15) * 1024 * 1024;
        for (const file of files) {
            if (!ACCEPTED_TYPES.includes(file.type)) {
                this.editor.notify(_t("%s: only PNG, JPG or WebP images are accepted.", file.name), "warning");
                continue;
            }
            if (file.size > maxBytes) {
                this.editor.notify(_t("%s is too large.", file.name), "warning");
                continue;
            }
            const dataUrl = await readFileAsDataUrl(file);
            if (minPx) {
                const { width, height } = await imageSize(dataUrl);
                if (Math.min(width, height) < minPx) {
                    this.editor.notify(
                        _t(
                            "%(name)s is small (%(width)s x %(height)s px): it may look blurry once printed.",
                            { name: file.name, width, height }
                        ),
                        "warning"
                    );
                }
            }
            await this.addFromUrl(dataUrl, file.name);
        }
    }

    addFromUrl(url, label, extra = {}) {
        return new Promise((resolve) => {
            window.fabric.Image.fromURL(
                url,
                (img) => {
                    if (!img || !img.width) {
                        this.editor.notify(_t("This image could not be loaded."), "danger");
                        resolve(null);
                        return;
                    }
                    const zone = this.editor.canvasManager.zone;
                    img.set({ lfLabel: label, ...extra });
                    ObjectUtils.center(img, zone, EDITOR_SIZE);
                    ObjectUtils.fit(img, zone, EDITOR_SIZE);
                    this.canvas.add(img);
                    this.canvas.setActiveObject(img);
                    this.canvas.requestRenderAll();
                    resolve(img);
                },
                { crossOrigin: "anonymous" }
            );
        });
    }

    operate(img, op) {
        if (!isImage(img)) {
            return;
        }
        if (op === "flipX" || op === "flipY") {
            img.toggle(op);
        } else if (op === "grayscale") {
            this._setFilter(img, "Grayscale", new window.fabric.Image.filters.Grayscale());
            this._removeFilter(img, "Sepia");
        } else if (op === "sepia") {
            this._setFilter(img, "Sepia", new window.fabric.Image.filters.Sepia());
            this._removeFilter(img, "Grayscale");
        } else if (op === "resetFilters") {
            img.filters = [];
            img.applyFilters();
        }
        this.canvas.requestRenderAll();
        this.canvas.fire("object:modified", { target: img });
    }

    setAdjustment(img, name, value) {
        if (!isImage(img) || !FILTERS[name]) {
            return;
        }
        value = parseFloat(value) || 0;
        if (value) {
            this._setFilter(img, FILTER_TYPES[name], FILTERS[name](value));
        } else {
            this._removeFilter(img, FILTER_TYPES[name]);
        }
        this.canvas.requestRenderAll();
    }

    adjustmentValues(img) {
        const values = {};
        for (const [name, type] of Object.entries(FILTER_TYPES)) {
            const filter = (img?.filters || []).find((f) => f && f.type === type);
            values[name] = filter ? filter[name] : 0;
        }
        return values;
    }

    _setFilter(img, type, filter) {
        const filters = (img.filters || []).filter((f) => f && f.type !== type);
        filters.push(filter);
        img.filters = filters;
        img.applyFilters();
    }

    _removeFilter(img, type) {
        img.filters = (img.filters || []).filter((f) => f && f.type !== type);
        img.applyFilters();
    }

    // ------------------------------------------------------------------
    // Crop: first click shows a frame, second click applies it
    // ------------------------------------------------------------------

    startCrop(img) {
        if (!isImage(img)) {
            return false;
        }
        if (img.angle) {
            this.editor.notify(_t("Straighten the image (rotation 0°) before cropping it."), "warning");
            return false;
        }
        const box = img.getBoundingRect(true, true);
        this.cropTarget = img;
        this.cropRect = new window.fabric.Rect({
            left: box.left + box.width * 0.1,
            top: box.top + box.height * 0.1,
            width: box.width * 0.8,
            height: box.height * 0.8,
            fill: "rgba(13, 110, 253, 0.12)",
            stroke: "#0d6efd",
            strokeWidth: 2,
            strokeDashArray: [6, 4],
            strokeUniform: true,
            lockRotation: true,
            hasRotatingPoint: false,
            isCropRect: true,
            excludeFromExport: true,
        });
        this.cropRect.setControlsVisibility({ mtr: false });
        img.set({ selectable: false, evented: false });
        this.canvas.add(this.cropRect);
        this.canvas.setActiveObject(this.cropRect);
        this.canvas.requestRenderAll();
        return true;
    }

    applyCrop() {
        const img = this.cropTarget;
        const rect = this.cropRect;
        if (!img || !rect) {
            return;
        }
        const imgBox = img.getBoundingRect(true, true);
        const rectBox = rect.getBoundingRect(true, true);
        const left = Math.max(rectBox.left, imgBox.left);
        const top = Math.max(rectBox.top, imgBox.top);
        const right = Math.min(rectBox.left + rectBox.width, imgBox.left + imgBox.width);
        const bottom = Math.min(rectBox.top + rectBox.height, imgBox.top + imgBox.height);
        if (right - left > 2 && bottom - top > 2) {
            const sx = Math.abs(img.scaleX);
            const sy = Math.abs(img.scaleY);
            // Offsets in source pixels, mirrored when the image is flipped.
            const offsetX = img.flipX ? imgBox.left + imgBox.width - right : left - imgBox.left;
            const offsetY = img.flipY ? imgBox.top + imgBox.height - bottom : top - imgBox.top;
            img.set({
                cropX: (img.cropX || 0) + offsetX / sx,
                cropY: (img.cropY || 0) + offsetY / sy,
                width: (right - left) / sx,
                height: (bottom - top) / sy,
            });
            img.setPositionByOrigin(new window.fabric.Point(left, top), "left", "top");
            img.setCoords();
        }
        this.cancelCrop();
        this.canvas.setActiveObject(img);
        this.canvas.fire("object:modified", { target: img });
    }

    cancelCrop() {
        if (this.cropRect) {
            this.canvas.remove(this.cropRect);
        }
        if (this.cropTarget) {
            this.cropTarget.set({ selectable: true, evented: true });
        }
        this.cropRect = null;
        this.cropTarget = null;
        this.canvas.requestRenderAll();
    }
}
