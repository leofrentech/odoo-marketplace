from odoo import api, fields, models

from odoo.addons.lf_product_watermark_overlay.models.watermark_utils import render_watermark


class ProductImage(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "product.image"

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    original_image_1920 = fields.Image(
        string="Original Image",
        store=True,
        readonly=True,
        help="Same purpose as product.template.original_image_1920, but "
             "for this eCommerce extra image.",
    )

    # ------------------------------------------------------------------
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-apply the company-wide watermark to any extra image
        created with a photo already set, unless its product is marked
        not eligible for watermarking."""
        records = super().create(vals_list)
        records.filtered(
            lambda img: img.image_1920 and img._watermark_template().is_watermark_eligible
        )._apply_watermark()
        return records

    def write(self, vals):
        """Auto re-apply the watermark whenever a new photo is uploaded
        to this extra image."""
        res = super().write(vals)
        if "image_1920" in vals:
            # See ProductTemplate.write() for why the stale original must
            # be cleared before re-evaluating: a freshly uploaded photo
            # is never "sticky" to a previous watermark.
            super(ProductImage, self).write({"original_image_1920": False})
            self.filtered(
                lambda img: img._watermark_template().is_watermark_eligible
            )._apply_watermark()
        return res

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    def _watermark_template(self):
        """The product.template whose watermark settings/eligibility
        govern this extra image — the variant's template when this
        image is variant-specific, else the template it's directly
        attached to."""
        self.ensure_one()
        return self.product_variant_id.product_tmpl_id or self.product_tmpl_id

    def _apply_watermark(self, settings=None):
        """Mirror of `ProductTemplate._apply_watermark()`, scoped to this
        extra image's own `image_1920`. Settings are resolved from the
        governing template — there is no separate per-extra-image
        configuration — unless `settings` overrides them, which callers
        use to force a revert (`{"type": "none"}`) regardless of what
        the template's own settings currently resolve to: like
        `_get_watermark_settings()` itself, that resolution doesn't
        factor in `is_watermark_eligible`, so an explicit override is
        how eligibility-driven callers (e.g. marking a product
        ineligible) force a revert instead of a re-apply."""
        for image in self:
            template = image._watermark_template()
            if not template:
                continue
            image_settings = settings if settings is not None else template._get_watermark_settings()

            if image_settings["type"] == "none":
                if not image.original_image_1920:
                    continue  # already plain, nothing to restore
                super(ProductImage, image).write({
                    "image_1920": image.original_image_1920,
                    "original_image_1920": False,
                })
                continue

            if image.video_url:
                continue  # image_1920 is just the video's thumbnail

            original = image.original_image_1920 or image.image_1920
            if not original:
                continue  # no photo at all yet, nothing to watermark

            watermarked = render_watermark(self.env, original, image_settings)
            if not watermarked:
                continue  # unsupported format or failed rendering, leave as is
            vals = {"image_1920": watermarked}
            if not image.original_image_1920:
                vals["original_image_1920"] = original
            super(ProductImage, image).write(vals)
