/** @odoo-module **/

import { ObjectUtils, isText } from "../utils/object_utils";
import { EDITOR_SIZE } from "../utils/fabric_loader";

export class TextHandler {
    constructor(editor) {
        this.editor = editor;
    }

    get canvas() {
        return this.editor.canvasManager.canvas;
    }

    add(text, { fontFamily, fill }) {
        const zone = this.editor.canvasManager.zone;
        const obj = new window.fabric.IText(text, {
            fontFamily,
            fill,
            fontSize: 48,
            textAlign: "center",
            lfLabel: text,
        });
        ObjectUtils.center(obj, zone, EDITOR_SIZE);
        ObjectUtils.fit(obj, zone, EDITOR_SIZE);
        this.canvas.add(obj);
        this.canvas.setActiveObject(obj);
        this.canvas.requestRenderAll();
        return obj;
    }

    update(obj, props) {
        if (!isText(obj)) {
            return;
        }
        obj.set(props);
        if ("text" in props) {
            obj.set("lfLabel", props.text);
        }
        obj.setCoords();
        this.editor.canvasManager.clampToZone(obj);
        this.canvas.requestRenderAll();
        this.canvas.fire("object:modified", { target: obj });
    }

    toggleStyle(obj, style) {
        if (!isText(obj)) {
            return;
        }
        const toggles = {
            bold: { fontWeight: obj.fontWeight === "bold" ? "normal" : "bold" },
            italic: { fontStyle: obj.fontStyle === "italic" ? "normal" : "italic" },
            underline: { underline: !obj.underline },
        };
        if (toggles[style]) {
            this.update(obj, toggles[style]);
        }
    }

    /** Turn scaling into a font size so the text stays crisp. */
    bakeScale(obj) {
        if (!isText(obj) || (obj.scaleX === 1 && obj.scaleY === 1)) {
            return;
        }
        const scale = Math.max(obj.scaleX, obj.scaleY);
        obj.set({ fontSize: Math.round(obj.fontSize * scale), scaleX: 1, scaleY: 1 });
        obj.setCoords();
    }
}
