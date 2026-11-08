/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

/** "My Designs" portal page: copy share links and confirm deletion. */
publicWidget.registry.LfPortalDesigns = publicWidget.Widget.extend({
    selector: ".o_lf_my_designs",
    events: {
        "click .o_lf_copy_link": "_onCopy",
        "submit .o_lf_delete_design": "_onDelete",
    },

    init() {
        this._super(...arguments);
        this.notification = this.bindService("notification");
    },

    async _onCopy(ev) {
        const url = ev.currentTarget.dataset.url;
        try {
            await browser.navigator.clipboard.writeText(url);
            this.notification.add(_t("Link copied: anyone with it can open this design."), {
                type: "success",
            });
        } catch {
            this.notification.add(url, { type: "info" });
        }
    },

    _onDelete(ev) {
        const form = ev.currentTarget;
        if (form.dataset.confirmed) {
            return;
        }
        ev.preventDefault();
        this.call("dialog", "add", ConfirmationDialog, {
            title: _t("Delete this design?"),
            body: _t("This cannot be undone. Share links will stop working."),
            confirmLabel: _t("Delete"),
            confirm: () => {
                form.dataset.confirmed = "1";
                form.submit();
            },
            cancel: () => {},
        });
    },
});
