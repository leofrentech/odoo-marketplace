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

        this.fabricCanvas.loadFromJSON(this.history[this.historyStep], () => {
            if (bg) {
                this.fabricCanvas.setBackgroundImage(
                    bg,
                    this.fabricCanvas.renderAll.bind(this.fabricCanvas)
                );
            }

            if (currentZone && callback) {
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