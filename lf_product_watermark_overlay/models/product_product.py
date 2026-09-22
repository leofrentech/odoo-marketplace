import logging

from odoo import fields, models, api
from .watermark_utils import decode_image, encode_image, apply_watermark


_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "product.product"

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    original_image_variant_1920 = fields.Image(
        string="Original Variant Image",
        store=True,
        readonly=True,
        help="Same purpose as product.template.original_image_1920, but "
             "for this variant's own image_variant_1920 when it differs "
             "from the template's image.",
    )

    # ------------------------------------------------------------------
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-apply the company-wide watermark to any variant created
        with its own photo already set, unless its template is marked
        not eligible for watermarking."""
        records = super().create(vals_list)
        records.filtered(
            lambda p: p.image_variant_1920 and p.product_tmpl_id.is_watermark_eligible
        )._apply_variant_watermark()
        return records

    def write(self, vals):
        """Auto re-apply the watermark whenever a new variant-specific
        photo is uploaded."""
        res = super().write(vals)
        if "image_variant_1920" in vals:
            # See ProductTemplate.write() for why the stale original must
            # be cleared before re-evaluating: a freshly uploaded photo
            # is never "sticky" to a previous watermark. Applies to every
            # variant in `self` regardless of eligibility.
            super(ProductProduct, self).write({"original_image_variant_1920": False})
            self.filtered(
                lambda p: p.product_tmpl_id.is_watermark_eligible
            )._apply_variant_watermark()
        return res

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    def _apply_variant_watermark(self, settings=None):
        """Mirror of `ProductTemplate._apply_watermark()`, scoped to this
        variant's own `image_variant_1920`. Settings are resolved from
        the template — there is no separate per-variant configuration
        (watermarking applies uniformly per product) — unless `settings`
        overrides them, which callers use to force a revert
        (`{"type": "none"}`) regardless of what the template's own
        settings currently resolve to: like `_get_watermark_settings()`
        itself, that resolution doesn't factor in `is_watermark_eligible`,
        so an explicit override is how eligibility-driven callers (e.g.
        marking a product ineligible) force a revert instead of a
        re-apply."""
        for product in self:
            product_settings = settings if settings is not None else product.product_tmpl_id._get_watermark_settings()

            if product_settings["type"] == "none":
                if not product.original_image_variant_1920:
                    continue  # already plain, nothing to restore
                super(ProductProduct, product).write({
                    "image_variant_1920": product.original_image_variant_1920,
                    "original_image_variant_1920": False,
                })
                continue

            original = product.original_image_variant_1920 or product.image_variant_1920
            if not original:
                continue  # no variant-specific photo yet, nothing to watermark

            try:
                base_image = decode_image(original)
                result = apply_watermark(base_image, product_settings)
                vals = {"image_variant_1920": encode_image(result)}
                if not product.original_image_variant_1920:
                    vals["original_image_variant_1920"] = original
                # Top-level guard: a bad image/font/setting must never
                # block saving the product itself, only skip its watermark.
                super(ProductProduct, product).write(vals)

            except Exception as e:
                _logger.warning(
                    "Watermark failed for product variant %s: %s",
                    product.id,
                    str(e),
                )
