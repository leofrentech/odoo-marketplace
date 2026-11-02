/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("access_management_tour", {
    test: true,
    steps: () => [
        {
            content: "The form view and its chatter are loaded",
            trigger: ".o_form_view .o-mail-Chatter-sendMessage",
            isCheck: true,
        },
        {
            content: "Log note is hidden by the rule",
            trigger: ".o-mail-Chatter-topbar:not(:has(.o-mail-Chatter-logNote))",
            isCheck: true,
        },
        {
            content: "Debug mode is restricted",
            trigger: "body:not(.o_debug)",
            isCheck: true,
        },
        {
            content: "Go to the list view",
            trigger: ".o_breadcrumb .o_back_button a, .o_breadcrumb li a",
        },
        {
            content: "Switch to the list view",
            trigger: ".o_switch_view.o_list",
        },
        {
            content: "Select a record",
            trigger: ".o_list_view .o_data_row .o_list_record_selector input",
        },
        {
            content: "Open the actions menu",
            trigger: ".o_control_panel .o_cp_action_menus .dropdown-toggle",
        },
        {
            content: "Export is hidden by the rule",
            trigger: ".o-dropdown--menu:not(:has(.dropdown-item:contains(Export)))",
            isCheck: true,
        },
    ],
});
