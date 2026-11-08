/** @odoo-module **/

import { loadJS } from "@web/core/assets";

/** Size (px) of the square logical canvas every area is designed on. */
export const EDITOR_SIZE = 800;

const FABRIC_URL = "/lf_product_personalizer/static/lib/fabric/fabric.min.js";

/**
 * Load Fabric.js only on pages that need it.
 * @returns {Promise<typeof window.fabric>}
 */
export async function loadFabric() {
    if (!window.fabric) {
        await loadJS(FABRIC_URL);
    }
    return window.fabric;
}
