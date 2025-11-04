import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";

patch(ControlPanel.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService('orm')
    },
    async shareCurrentView() {
        const searchModel = this.env.searchModel;
        const action_id = this.env.services.action.currentController.action.id

        debugger
        const payload = {
            action_id: action_id,
            model: searchModel.resModel,
            view_mode: searchModel.viewMode,
            domain: JSON.stringify(searchModel.domain).replaceAll('"uid"', user.userId),
            context: JSON.stringify(searchModel.context),
            sort: JSON.stringify(searchModel.orderBy),
        };

        const result_id = await this.orm.call('shared.view.state', 'create', [payload])

        const url = `${window.location.origin}/share/view/${result_id}`;
        navigator.clipboard.writeText(url);
        this.notification.add("✅ Shareable link copied!", { type: "success" });
    }

});

