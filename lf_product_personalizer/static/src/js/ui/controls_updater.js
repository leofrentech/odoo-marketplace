/** @odoo-module **/

// Controls Updater - Updates UI panels based on the selected canvas object

export class ControlsUpdater {
    /**
     * @param {jQuery} $element - Root UI container
     */
    constructor($element) {
        this.$element = $element;
    }

    /**
     * Update the UI control panels based on selected object
     * @param {fabric.Object|null} obj
     * @param {fabric.Rect|null} zoneRect
     */
    updateControls(obj, zoneRect) {
        if (!obj || obj === zoneRect) {
            this.hideControls();
            return;
        }

        const isText = obj.type === "i-text" || obj.type === "text";
        const isImage = obj.type === "image";
        const isShape = !isText && !isImage;

        this.$element.find("#text_controls").toggle(isText);
        this.$element.find("#shape_controls").toggle(isShape);
        this.$element.find("#layer_controls").show();

        if (isText) {
            this._updateTextControls(obj);
        } else if (isShape) {
            this._updateShapeControls(obj);
        }
    }

    /**
     * Update text control UI inputs
     * @private
     */
    _updateTextControls(obj) {
        this.$element.find("#text_font_family").val(obj.fontFamily || "Arial");
        this.$element.find("#text_font_size").val(obj.fontSize || 40);
        this.$element.find("#text_color").val(this._toHex(obj.fill));
        this.$element.find("#text_bold").toggleClass("active", obj.fontWeight === "bold");
        this.$element.find("#text_italic").toggleClass("active", obj.fontStyle === "italic");
        this.$element.find("#text_underline").toggleClass("active", obj.underline);
    }

    /**
     * Update shape control UI inputs
     * @private
     */
    _updateShapeControls(obj) {
        this.$element.find("#shape_fill_color").val(this._toHex(obj.fill));
        this.$element.find("#shape_stroke_color").val(this._toHex(obj.stroke));
        this.$element.find("#shape_stroke_width").val(obj.strokeWidth || 2);
    }

    /** Hide all control panels and reset UI state */
    hideControls() {
        this.$element.find("#text_controls, #shape_controls, #layer_controls").hide();
        this.$element.find("#personalization_text, #add_text_button").show();
        this.$element.find("#shapes_grid").show();
    }

    /**
     * Update undo/redo button enabled state
     * @param {boolean} canUndo
     * @param {boolean} canRedo
     */
    updateHistoryButtons(canUndo, canRedo) {
        this.$element.find("#undo_button").prop("disabled", !canUndo);
        this.$element.find("#redo_button").prop("disabled", !canRedo);
    }

    /**
     * Convert rgb/rgba color to hex format
     * @private
     */
    _toHex(color) {
        if (!color || color.startsWith("#")) return color || "#000000";

        const rgb = color.match(/\d+/g);
        if (!rgb || rgb.length < 3) return "#000000";

        return (
            "#" +
            rgb
                .slice(0, 3)
                .map(x => parseInt(x).toString(16).padStart(2, "0"))
                .join("")
        );
    }
}