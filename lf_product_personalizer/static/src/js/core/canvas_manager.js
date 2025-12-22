/** @odoo-module **/

/**
 * CanvasManager
 * Manages Fabric.js canvas, background images, and restricted zones.
 */
export class CanvasManager {

    constructor() {
        this.fabricCanvas = null;
        this.zoneRect = null;
        this.zone = null;
    }

    /** Initialize the canvas and attach to DOM */
    initialize() {
        const wrapper = document.getElementById("canvas_wrapper");
        if (!wrapper) {
            console.error("canvas_wrapper not found");
            return null;
        }

        wrapper.innerHTML = "";
        const canvasEl = document.createElement("canvas");
        Object.assign(canvasEl, { id: "personalization_canvas", width: 800, height: 800 });
        Object.assign(canvasEl.style, { width: "800px", height: "800px", border: "2px solid #dee2e6" });

        wrapper.appendChild(canvasEl);

        this.fabricCanvas = new fabric.Canvas('personalization_canvas', {
            preserveObjectStacking: true,
        });
        return this.fabricCanvas;
    }

    /** Load image from URL and set as background */
    setBackgroundFromUrl(url, callback) {
        fabric.Image.fromURL(
            url,
            img => this._handleBackgroundLoad(img, url, callback),
            { crossOrigin: "anonymous" }
        );
    }

    /** Internal helper for background loading */
    _handleBackgroundLoad(img, url, callback) {
        if (!img) {
            const abs = url.startsWith("/") ? window.location.origin + url : null;
            if (!abs) return callback?.();

            fabric.Image.fromURL(
                abs,
                img2 => {
                    if (img2) this._applyBackgroundImage(img2);
                    callback?.();
                },
                { crossOrigin: "anonymous" }
            );
            return;
        }

        this._applyBackgroundImage(img);
        callback?.();
    }

    /** Apply image to canvas background */
    _applyBackgroundImage(img) {
        if (!this.fabricCanvas) return;

        img.set({ selectable: false, evented: false });

        const w = this.fabricCanvas.getWidth();
        const h = this.fabricCanvas.getHeight();
        const s = Math.min(w / img.width, h / img.height);

        img.set({
            left: (w - img.width * s) / 2,
            top: (h - img.height * s) / 2,
            scaleX: s,
            scaleY: s
        });

        this.fabricCanvas.setBackgroundImage(img, this.fabricCanvas.renderAll.bind(this.fabricCanvas));
    }

    /** Set a restricted zone area */
    setZone(zoneObj) {
        this._removePreviousZone();

        if (!zoneObj) {
            this.zone = null;
            this.fabricCanvas.renderAll();
            return;
        }

        const bx = Number(zoneObj.bound_x || 0);
        const by = Number(zoneObj.bound_y || 0);
        const bw = Number(zoneObj.width || 0);
        const bh = Number(zoneObj.height || 0);

        if (bw <= 0 || bh <= 0) return;

        this.zone = { bound_x: bx, bound_y: by, width: bw, height: bh };

        this.zoneRect = new fabric.Rect({
            left: bx,
            top: by,
            width: bw,
            height: bh,
            fill: "rgba(0,150,255,0.15)",
            stroke: "#0096FF",
            strokeWidth: 3,
            strokeDashArray: [10, 5],
            selectable: false,
            evented: false,
            name: "zoneRect",
            isZoneRect: true,
            excludeFromExport: true,
        });

        this.fabricCanvas.add(this.zoneRect);
        this.fabricCanvas.bringToFront(this.zoneRect);
        this.fabricCanvas.renderAll();
    }

    /** Remove old zone rectangles */
    _removePreviousZone() {
        this.fabricCanvas.getObjects().forEach(o => {
            if (o.isZoneRect || o.name === "zoneRect") {
                this.fabricCanvas.remove(o);
            }
        });
        this.zoneRect = null;
        this.zone = null;
    }

    /** Keep the zone rectangle above all other objects */
    ensureZoneOnTop() {
        if (!this.zoneRect) return;

        this.fabricCanvas.getObjects().forEach(o => {
            if (o.isZoneRect && o !== this.zoneRect) this.fabricCanvas.remove(o);
        });

        this.fabricCanvas.bringToFront(this.zoneRect);
    }

    /** Clamp object movement so it stays inside the restricted zone */
    clampObjectToZone(obj) {
        if (!obj || !this.zone || obj === this.zoneRect) return;

        obj.setCoords();
        let br = obj.getBoundingRect(true, true);

        const minL = this.zone.bound_x;
        const minT = this.zone.bound_y;
        const maxR = minL + this.zone.width;
        const maxB = minT + this.zone.height;

        this._autoScaleObjectToZone(obj, br);

        obj.setCoords();
        br = obj.getBoundingRect(true, true);

        let newLeft = obj.left;
        let newTop = obj.top;

        if (br.left < minL) newLeft += (minL - br.left);
        if (br.top < minT) newTop += (minT - br.top);
        if (br.left + br.width > maxR) newLeft -= ((br.left + br.width) - maxR);
        if (br.top + br.height > maxB) newTop -= ((br.top + br.height) - maxB);

        obj.set({ left: newLeft, top: newTop }).setCoords();

        this.ensureZoneOnTop();
        this.fabricCanvas.renderAll();
    }

    /** Auto-scale object if it's too large for zone */
    _autoScaleObjectToZone(obj, br) {
        let changed = false;

        if (br.width > this.zone.width) {
            const scale = (this.zone.width - 10) / obj.width;
            obj.scaleX = Math.min(obj.scaleX, scale);
            obj.scaleY = Math.min(obj.scaleY, scale);
            changed = true;
        }

        if (br.height > this.zone.height) {
            const scale = (this.zone.height - 10) / obj.height;
            obj.scaleX = Math.min(obj.scaleX, scale);
            obj.scaleY = Math.min(obj.scaleY, scale);
            changed = true;
        }

        if (changed) obj.setCoords();
    }

    /** Clear canvas and remove zone */
    clear() {
        this.fabricCanvas.clear();
        this.zone = null;
        this.zoneRect = null;
    }

    /** Get canvas instance */
    getCanvas() {
        return this.fabricCanvas;
    }
}