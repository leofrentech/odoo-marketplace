from odoo import api, fields, models


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

    qr_url = fields.Char("QR URL", compute="_compute_qr_url")
    qr_visit_count = fields.Integer(
        "#QR Visits", compute="_compute_qr_visit_count"
    )

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    @api.depends("product_variant_id")
    def _compute_qr_url(self):
        for template in self:
            template.qr_url = template.product_variant_id.qr_url

    @api.depends("product_variant_ids", "product_variant_ids.qr_visit_ids")
    def _compute_qr_visit_count(self):
        for template in self:
            template.qr_visit_count = sum(
                template.product_variant_ids.mapped("qr_visit_count")
            )

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
            "domain": [("product_id", "in", self.product_variant_ids.ids)],
            "context": {"search_default_groupby_os": 1},
        }

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------
