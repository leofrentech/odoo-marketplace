/** @odoo-module **/

import { Message } from "@mail/core/common/message_model";
import { Record } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.email_tracker_recipient_ids = Record.many("EmailTrackerRecipient", {
            inverse: "message",
        });
    },
    get emailTrackerOpenedCount() {
        return this.email_tracker_recipient_ids.filter((tracker) => tracker.isOpened).length;
    },
});
