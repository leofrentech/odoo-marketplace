import logging

from odoo import fields, models, api
from odoo.exceptions import ValidationError

from ..models.watermark_utils import apply_watermark, decode_image, encode_image, is_valid_opacity


_logger = logging.getLogger(__name__)


class ProductWatermarkWizard(models.TransientModel):
    _name = "product.watermark.wizard"
    _description = "Apply a one-off custom watermark to a product's current photo"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        """Pre-fill from the company-wide resolved defaults — there is
        no per-product persisted customization to remember, by design
        (see the module's watermarking architecture notes)."""
        res = super().default_get(fields_list)
        product = self.env["product.template"].browse(self.env.context.get("active_id"))
        if not product:
            return res

        settings = product._get_watermark_settings()
        res.update({
            "product_tmpl_id": product.id,
            "watermark_type": settings["type"] if settings["type"] != "none" else "image",
            "watermark_logo": settings["logo"],
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
    watermark_type = fields.Selection(
        [("image", "Image"), ("text", "Text")],
        string="Watermark Type",
        default="image",
        required=True,
    )
    watermark_logo = fields.Image(
        string="Watermark Logo",
    )
    watermark_text = fields.Char(
        string="Watermark Text",
    )
    watermark_font = fields.Selection(
        [
            ("Arial", "Arial"),
            ("Times New Roman", "Times New Roman"),
            ("Courier New", "Courier New"),
            ("Verdana", "Verdana"),
            ("Georgia", "Georgia"),
            ("Comic Sans MS", "Comic Sans MS"),
            ("Impact", "Impact"),
        ],
        string="Watermark Font",
        default="Arial",
    )
    watermark_size = fields.Integer(
        string="Watermark Size",
        default=6,
    )
    watermark_color = fields.Char(
        string="Watermark Color",
        default="#000000",
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

    @api.depends(
        "product_tmpl_id",
        "watermark_type",
        "watermark_logo",
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

            except Exception as e:
                _logger.warning("Watermark preview failed: %s", str(e))

    # ------------------------------------------------------------------
    # 6. CONSTRAINS METHODS AND ONCHANGE METHODS
    # ------------------------------------------------------------------

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
        """Apply the chosen watermark to the target product's current
        photo."""
        self.ensure_one()
        self.product_tmpl_id.action_apply_watermark(self._get_wizard_settings())
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
            "text": self.watermark_text,
            "font": self.watermark_font,
            "size": self.watermark_size,
            "color": self.watermark_color,
            "position": self.watermark_position,
            "opacity": self.watermark_opacity,
        }
