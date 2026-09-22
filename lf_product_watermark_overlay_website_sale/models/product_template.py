from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # ------------------------------------------------------------------
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    def write(self, vals):
        """Also revert any already-watermarked eCommerce extra image
        (product.image) once this product is marked not eligible for
        watermarking — same reasoning as the base module's own write()
        override for the main product image."""
        res = super().write(vals)
        if "is_watermark_eligible" in vals and not vals["is_watermark_eligible"]:
            images = self.env["product.image"].search([
                "|",
                ("product_tmpl_id", "in", self.ids),
                ("product_variant_id.product_tmpl_id", "in", self.ids),
                ("original_image_1920", "!=", False),
            ])
            images._apply_watermark({"type": "none"})
        return res

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    @api.model
    def _cron_regenerate_watermarked_images(self):
        """Extend the base backfill cron to also cover eCommerce extra
        images (product.image) — same "only ever adds, never removes"
        rule: does nothing while watermarking is disabled company-wide,
        and only backfills extra images that don't already have one."""
        super()._cron_regenerate_watermarked_images()

        # sudo: reading the global config parameter must work regardless
        # of the calling user's own access rights.
        watermark_enabled = self.env["ir.config_parameter"].sudo().get_param(
            "lf_product_watermark_overlay.watermark_enabled", "False"
        ) == "True"
        if not watermark_enabled:
            return

        images = self.env["product.image"]
        domain = [
            ("image_1920", "!=", False),
            ("original_image_1920", "=", False),
            "|",
            ("product_tmpl_id.is_watermark_eligible", "=", True),
            ("product_variant_id.product_tmpl_id.is_watermark_eligible", "=", True),
        ]
        total = images.search_count(domain)
        processed = 0
        while processed < total:
            batch = images.search(domain, limit=self._WATERMARK_REGEN_BATCH_SIZE, offset=processed)
            if not batch:
                break
            batch._apply_watermark()
            processed += len(batch)
            self.env.cr.commit()
