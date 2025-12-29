from odoo import fields, models


class ProductLabelLayout(models.TransientModel):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "product.label.layout"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    print_format = fields.Selection(
        selection_add=[("qr", "QR")], ondelete={"qr": "cascade"}
    )

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

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    def _prepare_report_data(self):
        """
        Prepare report action and data for printing product QR labels.
        """
        # Use default behavior if not QR format
        if self.print_format != "qr":
            return super(ProductLabelLayout, self)._prepare_report_data()

        data = {
            "quantity": self.custom_quantity,
            "base_url": self.get_base_url(),
            "layout_wizard": self.id,
        }
        # Determine active model and product records
        products = self.product_tmpl_ids or self.product_ids

        data.update(
            {
                "active_model": products._name,
                "products": [
                    {
                        "name": product.display_name,
                        "qr_url": product.qr_url,
                    }
                    for product in products
                ],
            }
        )

        return "product_qr_track.action_report_product_qr", data
