import { EDITOR_SIZE } from "../utils/fabric_loader";
import { PreviewGenerator } from "../utils/preview_generator";
import { isUserObject } from "../utils/object_utils";

/**
 * Owns the visible Fabric canvas: responsive sizing, mockup background and
 * the printable zone. Coordinates are always expressed in the 800x800 logical
 * space; the canvas is zoomed to fit the screen.
 */
export class CanvasManager {
    constructor(wrapperEl) {
        this.wrapperEl = wrapperEl;
        this.canvas = null;
        this.zone = null;
        this.zoneRect = null;
        this.resizeObserver = null;
    }

    initialize() {
        this.wrapperEl.replaceChildren();
        const canvasEl = document.createElement("canvas");
        canvasEl.className = "o_lf_canvas";
        this.wrapperEl.appendChild(canvasEl);
        this.canvas = new window.fabric.Canvas(canvasEl, {
            width: EDITOR_SIZE,
            height: EDITOR_SIZE,
            preserveObjectStacking: true,
            backgroundColor: "#ffffff",
            selectionColor: "rgba(13, 110, 253, 0.08)",
        });
        window.fabric.Object.prototype.set({
            transparentCorners: false,
            cornerColor: "#ffffff",
            cornerStrokeColor: "#0d6efd",
            borderColor: "#0d6efd",
            cornerStyle: "circle",
            cornerSize: 12,
            touchCornerSize: 28,
            padding: 4,
        });
        this.resize();
        this.resizeObserver = new ResizeObserver(() => this.resize());
        this.resizeObserver.observe(this.wrapperEl);
        return this.canvas;
    }

    /** Fit the canvas in the available width (and viewport height). */
    resize() {
        if (!this.canvas) {
            return;
        }
        const width = this.wrapperEl.clientWidth || EDITOR_SIZE;
        const height = Math.max(320, window.innerHeight - 190);
        const size = Math.floor(Math.min(width, height, EDITOR_SIZE));
        if (size <= 0 || size === this.canvas.getWidth()) {
            return;
        }
        this.canvas.setDimensions({ width: size, height: size });
        this.canvas.setZoom(size / EDITOR_SIZE);
        this.canvas.requestRenderAll();
    }

    async setBackground(url) {
        const img = await PreviewGenerator.loadImage(url);
        this.canvas.setBackgroundImage(img ? PreviewGenerator.fitBackground(img) : null, () =>
            this.canvas.requestRenderAll()
        );
    }

    setZone(zone) {
        if (this.zoneRect) {
            this.canvas.remove(this.zoneRect);
        }
        this.zone = zone;
        this.zoneRect = null;
        if (zone) {
            this.zoneRect = new window.fabric.Rect({
                left: zone.x,
                top: zone.y,
                width: zone.width,
                height: zone.height,
                fill: "rgba(13, 110, 253, 0.04)",
                stroke: "#0d6efd",
                strokeWidth: 2,
                strokeDashArray: [8, 6],
                strokeUniform: true,
                selectable: false,
                evented: false,
                excludeFromExport: true,
                isZoneRect: true,
            });
            this.canvas.add(this.zoneRect);
        }
        this.canvas.requestRenderAll();
    }

    keepZoneOnTop() {
        if (this.zoneRect) {
            this.canvas.bringToFront(this.zoneRect);
        }
    }

    /** Remove the customer's objects (keeps background and zone). */
    clearObjects() {
        for (const obj of this.canvas.getObjects().filter(isUserObject)) {
            this.canvas.remove(obj);
        }
        this.canvas.discardActiveObject();
        this.canvas.requestRenderAll();
    }

    /** Keep an object inside the printable zone, shrinking it if needed. */
    clampToZone(obj) {
        if (!obj || !this.zone || !isUserObject(obj)) {
            return;
        }
        const zone = this.zone;
        obj.setCoords();
        let box = obj.getBoundingRect(true, true);
        if (box.width > zone.width || box.height > zone.height) {
            const ratio = Math.min(zone.width / box.width, zone.height / box.height);
            obj.set({ scaleX: obj.scaleX * ratio, scaleY: obj.scaleY * ratio });
            obj.setCoords();
            box = obj.getBoundingRect(true, true);
        }
        let dx = 0;
        let dy = 0;
        if (box.left < zone.x) {
            dx = zone.x - box.left;
        } else if (box.left + box.width > zone.x + zone.width) {
            dx = zone.x + zone.width - (box.left + box.width);
        }
        if (box.top < zone.y) {
            dy = zone.y - box.top;
        } else if (box.top + box.height > zone.y + zone.height) {
            dy = zone.y + zone.height - (box.top + box.height);
        }
        if (dx || dy) {
            obj.set({ left: obj.left + dx, top: obj.top + dy });
            obj.setCoords();
        }
    }

    dispose() {
        this.resizeObserver?.disconnect();
        this.canvas?.dispose();
        this.canvas = null;
    }
}
