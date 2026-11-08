import { _t } from "@web/core/l10n/translation";
import { el, icon } from "../utils/dom_utils";
import { isImage, isText, isUserObject } from "../utils/object_utils";

/** Layers panel: list, reorder, duplicate, lock and delete objects. */
export class LayerHandler {
    constructor(editor, listEl, emptyEl) {
        this.editor = editor;
        this.listEl = listEl;
        this.emptyEl = emptyEl;
    }

    get canvas() {
        return this.editor.canvasManager.canvas;
    }

    label(obj) {
        if (isText(obj)) {
            return obj.text || _t("Text");
        }
        if (isImage(obj)) {
            return obj.lfLabel || _t("Image");
        }
        return obj.lfLabel || _t("Shape");
    }

    render() {
        const objects = this.canvas.getObjects().filter(isUserObject).reverse();
        const active = this.canvas.getActiveObject();
        this.emptyEl.classList.toggle("d-none", objects.length > 0);
        this.listEl.replaceChildren(
            ...objects.map((obj) => {
                const item = el("div", {
                    classes: `list-group-item d-flex align-items-center gap-2 o_lf_layer${obj === active ? " active" : ""}`,
                });
                const thumb = el("span", { classes: "o_lf_layer_thumb" });
                if (isImage(obj)) {
                    thumb.appendChild(el("img", { attrs: { src: obj.getSrc(), alt: "" } }));
                } else {
                    thumb.appendChild(icon(isText(obj) ? "fa-font" : "fa-star-o"));
                }
                const name = el("button", {
                    classes: "btn btn-link text-start text-truncate flex-grow-1 p-0 o_lf_layer_name",
                    attrs: { type: "button" },
                    text: this.label(obj),
                });
                name.addEventListener("click", () => this.editor.selectObject(obj));
                item.append(thumb, name, this._actions(obj));
                return item;
            })
        );
    }

    _actions(obj) {
        const group = el("div", { classes: "btn-group btn-group-sm flex-shrink-0" });
        const actions = [
            ["fa-arrow-up", _t("Bring forward"), () => this.canvas.bringForward(obj)],
            ["fa-arrow-down", _t("Send backward"), () => this.canvas.sendBackwards(obj)],
            ["fa-clone", _t("Duplicate"), () => this.duplicate(obj)],
            [obj.lfLocked ? "fa-lock" : "fa-unlock", _t("Lock"), () => this.toggleLock(obj)],
            ["fa-trash-o", _t("Delete"), () => this.remove(obj)],
        ];
        for (const [faClass, title, action] of actions) {
            const button = el("button", {
                classes: "btn btn-light",
                attrs: { type: "button", title, "aria-label": title },
            });
            button.appendChild(icon(faClass));
            button.addEventListener("click", (ev) => {
                ev.stopPropagation();
                action();
                this.editor.canvasManager.keepZoneOnTop();
                this.canvas.requestRenderAll();
                this.editor.onCanvasChanged();
            });
            group.appendChild(button);
        }
        return group;
    }

    duplicate(obj) {
        obj.clone((clone) => {
            clone.set({ left: clone.left + 20, top: clone.top + 20 });
            this.canvas.add(clone);
            this.editor.canvasManager.clampToZone(clone);
            this.canvas.setActiveObject(clone);
            this.editor.onCanvasChanged();
        }, ["lfLabel", "lfLocked", "lfClipart"]);
    }

    toggleLock(obj) {
        const locked = !obj.lfLocked;
        obj.set({
            lfLocked: locked,
            lockMovementX: locked,
            lockMovementY: locked,
            lockRotation: locked,
            lockScalingX: locked,
            lockScalingY: locked,
            hasControls: !locked,
        });
    }

    remove(obj) {
        this.canvas.remove(obj);
        this.canvas.discardActiveObject();
    }
}
