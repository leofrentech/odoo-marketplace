/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { onWillStart } from "@odoo/owl";


patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        onWillStart(this.onWillStart);
    },

    async onWillStart() {
        const access = await this.orm.call(this.props.threadModel, 'get_chatter_data', [], {})
        Object.assign(this.state, access)
    }
})