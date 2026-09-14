from odoo import fields, models
from odoo.exceptions import UserError

MAX_FILENAME_PRODUCTS_LENGTH = 80


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

    def process(self):
        """
        Download QR labels as a named attachment instead of through the
        generic report-download route, which can't include the product
        name(s) in the filename here: the client only appends docids to
        the report URL when the action carries no `data`, but reports
        built from a wizard (this one included) always populate `data`
        with the print options, so that branch never triggers.
        """
        self.ensure_one()
        if self.print_format != "qr":
            return super().process()

        xml_id, data = self._prepare_report_data()
        pdf_content, __ = self.env["ir.actions.report"]._render_qweb_pdf(
            xml_id, data=data
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": self._get_qr_report_filename(data["products"]),
                "type": "binary",
                "raw": pdf_content,
                "mimetype": "application/pdf",
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
            "close_on_report_download": True,
        }

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    def _get_qr_report_filename(self, products):
        """Build a PDF filename that names the product(s) it covers.

        :param products: list of dicts as built by _prepare_report_data,
            each with at least a "name" key.
        """
        names = [product["name"] for product in products]
        if len(names) == 1:
            return self.env._("QR Label - %s.pdf", names[0])

        joined = ", ".join(names)
        if len(joined) > MAX_FILENAME_PRODUCTS_LENGTH:
            joined = self.env._(
                "%(first)s and %(count)s more",
                first=names[0],
                count=len(names) - 1,
            )
        return self.env._("QR Labels - %s.pdf", joined)

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
        products = (
            self.product_tmpl_ids.product_variant_ids or self.product_ids
        )

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
