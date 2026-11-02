import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("access_management_tour", {
    steps: () => [
        {
            content: "The form view and its chatter are loaded",
            trigger: ".o_form_view .o-mail-Chatter-sendMessage",
        },
        {
            content: "Log note is hidden by the rule",
            trigger: ".o-mail-Chatter-topbar:not(:has(.o-mail-Chatter-logNote))",
        },
        {
            content: "Debug mode is restricted",
            trigger: "body:not(.o_debug)",
        },
        {
            content: "Go to the list view",
            trigger: ".o_breadcrumb .o_back_button a, .o_breadcrumb li a",
            run: "click",
        },
        {
            content: "Switch to the list view",
            trigger: ".o_switch_view.o_list",
            run: "click",
        },
        {
            content: "Select a record",
            trigger: ".o_list_view .o_data_row .o_list_record_selector input",
            run: "click",
        },
        {
            content: "Open the actions menu",
            trigger: ".o_control_panel .o_cp_action_menus .dropdown-toggle",
            run: "click",
        },
        {
            content: "Export is hidden by the rule",
            trigger: ".o-dropdown--menu:not(:has(.o-dropdown-item:contains(Export)))",
        },
    ],
});
