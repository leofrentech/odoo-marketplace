from odoo import models

from odoo.addons.lf_product_watermark_overlay.models.watermark_utils import detach_image


class ProductProduct(models.Model):
    _inherit = "product.product"

    # ------------------------------------------------------------------
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    def write(self, vals):
        """Variant counterpart of ProductTemplate.write(): a variant's main
        image that follows its first variant image mirrors that image's
        watermark and original."""
        if (
            "image_variant_1920" not in vals
            or not self.env.context.get("from_extra_image")
            or self.env.context.get("lf_watermark_mirror")
        ):
            return super().write(vals)
        res = super(ProductProduct, self.with_context(lf_watermark_mirror=True)).write(vals)
        for product in self:
            source = product.variant_image_ids.sorted("sequence")[:1]
            product.with_context(lf_watermark_mirror=True).write({
                "original_image_variant_1920": detach_image(source.original_image_1920),
            })
        return res
