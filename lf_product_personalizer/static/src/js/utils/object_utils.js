/** @odoo-module **/

/**
 * Helpers to place, serialize and restore the customer's Fabric objects.
 * The zone rectangle (printable area outline) is never part of the design.
 */

const TEXT_TYPES = ["i-text", "text", "textbox"];
const EXTRA_PROPS = ["lfLabel", "lfLocked", "lfClipart"];

export function isText(obj) {
    return Boolean(obj) && TEXT_TYPES.includes(obj.type);
}

export function isImage(obj) {
    return Boolean(obj) && obj.type === "image";
}

export function isUserObject(obj) {
    return Boolean(obj) && !obj.isZoneRect && !obj.isCropRect;
}

export class ObjectUtils {
    /** Center an object in the zone, or in the canvas when there is none. */
    static center(obj, zone, size) {
        const cx = zone ? zone.x + zone.width / 2 : size / 2;
        const cy = zone ? zone.y + zone.height / 2 : size / 2;
        obj.set({ originX: "center", originY: "center", left: cx, top: cy });
        obj.setCoords();
    }

    /** Scale an object down so it fits in the zone (80% of it). */
    static fit(obj, zone, size) {
        const maxW = (zone ? zone.width : size) * 0.8;
        const maxH = (zone ? zone.height : size) * 0.8;
        const ratio = Math.min(maxW / obj.getScaledWidth(), maxH / obj.getScaledHeight(), 1);
        if (ratio < 1) {
            obj.scale((obj.scaleX || 1) * ratio);
            obj.setCoords();
        }
    }

    /** @returns {{objects: Object[]}} */
    static serialize(canvas) {
        return {
            objects: canvas.getObjects().filter(isUserObject).map((obj) => obj.toObject(EXTRA_PROPS)),
        };
    }

    /** Add the objects of a design JSON to a canvas. */
    static restore(canvas, json) {
        const objects = (json?.objects || []).filter((obj) => !obj.isZoneRect);
        if (!objects.length) {
            return Promise.resolve([]);
        }
        return new Promise((resolve) => {
            window.fabric.util.enlivenObjects(objects, (enlivened) => {
                for (const obj of enlivened) {
                    canvas.add(obj);
                }
                resolve(enlivened);
            });
        });
    }

    static isEmpty(json) {
        return !(json?.objects || []).length;
    }
}
