import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
DEFAULT_PALETTE = [
    "#000000", "#FFFFFF", "#E53935", "#43A047", "#1E88E5", "#FDD835",
    "#8E24AA", "#00ACC1", "#FB8C00", "#6D4C41", "#757575", "#F06292",
]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_product_personalization = fields.Boolean(
        string="Personalizable",
        help="Let customers design this product on the website.",
    )
    design_set_id = fields.Many2one(
        "product.design.set",
        string="Design Template",
        help="Reuse the areas of a design template. Areas defined on the product take priority.",
    )
    design_set_area_ids = fields.One2many(
        related="design_set_id.area_ids", string="Template Areas",
    )
    design_config_ids = fields.One2many(
        "product.design.config",
        "product_tmpl_id",
        string="Areas",
        copy=True,
    )
    personalization_required = fields.Boolean(
        help="Hide the standard 'Add to cart' button: this product can only be "
        "bought personalized.",
    )
    personalization_fee = fields.Float(
        digits="Product Price",
        help="Added to the unit price of every personalized item, on top of "
        "the extra price of each customized area.",
    )
    personalization_allow_text = fields.Boolean(string="Text", default=True)
    personalization_allow_image = fields.Boolean(string="Image Upload", default=True)
    personalization_allow_clipart = fields.Boolean(string="Clipart", default=True)
    personalization_allow_shape = fields.Boolean(string="Shapes", default=True)
    personalization_max_text_length = fields.Integer(
        string="Max Text Length",
        help="Maximum number of characters per text, e.g. what fits on an engraving "
        "plate. 0 means no limit.",
    )
    personalization_min_image_px = fields.Integer(
        string="Min. Image Size",
        default=600,
        help="Warn customers when an uploaded image is too small to print sharply "
        "(shortest side, in pixels). 0 turns the warning off.",
    )
    personalization_palette = fields.Char(
        string="Colour Palette",
        help="Colours customers can choose from, e.g. your thread or vinyl colours. "
        "Leave empty to offer the default colours plus a free colour picker.",
    )
    personalization_font_ids = fields.Many2many(
        "product.design.font",
        string="Fonts",
        help="Fonts offered for this product. Leave empty to offer every active font.",
    )
    personalization_requires_approval = fields.Boolean(
        string="Artwork Approval",
        help="Each design must be approved by your team before production.",
    )

    _check_max_text_length = models.Constraint(
        "CHECK(personalization_max_text_length IS NULL OR personalization_max_text_length >= 0)",
        "The maximum text length cannot be negative.",
    )

    @api.constrains("personalization_palette")
    def _check_palette(self):
        for template in self:
            for color in template._lf_split_palette():
                if not HEX_COLOR.match(color):
                    raise ValidationError(
                        self.env._("'%s' is not a valid colour. Use the #RRGGBB format.", color),
                    )

    def _lf_split_palette(self):
        self.ensure_one()
        return [c.strip() for c in (self.personalization_palette or "").split(",") if c.strip()]

    def _lf_get_areas(self, variant=None):
        """Areas available for ``variant``: product areas, else template areas."""
        self.ensure_one()
        areas = self.design_config_ids or self.design_set_id.area_ids
        return areas.filtered(
            lambda area: not area.product_variant_id or area.product_variant_id == variant,
        )

    def _lf_is_personalizable(self):
        self.ensure_one()
        return bool(
            self.is_product_personalization
            and (self.design_config_ids or self.design_set_id.area_ids),
        )

    def _lf_get_fonts(self):
        self.ensure_one()
        return self.personalization_font_ids.filtered("active") or self.env[
            "product.design.font"
        ].search([])

    def _lf_get_editor_settings(self):
        self.ensure_one()
        return {
            "required": self.personalization_required,
            "allow_text": self.personalization_allow_text,
            "allow_image": self.personalization_allow_image,
            "allow_clipart": self.personalization_allow_clipart,
            "allow_shape": self.personalization_allow_shape,
            "max_text_length": self.personalization_max_text_length,
            "min_image_px": self.personalization_min_image_px,
            "palette": self._lf_split_palette() or DEFAULT_PALETTE,
            "palette_is_custom": bool(self._lf_split_palette()),
            "fonts": self._lf_get_fonts()._lf_to_frontend(),
            "print_scale": self.env["res.config.settings"]._lf_print_scale(),
            "requires_approval": self.personalization_requires_approval,
        }

    def _lf_get_presets(self):
        self.ensure_one()
        domain = [("product_tmpl_id", "=", self.id)]
        if self.design_set_id and not self.design_config_ids:
            domain = ["|", ("design_set_id", "=", self.design_set_id.id)] + domain
        return self.env["product.design.preset"].search(domain)
