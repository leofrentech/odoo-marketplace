from odoo import fields, models


class ProductDesignSaved(models.Model):
    """A design saved by a customer in their account, reopened or shared later."""

    _name = "product.design.saved"
    _inherit = ["portal.mixin"]
    _description = "Customer Saved Design"
    _order = "write_date desc, id desc"

    name = fields.Char(required=True)
    partner_id = fields.Many2one(
        "res.partner", string="Customer", required=True, index=True, ondelete="cascade",
    )
    product_tmpl_id = fields.Many2one(
        "product.template", string="Product", required=True, ondelete="cascade",
    )
    product_id = fields.Many2one("product.product", string="Variant", ondelete="set null")
    website_id = fields.Many2one("website", ondelete="set null")
    design_json = fields.Text(required=True)
    preview_image = fields.Image(max_width=1024, max_height=1024)

    def _compute_access_url(self):
        super()._compute_access_url()
        for design in self:
            design.access_url = f"/shop/personalize/design/{design.id}"
