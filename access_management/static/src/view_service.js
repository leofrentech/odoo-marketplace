// @odoo-module

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { jsonrpc } from "@web/core/network/rpc_service";
import { objectToUrlEncodedString } from "@web/core/utils/urls";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";
import { routeToUrl } from "@web/core/browser/router_service";


patch(registry.category("services").get("view"), {
    start(env, { orm }) {
        let cache = {};
        super.start(...arguments)

        async function loadViews(params, options = {}) {
            const { context, resModel, views } = params;
            const loadViewsOptions = {
                action_id: options.actionId || false,
                load_filters: options.loadIrFilters || false,
                toolbar: (!context?.disable_toolbar && options.loadActionMenus) || false,
            };
            for (const key in options) {
                if (!["actionId", "loadIrFilters", "loadActionMenus"].includes(key)) {
                    loadViewsOptions[key] = options[key];
                }
            }
            if (env.isSmall) {
                loadViewsOptions.mobile = true;
            }
            const filteredContext = Object.fromEntries(
                Object.entries(context || {}).filter(
                    ([k, v]) => k == "lang" || k.endsWith("_view_ref")
                )
            );

            const key = JSON.stringify([resModel, views, filteredContext, loadViewsOptions]);
            if (!cache[key]) {
                cache[key] = orm
                    .call(resModel, "get_views", [], {
                        context: filteredContext,
                        views,
                        options: loadViewsOptions,
                    })
                    .then((result) => {
                        jsonrpc("/restrict_debug/check", { model_name: resModel }).then((is_debug_restricted) => {
                            if (is_debug_restricted) {
                                // For Odoo-debug extension from Droggol
                                const body = document.getElementsByTagName('body')[0];
                                body.setAttribute('data-odoo-debug-mode', '')

                                // Hides the debug icon
                                $('.fa-bug').parent().hide()

                                // Keeps debug mode deactivated
                                let router = env.services.router
                                // delete router.current.search.debug
                                router.current.search.debug = ''
                                router.pushState(router.current, { replace: true })

                                // Removes the ? on the fields
                                odoo.debug = ''
                                session.bundle_params.debug = ''
                            }
                        });

                        const { models, views } = result;
                        const viewDescriptions = {
                            fields: models[resModel],
                            relatedModels: models,
                            views: {},
                        };
                        for (const viewType in views) {
                            const { arch, toolbar, id, filters, custom_view_id } = views[viewType];
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
                    })
                    .catch((error) => {
                        delete cache[key];
                        return Promise.reject(error);
                    });
            }
            return cache[key];
        }
        return { loadViews }
    }
})
