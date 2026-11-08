import { EDITOR_SIZE } from "./fabric_loader";
import { ObjectUtils } from "./object_utils";

/**
 * Renders an area design off-screen:
 * - preview: the design on the product mockup (shown in cart, order, PDF)
 * - print: the design only, transparent, cropped to the printable zone,
 *   at a higher resolution (scale) for production
 * - svg: the same zone as a vector file
 */
export class PreviewGenerator {
    static zoneOf(area) {
        if (area?.is_restricted_area && area.bound_width > 0 && area.bound_height > 0) {
            return {
                x: area.bound_x,
                y: area.bound_y,
                width: area.bound_width,
                height: area.bound_height,
            };
        }
        return null;
    }

    static loadImage(url) {
        return new Promise((resolve) => {
            if (!url) {
                resolve(null);
                return;
            }
            window.fabric.Image.fromURL(url, (img) => resolve(img && img.width ? img : null), {
                crossOrigin: "anonymous",
            });
        });
    }

    /** Scale and center a mockup image on the square editor canvas. */
    static fitBackground(img) {
        const scale = Math.min(EDITOR_SIZE / img.width, EDITOR_SIZE / img.height);
        img.set({
            originX: "left",
            originY: "top",
            left: (EDITOR_SIZE - img.width * scale) / 2,
            top: (EDITOR_SIZE - img.height * scale) / 2,
            scaleX: scale,
            scaleY: scale,
            selectable: false,
            evented: false,
        });
        return img;
    }

    static async _canvas(area, json, withBackground) {
        const canvas = new window.fabric.StaticCanvas(document.createElement("canvas"), {
            width: EDITOR_SIZE,
            height: EDITOR_SIZE,
            enableRetinaScaling: false,
        });
        if (withBackground) {
            canvas.backgroundColor = "#ffffff";
            const img = await this.loadImage(area?.image_url);
            if (img) {
                canvas.setBackgroundImage(this.fitBackground(img));
            }
        }
        await ObjectUtils.restore(canvas, json);
        canvas.renderAll();
        return canvas;
    }

    /** @returns {Promise<string>} JPEG data URL of the design on the mockup */
    static async preview(area, json) {
        const canvas = await this._canvas(area, json, true);
        const url = canvas.toDataURL({ format: "jpeg", quality: 0.9 });
        canvas.dispose();
        return url;
    }

    /** @returns {Promise<string>} PNG data URL of the printable zone only */
    static async print(area, json, scale = 4) {
        const canvas = await this._canvas(area, json, false);
        const zone = this.zoneOf(area) || { x: 0, y: 0, width: EDITOR_SIZE, height: EDITOR_SIZE };
        const url = canvas.toDataURL({
            format: "png",
            left: zone.x,
            top: zone.y,
            width: zone.width,
            height: zone.height,
            multiplier: Math.max(1, Math.min(10, scale)),
        });
        canvas.dispose();
        return url;
    }

    /** @returns {Promise<string>} SVG of the printable zone */
    static async svg(area, json) {
        const canvas = await this._canvas(area, json, false);
        const zone = this.zoneOf(area) || { x: 0, y: 0, width: EDITOR_SIZE, height: EDITOR_SIZE };
        const svg = canvas.toSVG({
            width: zone.width,
            height: zone.height,
            viewBox: { x: zone.x, y: zone.y, width: zone.width, height: zone.height },
        });
        canvas.dispose();
        return svg;
    }
}
