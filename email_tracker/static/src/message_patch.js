import { Message } from "@mail/core/common/message";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { patch } from "@web/core/utils/patch";

import { EmailTrackerPopover } from "./email_tracker_popover";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.emailTrackerPopover = usePopover(EmailTrackerPopover, { position: "top" });
    },
    get emailTrackerLabel() {
        const total = this.message.email_tracker_recipient_ids.length;
        const opened = this.message.emailTrackerOpenedCount;
        if (!opened) {
            return _t("Not opened");
        }
        if (total === 1) {
            return _t("Opened");
        }
        return _t("Opened %(opened)s/%(total)s", { opened, total });
    },
    onClickEmailTracker(ev) {
        if (this.emailTrackerPopover.isOpen) {
            this.emailTrackerPopover.close();
            return;
        }
        this.emailTrackerPopover.open(ev.currentTarget, { message: this.message });
    },
});
