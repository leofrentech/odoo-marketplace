import logging

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from .watermark_utils import decode_image, encode_image, apply_watermark


_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "product.template"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    is_watermark_override = fields.Boolean(
        string="Is Product Watermark Override",
        help="Enables watermark override features for this product.",
    )
    watermark_type = fields.Selection(
        [("image", "Image"), ("text", "Text")],
        string="Custom Watermark Type",
    )
    watermark_logo = fields.Image(
        string="Watermark Logo",
    )
    watermark_text = fields.Char(
        string="Watermark Text",
        translate=True,
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
        default=0.5
    )
    
    watermarked_image_1920 = fields.Image(
        string="Watermarked Image", max_width=1920, max_height=1920, readonly=True
    )
    watermarked_image_1024 = fields.Image(
        string="Watermarked Image 1024",
        max_width=1024,
        max_height=1024,
        compute="_compute_watermarked_images",
        store=True,
    )
    watermarked_image_512 = fields.Image(
        string="Watermarked Image 512",
        max_width=512,
        max_height=512,
        compute="_compute_watermarked_images",
        store=True,
    )
    watermarked_image_256 = fields.Image(
        string="Watermarked Image 256",
        max_width=256,
        max_height=256,
        compute="_compute_watermarked_images",
        store=True,
    )
    watermarked_image_128 = fields.Image(
        string="Watermarked Image 128",
        max_width=128,
        max_height=128,
        compute="_compute_watermarked_images",
        store=True,
    )

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    @api.depends("watermarked_image_1920")
    def _compute_watermarked_images(self):
        """Compute smaller watermarked image variants."""
        for product in self:
            product.watermarked_image_1024 = product.watermarked_image_1920
            product.watermarked_image_512 = product.watermarked_image_1920
            product.watermarked_image_256 = product.watermarked_image_1920
            product.watermarked_image_128 = product.watermarked_image_1920

    # ------------------------------------------------------------------
    # 5. SELECTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 6. CONSTRAINTS METHODS AND ONCHANGE METHODS
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

    @api.model_create_multi
    def create(self, vals_list):
        """Generate watermarks on product creation."""
        records = super(ProductTemplate, self).create(vals_list)
        records.filtered("image_1920")._generate_watermarked_images()
        return records
    
    def write(self, vals):
        """Regenerate watermarks when image or settings change."""
        res = super(ProductTemplate, self).write(vals)

        watermark_fields = {
            "image_1920",
            "is_watermark_override",
            "watermark_type",
            "watermark_logo",
            "watermark_text",
            "watermark_font",
            "watermark_size",
            "watermark_color",
            "watermark_position",
            "watermark_opacity",
        }

        if watermark_fields & vals.keys(): # Used set intersection 
            self._generate_watermarked_images()

        return res

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    def _get_watermark_settings(self):
        """Get watermark settings."""
        self.ensure_one()
        params = self.env["ir.config_parameter"].sudo()

        if self.is_watermark_override:
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

        company = self.env.company
        logo_attachment = self.env["ir.attachment"].sudo().search(
            [
                ("res_model", "=", "res.company"),
                ("res_field", "=", "watermark_logo"),
                ("res_id", "=", company.id),
            ],
            limit=1,
        )

        return {
            "type": params.get_param("lf_product_watermark_overlay.watermark_type", "none"),
            "logo": logo_attachment.datas if logo_attachment else False,
            "text": params.get_param("lf_product_watermark_overlay.watermark_text", company.name),
            "font": params.get_param("lf_product_watermark_overlay.watermark_font", "Arial"),
            "size": int(params.get_param("lf_product_watermark_overlay.watermark_size", 24)),
            "color": params.get_param("lf_product_watermark_overlay.watermark_color", "#FFFFFF"),
            "position": params.get_param(
                "lf_product_watermark_overlay.watermark_position", "bottom_right"
            ),
            "opacity": float(
                params.get_param("lf_product_watermark_overlay.watermark_opacity", 50.0)
            ),
        }
    
    def _generate_watermarked_images(self):
        for product in self:
            settings = product._get_watermark_settings()

            if not product.image_1920 or settings["type"] == "none":
                product.watermarked_image_1920 = False
                continue

            try:
                base_image = decode_image(product.image_1920)
                result = apply_watermark(base_image, settings)
                product.watermarked_image_1920 = encode_image(result)

            except Exception as e:
                _logger.warning(
                    "Watermark failed for product %s: %s",
                    product.id,
                    str(e),
                )