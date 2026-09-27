import io
import logging

from PIL import Image

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import file_open

from .watermark_utils import (
    DEFAULT_LOGO_SIZE,
    FONT_SELECTION,
    apply_watermark,
    encode_image,
    is_valid_opacity,
    is_valid_size_percent,
    resolve_watermark_type,
)

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):

    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "res.config.settings"

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    # Every field below except the logo is a global `config_parameter`,
    # loaded and saved by res.config.settings itself. The logo lives on
    # the company, since each company typically has its own.
    watermark_enabled = fields.Boolean(
        string="Enable Watermark",
        config_parameter="lf_product_watermark_overlay.watermark_enabled",
    )
    watermark_type = fields.Selection(
        [("image", "Image"), ("text", "Text")],
        string="Watermark Type",
        default="image",
        config_parameter="lf_product_watermark_overlay.watermark_type",
    )
    watermark_logo = fields.Image(
        related="company_id.watermark_logo",
        readonly=False,
    )
    watermark_logo_size = fields.Integer(
        string="Logo Size (%)",
        default=DEFAULT_LOGO_SIZE,
        config_parameter="lf_product_watermark_overlay.watermark_logo_size",
        help="The logo is scaled, keeping its aspect ratio, to fit within "
             "this percentage of the product image's width and height.",
    )
    watermark_text = fields.Char(
        string="Watermark Text",
        config_parameter="lf_product_watermark_overlay.watermark_text",
    )
    watermark_font = fields.Selection(
        FONT_SELECTION,
        string="Watermark Font",
        default="Arial",
        config_parameter="lf_product_watermark_overlay.watermark_font",
    )
    watermark_size = fields.Integer(
        string="Watermark Size",
        default=6,
        config_parameter="lf_product_watermark_overlay.watermark_size",
        help="Font size, as a percentage of the product image's diagonal.",
    )
    watermark_color = fields.Char(
        string="Watermark Color",
        default="#FFFFFF",
        config_parameter="lf_product_watermark_overlay.watermark_color",
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
        config_parameter="lf_product_watermark_overlay.watermark_position",
    )
    watermark_opacity = fields.Float(
        string="Watermark Opacity",
        default=0.5,
        config_parameter="lf_product_watermark_overlay.watermark_opacity",
    )

    watermark_preview = fields.Image(
        string="Watermark Preview",
        compute="_compute_watermark_preview",
        max_width=1024,
        max_height=1024,
    )

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    @api.depends(
        "watermark_enabled",
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
        for settings_record in self:
            settings_record.watermark_preview = settings_record._render_watermark_preview()

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

    def regenerate_all_images(self):
        """Queue watermark backfill for every eligible product/variant
        with a photo and no watermark yet.

        Triggers the `_cron_regenerate_watermarked_images` scheduled
        action rather than processing inline on this button click, so a
        large catalog never blocks the UI or risks an HTTP timeout.
        """
        self.env.ref(
            "lf_product_watermark_overlay.ir_cron_regenerate_watermarked_images"
        )._trigger()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Watermark regeneration queued"),
                "message": self.env._(
                    "Product images will be updated in the background shortly."
                ),
                "sticky": False,
                "type": "success",
            },
        }

    def action_uncheck_all_products_watermark_eligibility(self):
        """Mass-uncheck `is_watermark_eligible` on every product.

        A separate, explicit action from disabling watermarking itself —
        this button lets an admin deliberately reset which products are
        eligible, e.g. before re-launching the feature with a hand-picked
        subset, without it happening automatically just from toggling the
        company-wide setting off.
        """
        self.env["product.template"]._uncheck_watermark_eligibility_for_all_products()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Watermarks removed"),
                "message": self.env._(
                    "Every product's original photo has been restored, and "
                    "every product has been marked not eligible for watermarking."
                ),
                "sticky": False,
                "type": "success",
            },
        }

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    def _render_watermark_preview(self):
        """The current settings applied to a bundled demo photo, or False
        when there's nothing to show yet."""
        self.ensure_one()
        if not self.watermark_enabled or (
            self.watermark_type == "text" and not self.watermark_text
        ) or (self.watermark_type == "image" and not self.watermark_logo):
            return False

        with file_open(
            "lf_product_watermark_overlay/static/img/watermark_preview_demo.jpg", "rb"
        ) as f:
            base_image = Image.open(io.BytesIO(f.read())).convert("RGBA")

        settings = {
            "type": resolve_watermark_type(self.watermark_enabled, self.watermark_type),
            "logo": self.watermark_logo,
            "logo_size": self.watermark_logo_size or DEFAULT_LOGO_SIZE,
            "text": self.watermark_text,
            "font": self.watermark_font or "Arial",
            "size": self.watermark_size or 6,
            "color": self.watermark_color or "#FFFFFF",
            "position": self.watermark_position or "bottom_right",
            # No `or 0.5` fallback here: a Float field always holds a
            # real number (0.0 included), and 0 is a valid — if
            # pointless — opacity that must not be silently overridden.
            "opacity": self.watermark_opacity,
        }
        try:
            return encode_image(apply_watermark(base_image, settings))
        except (OSError, ValueError) as e:
            _logger.warning("Watermark preview failed: %s", e)
            return False
