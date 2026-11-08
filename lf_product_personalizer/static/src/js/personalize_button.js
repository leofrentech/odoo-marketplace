import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/** Variant currently selected on the product page. */
function selectedVariantId(fromEl) {
    const root = fromEl.closest("form") || fromEl.closest("#product_detail") || document;
    return parseInt(root.querySelector("input.product_id[name='product_id']")?.value) || null;
}

/**
 * "Personalize" button of the product page: open the editor on the variant
 * selected on the product page.
 */
export class PersonalizeButton extends Interaction {
    static selector = ".o_lf_personalize_btn";
    dynamicContent = {
        _root: { "t-on-click.prevent.noUpdate": this.onClick },
    };

    onClick() {
        const url = new URL(this.el.href, window.location.origin);
        const variantId = selectedVariantId(this.el);
        if (variantId) {
            url.searchParams.set("variant_id", variantId);
        }
        window.location.assign(url.toString());
    }
}

registry
    .category("public.interactions")
    .add("lf_product_personalizer.personalize_button", PersonalizeButton);
