import { DebugMenu } from "@web/core/debug/debug_menu";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { router } from "@web/core/browser/router";
import { session } from "@web/session";

const systrayRegistry = registry.category("systray");
const DEBUG_MENU_KEY = "web.debug_mode_menu";
const DEBUG_MENU_ITEM = { Component: DebugMenu };
const DEBUG_MENU_SEQUENCE = 100;
const initialDebug = odoo.debug || session.bundle_params.debug || "";

function syncDebugState(env, isRestricted) {
    const body = document.body;
    if (isRestricted) {
        // Keep third-party debug helpers and the webclient itself out of debug mode.
        body.setAttribute("data-odoo-debug-mode", "");
        body.classList.remove("o_debug");
        router.hideKeyFromUrl("debug");
        router.replaceState({ debug: undefined });
        env.debug = "";
        odoo.debug = "";
        session.bundle_params.debug = "";
        if (systrayRegistry.contains(DEBUG_MENU_KEY)) {
            systrayRegistry.remove(DEBUG_MENU_KEY);
        }
        return;
    }

    body.removeAttribute("data-odoo-debug-mode");
    if (!initialDebug) {
        body.classList.remove("o_debug");
        if (systrayRegistry.contains(DEBUG_MENU_KEY)) {
            systrayRegistry.remove(DEBUG_MENU_KEY);
        }
        return;
    }

    body.classList.add("o_debug");
    body.setAttribute("data-odoo-debug-mode", initialDebug);
    env.debug = initialDebug;
    odoo.debug = initialDebug;
    session.bundle_params.debug = initialDebug;
    if (!systrayRegistry.contains(DEBUG_MENU_KEY)) {
        systrayRegistry.add(DEBUG_MENU_KEY, DEBUG_MENU_ITEM, {
            sequence: DEBUG_MENU_SEQUENCE,
        });
    }
}


patch(registry.category("services").get("view"), {
    start(env, dependencies) {
        // Views depend on the user's access rules: don't serve them from the
        // disk cache, which would keep showing them after a rule change.
        const orm = Object.create(dependencies.orm);
        orm.cache = () => dependencies.orm;
        const viewService = super.start(env, { ...dependencies, orm });
        return {
            ...viewService,
            async loadViews(params, options) {
                const isDebugRestricted = params.resModel
                    ? await rpc("/restrict_debug/check", { model_name: params.resModel })
                    : false;
                syncDebugState(env, isDebugRestricted);
                return viewService.loadViews(params, options);
            },
        };
    },
});
