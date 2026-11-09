import { Message } from "@mail/core/common/message_model";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.email_tracker_recipient_ids = fields.Many("email.tracker.recipient", {
            inverse: "mail_message_id",
        });
    },
    emailTrackerOpenedCount() {
        return this.email_tracker_recipient_ids.filter((tracker) => tracker.isOpened()).length;
    },
});
