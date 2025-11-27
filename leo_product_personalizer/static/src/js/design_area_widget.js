/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount, onPatched, useRef, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class DesignAreaWidget extends Component {
    static props = {
        ...standardFieldProps,
    };

    static template = "leo_product_personalizer.DesignAreaWidget";

    setup() {
        this.canvasRef = useRef("canvas");
        this.state = useState({
            initialized: false,
            hasImage: false,
            isRestricted: false,
        });
        this.fabricCanvas = null;
        this.restrictedRect = null;
        this.previousImageId = null;
        this.previousRestricted = null;

        onMounted(async () => {
            await this.initCanvas();
        });

        onPatched(async () => {
            // Re-initialize when is_restricted_area or image changes
            const hasImage = !!this.record.data.design_image;
            const isRestricted = this.record.data.is_restricted_area;
            const recordId = this.record.resId;
            
            // Check if image or restriction state changed
            if (this.previousImageId !== recordId || this.previousRestricted !== isRestricted) {
                console.log('Field changed, re-initializing canvas');
                this.previousImageId = recordId;
                this.previousRestricted = isRestricted;
                await this.initCanvas();
            }
        });

        onWillUnmount(() => {
            if (this.fabricCanvas) {
                this.fabricCanvas.dispose();
                this.fabricCanvas = null;
            }
        });
    }

    get record() {
        return this.props.record;
    }

    async initCanvas() {
        // Wait for DOM to be ready
        await new Promise(resolve => setTimeout(resolve, 150));

        const hasImage = !!this.record.data.design_image;
        const isRestricted = this.record.data.is_restricted_area;
        const recordId = this.record.resId;
                
        this.state.hasImage = hasImage;
        this.state.isRestricted = isRestricted;

        // Dispose existing canvas if any
        if (this.fabricCanvas) {
            console.log('Disposing existing canvas');
            this.fabricCanvas.dispose();
            this.fabricCanvas = null;
            this.restrictedRect = null;
        }

        // Check if we should show the canvas
        if (!hasImage) {
            this.state.initialized = false;
            return;
        }

        if (!isRestricted) {
            this.state.initialized = false;
            return;
        }

        try {
            this.fabricCanvas = new fabric.Canvas(this.canvasRef.el, {
                width: 800,
                height: 800,
                backgroundColor: "#f5f5f5",
            });

            // Load image
            const imageUrl = `/web/image/product.design.config/${recordId}/design_image`;
            
            await this.loadBackgroundImage(imageUrl);            
            this.createRestrictedRect();
            this.setupEvents();

            this.state.initialized = true;
        } catch (error) {
            console.error('Error initializing canvas:', error);
        }
    }

    async loadBackgroundImage(imageUrl) {
        return new Promise((resolve, reject) => {
            console.log('Attempting to load image from:', imageUrl);
            fabric.Image.fromURL(imageUrl, (img) => {
                if (!img || !img.width || !img.height) {
                    reject(new Error('Image load failed'));
                    return;
                }

                const w = this.fabricCanvas.getWidth();
                const h = this.fabricCanvas.getHeight();
                const scale = Math.min(w / img.width, h / img.height);

                img.set({
                    left: (w - img.width * scale) / 2,
                    top: (h - img.height * scale) / 2,
                    scaleX: scale,
                    scaleY: scale,
                    selectable: false,
                    evented: false,
                });

                this.fabricCanvas.setBackgroundImage(
                    img,
                    this.fabricCanvas.renderAll.bind(this.fabricCanvas)
                );
                
                resolve();
            }, { crossOrigin: 'anonymous' });
        });
    }

    createRestrictedRect() {
        // Get existing values or use defaults
        const x = this.record.data.bound_x || 100;
        const y = this.record.data.bound_y || 100;
        const w = this.record.data.bound_width || 100;
        const h = this.record.data.bound_height || 100;

        this.restrictedRect = new fabric.Rect({
            left: x,
            top: y,
            width: w,
            height: h,
            fill: "rgba(0, 150, 255, 0.2)",
            stroke: "#0096FF",
            strokeWidth: 3,
            strokeDashArray: [10, 5],
            cornerColor: "#0096FF",
            cornerSize: 14,
            transparentCorners: false,
            cornerStyle: "circle",
            borderColor: "#0096FF",
            lockRotation: true,
            hasRotatingPoint: false,
        });

        this.fabricCanvas.add(this.restrictedRect);
        this.fabricCanvas.setActiveObject(this.restrictedRect);
        this.fabricCanvas.renderAll();
        
    }

    setupEvents() {
        this.fabricCanvas.on("object:modified", () => this.onRectModified());
        this.fabricCanvas.on("object:moving", () => this.clampRect());
        this.fabricCanvas.on("object:scaling", () => this.clampRect());
        console.log('Canvas events registered');
    }

    clampRect() {
        if (!this.restrictedRect) return;

        const rect = this.restrictedRect;
        const canvasW = this.fabricCanvas.getWidth();
        const canvasH = this.fabricCanvas.getHeight();

        rect.setCoords();
        const br = rect.getBoundingRect();

        let left = rect.left;
        let top = rect.top;

        if (br.left < 0) left -= br.left;
        if (br.top < 0) top -= br.top;
        if (br.left + br.width > canvasW) {
            left -= br.left + br.width - canvasW;
        }
        if (br.top + br.height > canvasH) {
            top -= br.top + br.height - canvasH;
        }

        rect.set({ left, top });
        rect.setCoords();
        this.fabricCanvas.renderAll();
    }

    onRectModified() {
        if (!this.restrictedRect) return;
        const br = this.restrictedRect.getBoundingRect();
        this.record.update({
            bound_x: Math.round(br.left),
            bound_y: Math.round(br.top),
            bound_width: Math.round(br.width),
            bound_height: Math.round(br.height),
        });
    }
}

registry.category("fields").add("design_area_widget", {
    component: DesignAreaWidget,
});