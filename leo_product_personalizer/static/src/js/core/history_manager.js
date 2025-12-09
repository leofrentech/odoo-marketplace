/** @odoo-module **/

// History Manager - Handles undo/redo functionality

export class HistoryManager {
    /**
     * @param {fabric.Canvas} fabricCanvas - The Fabric.js canvas instance
     * @param {fabric.Rect|null} zoneRect - The restricted zone rectangle (if any)
     */
    constructor(fabricCanvas, zoneRect) {
        this.fabricCanvas = fabricCanvas;
        this.zoneRect = zoneRect;
        this.history = [];
        this.historyStep = -1;
        this.isUndoRedoAction = false;
    }

    /** Save current canvas JSON state (excluding zone rect) */
    saveState() {
        try {
            this.history = this.history.slice(0, this.historyStep + 1);

            const json = this.fabricCanvas.toJSON();
            if (json.objects) {
                json.objects = json.objects.filter(obj => 
                    !obj.isZoneRect && obj.name !== "zoneRect"
                );
            }

            // Also save zone information with the state
            if (!json.metadata) json.metadata = {};
            if (this.zoneRect) {
                json.metadata.hasZone = true;
            } else {
                json.metadata.hasZone = false;
            }

            this.history.push(JSON.stringify(json));
            this.historyStep++;
        } catch (e) {
            console.error("saveState error", e);
        }
    }

    /**
     * Undo last action
     * @param {Function} callback - Called after undo state loads
     */
    undo(callback) {
        if (this.historyStep > 0) {
            this.historyStep--;
            this._loadHistoryState(callback);
        }
    }

    /**
     * Redo last undone action
     * @param {Function} callback - Called after redo state loads
     */
    redo(callback) {
        if (this.historyStep < this.history.length - 1) {
            this.historyStep++;
            this._loadHistoryState(callback);
        }
    }

    /**
     * Load a state from the history stack
     * @private
     * @param {Function} callback - Called after canvas loads
     */
    _loadHistoryState(callback) {
        const bg = this.fabricCanvas.backgroundImage;
        const currentZone = this.zoneRect
            ? {
                bound_x: this.zoneRect.left,
                bound_y: this.zoneRect.top,
                width: this.zoneRect.width,
                height: this.zoneRect.height,
            }
            : null;

        this.isUndoRedoAction = true;

        const historyJson = JSON.parse(this.history[this.historyStep]);
        const shouldHaveZone = historyJson.metadata?.hasZone || false;

        this.fabricCanvas.loadFromJSON(historyJson, () => {
            if (bg) {
                this.fabricCanvas.setBackgroundImage(
                    bg,
                    this.fabricCanvas.renderAll.bind(this.fabricCanvas)
                );
            }

            // Re-add zone if it should exist
            if (shouldHaveZone && currentZone && currentZone.width > 0 && currentZone.height > 0) {
                // Recreate zone rectangle after canvas load
                const newZoneRect = new fabric.Rect({
                    left: currentZone.bound_x,
                    top: currentZone.bound_y,
                    width: currentZone.width,
                    height: currentZone.height,
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
                this.fabricCanvas.add(newZoneRect);
                this.fabricCanvas.bringToFront(newZoneRect);
                this.zoneRect = newZoneRect;
            } else {
                // Remove zone if it shouldn't exist
                this.fabricCanvas.getObjects().forEach(o => {
                    if (o.isZoneRect || o.name === "zoneRect") {
                        this.fabricCanvas.remove(o);
                    }
                });
                this.zoneRect = null;
            }

            if (shouldHaveZone && currentZone && callback) {
                callback(currentZone);
            }

            this.fabricCanvas.renderAll();
            this.isUndoRedoAction = false;
        });
    }

    /** Whether undo can be performed */
    canUndo() {
        return this.historyStep > 0;
    }

    /** Whether redo can be performed */
    canRedo() {
        return this.historyStep < this.history.length - 1;
    }

    /** Clear all history records */
    reset() {
        this.history = [];
        this.historyStep = -1;
    }

    /**
     * Update reference to the current zone rect
     * @param {fabric.Rect} zoneRect
     */
    updateZoneRect(zoneRect) {
        this.zoneRect = zoneRect;
    }
}