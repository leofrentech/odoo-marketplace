from odoo import api, fields, models

# Resolution of print files compared to the 800px editor.
PRINT_QUALITY_SCALES = {"standard": 2, "high": 4, "very_high": 6}


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    lf_personalizer_max_upload_mb = fields.Integer(
        string="Max. Upload Size (MB)",
        config_parameter="lf_product_personalizer.max_upload_mb",
        default=15,
        help="Largest image a customer can upload in the design editor.",
    )
    lf_personalizer_print_quality = fields.Selection(
        [
            ("standard", "Standard (1600 px)"),
            ("high", "High (3200 px)"),
            ("very_high", "Very high (4800 px)"),
        ],
        string="Print File Quality",
        config_parameter="lf_product_personalizer.print_quality",
        default="high",
        help="Size of the print files generated for production (for a full area). "
        "Higher quality gives sharper large prints but bigger files.",
    )

    @api.model
    def _lf_print_scale(self):
        quality = self.env["ir.config_parameter"].sudo().get_str(
            "lf_product_personalizer.print_quality", "high",
        )
        return PRINT_QUALITY_SCALES.get(quality, PRINT_QUALITY_SCALES["high"])
