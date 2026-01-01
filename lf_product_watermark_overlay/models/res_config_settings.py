import io
from PIL import Image
import logging

from odoo import models, fields, api
from odoo.tools import file_open
from odoo.exceptions import ValidationError

from .watermark_utils import apply_watermark, encode_image

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

    watermark_type = fields.Selection(
        [("image", "Image"), ("text", "Text"), ("none", "None")],
        string="Watermark Type",
        default="none",
        config_parameter="lf_product_watermark_overlay.watermark_type",
    )
    watermark_logo = fields.Image(
        string="Watermark Logo",
        max_width=1024,
        max_height=1024,
    )
    watermark_text = fields.Char(
        string="Watermark Text",
        translate=True,
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

        if self.watermark_type == "none" or (
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
            "type": self.watermark_type,
            "logo": self.watermark_logo,
            "text": self.watermark_text or "Test",
            "font": self.watermark_font or "Arial",
            "size": self.watermark_size or 30,
            "color": self.watermark_color or "#000000",
            "position": self.watermark_position or "bottom_right",
            "opacity": self.watermark_opacity or 50.0,
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
            if rec.watermark_opacity < 0 or rec.watermark_opacity > 1:
                raise ValidationError(
                    "Watermark Opacity must be between 0 and 1."
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
        params = self.env["ir.config_parameter"].sudo()

        # Get logo from attachment
        company = self.env.company
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
                "watermark_type": params.get_param(
                    "lf_product_watermark_overlay.watermark_type", "none"
                ),
                "watermark_logo": attachment.datas if attachment else False,
                "watermark_text": params.get_param(
                    "lf_product_watermark_overlay.watermark_text", ""
                ),
                "watermark_font": params.get_param(
                    "lf_product_watermark_overlay.watermark_font", "Arial"
                ),
                "watermark_size": int(
                    params.get_param("lf_product_watermark_overlay.watermark_size", 30)
                ),
                "watermark_color": params.get_param(
                    "lf_product_watermark_overlay.watermark_color", "#FFFFFF"
                ),
                "watermark_position": params.get_param(
                    "lf_product_watermark_overlay.watermark_position", "bottom_right"
                ),
                "watermark_opacity": float(
                    params.get_param("lf_product_watermark_overlay.watermark_opacity", 50.0)
                ),
            }
        )
        return res

    def set_values(self):
        """Save configuration parameter values."""
        super(ResConfigSettings, self).set_values()
        params = self.env["ir.config_parameter"].sudo()

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
        """Trigger watermark regeneration for all products."""
        self.watermark_preview = False

        if self.watermark_type == "none":
            return

        self._compute_watermark_preview()

        try:
            product_tmpl_ids = self.env["product.template"].search([("is_watermark_override", "=", False)])
            for product_tmpl in product_tmpl_ids:
                product_tmpl._generate_watermarked_images()
        
        except Exception as e:
            _logger.warning("Watermark generation failed: %s", str(e))
