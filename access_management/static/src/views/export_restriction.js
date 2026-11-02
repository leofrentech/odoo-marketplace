import { onWillStart } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";

/**
 * Hide the "Export" action when an access rule restricts the export of the
 * model. Wraps the action item rather than overriding `isExportEnable`, which
 * the core controller sets in its own `onWillStart`.
 *
 * The kanban views have no action menu: their "Export All" button follows the
 * `export_xlsx` attribute set on the server.
 */
patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        const orm = useService("orm");
        this.isExportAllowedByRules = true;
        onWillStart(async () => {
            this.isExportAllowedByRules = await orm.call(
                "res.users",
                "check_export_enable",
                [this.props.resModel]
            );
        });
    },

    getStaticActionMenuItems() {
        const items = super.getStaticActionMenuItems();
        if (items.export) {
            const isAvailable = items.export.isAvailable;
            items.export.isAvailable = () => this.isExportAllowedByRules && isAvailable();
        }
        return items;
    },
});
