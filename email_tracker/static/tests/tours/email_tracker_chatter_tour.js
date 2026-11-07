/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("email_tracker_chatter_badge", {
    test: true,
    steps: () => [
        {
            content: "Sent email shows how many recipients opened it",
            trigger: ".o-mail-Message:contains('Please find our offer') .o-email-tracker-badge:contains('Opened 1/2')",
            run: "click",
        },
        {
            content: "Popover lists the recipient who opened it",
            trigger: ".o-email-tracker-popover-line:contains('Brandon Freeman (Azure Interior)'):contains('Opened')",
            isCheck: true,
        },
        {
            content: "and the one who did not",
            trigger: ".o-email-tracker-popover-line:contains('Second Customer'):contains('Not opened yet')",
            isCheck: true,
        },
        {
            content: "Messages without tracking have no badge",
            trigger: ".o-mail-Message:contains('Internal remark'):not(:has(.o-email-tracker-badge))",
            isCheck: true,
        },
    ],
});
