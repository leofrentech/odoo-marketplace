from odoo import fields, models


class ProductDesignClipartCategory(models.Model):
    _name = "product.design.clipart.category"
    _description = "Clipart Category"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    clipart_ids = fields.One2many("product.design.clipart", "category_id")


class ProductDesignClipart(models.Model):
    _name = "product.design.clipart"
    _description = "Personalization Clipart"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    image = fields.Image(required=True, max_width=1024, max_height=1024)
    category_id = fields.Many2one("product.design.clipart.category", ondelete="set null")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    def _lf_to_frontend(self):
        return [
            {
                "id": clipart.id,
                "name": clipart.name,
                "category": clipart.category_id.name or "",
                "url": f"/web/image/product.design.clipart/{clipart.id}/image",
            }
            for clipart in self
        ]
