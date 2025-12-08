/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from '@web/core/network/rpc';

/**
 * Cart Personalization Buttons
 * Handles Edit & Preview actions for personalized cart items
 */
publicWidget.registry.CartPersonalizationButtons = publicWidget.Widget.extend({
    selector: '.o_cart_product',

    events: {
        'click .edit-design-btn': '_onClickEditDesign',
        'click .preview-design-btn': '_onClickPreviewDesign',
    },

    /**
     * Open personalization editor for a cart line
     * @param {Event} ev
     */
    _onClickEditDesign: function (ev) {
        ev.preventDefault();
        const lineId = $(ev.currentTarget).data('line-id');
        window.location.href = `/shop/personalize/edit/${lineId}`;
    },

    /**
     * Request design preview for a cart line
     * @param {Event} ev
     */
    _onClickPreviewDesign: function (ev) {
        ev.preventDefault();
        const lineId = $(ev.currentTarget).data('line-id');

        rpc('/shop/cart/preview_personalization', {
            line_id: parseInt(lineId),
        })
        .then(result => this._showPreviewModal(result))
        .catch(err => console.error('Error loading preview:', err));
    },

    /**
     * Fill and display the preview modal
     * @param {Object} data
     */
    _showPreviewModal: function (data) {
        const previews = data.previews || [];
        const $grid = $('#preview_grid');

        $grid.find('.design-title').each((i, el) => {
            if (previews[i]?.design_type) {
                $(el).text(previews[i].design_type);
            }
        });
        $grid.find('.preview-item img').each((i, el) => {
            if (previews[i]?.preview_url) {
                $(el).attr('src', previews[i].preview_url);
            }
        });

        $('#preview_personalization_modal').modal('show');
    },
});