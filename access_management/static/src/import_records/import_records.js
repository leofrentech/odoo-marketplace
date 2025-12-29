/** @odoo-module **/

import { registry } from "@web/core/registry";
// import { patch } from "@web/core/utils/patch";
// import { importRecordsItem } from "@base_import/import_records/import_records";
// import { useService } from "@web/core/utils/hooks";
// import { onWillStart } from "@odoo/owl";
import { archParseBoolean } from "@web/views/utils";

const cogMenuRegistry = registry.category("cogMenu");
cogMenuRegistry.get('import-menu').isDisplayed = ({ config, isSmall }) => {
    return !isSmall &&
        config.actionType === "ir.actions.act_window" &&
        ["kanban", "list"].includes(config.viewType) &&
        archParseBoolean(config.viewArch.getAttribute("import"), true) &&
        archParseBoolean(config.viewArch.getAttribute("create"), true)
}

// cogMenuRegistry.remove("import-menu")
// cogMenuRegistry.add("import-menu", importRecordsItem, { sequence: 1 });

// patch(ImportRecords.prototype, {
//     setup() {
//         super.setup(...arguments)
//         this.orm = useService('orm')
//         onWillStart(this.hideImportRecords)
//     },

//     async hideImportRecords() {
//         this.hideImportRecords = await this.orm.call('res.users', 'check_import_enabled', [this.env.model.config.resModel], {})
//     }
// })
