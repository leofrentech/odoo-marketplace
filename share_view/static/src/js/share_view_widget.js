/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.SharedViewWidget = publicWidget.Widget.extend({
    selector: '#shared_view',
    start() {
        this.action = this.bindService('action')
        return this._super()
    }
})