import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

/** "My Designs" portal page: copy share links and confirm deletion. */
export class PortalDesigns extends Interaction {
    static selector = ".o_lf_my_designs";
    dynamicContent = {
        ".o_lf_copy_link": { "t-on-click.noUpdate.withTarget": this.onCopy },
        ".o_lf_delete_design": { "t-on-submit.noUpdate.withTarget": this.onDelete },
    };

    async onCopy(ev, button) {
        try {
            await browser.navigator.clipboard.writeText(button.dataset.url);
            this.services.notification.add(_t("Link copied: anyone with it can open this design."), {
                type: "success",
            });
        } catch {
            this.services.notification.add(button.dataset.url, { type: "info" });
        }
    }

    onDelete(ev, form) {
        if (form.dataset.confirmed) {
            return;
        }
        ev.preventDefault();
        this.services.dialog.add(ConfirmationDialog, {
            title: _t("Delete this design?"),
            body: _t("This cannot be undone. Share links will stop working."),
            confirmLabel: _t("Delete"),
            confirm: () => {
                form.dataset.confirmed = "1";
                form.submit();
            },
            cancel: () => {},
        });
    }
}

registry.category("public.interactions").add("lf_product_personalizer.portal_designs", PortalDesigns);
