from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductDesignPreset(models.Model):
    """Ready-made design that customers can start from. Created by the shop from
    the website editor ("Save as template")."""

    _name = "product.design.preset"
    _description = "Personalization Ready-made Design"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    product_tmpl_id = fields.Many2one("product.template", string="Product", ondelete="cascade")
    design_set_id = fields.Many2one(
        "product.design.set", string="Design Template", ondelete="cascade",
        help="Offer this design on every product using this design template.",
    )
    design_json = fields.Text(
        required=True, help="Design per area id, as saved by the editor.",
    )
    preview_image = fields.Image(max_width=1024, max_height=1024)

    @api.constrains("product_tmpl_id", "design_set_id")
    def _check_owner(self):
        for preset in self:
            if not (preset.product_tmpl_id or preset.design_set_id):
                raise ValidationError(self.env._("Set a product or a design template on '%s'.", preset.name))
