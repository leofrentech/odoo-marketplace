from odoo import api, fields, models


class ProductDesignSet(models.Model):
    """A reusable list of areas (e.g. "T-shirt: Front, Back, Sleeve") that many
    products can share, so the zones are configured only once."""

    _name = "product.design.set"
    _description = "Personalization Design Template"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    area_ids = fields.One2many(
        "product.design.config", "design_set_id", string="Areas", copy=True,
    )
    product_tmpl_ids = fields.One2many(
        "product.template", "design_set_id", string="Products",
    )
    product_count = fields.Integer(compute="_compute_product_count")

    @api.depends("product_tmpl_ids")
    def _compute_product_count(self):
        groups = self.env["product.template"]._read_group(
            [("design_set_id", "in", self.ids)], ["design_set_id"], ["__count"],
        )
        counts = {design_set.id: count for design_set, count in groups}
        for design_set in self:
            design_set.product_count = counts.get(design_set.id, 0)

    def action_view_products(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "website_sale.product_template_action_website",
        )
        action["domain"] = [("design_set_id", "=", self.id)]
        action["context"] = {
            "default_design_set_id": self.id,
            "default_is_product_personalization": True,
        }
        return action
