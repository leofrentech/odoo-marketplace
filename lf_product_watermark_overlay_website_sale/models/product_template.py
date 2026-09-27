from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    @api.model
    def _cron_regenerate_watermarked_images(self):
        """Extend the base backfill cron to also cover eCommerce extra
        images (product.image), with the same rules: only while
        watermarking is enabled, only images without a watermark yet,
        and never video media."""
        if not super()._cron_regenerate_watermarked_images():
            return False
        return self._watermark_in_batches(
            self.env["product.image"],
            [
                ("image_1920", "!=", False),
                ("original_image_1920", "=", False),
                ("video_url", "=", False),
                "|",
                ("product_tmpl_id.is_watermark_eligible", "=", True),
                ("product_variant_id.product_tmpl_id.is_watermark_eligible", "=", True),
            ],
            lambda batch: batch._apply_watermark(),
        )

    def _apply_watermark_to_all_images(self, settings):
        """Also watermark the eCommerce extra images (product.image);
        video media is skipped by `ProductImage._apply_watermark()`."""
        super()._apply_watermark_to_all_images(settings)
        self.env["product.image"].search(
            self._get_extra_images_domain()
        )._apply_watermark(settings)

    def _remove_all_watermarks(self):
        """Also restore the eCommerce extra images (product.image)."""
        super()._remove_all_watermarks()
        self.env["product.image"].search(
            self._get_watermarked_extra_images_domain()
        )._apply_watermark({"type": "none"})

    def _has_any_watermark(self):
        return super()._has_any_watermark() or bool(self.env["product.image"].search_count(
            self._get_watermarked_extra_images_domain(), limit=1
        ))

    def _get_extra_images_domain(self):
        """Extra images of these products, attached either to the
        template or to one of its variants."""
        return [
            "|",
            ("product_tmpl_id", "in", self.ids),
            ("product_variant_id.product_tmpl_id", "in", self.ids),
        ]

    def _get_watermarked_extra_images_domain(self):
        """Extra images of these products that currently carry a
        watermark."""
        return self._get_extra_images_domain() + [("original_image_1920", "!=", False)]
