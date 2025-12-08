/** @odoo-module **/

// Layer Handler - Manages object layers, thumbnails, actions, and UI rendering

export class LayerHandler {
    /**
     * @param {fabric.Canvas} fabricCanvas - Fabric canvas instance
     * @param {fabric.Rect|null} zoneRect - Restricted zone rectangle
     */
    constructor(fabricCanvas, zoneRect) {
        this.fabricCanvas = fabricCanvas;
        this.zoneRect = zoneRect;
        this.layerCounter = 1;
    }

    /** Assign a unique layer ID to object */
    assignLayerId(obj) {
        if (!obj) return;
        if (!obj.__layerId) {
            obj.__layerId = "layer_" + this.layerCounter++;
        }
        return obj.__layerId;
    }

    /** Assign layer IDs to all canvas objects */
    assignLayerIds() {
        const objs = this.fabricCanvas?.getObjects() || [];
        objs.forEach(o => {
            if (o && !o.isZoneRect && o.name !== "zoneRect") {
                this.assignLayerId(o);
            }
        });
    }

    /**
     * Render layers panel UI
     * @param {jQuery} $listElement - Container element
     * @param {Function} onSelect - Called when layer clicked
     */
    renderLayersList($listElement, onSelect) {
        if (!$listElement || !$listElement.length) return;

        this.assignLayerIds();

        const objs = (this.fabricCanvas?.getObjects() || []).filter(
            o => o && !o.isZoneRect && o.name !== "zoneRect"
        );

        const ordered = objs.slice().reverse();
        $listElement.empty();

        ordered.forEach(obj => {
            $listElement.append(this._createLayerItem(obj, onSelect));
        });
    }

    /**
     * Create a single layer entry
     * @private
     */
    _createLayerItem(obj, onSelect) {
        const layerId = obj.__layerId;
        const $item = $(`
            <div class="layer-item d-flex align-items-center p-2"
                 data-layer-id="${layerId}"
                 style="border-bottom:1px solid #eee; cursor:pointer;">
            </div>
        `);

        const $thumb = this._createThumbnail(obj);
        const $label = $(
            `<div style="flex:1; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;"></div>`
        ).text(this._getObjectLabel(obj));

        const $controls = this._createLayerControls(obj);

        $item.append($thumb, $label, $controls);

        $item.on("mouseenter", () => $controls.show());
        $item.on("mouseleave", () => $controls.hide());
        $item.on("click", ev => {
            ev.stopPropagation();
            if (onSelect) onSelect(obj);
        });

        if (this.fabricCanvas.getActiveObject() === obj) {
            $item.css("background", "#f1f5f9");
        }

        return $item;
    }

    /**
     * Create thumbnail display
     * @private
     */
    _createThumbnail(obj) {
        const $thumb = $(`
            <div style="
                width:46px; height:46px; flex:0 0 46px;
                border:1px solid #ddd; background:#fff;
                display:flex; align-items:center; justify-content:center;
                overflow:hidden; margin-right:8px;">
            </div>
        `);

        if (obj.type === "image" && obj._element?.src) {
            $thumb.append(
                $(`<img/>`).attr("src", obj._element.src).css({
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                })
            );
        } else if (obj.type === "i-text" || obj.type === "text") {
            const text = obj.text || "";
            $thumb.append(
                $(`<div style="font-size:11px; padding:4px; text-align:center;"></div>`)
                    .text(text.length > 20 ? text.substring(0, 20) + "…" : text)
            );
        } else {
            const icon = this._getShapeIcon(obj);
            $thumb.append(
                $(`<i class="fa ${icon}" style="font-size:20px; color:#3b82f6;"></i>`)
            );
        }

        return $thumb;
    }

    /**
     * Pick icon based on object type
     * @private
     */
    _getShapeIcon(obj) {
        const name = (obj.__label || obj.type || "shape").toLowerCase();

        const iconMap = {
            rect: "fa-square",
            circle: "fa-circle",
            ellipse: "fa-circle",
            triangle: "fa-play",
            star: "fa-star",
            heart: "fa-heart",
            diamond: "fa-diamond",
            arrow: "fa-arrow-right",
            pentagon: "fa-stop",
            hexagon: "fa-stop",
            line: "fa-minus",
        };

        for (const key in iconMap) {
            if (name.includes(key)) return iconMap[key];
        }
        return "fa-layer-group";
    }

    /**
     * Get readable label for object
     * @private
     */
    _getObjectLabel(obj) {
        if (obj.type === "i-text" || obj.type === "text") {
            return obj.text || "Text";
        }
        if (obj.type === "image") {
            return obj._element?.name || "Image";
        }
        return obj.__label || obj.type || "Shape";
    }

    /**
     * Create control buttons (duplicate, lock, delete, reorder)
     * @private
     */
    _createLayerControls(obj) {
        const $controls = $(`
            <div class="layer-controls btn-group"
                 style="display:none; margin-left:8px; gap:2px;">
            </div>
        `);

        const buttons = [
            { icon: "fa-arrow-up", title: "Bring to Front", action: () => this._bringToFront(obj) },
            { icon: "fa-arrow-down", title: "Send to Back", action: () => this._sendToBack(obj) },
            { icon: "fa-copy", title: "Duplicate", action: () => this._duplicate(obj) },
            { icon: "fa-lock", title: "Lock / Unlock", action: () => this._toggleLock(obj) },
            { icon: "fa-trash", title: "Delete", action: () => this._delete(obj), danger: true },
        ];

        buttons.forEach(btn => {
            const $btn = $(`
                <button class="btn btn-sm ${btn.danger ? "btn-outline-danger" : "btn-outline-secondary"}"
                        title="${btn.title}">
                    <i class="fa ${btn.icon}"></i>
                </button>
            `);

            $btn.on("click", ev => {
                ev.stopPropagation();
                btn.action();
            });

            $controls.append($btn);
        });

        return $controls;
    }

    /** Bring object to top layer */
    _bringToFront(obj) {
        this.fabricCanvas.bringToFront(obj);
        if (this.zoneRect) this.fabricCanvas.bringToFront(this.zoneRect);
        this.fabricCanvas.renderAll();
    }

    /** Send object to bottom layer */
    _sendToBack(obj) {
        this.fabricCanvas.sendToBack(obj);
        if (this.zoneRect) this.fabricCanvas.bringToFront(this.zoneRect);
        this.fabricCanvas.renderAll();
    }

    /** Duplicate object onto canvas */
    _duplicate(obj) {
        obj.clone(clone => {
            clone.set({ left: clone.left + 20, top: clone.top + 20 });
            this.fabricCanvas.add(clone);
            this.fabricCanvas.setActiveObject(clone);
            this.fabricCanvas.renderAll();
        });
    }

    /** Lock/unlock object movement and scaling */
    _toggleLock(obj) {
        const locked = !obj.lockMovementX;
        obj.set({
            lockMovementX: locked,
            lockMovementY: locked,
            lockRotation: locked,
            lockScalingX: locked,
            lockScalingY: locked,
        });
        this.fabricCanvas.renderAll();
    }

    /** Remove object from canvas */
    _delete(obj) {
        this.fabricCanvas.remove(obj);
        this.fabricCanvas.renderAll();
    }

    /**
     * Update zone rectangle reference
     * @param {fabric.Rect} zoneRect
     */
    updateZoneRect(zoneRect) {
        this.zoneRect = zoneRect;
    }
}