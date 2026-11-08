/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("lf_personalizer_editor_tour", {
    test: true,
    steps: () => [
        { trigger: ".o_lf_canvas_wrapper .canvas-container", isCheck: true },
        { trigger: ".o_lf_tool[data-panel='text']", run: "click" },
        { trigger: ".o_lf_text_input", run: "text Hello Tour" },
        { trigger: ".o_lf_add_text", run: "click" },
        {
            trigger: ".o_lf_text_controls:not(.d-none) .o_lf_text_edit",
            run() {
                if (this.$anchor.val() !== "Hello Tour") {
                    throw new Error("The selected text should be editable in the panel.");
                }
            },
        },
        { trigger: ".o_lf_area.active .o_lf_area_dot", isCheck: true },
        { trigger: ".o_lf_price_info:contains(Personalization)", isCheck: true },
        // Preview modal shows every side.
        { trigger: ".o_lf_topbar .dropdown-toggle", run: "click" },
        { trigger: ".o_lf_preview", run: "click" },
        // While a modal is open, Odoo 17 looks for triggers inside it.
        { trigger: ".o_lf_preview_grid img", isCheck: true },
        // Close once fully shown (Bootstrap ignores hide() while animating).
        { trigger: ".btn-close", extra_trigger: ".o_lf_preview_modal.modal_shown", run: "click" },
        { trigger: "body:not(.modal-open)", in_modal: false, isCheck: true },
        // Second area: leave it empty, it is optional.
        { trigger: ".o_lf_area:not(.active)", run: "click" },
        { trigger: ".o_lf_area.active:not(:has(.o_lf_area_dot))", isCheck: true },
        { trigger: ".o_lf_topbar .o_lf_add_to_cart", run: "click" },
        { trigger: ".o_lf_cart_designs img", isCheck: true },
        { trigger: ".o_lf_edit_design", run: "click" },
        { trigger: ".o_lf_personalizer .o_lf_area.active .o_lf_area_dot", isCheck: true },
        { trigger: ".o_lf_topbar .o_lf_add_to_cart:contains(Update cart)", isCheck: true },
    ],
});
