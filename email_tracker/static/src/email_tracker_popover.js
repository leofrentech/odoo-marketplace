import { RelativeTime } from "@mail/core/common/relative_time";

import { Component, types, useProps } from "@odoo/owl";

import { formatDateTime } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";

/** Who opened a sent email, and when. */
export class EmailTrackerPopover extends Component {
    static template = "email_tracker.EmailTrackerPopover";
    static components = { RelativeTime };

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = useProps({
            message: types.instanceOf(this.store["mail.message"]),
        });
    }

    trackers() {
        // opened first, then most recent open first
        return [...this.props.message.email_tracker_recipient_ids].sort(
            (a, b) =>
                (b.last_open_date?.ts || 0) - (a.last_open_date?.ts || 0) ||
                (a.recipient_label || "").localeCompare(b.recipient_label || "")
        );
    }

    formatDate(datetime) {
        return datetime ? formatDateTime(datetime) : "";
    }
}
