import io
from PIL import Image
import logging

from odoo import models, fields, api
from odoo.tools import file_open
from odoo.exceptions import ValidationError

from .watermark_utils import apply_watermark, encode_image, is_valid_opacity, resolve_watermark_type

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):

    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "res.config.settings"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

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
        string="Watermark Logo",
        max_width=1024,
        max_height=1024,
    )
    watermark_text = fields.Char(
        string="Watermark Text",
        config_parameter="lf_product_watermark_overlay.watermark_text",
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
        config_parameter="lf_product_watermark_overlay.watermark_font",
    )
    watermark_size = fields.Integer(
        string="Watermark Size",
        default=6,
        config_parameter="lf_product_watermark_overlay.watermark_size",
    )
    watermark_color = fields.Char(
        string="Watermark Color",
        default="#000000",
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
        "watermark_text",
        "watermark_font",
        "watermark_size",
        "watermark_color",
        "watermark_position",
        "watermark_opacity",
    )
    def _compute_watermark_preview(self):
        self.watermark_preview = False

        if not self.watermark_enabled or (
            self.watermark_type == "text" and not self.watermark_text
        ) or (self.watermark_type == "image" and not self.watermark_logo):
            return

        try:
            with file_open(
                "lf_product_watermark_overlay/static/img/watermark_preview_demo.jpg",
                "rb",
            ) as f:
                base_image = Image.open(io.BytesIO(f.read())).convert("RGBA")

        except Exception:
            return

        settings = {
            "type": resolve_watermark_type(self.watermark_enabled, self.watermark_type),
            "logo": self.watermark_logo,
            "text": self.watermark_text or "Test",
            "font": self.watermark_font or "Arial",
            "size": self.watermark_size or 6,
            "color": self.watermark_color or "#000000",
            "position": self.watermark_position or "bottom_right",
            # No `or 0.5` fallback here: a Float field always holds a
            # real number (0.0 included), and 0 is a valid — if
            # pointless — opacity that must not be silently overridden.
            "opacity": self.watermark_opacity,
        }

        try:
            result = apply_watermark(
                base_image=base_image, settings=settings
            )
            self.watermark_preview = encode_image(result)

        except Exception as e:
            _logger.warning("Watermark generation failed: %s", str(e))

    # ------------------------------------------------------------------
    # 5. SELECTION METHODS
    # ------------------------------------------------------------------

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
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    @api.model
    def get_values(self):
        """Retrieve configuration parameter values."""
        res = super(ResConfigSettings, self).get_values()
        # sudo: reading global config parameters must work regardless of
        # the calling user's own access rights.
        params = self.env["ir.config_parameter"].sudo()

        # Get logo from attachment
        company = self.env.company
        # sudo: a user opening Settings may not have direct read access
        # to another record's (res.company) attachment.
        attachment = self.env["ir.attachment"].sudo().search(
            [
                ("res_model", "=", "res.company"),
                ("res_field", "=", "watermark_logo"),
                ("res_id", "=", company.id),
            ],
            limit=1,
        )

        res.update(
            {
                "watermark_enabled": params.get_param(
                    "lf_product_watermark_overlay.watermark_enabled", "False"
                ) == "True",
                "watermark_type": params.get_param(
                    "lf_product_watermark_overlay.watermark_type", "image"
                ),
                "watermark_logo": attachment.datas if attachment else False,
                "watermark_text": params.get_param(
                    "lf_product_watermark_overlay.watermark_text", ""
                ),
                "watermark_font": params.get_param(
                    "lf_product_watermark_overlay.watermark_font", "Arial"
                ),
                "watermark_size": int(
                    params.get_param("lf_product_watermark_overlay.watermark_size", 6)
                ),
                "watermark_color": params.get_param(
                    "lf_product_watermark_overlay.watermark_color", "#FFFFFF"
                ),
                "watermark_position": params.get_param(
                    "lf_product_watermark_overlay.watermark_position", "bottom_right"
                ),
                "watermark_opacity": float(
                    params.get_param("lf_product_watermark_overlay.watermark_opacity", 0.5)
                ),
            }
        )
        return res

    def set_values(self):
        """Save configuration parameter values."""
        super(ResConfigSettings, self).set_values()
        # sudo: writing global config parameters must work regardless of
        # the calling user's own access rights.
        params = self.env["ir.config_parameter"].sudo()

        params.set_param(
            "lf_product_watermark_overlay.watermark_enabled", str(self.watermark_enabled)
        )
        params.set_param("lf_product_watermark_overlay.watermark_type", self.watermark_type)
        params.set_param("lf_product_watermark_overlay.watermark_text", self.watermark_text)
        params.set_param("lf_product_watermark_overlay.watermark_font", self.watermark_font)
        params.set_param("lf_product_watermark_overlay.watermark_size", self.watermark_size)
        params.set_param("lf_product_watermark_overlay.watermark_color", self.watermark_color)
        params.set_param(
            "lf_product_watermark_overlay.watermark_position", self.watermark_position
        )
        params.set_param("lf_product_watermark_overlay.watermark_opacity", self.watermark_opacity)

        # Save Image logo as attachment
        company = self.env.company
        # sudo: saving the company logo attachment must work regardless
        # of the calling user's own access rights.
        attachment = self.env["ir.attachment"].sudo().search(
            [
                ("res_model", "=", "res.company"),
                ("res_field", "=", "watermark_logo"),
                ("res_id", "=", company.id),
            ],
            limit=1,
        )

        if self.watermark_logo:
            if attachment:
                attachment.write({"datas": self.watermark_logo})
            else:
                self.env["ir.attachment"].sudo().create(
                    {
                        "name": "watermark_logo",
                        "type": "binary",
                        "datas": self.watermark_logo,
                        "res_model": "res.company",
                        "res_field": "watermark_logo",
                        "res_id": company.id,
                        "mimetype": "image/png",
                    }
                )
        elif attachment:
            attachment.unlink()

    def regenerate_all_images(self):
        """Queue watermark regeneration for every product/variant with a
        photo.

        This used to loop over every matching product and regenerate its
        watermark synchronously, inline on this button click — for a
        large catalog that blocks the UI and risks an HTTP timeout, with
        the whole batch rolled back if it doesn't finish in time. It now
        triggers the `_cron_regenerate_watermarked_images` scheduled
        action instead, which processes products in committed batches in
        the background.
        """
        self.watermark_preview = False
        self._compute_watermark_preview()

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

        A separate, explicit action from disabling watermarking itself
        (which only reverts already-watermarked images) — this button
        lets an admin deliberately reset which products are eligible,
        e.g. before re-launching the feature with a hand-picked subset,
        without it happening automatically just from toggling the
        company-wide setting off.
        """
        self.env["product.template"]._uncheck_watermark_eligibility_for_all_products()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Eligibility cleared"),
                "message": self.env._(
                    "Every product has been marked not eligible for watermarking."
                ),
                "sticky": False,
                "type": "success",
            },
        }
