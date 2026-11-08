import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const HEX = /^#[0-9a-f]{6}$/i;

/**
 * Edit a comma-separated list of hex colours as swatches:
 * "+" adds a colour with the colour picker, clicking a swatch removes it.
 */
export class ColorPaletteField extends Component {
    static template = "lf_product_personalizer.ColorPaletteField";
    static props = { ...standardFieldProps };

    get colors() {
        return (this.props.record.data[this.props.name] || "")
            .split(",")
            .map((color) => color.trim())
            .filter((color) => HEX.test(color));
    }

    get removeTitle() {
        return _t("Remove this colour");
    }

    save(colors) {
        this.props.record.update({ [this.props.name]: colors.join(",") || false });
    }

    onAdd(ev) {
        const color = ev.target.value.toUpperCase();
        const colors = this.colors;
        if (!colors.some((c) => c.toUpperCase() === color)) {
            this.save([...colors, color]);
        }
        ev.target.value = "#000000";
    }

    onRemove(index) {
        const colors = this.colors;
        colors.splice(index, 1);
        this.save(colors);
    }
}

registry.category("fields").add("lf_color_palette", {
    component: ColorPaletteField,
    supportedTypes: ["char"],
});
