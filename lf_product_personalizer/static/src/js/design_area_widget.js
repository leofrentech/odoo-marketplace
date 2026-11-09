import { Component, onWillUnmount, proxy, signal, useProps } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useLayoutEffect } from "@web/owl2/utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { EDITOR_SIZE, loadFabric } from "./utils/fabric_loader";

/**
 * Draw the printable zone on the mockup image of a personalization area.
 * Values are stored in the 800x800 coordinate space used by the website editor.
 */
export class DesignAreaWidget extends Component {
    static template = "lf_product_personalizer.DesignAreaWidget";
    props = useProps(standardFieldProps);
    canvasRef = signal.ref();
    containerRef = signal.ref();

    setup() {
        this.state = proxy({ ready: false });
        this.canvas = null;
        this.rect = null;
        this.imageKey = null;
        this.syncing = false;

        useLayoutEffect(
            (image) => {
                this.renderImage(image);
            },
            () => [this.props.record.data[this.props.name]]
        );
        useLayoutEffect(
            () => {
                this.syncRectFromRecord();
            },
            () => {
                const data = this.props.record.data;
                return [data.bound_x, data.bound_y, data.bound_width, data.bound_height];
            }
        );
        onWillUnmount(() => {
            this.resizeObserver?.disconnect();
            this.canvas?.dispose();
        });
    }

    hasImage() {
        return Boolean(this.props.record.data[this.props.name]);
    }

    imageUrl() {
        // Odoo 20 binary values are objects: `content` (base64) is only
        // there for a new or changed image, a saved one is served by URL.
        const record = this.props.record;
        const value = record.data[this.props.name];
        if (value?.content) {
            return `data:image/png;base64,${value.content}`;
        }
        const unique = encodeURIComponent(value?.checksum || record.data.write_date || "");
        return `/web/image/${record.resModel}/${record.resId}/${this.props.name}?unique=${unique}`;
    }

    async renderImage(image) {
        if (!image) {
            // The canvas element leaves the DOM with the image: start over next time.
            this.resizeObserver?.disconnect();
            this.canvas?.dispose();
            this.canvas = null;
            this.rect = null;
            this.imageKey = null;
            this.state.ready = false;
            return;
        }
        const content = image.content || "";
        const key = `${this.props.record.resId}-${image.size}-${content.slice(-16)}`;
        if (key === this.imageKey && this.canvas) {
            return;
        }
        this.imageKey = key;
        const fabric = await loadFabric();
        if (!this.canvasRef()) {
            return;
        }
        if (!this.canvas) {
            this.canvas = new fabric.Canvas(this.canvasRef(), {
                width: EDITOR_SIZE,
                height: EDITOR_SIZE,
                backgroundColor: "#f5f5f5",
                selection: false,
            });
            this.canvas.on("object:moving", () => this.clampRect());
            this.canvas.on("object:scaling", () => this.clampRect());
            this.canvas.on("object:modified", () => this.writeRect());
            this.resizeObserver = new ResizeObserver(() => this.resize());
            this.resizeObserver.observe(this.containerRef());
        }
        fabric.Image.fromURL(
            this.imageUrl(),
            (img) => {
                if (img && img.width) {
                    const scale = Math.min(EDITOR_SIZE / img.width, EDITOR_SIZE / img.height);
                    img.set({
                        left: (EDITOR_SIZE - img.width * scale) / 2,
                        top: (EDITOR_SIZE - img.height * scale) / 2,
                        scaleX: scale,
                        scaleY: scale,
                        selectable: false,
                        evented: false,
                    });
                    this.canvas.setBackgroundImage(img, () => this.canvas.requestRenderAll());
                }
                this.ensureRect();
                this.resize();
                this.state.ready = true;
            },
            { crossOrigin: "anonymous" }
        );
    }

    resize() {
        if (!this.canvas || !this.containerRef()) {
            return;
        }
        const size = Math.min(this.containerRef().clientWidth || EDITOR_SIZE, EDITOR_SIZE);
        this.canvas.setDimensions({ width: size, height: size });
        this.canvas.setZoom(size / EDITOR_SIZE);
        this.canvas.requestRenderAll();
    }

    ensureRect() {
        if (this.rect) {
            return;
        }
        const data = this.props.record.data;
        this.rect = new window.fabric.Rect({
            left: data.bound_x || 200,
            top: data.bound_y || 200,
            width: data.bound_width || 400,
            height: data.bound_height || 400,
            fill: "rgba(13, 110, 253, 0.15)",
            stroke: "#0d6efd",
            strokeWidth: 2,
            strokeDashArray: [8, 6],
            strokeUniform: true,
            cornerColor: "#0d6efd",
            cornerSize: 12,
            transparentCorners: false,
            lockRotation: true,
        });
        this.rect.setControlsVisibility({ mtr: false });
        this.canvas.add(this.rect);
        this.canvas.setActiveObject(this.rect);
        if (!data.bound_width || !data.bound_height) {
            this.writeRect();
        }
    }

    clampRect() {
        const rect = this.rect;
        rect.setCoords();
        const width = Math.min(rect.getScaledWidth(), EDITOR_SIZE);
        const height = Math.min(rect.getScaledHeight(), EDITOR_SIZE);
        rect.set({
            left: Math.max(0, Math.min(rect.left, EDITOR_SIZE - width)),
            top: Math.max(0, Math.min(rect.top, EDITOR_SIZE - height)),
        });
        rect.setCoords();
    }

    writeRect() {
        const rect = this.rect;
        // Bake the scale into width/height so stored values are real sizes.
        const width = Math.round(Math.min(rect.getScaledWidth(), EDITOR_SIZE));
        const height = Math.round(Math.min(rect.getScaledHeight(), EDITOR_SIZE));
        rect.set({ width, height, scaleX: 1, scaleY: 1 });
        this.clampRect();
        this.syncing = true;
        this.props.record.update({
            bound_x: Math.round(rect.left),
            bound_y: Math.round(rect.top),
            bound_width: width,
            bound_height: height,
        });
    }

    syncRectFromRecord() {
        if (!this.rect) {
            return;
        }
        if (this.syncing) {
            this.syncing = false;
            return;
        }
        const data = this.props.record.data;
        const width = Math.max(10, Math.min(data.bound_width || 10, EDITOR_SIZE));
        const height = Math.max(10, Math.min(data.bound_height || 10, EDITOR_SIZE));
        this.rect.set({
            left: Math.max(0, Math.min(data.bound_x || 0, EDITOR_SIZE - width)),
            top: Math.max(0, Math.min(data.bound_y || 0, EDITOR_SIZE - height)),
            width,
            height,
            scaleX: 1,
            scaleY: 1,
        });
        this.rect.setCoords();
        this.canvas.requestRenderAll();
    }
}

registry.category("fields").add("design_area_widget", {
    component: DesignAreaWidget,
    supportedTypes: ["binary"],
    fieldDependencies: [
        { name: "bound_x", type: "float" },
        { name: "bound_y", type: "float" },
        { name: "bound_width", type: "float" },
        { name: "bound_height", type: "float" },
        { name: "write_date", type: "datetime" },
    ],
});
