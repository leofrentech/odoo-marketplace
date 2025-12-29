import logging

from odoo import fields, models, api
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
    watermark_type_custom = fields.Selection(
        [("image", "Image"), ("text", "Text"), ("none", "None")],
        string="Custom Watermark Type",
        default="none",
    )
    watermark_logo_custom = fields.Image(
        string="Watermark Logo",
    )
    watermark_text_custom = fields.Char(
        string="Watermark Text",
        translate=True,
    )
    watermark_font_custom = fields.Char(
        string="Watermark Font",
    )
    watermark_size_custom = fields.Integer(
        string="Watermark Size",
    )
    watermark_color_custom = fields.Char(
        string="Watermark Color",
    )
    watermark_position_custom = fields.Selection(
        [
            ("top_left", "Top Left"),
            ("top_right", "Top Right"),
            ("center", "Center"),
            ("bottom_left", "Bottom Left"),
            ("bottom_right", "Bottom Right"),
        ],
        string="Watermark Position",
    )
    watermark_opacity_custom = fields.Float(
        string="Watermark Opacity",
        default=50.0
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
            "watermark_type_custom",
            "watermark_logo_custom",
            "watermark_text_custom",
            "watermark_font_custom",
            "watermark_size_custom",
            "watermark_color_custom",
            "watermark_position_custom",
            "watermark_opacity_custom",
        }

        if watermark_fields & vals.keys():
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
                "type": self.watermark_type_custom,
                "logo": self.watermark_logo_custom,
                "text": self.watermark_text_custom,
                "font": self.watermark_font_custom,
                "size": self.watermark_size_custom,
                "color": self.watermark_color_custom,
                "position": self.watermark_position_custom,
                "opacity": self.watermark_opacity_custom,
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