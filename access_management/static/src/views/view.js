import { onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { View } from "@web/views/view";

/**
 * Remove the views restricted by the user's access rules from the view
 * switcher: a view type is removed when the action uses its default view or
 * the restricted view itself, as on the server.
 */
patch(View.prototype, {
    setup() {
        super.setup(...arguments);
        onWillStart(async () => {
            const restrictedViews = await rpc("/check_restricted_views", {
                model: this.props.resModel,
            });
            if (!restrictedViews.length) {
                return;
            }
            const isRestricted = ([viewId, viewType]) =>
                restrictedViews.some(
                    ([restrictedId, restrictedType]) =>
                        restrictedType === viewType &&
                        (!viewId || viewId === restrictedId)
                );
            const views = this.env.config.views.filter((view) => !isRestricted(view));
            const viewTypes = views.map(([, viewType]) => viewType);
            this.env.config.views = views;
            this.env.config.viewSwitcherEntries = this.env.config.viewSwitcherEntries.filter(
                (entry) => viewTypes.includes(entry.type)
            );
        });
    },
});
