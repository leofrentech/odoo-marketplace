import { onWillStart } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { ListController } from "@web/views/list/list_controller";

/**
 * Hide the "Export" action when an access rule restricts the export of the
 * model. Wraps the action item rather than overriding `isExportEnable`, which
 * the core controllers set in their own `onWillStart`.
 *
 * A factory, as `patch` binds `super` to the patched prototype: a single
 * object can't be shared between two patches.
 */
const makeExportRestrictionPatch = () => ({
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

patch(ListController.prototype, makeExportRestrictionPatch());
patch(KanbanController.prototype, makeExportRestrictionPatch());
