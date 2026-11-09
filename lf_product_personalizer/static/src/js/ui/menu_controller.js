import { _t } from "@web/core/l10n/translation";
import { el, formatPrice, icon } from "../utils/dom_utils";
import { ShapeHandler } from "../handlers/shape_handler";

/** Builds the dynamic parts of the editor sidebar. */
export class MenuController {
    constructor(rootEl) {
        this.root = rootEl;
    }

    q(selector) {
        return this.root.querySelector(selector);
    }

    qa(selector) {
        return [...this.root.querySelectorAll(selector)];
    }

    showPanel(name) {
        for (const tool of this.qa(".o_lf_tool")) {
            tool.classList.toggle("active", tool.dataset.panel === name);
            tool.setAttribute("aria-pressed", tool.dataset.panel === name ? "true" : "false");
        }
        for (const panel of this.qa(".o_lf_panel")) {
            panel.classList.toggle("o_lf_panel_active", panel.dataset.panel === name);
        }
        this.activePanel = name;
    }

    /** Hide tools the shop disabled for this product. */
    applyToolSettings(settings, data) {
        const allowed = {
            text: settings.allow_text,
            image: settings.allow_image,
            clipart: settings.allow_clipart && data.cliparts.length > 0,
            shape: settings.allow_shape,
        };
        for (const tool of this.qa(".o_lf_tool[data-tool]")) {
            tool.classList.toggle("d-none", !allowed[tool.dataset.tool]);
        }
        this.q('.o_lf_tool[data-panel="templates"]').classList.toggle("d-none", !data.presets.length);
        this.q('.o_lf_tool[data-panel="variant"]').classList.toggle("d-none", data.variants.length < 2);
        const visible = this.qa(".o_lf_tool").filter((tool) => !tool.classList.contains("d-none"));
        const keepCurrent = visible.some((tool) => tool.dataset.panel === this.activePanel);
        this.showPanel(keepCurrent ? this.activePanel : visible[0]?.dataset.panel);
    }

    renderAreas(areas, activeKey, pricing, customizedKeys) {
        const container = this.q(".o_lf_areas");
        container.classList.toggle("d-none", areas.length < 2);
        container.replaceChildren(
            ...areas.map((area) => {
                const button = el("button", {
                    classes: `nav-link o_lf_area${area.key === activeKey ? " active" : ""}`,
                    attrs: {
                        type: "button",
                        role: "tab",
                        "data-area": area.key,
                        "aria-selected": area.key === activeKey ? "true" : "false",
                    },
                    text: area.name,
                });
                if (customizedKeys.has(area.key)) {
                    button.appendChild(el("span", { classes: "o_lf_area_dot", attrs: { title: _t("Customized") } }));
                }
                const extra = pricing.areas?.[area.key];
                if (extra) {
                    button.appendChild(
                        el("small", { classes: "ms-1 opacity-75", text: `+${formatPrice(extra, pricing.currency)}` })
                    );
                }
                if (area.is_required) {
                    button.appendChild(el("span", { classes: "text-danger ms-1", text: "*" }));
                }
                return button;
            })
        );
    }

    renderPalettes(colors, allowCustom) {
        for (const palette of this.qa(".o_lf_palette")) {
            const swatches = colors.map((color) =>
                el("button", {
                    classes: "o_lf_swatch",
                    attrs: {
                        type: "button",
                        "data-color": color,
                        title: color,
                        "aria-label": color,
                        style: `background-color: ${color}`,
                    },
                })
            );
            if (allowCustom) {
                const label = el("label", { classes: "o_lf_swatch o_lf_swatch_custom", attrs: { title: _t("Custom colour") } });
                label.append(icon("colorize"), el("input", {
                    classes: "o_lf_color_input visually-hidden",
                    attrs: { type: "color", "aria-label": _t("Custom colour") },
                }));
                swatches.push(label);
            }
            palette.replaceChildren(...swatches);
        }
    }

    renderFonts(fonts) {
        const select = this.q(".o_lf_font");
        select.replaceChildren(
            ...fonts.map((font) =>
                el("option", { attrs: { value: font.family, style: `font-family: "${font.family}"` }, text: font.name })
            )
        );
    }

    renderShapes() {
        this.q(".o_lf_shapes").replaceChildren(
            ...ShapeHandler.shapes.map((shape) => {
                const col = el("div", { classes: "col-4" });
                const button = el("button", {
                    classes: "o_lf_tile o_lf_shape w-100",
                    attrs: { type: "button", "data-shape": shape.id, title: shape.name },
                });
                button.append(icon(shape.icon, `${shape.iconClasses || ""} oi-2x`), el("small", { text: shape.name }));
                col.appendChild(button);
                return col;
            })
        );
    }

    renderCliparts(cliparts, search = "") {
        const term = search.trim().toLowerCase();
        const items = cliparts.filter(
            (clip) => !term || clip.name.toLowerCase().includes(term) || clip.category.toLowerCase().includes(term)
        );
        const container = this.q(".o_lf_cliparts");
        if (!items.length) {
            container.replaceChildren(el("p", { classes: "text-muted small", text: _t("No clipart found.") }));
            return;
        }
        container.replaceChildren(
            ...items.map((clip) => {
                const col = el("div", { classes: "col-4" });
                const button = el("button", {
                    classes: "o_lf_tile o_lf_clipart w-100",
                    attrs: { type: "button", "data-url": clip.url, "data-name": clip.name, title: clip.name },
                });
                button.appendChild(el("img", { attrs: { src: clip.url, alt: clip.name, loading: "lazy" } }));
                col.appendChild(button);
                return col;
            })
        );
    }

    renderPresets(presets) {
        this.q(".o_lf_presets").replaceChildren(
            ...presets.map((preset) => {
                const col = el("div", { classes: "col-6" });
                const button = el("button", {
                    classes: "o_lf_tile o_lf_preset w-100",
                    attrs: { type: "button", "data-preset": preset.id, title: preset.name },
                });
                button.append(
                    el("img", { attrs: { src: preset.preview_url, alt: preset.name, loading: "lazy" } }),
                    el("small", { classes: "text-truncate w-100", text: preset.name })
                );
                col.appendChild(button);
                return col;
            })
        );
    }

    renderVariants(variants, activeId) {
        this.q(".o_lf_variants").replaceChildren(
            ...variants.map((variant) => {
                const col = el("div", { classes: "col-6" });
                const button = el("button", {
                    classes: `o_lf_tile o_lf_variant w-100${variant.id === activeId ? " active" : ""}`,
                    attrs: { type: "button", "data-variant": variant.id, title: variant.name },
                });
                button.append(
                    el("img", { attrs: { src: variant.image_url, alt: variant.name, loading: "lazy" } }),
                    el("small", { classes: "text-truncate w-100", text: variant.name })
                );
                col.appendChild(button);
                return col;
            })
        );
    }
}
