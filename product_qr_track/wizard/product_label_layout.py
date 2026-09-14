from odoo import fields, models
from odoo.exceptions import UserError


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
            return super()._prepare_report_data()

        # A QR code identifies a single variant, so a multi-variant
        # product can't be printed as one label: which variant's code
        # would it even carry? Require printing from the Product
        # Variants list instead, where each variant is picked explicitly.
        multi_variant_templates = self.product_tmpl_ids.filtered(
            lambda template: len(template.product_variant_ids) > 1
        )
        if multi_variant_templates:
            raise UserError(
                self.env._(
                    "%s has multiple variants. Print QR labels from the "
                    "Product Variants list instead, so each variant gets "
                    "its own code.",
                    ", ".join(multi_variant_templates.mapped("name")),
                )
            )

        data = {
            "quantity": self.custom_quantity,
            "layout_wizard": self.id,
        }
        products = self.product_tmpl_ids.product_variant_ids or self.product_ids

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
