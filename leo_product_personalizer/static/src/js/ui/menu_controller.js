/** @odoo-module **/

// Menu Controller - Handles menu navigation and panel switching

export class MenuController {
    /**
     * @param {jQuery} $element - Root UI container
     */
    constructor($element) {
        this.$element = $element;
    }

    /**
     * Switch to a specific menu panel
     * @param {string} menuType
     */
    switchToPanel(menuType) {
        this.$element.find(".menu-item").removeClass("active");
        this.$element.find(`.menu-item[data-menu="${menuType}"]`).addClass("active");

        this.$element.find(".menu-panel").hide();
        this.$element.find(`#${menuType}_panel`).show();

        if (menuType === "text") {
            this.$element.find("#personalization_text, #add_text_button").show();
        } else if (menuType === "shape") {
            this.$element.find("#shapes_grid").show();
        }
    }

    /**
     * Auto-switch panel depending on selected object type
     * @param {boolean} isText
     * @param {boolean} isImage
     * @param {boolean} isShape
     */
    autoSwitchPanel(isText, isImage, isShape) {
        this.$element.find(".menu-panel").hide();
        this.$element.find(".menu-item").removeClass("active");

        if (isText) {
            this.$element.find("#text_panel").show();
            this.$element.find('.menu-item[data-menu="text"]').addClass("active");
            this.$element.find("#personalization_text, #add_text_button").hide();
        } else if (isImage) {
            this.$element.find("#image_panel").show();
            this.$element.find('.menu-item[data-menu="image"]').addClass("active");
        } else if (isShape) {
            this.$element.find("#shape_panel").show();
            this.$element.find('.menu-item[data-menu="shape"]').addClass("active");
            this.$element.find("#shapes_grid").hide();
        }
    }

    /**
     * Render variant grid items
     * @param {Array} variants
     * @param {number} activeVariantId
     */
    renderVariantGrid(variants, activeVariantId) {
        const $grid = this.$element.find("#variants_grid");
        $grid.empty();

        if (!variants) return;

        variants.forEach(variant => {
            const isActive = variant.id === activeVariantId;
            const $item = $("<div>")
                .addClass(`col-6 variant-item p-2 ${isActive ? "active" : ""}`)
                .attr("data-variant-id", variant.id);

            if (variant.image_url) {
                const $wrapper = $('<div class="variant-image-wrapper"></div>');
                const $img = $("<img>")
                    .addClass("img-fluid")
                    .attr("src", variant.image_url)
                    .attr("alt", variant.name);

                $wrapper.append($img);
                $item.append($wrapper);
            }

            $grid.append($item);
        });
    }

    /**
     * Render shape selection grid
     * @param {Array} shapes
     */
    renderShapesGrid(shapes) {
        const $grid = this.$element.find("#shapes_grid");
        $grid.empty();

        shapes.forEach(shape => {
            const $item = $("<div>")
                .addClass("col-6 shape-item")
                .attr("data-shape-id", shape.id);

            $item.append(
                $("<div>")
                    .addClass("shape-item-icon")
                    .html(`<i class="${shape.faClass}"></i>`)
            );

            $item.append(
                $("<div>")
                    .addClass("shape-item-name")
                    .text(shape.name)
            );

            $grid.append($item);
        });
    }

    /**
     * Populate design type dropdown
     * @param {Array} designTypes
     * @param {string} defaultType
     */
    initializeDesignTypeSelector(designTypes, defaultType) {
        const $selector = this.$element.find("#design_type_selector");
        $selector.empty();

        designTypes.forEach(type => {
            const label = type
                .replace(/_/g, " ")
                .replace(/\b\w/g, c => c.toUpperCase());

            $selector.append(`<option value="${type}">${label}</option>`);
        });

        $selector.val(defaultType);
    }
}