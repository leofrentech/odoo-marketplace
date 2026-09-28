import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..models.watermark_utils import (
    DEFAULT_LOGO_SIZE,
    FONT_SELECTION,
    apply_watermark,
    decode_image,
    encode_image,
    is_valid_opacity,
    is_valid_size_percent,
)


_logger = logging.getLogger(__name__)


class ProductTemplateWatermark(models.TransientModel):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _name = "product.template.watermark"
    _description = "Apply or remove a custom watermark on a product's images"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    @api.model
    def default_get(self, fields):
        """Pre-fill from the company-wide resolved defaults — there is
        no per-product persisted customization to remember, by design
        (see the module's watermarking architecture notes)."""
        res = super().default_get(fields)
        if self.env.context.get("active_model") != "product.template":
            return res
        product = self.env["product.template"].browse(self.env.context.get("active_id")).exists()
        if not product:
            return res

        settings = product._get_watermark_settings()
        res.update({
            "product_tmpl_id": product.id,
            "watermark_type": settings["type"] if settings["type"] != "none" else "image",
            "watermark_logo": settings["logo"],
            "watermark_logo_size": settings["logo_size"],
            "watermark_text": settings["text"],
            "watermark_font": settings["font"],
            "watermark_size": settings["size"],
            "watermark_color": settings["color"],
            "watermark_position": settings["position"],
            "watermark_opacity": settings["opacity"],
        })
        return res

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
    )
    has_watermark = fields.Boolean(
        compute="_compute_product_watermark_state",
        help="Technical field: whether any of the product's images "
             "currently carries a watermark, to show the Remove button.",
    )
    can_apply = fields.Boolean(
        compute="_compute_product_watermark_state",
        help="Technical field: whether the product is eligible and "
             "watermarking is enabled company-wide, to show the Apply "
             "button. The wizard is also reachable without these just "
             "to remove an existing watermark.",
    )
    watermark_type = fields.Selection(
        [("image", "Image"), ("text", "Text")],
        string="Watermark Type",
        default="image",
        required=True,
    )
    watermark_logo = fields.Image(
        string="Watermark Logo",
    )
    watermark_logo_size = fields.Integer(
        string="Logo Size (%)",
        default=DEFAULT_LOGO_SIZE,
        help="The logo is scaled, keeping its aspect ratio, to fit within "
             "this percentage of the product image's longer side.",
    )
    watermark_text = fields.Char(
        string="Watermark Text",
    )
    watermark_font = fields.Selection(
        FONT_SELECTION,
        string="Watermark Font",
        default="Arial",
    )
    watermark_size = fields.Integer(
        string="Watermark Size",
        default=6,
        help="Font size, as a percentage of the product image's diagonal.",
    )
    watermark_color = fields.Char(
        string="Watermark Color",
        default="#FFFFFF",
    )
    watermark_position = fields.Selection(
        [
            ("top_left", "Top Left"),
            ("top_right", "Top Right"),
            ("center", "Center"),
            ("bottom_left", "Bottom Left"),
            ("bottom_right", "Bottom Right"),
        ],
        string="Watermark Position",
        default="bottom_right",
    )
    watermark_opacity = fields.Float(
        string="Watermark Opacity",
        default=0.5,
    )
    watermark_preview = fields.Image(
        string="Watermark Preview",
        compute="_compute_watermark_preview",
    )

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    @api.depends("product_tmpl_id")
    def _compute_product_watermark_state(self):
        for wizard in self:
            product = wizard.product_tmpl_id
            wizard.has_watermark = product.has_watermark
            wizard.can_apply = product.is_watermark_eligible and product.watermark_globally_enabled

    @api.depends(
        "product_tmpl_id",
        "watermark_type",
        "watermark_logo",
        "watermark_logo_size",
        "watermark_text",
        "watermark_font",
        "watermark_size",
        "watermark_color",
        "watermark_position",
        "watermark_opacity",
    )
    def _compute_watermark_preview(self):
        for wizard in self:
            wizard.watermark_preview = False
            product = wizard.product_tmpl_id
            base_b64 = product and (product.original_image_1920 or product.image_1920)
            if not base_b64:
                continue
            if wizard.watermark_type == "text" and not wizard.watermark_text:
                continue
            if wizard.watermark_type == "image" and not wizard.watermark_logo:
                continue

            try:
                base_image = decode_image(base_b64)
                settings = wizard._get_wizard_settings()
                result = apply_watermark(base_image, settings)
                wizard.watermark_preview = encode_image(result)

            except (OSError, ValueError) as e:
                _logger.warning("Watermark preview failed: %s", e)

    # ------------------------------------------------------------------
    # 6. CONSTRAINS METHODS AND ONCHANGE METHODS
    # ------------------------------------------------------------------

    @api.constrains('watermark_size', 'watermark_logo_size')
    def _check_watermark_sizes(self):
        for rec in self:
            if not is_valid_size_percent(rec.watermark_size) or not is_valid_size_percent(
                rec.watermark_logo_size
            ):
                raise ValidationError(
                    self.env._("Watermark and Logo Size must be between 1 and 100%.")
                )

    @api.constrains('watermark_opacity')
    def _check_watermark_opacity(self):
        for rec in self:
            if not is_valid_opacity(rec.watermark_opacity):
                raise ValidationError(
                    self.env._("Watermark Opacity must be between 0 and 1.")
                )

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    def action_apply(self):
        """Apply the chosen watermark to every current photo of the target
        product."""
        self.ensure_one()
        self.product_tmpl_id._apply_watermark_to_all_images(self._get_wizard_settings())
        return {"type": "ir.actions.act_window_close"}

    def action_remove(self):
        """Restore the target product's original, unwatermarked photo."""
        self.ensure_one()
        self.product_tmpl_id.action_remove_watermark()
        return {"type": "ir.actions.act_window_close"}

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    def _get_wizard_settings(self):
        """Build the settings dict `watermark_utils.apply_watermark()`
        expects from this wizard's current field values."""
        self.ensure_one()
        return {
            "type": self.watermark_type,
            "logo": self.watermark_logo,
            "logo_size": self.watermark_logo_size,
            "text": self.watermark_text,
            "font": self.watermark_font,
            "size": self.watermark_size,
            "color": self.watermark_color,
            "position": self.watermark_position,
            "opacity": self.watermark_opacity,
        }
