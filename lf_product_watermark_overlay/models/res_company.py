from odoo import fields, models


class ResCompany(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "res.company"

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    watermark_logo = fields.Image(
        string="Watermark Logo",
        max_width=1024,
        max_height=1024,
        help="Logo used for image watermarks on this company's products.",
    )
