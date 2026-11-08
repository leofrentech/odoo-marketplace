import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .design_tools import (
    decode_data_url,
    max_upload_bytes,
    sanitize_canvas_json,
    sanitize_svg,
)


def _canonical(canvas):
    """Comparable form of a design (ignores float noise from the editor)."""
    def clean(value):
        if isinstance(value, float):
            return round(value, 2)
        if isinstance(value, dict):
            return {key: clean(val) for key, val in value.items()}
        if isinstance(value, list):
            return [clean(val) for val in value]
        return value
    return json.dumps(clean(canvas.get("objects", [])), sort_keys=True)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    personalization_ids = fields.One2many(
        "sale.order.line.personalization",
        "sale_order_line_id",
        string="Personalizations",
        help="Designs made by the customer for this line.",
    )
    has_personalization = fields.Boolean(
        compute="_compute_has_personalization", store=True
    )

    @api.depends("personalization_ids")
    def _compute_has_personalization(self):
        for line in self:
            line.has_personalization = bool(line.personalization_ids)

    # ------------------------------------------------------------------
    # Price & description
    # ------------------------------------------------------------------

    def _lf_get_surcharge(self):
        """Personalization surcharge per unit, in the order currency."""
        self.ensure_one()
        customized = self.personalization_ids.filtered("is_customized")
        if not customized:
            return 0.0
        amount = self.product_id.product_tmpl_id.personalization_fee + sum(
            customized.mapped("price_extra")
        )
        if not amount:
            return 0.0
        product_currency = self.product_id.currency_id or self.company_id.currency_id
        return product_currency._convert(
            amount,
            self.currency_id or product_currency,
            self.company_id or self.env.company,
            fields.Date.to_date(self._get_order_date()) or fields.Date.today(),
        )

    def _get_display_price_ignore_combo(self):
        price = super()._get_display_price_ignore_combo()
        if self.personalization_ids:
            price += self._lf_get_surcharge()
        return price

    def _get_sale_order_line_multiline_description_sale(self):
        description = super()._get_sale_order_line_multiline_description_sale()
        customized = self.personalization_ids.filtered("is_customized")
        if customized:
            description += "\n" + _(
                "Personalized: %s", ", ".join(customized.mapped("design_type"))
            )
        return description

    # ------------------------------------------------------------------
    # Saving designs from the website
    # ------------------------------------------------------------------

    def _lf_set_personalization(self, designs, revision=False):
        """Replace the designs of this line by ``designs``.

        :param dict designs: ``{area_id: {"json", "preview", "print", "svg"}}``
            as posted by the website editor (untrusted).
        :param bool revision: the customer fixes a rejected design of an order
            already placed: the price cannot change, unchanged approved areas
            stay approved and the others go back to review.
        """
        self.ensure_one()
        previous = self.personalization_ids
        previous_by_area = {p.design_config_id.id: p for p in previous if p.design_config_id}
        template = self.product_id.product_tmpl_id
        areas = template._lf_get_areas(self.product_id)
        if not isinstance(designs, dict):
            raise UserError(_("The design data is invalid."))
        unknown = set(designs) - {str(area_id) for area_id in areas.ids}
        if unknown:
            raise UserError(_("This design does not match the product areas."))

        max_bytes = max_upload_bytes(self.env)
        values_list = []
        for area in areas:
            design = designs.get(str(area.id)) or {}
            if not isinstance(design, dict):
                raise UserError(_("The design data is invalid."))
            canvas = sanitize_canvas_json(
                self.env, design.get("json"), template.personalization_max_text_length
            )
            customized = bool(canvas["objects"])
            if area.is_required and not customized:
                raise UserError(_("Please personalize the area '%s'.", area.design_type))
            approval_state = (
                "pending"
                if customized and (template.personalization_requires_approval or revision)
                else "not_required"
            )
            old = previous_by_area.get(area.id)
            if (
                revision and customized and old
                and old.approval_state == "approved"
                and _canonical(old._lf_canvas_data()) == _canonical(canvas)
            ):
                approval_state = "approved"
            values = {
                "sale_order_line_id": self.id,
                "sequence": area.sequence,
                "design_type": area.design_type,
                "design_config_id": area.id,
                "personalized_json": json.dumps(canvas),
                "is_customized": customized,
                "price_extra": area.price_extra if customized else 0.0,
                "approval_state": approval_state,
                "approved_by_id": old.approved_by_id.id
                if approval_state == "approved" else False,
            }
            if design.get("preview"):
                raw, _mimetype = decode_data_url(self.env, design["preview"], max_bytes)
                values["product_image"] = self.env[
                    "sale.order.line.personalization"
                ]._lf_b64(raw)
            elif area.design_image:
                values["product_image"] = area.design_image
            if customized and design.get("print"):
                # Print files are generated, not uploaded: allow bigger files.
                raw, _mimetype = decode_data_url(self.env, design["print"], max_bytes * 4)
                values["print_image"] = self.env[
                    "sale.order.line.personalization"
                ]._lf_b64(raw)
            if customized and design.get("svg"):
                values["print_svg"] = self.env[
                    "sale.order.line.personalization"
                ]._lf_b64(sanitize_svg(self.env, design["svg"], max_bytes * 4))
            values_list.append(values)

        if not any(values["is_customized"] for values in values_list):
            raise UserError(_("Add some text or an image to your design first."))

        if revision:
            new_extra = sum(v["price_extra"] for v in values_list)
            old_extra = sum(previous.filtered("is_customized").mapped("price_extra"))
            if self.currency_id.compare_amounts(new_extra, old_extra) > 0:
                raise UserError(_(
                    "Your order did not include a paid personalization for all these areas. "
                    "Please contact us to add one."
                ))

        Personalization = self.env["sale.order.line.personalization"].sudo()
        new = Personalization.create(values_list)
        new._lf_extract_artwork()
        # Before deleting the old designs: keep the images the new ones reuse.
        new._lf_adopt_artwork(previous.sudo())
        previous.sudo().unlink()
        self._lf_refresh_from_personalization()

    def _lf_refresh_from_personalization(self):
        """Recompute price and description once designs changed (draft only)."""
        for line in self.filtered(lambda line: line.order_id.state in ("draft", "sent")):
            line._compute_name()
            if not line.qty_invoiced:
                line._reset_price_unit()

    def action_view_personalizations(self):
        self.ensure_one()
        return {
            "name": _("Designs"),
            "type": "ir.actions.act_window",
            "res_model": "sale.order.line.personalization",
            "view_mode": "kanban,list,form",
            "domain": [("sale_order_line_id", "=", self.id)],
            "context": {"create": False},
        }
