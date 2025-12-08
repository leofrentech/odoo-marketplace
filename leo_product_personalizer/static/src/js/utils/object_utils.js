/** @odoo-module **/

// Object Utils - Helper functions for fabric object positioning and serialization

export class ObjectUtils {
    /**
     * Center object inside the given zone
     * @param {fabric.Object} obj
     * @param {Object} zone
     */
    static positionInZoneCenter(obj, zone) {
        if (!obj || !zone) return;

        const cx = zone.bound_x + zone.width / 2;
        const cy = zone.bound_y + zone.height / 2;

        obj.set({
            left: cx,
            top: cy,
            originX: "center",
            originY: "center"
        });

        obj.setCoords();
    }

    /**
     * Scale object so it fits inside the zone (with padding)
     * @param {fabric.Object} obj
     * @param {Object} zone
     */
    static scaleToFitZone(obj, zone) {
        if (!obj || !zone) return;

        const br = obj.getBoundingRect(true, true);

        if (br.width > zone.width - 20 || br.height > zone.height - 20) {
            const scaleX = (zone.width - 40) / obj.width;
            const scaleY = (zone.height - 40) / obj.height;
            const scale = Math.min(scaleX, scaleY);

            obj.set({ scaleX: scale, scaleY: scale });
            obj.setCoords();
        }
    }

    /**
     * Remove zone rectangles from object list
     * @param {Array} objects
     * @returns {Array}
     */
    static filterZoneRects(objects) {
        return objects.filter(obj => !obj.isZoneRect && obj.name !== "zoneRect");
    }

    /**
     * Serialize canvas to custom JSON (excluding zone rects)
     * @param {fabric.Canvas} canvas
     * @returns {Object}
     */
    static serializeCanvas(canvas) {
        const objs = canvas.getObjects().filter(
            obj => !obj.isZoneRect && obj.name !== "zoneRect"
        );

        return {
            version: "5.3.0",
            objects: objs.map(obj => obj.toObject())
        };
    }

    /**
     * Restore canvas from cleaned JSON (excluding zone rects)
     * @param {fabric.Canvas} canvas
     * @param {Object} json
     * @param {Function} callback
     */
    static restoreCanvas(canvas, json, callback) {
        if (!json || !json.objects) {
            callback?.();
            return;
        }

        const filtered = {
            version: json.version || "5.3.0",
            objects: (json.objects || []).filter(
                obj => obj.isZoneRect !== true && obj.name !== "zoneRect"
            )
        };

        fabric.util.enlivenObjects(filtered.objects, enlivened => {
            enlivened.forEach(obj => canvas.add(obj));
            callback?.();
        });
    }
}