// @odoo-module

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
    start(env, { orm }) {
        super.start(...arguments)

        async function loadViews(params, options = {}) {
            const { context, resModel, views } = params;
            const isDebugRestricted = resModel
                ? await rpc("/restrict_debug/check", { model_name: resModel })
                : false;
            syncDebugState(env, isDebugRestricted);
            const loadViewsOptions = {
                action_id: options.actionId || false,
                embedded_action_id: options.embeddedActionId || false,
                embedded_parent_res_id: options.embeddedParentResId || false,
                load_filters: options.loadIrFilters || false,
                toolbar: (!context?.disable_toolbar && options.loadActionMenus) || false,
            };
            for (const key in options) {
                if (
                    ![
                        "actionId",
                        "embeddedActionId",
                        "embeddedParentResId",
                        "loadIrFilters",
                        "loadActionMenus",
                    ].includes(key)
                ) {
                    loadViewsOptions[key] = options[key];
                }
            }
            if (env.isSmall) {
                loadViewsOptions.mobile = true;
            }
            if (env.debug && !isDebugRestricted) {
                loadViewsOptions.debug = true;
            }
            const filteredContext = Object.fromEntries(
                Object.entries(context || {}).filter(
                    ([k, v]) => k == "lang" || k.endsWith("_view_ref")
                )
            );

            const result = await orm.call(resModel, "get_views", [], {
                context: filteredContext,
                views,
                options: loadViewsOptions,
            });

            const viewDescriptions = {
                fields: result.models[resModel].fields,
                relatedModels: result.models,
                views: {},
            };
            for (const viewType in result.views) {
                const { arch, toolbar, id, filters, custom_view_id } = result.views[viewType];
                const viewDescription = { arch, id, custom_view_id };
                if (toolbar) {
                    viewDescription.actionMenus = toolbar;
                }
                if (filters) {
                    viewDescription.irFilters = filters;
                }
                viewDescriptions.views[viewType] = viewDescription;
            }
            return viewDescriptions;
        }
        return { loadViews }
    }
})
