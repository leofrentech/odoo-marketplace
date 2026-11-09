import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { onWillStart } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        onWillStart(() => this.loadAccessRuleChatterData());
    },

    /** Hide the chatter parts hidden by the user's access rules. */
    async loadAccessRuleChatterData() {
        try {
            const access = await this.orm.call(this.threadModel(), "get_chatter_data", [], {});
            if (access) {
                Object.assign(this.state, access);
            }
        } catch (error) {
            // Models without chatter data (not a mail.thread) keep it whole
            if (
                error?.data?.name === "builtins.AttributeError" ||
                error?.message?.includes("does not exist")
            ) {
                return;
            }
            throw error;
        }
    },
});
