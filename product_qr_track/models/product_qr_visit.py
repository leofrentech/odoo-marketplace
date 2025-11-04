from odoo import fields, models


class ProductQRVisit(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _name = "product.qr.visit"
    _description = "Product QR Visits"
    _rec_name = "product_id"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    os = fields.Char("OS")
    browser = fields.Char("Browser")
    geoip = fields.Char("GeoIP")
    city = fields.Char("City")

    product_id = fields.Many2one(
        "product.product", "Product", ondelete="cascade", required=True
    )
    country_id = fields.Many2one("res.country", "Country", ondelete="restrict")

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 5. SELECTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 6. CONSTRAINS METHODS AND ONCHANGE METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    def action_open_product(self):
        self.ensure_one()
        return {
            "name": "Product",
            "type": "ir.actions.act_window",
            "res_model": "product.product",
            "view_mode": "form",
            "res_id": self.product_id.id,
        }

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------
