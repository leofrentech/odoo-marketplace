import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("lf_personalizer_editor_tour", {
    steps: () => [
        { trigger: ".o_lf_canvas_wrapper .canvas-container" },
        // Wait until the area is loaded (its printable zone hint is shown):
        // objects added while it loads are not recorded.
        { trigger: ".o_lf_hint:not(.d-none)" },
        { trigger: ".o_lf_tool[data-panel='text']", run: "click" },
        { trigger: ".o_lf_text_input", run: "edit Hello Tour" },
        { trigger: ".o_lf_add_text", run: "click" },
        { trigger: ".o_lf_text_controls:not(.d-none) .o_lf_text_edit:value(Hello Tour)" },
        { trigger: ".o_lf_area.active .o_lf_area_dot" },
        { trigger: ".o_lf_price_info:contains(Personalization)" },
        // Preview modal shows every side.
        { trigger: ".o_lf_topbar .dropdown-toggle", run: "click" },
        { trigger: ".o_lf_preview", run: "click" },
        { trigger: ".o_lf_preview_modal.show .o_lf_preview_grid img" },
        // Close once fully shown (Bootstrap ignores hide() while animating).
        { trigger: ".o_lf_preview_modal.show.modal_shown .btn-close", run: "click" },
        { trigger: ".o_lf_preview_modal:not(:visible)" },
        // Second area: leave it empty, it is optional.
        { trigger: ".o_lf_area:not(.active)", run: "click" },
        { trigger: ".o_lf_area.active:not(:has(.o_lf_area_dot))" },
        { trigger: ".o_lf_topbar .o_lf_add_to_cart", run: "click", expectUnloadPage: true },
        { trigger: ".o_lf_cart_designs img" },
        { trigger: ".o_lf_edit_design", run: "click", expectUnloadPage: true },
        { trigger: ".o_lf_personalizer .o_lf_area.active .o_lf_area_dot" },
        { trigger: ".o_lf_topbar .o_lf_add_to_cart:contains(Update cart)" },
    ],
});
