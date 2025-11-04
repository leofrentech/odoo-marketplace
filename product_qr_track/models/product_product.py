from odoo import api, fields, models


class ProductProduct(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "product.product"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    qr_url = fields.Char("QR URL", compute="_compute_qr_url")
    qr_visit_ids = fields.One2many(
        "product.qr.visit", "product_id", "QR Visits"
    )
    qr_visit_count = fields.Integer(
        "#QR Visits", compute="_compute_qr_visit_count"
    )

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    def _compute_qr_url(self):
        for product in self:
            product.qr_url = f"{product.get_base_url()}/qr/{product.id}"

    @api.depends("qr_visit_ids")
    def _compute_qr_visit_count(self):
        for product in self:
            product.qr_visit_count = len(product.qr_visit_ids)

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

    def action_open_qr_visits(self):
        self.ensure_one()
        return {
            "name": "Product QR Visits",
            "type": "ir.actions.act_window",
            "res_model": "product.qr.visit",
            "view_mode": "graph,list,form",
            "domain": [("product_id", "=", self.id)],
            "context": {"search_default_groupby_os": 1},
        }

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------
