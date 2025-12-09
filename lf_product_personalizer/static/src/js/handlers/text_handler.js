/** @odoo-module **/

// Text Handler - Handles adding and styling text objects

export class TextHandler {
    /**
     * @param {fabric.Canvas} fabricCanvas - Fabric.js canvas instance
     * @param {Object|null} zone - Optional restricted zone
     */
    constructor(fabricCanvas, zone) {
        this.fabricCanvas = fabricCanvas;
        this.zone = zone;
    }

    /**
     * Add text object to canvas
     * @param {string} text
     * @param {Object} options
     * @returns {fabric.IText|null}
     */
    addText(text, options = {}) {
        if (!text.trim()) {
            alert("Please enter some text");
            return null;
        }

        let left = 100, top = 100;

        if (this.zone) {
            left = this.zone.bound_x + this.zone.width / 2;
            top = this.zone.bound_y + this.zone.height / 2;
        }

        const textObj = new fabric.IText(text, {
            left,
            top,
            fontFamily: options.fontFamily || "Arial",
            fill: options.fill || "#000000",
            fontSize: options.fontSize || 40,
            ...options
        });

        try { textObj.__label = text; } catch (e) {}

        this.fabricCanvas.add(textObj);
        this.fabricCanvas.setActiveObject(textObj);
        this.fabricCanvas.renderAll();

        return textObj;
    }

    /**
     * Update text property (font, color, alignment, etc.)
     * @param {fabric.IText} textObj
     * @param {string} property
     * @param {any} value
     */
    updateTextProperty(textObj, property, value) {
        if (!textObj || (textObj.type !== "i-text" && textObj.type !== "text")) return;
        textObj.set(property, value);
        this.fabricCanvas.renderAll();
    }

    /**
     * Toggle style such as bold/italic/underline
     * @param {fabric.IText} textObj
     * @param {string} style
     */
    toggleTextStyle(textObj, style) {
        if (!textObj || (textObj.type !== "i-text" && textObj.type !== "text")) return;

        const styleMap = {
            bold: ["fontWeight", textObj.fontWeight === "bold" ? "normal" : "bold"],
            italic: ["fontStyle", textObj.fontStyle === "italic" ? "normal" : "italic"],
            underline: ["underline", !textObj.underline],
        };

        const cfg = styleMap[style];
        if (cfg) {
            textObj.set(cfg[0], cfg[1]);
            this.fabricCanvas.renderAll();
        }
    }

    /**
     * Convert scale into actual font size (keeps text crisp)
     * @param {fabric.IText} textObj
     */
    updateFontSizeOnScale(textObj) {
        const scale = Math.max(textObj.scaleX, textObj.scaleY);
        const newFontSize = (textObj.fontSize || 20) * scale;

        textObj.set({
            fontSize: newFontSize,
            scaleX: 1,
            scaleY: 1
        });

        if (textObj.type === "curved-text") {
            textObj.set("diameter", (textObj.diameter || 250) * scale);
        }
    }

    /** Update restricted zone reference */
    updateZone(zone) {
        this.zone = zone;
    }
}