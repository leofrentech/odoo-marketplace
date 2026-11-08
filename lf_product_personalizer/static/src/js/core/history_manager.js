import { ObjectUtils } from "../utils/object_utils";

const MAX_STEPS = 50;

/**
 * Undo / redo for the objects of the current area. Only the customer's
 * objects are stored, the background and zone are left untouched.
 */
export class HistoryManager {
    constructor(canvasManager, onRestored) {
        this.canvasManager = canvasManager;
        this.onRestored = onRestored;
        this.stack = [];
        this.index = -1;
        this.restoring = false;
    }

    reset() {
        this.stack = [];
        this.index = -1;
        this.save();
    }

    save() {
        if (this.restoring) {
            return;
        }
        const state = JSON.stringify(ObjectUtils.serialize(this.canvasManager.canvas));
        if (state === this.stack[this.index]) {
            return;
        }
        this.stack = this.stack.slice(0, this.index + 1);
        this.stack.push(state);
        if (this.stack.length > MAX_STEPS) {
            this.stack.shift();
        }
        this.index = this.stack.length - 1;
    }

    canUndo() {
        return this.index > 0;
    }

    canRedo() {
        return this.index < this.stack.length - 1;
    }

    async undo() {
        if (this.canUndo()) {
            this.index--;
            await this._restore();
        }
    }

    async redo() {
        if (this.canRedo()) {
            this.index++;
            await this._restore();
        }
    }

    async _restore() {
        this.restoring = true;
        try {
            this.canvasManager.clearObjects();
            await ObjectUtils.restore(this.canvasManager.canvas, JSON.parse(this.stack[this.index]));
            this.canvasManager.keepZoneOnTop();
            this.canvasManager.canvas.requestRenderAll();
        } finally {
            this.restoring = false;
        }
        this.onRestored?.();
    }
}
