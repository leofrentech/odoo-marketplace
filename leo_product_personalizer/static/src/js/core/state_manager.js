/** @odoo-module **/

// State Manager - Manages design state across different design types

export class StateManager {
    constructor() {
        this.designData = {};
        this.activeDesignType = null;
        this.activeVariantId = null;
        this.productData = null;
    }

    /** Store product data received from backend */
    setProductData(data) {
        this.productData = data;
        this.activeVariantId = data.active_variant_id;
    }

    /**
     * Save canvas JSON for a design type
     * @param {string} designType
     * @param {Object} canvasJSON
     */
    saveDesignState(designType, canvasJSON) {
        if (!designType) return;

        if (!this.designData[designType]) {
            this.designData[designType] = {};
        }

        this.designData[designType].json = canvasJSON;
    }

    /**
     * Retrieve saved design state
     * @param {string} designType
     * @returns {Object|null}
     */
    getDesignState(designType) {
        return this.designData[designType] || null;
    }

    /**
     * Set current active design type
     * @param {string} designType
     */
    setActiveDesignType(designType) {
        this.activeDesignType = designType;
    }

    /** Get current active design type */
    getActiveDesignType() {
        return this.activeDesignType;
    }

    /**
     * Set selected variant ID
     * @param {number} variantId
     */
    setActiveVariant(variantId) {
        this.activeVariantId = variantId;
    }

    /** Get selected variant ID */
    getActiveVariant() {
        return this.activeVariantId;
    }

    /** Remove all saved design states */
    clearDesignData() {
        this.designData = {};
    }

    /** Get all stored design states */
    getAllDesignData() {
        return this.designData;
    }

    /**
     * Load design data (typically in edit mode)
     * @param {Object} data
     */
    setDesignData(data) {
        this.designData = data;
    }

    /** Get stored product data */
    getProductData() {
        return this.productData;
    }
}