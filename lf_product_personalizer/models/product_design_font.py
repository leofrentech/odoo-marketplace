from urllib.parse import quote_plus

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductDesignFont(models.Model):
    _name = "product.design.font"
    _description = "Personalization Font"
    _order = "sequence, name"

    name = fields.Char(required=True, help="Name shown in the font list.")
    family = fields.Char(
        string="Font Family",
        required=True,
        help="CSS font family, e.g. 'Roboto'. For Google Fonts use the exact name "
        "shown on fonts.google.com.",
    )
    source = fields.Selection(
        [
            ("system", "Installed on Device"),
            ("google", "Google Fonts"),
            ("upload", "Uploaded File"),
        ],
        default="system",
        required=True,
        help="Installed on Device: only safe for common fonts (Arial, Georgia...).\n"
        "Google Fonts: loaded from fonts.googleapis.com when the editor opens. "
        "Visitors' browsers then contact Google, keep that in mind for GDPR.\n"
        "Uploaded File: a .woff2/.woff/.ttf file served by your own website.",
    )
    font_file = fields.Binary(attachment=True)
    font_filename = fields.Char()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    @api.constrains("source", "font_file")
    def _check_font_file(self):
        for font in self:
            if font.source == "upload" and not font.font_file:
                raise ValidationError(self.env._("Upload a font file for '%s'.", font.name))

    def _lf_to_frontend(self):
        result = []
        for font in self:
            url = False
            if font.source == "google":
                url = (
                    "https://fonts.googleapis.com/css2?family="
                    f"{quote_plus(font.family)}:ital,wght@0,400;0,700;1,400;1,700&display=swap"
                )
            elif font.source == "upload":
                url = f"/web/content/product.design.font/{font.id}/font_file"
            result.append({
                "name": font.name,
                "family": font.family,
                "source": font.source,
                "url": url,
            })
        return result
