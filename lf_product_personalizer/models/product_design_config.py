from odoo import api, fields, models
from odoo.exceptions import ValidationError

# Every design area is drawn on a square logical canvas of this size (in px).
# Zone coordinates are stored in this coordinate space, whatever the size the
# editor is displayed at.
EDITOR_SIZE = 800


class ProductDesignConfig(models.Model):
    _name = "product.design.config"
    _description = "Personalization Area"
    _order = "sequence, id"
    _rec_name = "design_type"

    sequence = fields.Integer(default=10)
    design_type = fields.Char(
        string="Area Name",
        required=True,
        translate=True,
        help="Name shown to the customer, e.g. Front, Back, Left Sleeve.",
    )
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        ondelete="cascade",
        index=True,
    )
    design_set_id = fields.Many2one(
        "product.design.set",
        string="Design Template",
        ondelete="cascade",
        index=True,
    )
    product_variant_id = fields.Many2one(
        "product.product",
        string="Only for Variant",
        ondelete="cascade",
        domain="[('product_tmpl_id', '=', product_tmpl_id)]",
        help="Leave empty to use this area for every variant of the product.",
    )
    design_image = fields.Image(
        string="Mockup Image",
        max_width=1920,
        max_height=1920,
        help="Picture of this side of the product. The variant image is used when empty.",
    )
    is_restricted_area = fields.Boolean(
        string="Printable Zone",
        help="Keep the customer's design inside a rectangle of the mockup.",
    )
    bound_x = fields.Float(string="Zone X")
    bound_y = fields.Float(string="Zone Y")
    bound_width = fields.Float(string="Zone Width")
    bound_height = fields.Float(string="Zone Height")
    is_required = fields.Boolean(
        string="Required",
        help="The customer must add something on this area before adding to cart.",
    )
    price_extra = fields.Float(
        string="Extra Price",
        digits="Product Price",
        help="Added to the unit price when the customer customizes this area.",
    )

    _sql_constraints = [
        (
            "check_bounds_positive",
            "CHECK(bound_x >= 0 AND bound_y >= 0 AND bound_width >= 0 AND bound_height >= 0)",
            "Zone coordinates cannot be negative.",
        ),
    ]

    @api.constrains("product_tmpl_id", "design_set_id")
    def _check_owner(self):
        for area in self:
            if bool(area.product_tmpl_id) == bool(area.design_set_id):
                raise ValidationError(
                    self.env._("Area '%s' must belong to either a product or a design template.",
                      area.design_type)
                )

    @api.constrains("product_variant_id", "product_tmpl_id")
    def _check_variant(self):
        for area in self:
            variant = area.product_variant_id
            if variant and variant.product_tmpl_id != area.product_tmpl_id:
                raise ValidationError(
                    self.env._("The variant of area '%s' must belong to the same product.",
                      area.design_type)
                )

    @api.constrains("is_restricted_area", "bound_x", "bound_y", "bound_width", "bound_height")
    def _check_zone(self):
        for area in self.filtered("is_restricted_area"):
            if area.bound_width <= 0 or area.bound_height <= 0:
                raise ValidationError(
                    self.env._("The printable zone of area '%s' needs a width and a height.",
                      area.design_type)
                )
            if (area.bound_x + area.bound_width > EDITOR_SIZE
                    or area.bound_y + area.bound_height > EDITOR_SIZE):
                raise ValidationError(
                    self.env._("The printable zone of area '%(area)s' must fit in the %(size)sx%(size)s editor.",
                      area=area.design_type, size=EDITOR_SIZE)
                )

    def _lf_get_image_url(self, variant):
        """Mockup URL for this area, falling back on the variant image."""
        self.ensure_one()
        if self.design_image:
            return f"/shop/personalize/area/{self.id}/image?unique={self._lf_unique()}"
        if variant and variant.image_1920:
            return f"/web/image/product.product/{variant.id}/image_1920"
        return None

    def _lf_unique(self):
        return fields.Datetime.to_string(self.write_date or fields.Datetime.now()).replace(" ", "")

    def _lf_to_frontend(self, variant):
        self.ensure_one()
        return {
            "id": self.id,
            "key": str(self.id),
            "name": self.design_type,
            "image_url": self._lf_get_image_url(variant),
            "is_restricted_area": self.is_restricted_area,
            "bound_x": self.bound_x,
            "bound_y": self.bound_y,
            "bound_width": self.bound_width,
            "bound_height": self.bound_height,
            "is_required": self.is_required,
            "price_extra": self.price_extra,
        }
