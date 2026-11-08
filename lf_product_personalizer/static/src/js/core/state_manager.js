/** @odoo-module **/

import { ObjectUtils } from "../utils/object_utils";

/**
 * Editor data: product configuration from the server and the design of
 * each area (keyed by area id).
 */
export class StateManager {
    constructor() {
        this.data = null;
        this.designs = {};
        this.activeAreaKey = null;
    }

    setData(data) {
        this.data = data;
        const keys = new Set(this.areas.map((area) => area.key));
        // Keep designs of areas that still exist (e.g. after a variant switch).
        for (const key of Object.keys(this.designs)) {
            if (!keys.has(key)) {
                delete this.designs[key];
            }
        }
        if (!keys.has(this.activeAreaKey)) {
            this.activeAreaKey = this.areas[0]?.key || null;
        }
    }

    get areas() {
        return this.data?.areas || [];
    }

    get settings() {
        return this.data?.settings || {};
    }

    get activeArea() {
        return this.areaByKey(this.activeAreaKey);
    }

    areaByKey(key) {
        return this.areas.find((area) => area.key === key) || null;
    }

    setDesign(key, json) {
        this.designs[key] = { json };
    }

    getDesign(key) {
        return this.designs[key]?.json || { objects: [] };
    }

    loadDesigns(designs) {
        const keys = new Set(this.areas.map((area) => area.key));
        for (const [key, design] of Object.entries(designs || {})) {
            if (keys.has(key)) {
                this.setDesign(key, design?.json || { objects: [] });
            }
        }
    }

    customizedAreas() {
        return this.areas.filter((area) => !ObjectUtils.isEmpty(this.getDesign(area.key)));
    }

    /** Designs as saved in an account or template: only customized areas. */
    exportDesigns() {
        const result = {};
        for (const area of this.customizedAreas()) {
            result[area.key] = { json: this.getDesign(area.key) };
        }
        return result;
    }
}
