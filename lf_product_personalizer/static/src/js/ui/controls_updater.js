import { isImage, isText, isUserObject } from "../utils/object_utils";

function toHex(color) {
    if (!color || typeof color !== "string") {
        return "#000000";
    }
    if (color.startsWith("#")) {
        return color.length === 4
            ? "#" + [...color.slice(1)].map((c) => c + c).join("")
            : color.slice(0, 7);
    }
    const rgb = color.match(/\d+/g);
    if (!rgb || rgb.length < 3) {
        return "#000000";
    }
    return "#" + rgb.slice(0, 3).map((x) => parseInt(x).toString(16).padStart(2, "0")).join("");
}

/** Shows the controls matching the selected object and fills their values. */
export class ControlsUpdater {
    constructor(rootEl) {
        this.root = rootEl;
    }

    q(selector) {
        return this.root.querySelector(selector);
    }

    update(obj, imageValues) {
        const valid = isUserObject(obj);
        const text = valid && isText(obj);
        const image = valid && isImage(obj);
        const shape = valid && !text && !image;
        this.q(".o_lf_text_controls").classList.toggle("d-none", !text);
        this.q(".o_lf_image_controls").classList.toggle("d-none", !image);
        this.q(".o_lf_shape_controls").classList.toggle("d-none", !shape);

        if (text) {
            const edit = this.q(".o_lf_text_edit");
            if (document.activeElement !== edit) {
                edit.value = obj.text;
            }
            this.q(".o_lf_font").value = obj.fontFamily;
            this.q(".o_lf_font_size").value = Math.round(obj.fontSize);
            this._toggle('.o_lf_style[data-style="bold"]', obj.fontWeight === "bold");
            this._toggle('.o_lf_style[data-style="italic"]', obj.fontStyle === "italic");
            this._toggle('.o_lf_style[data-style="underline"]', Boolean(obj.underline));
            for (const button of this.root.querySelectorAll(".o_lf_align")) {
                button.classList.toggle("active", button.dataset.align === (obj.textAlign || "center"));
            }
            this._markSwatch("text", obj.fill);
        }
        if (image && imageValues) {
            for (const input of this.root.querySelectorAll(".o_lf_image_filter")) {
                input.value = imageValues[input.dataset.op] || 0;
            }
        }
        if (shape) {
            this._markSwatch("fill", obj.type === "line" ? obj.stroke : obj.fill);
            this._markSwatch("stroke", obj.stroke);
            this.q(".o_lf_stroke_width").value = obj.type === "line" ? obj.strokeWidth : obj.strokeWidth || 0;
        }
    }

    _toggle(selector, active) {
        const node = this.q(selector);
        node.classList.toggle("active", active);
        node.setAttribute("aria-pressed", active ? "true" : "false");
    }

    _markSwatch(target, color) {
        const hex = toHex(color).toLowerCase();
        const palette = this.q(`.o_lf_palette[data-target="${target}"]`);
        for (const swatch of palette.querySelectorAll(".o_lf_swatch[data-color]")) {
            swatch.classList.toggle("active", swatch.dataset.color.toLowerCase() === hex);
        }
        const custom = palette.querySelector(".o_lf_color_input");
        if (custom) {
            custom.value = hex;
        }
    }

    updateHistory(canUndo, canRedo) {
        this.q(".o_lf_undo").disabled = !canUndo;
        this.q(".o_lf_redo").disabled = !canRedo;
    }
}
