import publicWidget from "@web/legacy/js/public/public_widget";

/** Variant currently selected on the product page. */
function selectedVariantId(fromEl) {
    const root = fromEl.closest("form") || fromEl.closest("#product_detail") || document;
    return parseInt(root.querySelector("input.product_id[name='product_id']")?.value) || null;
}

/**
 * "Personalize" button of the product page: open the editor on the variant
 * selected on the product page.
 */
publicWidget.registry.LfPersonalizeButton = publicWidget.Widget.extend({
    selector: ".o_lf_personalize_btn",
    events: {
        click: "_onClick",
    },

    _onClick(ev) {
        ev.preventDefault();
        const url = new URL(this.el.href, window.location.origin);
        const variantId = selectedVariantId(this.el);
        if (variantId) {
            url.searchParams.set("variant_id", variantId);
        }
        window.location.assign(url.toString());
    },
});
