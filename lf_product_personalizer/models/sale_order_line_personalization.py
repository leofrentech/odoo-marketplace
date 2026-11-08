import base64
import json
import re

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import consteq

from .design_tools import check_json_size, extract_artwork

CONTENT_SRC_RE = re.compile(r"^/web/content/(\d+)\?access_token=([\w-]+)$")


class SaleOrderLinePersonalization(models.Model):
    _name = "sale.order.line.personalization"
    _description = "Order Line Personalization"
    _order = "sale_order_line_id, sequence, id"
    _rec_name = "design_type"

    sale_order_line_id = fields.Many2one(
        "sale.order.line",
        string="Order Line",
        required=True,
        ondelete="cascade",
        index=True,
    )
    order_id = fields.Many2one(
        related="sale_order_line_id.order_id", store=True, index=True
    )
    company_id = fields.Many2one(related="order_id.company_id", store=True)
    partner_id = fields.Many2one(related="order_id.partner_id", string="Customer")
    product_id = fields.Many2one(related="sale_order_line_id.product_id")
    salesman_id = fields.Many2one(related="sale_order_line_id.salesman_id", store=True)
    sequence = fields.Integer(default=10)
    design_type = fields.Char(
        string="Area",
        required=True,
        help="Name of the area (e.g. Front) when the design was made.",
    )
    design_config_id = fields.Many2one(
        "product.design.config", string="Area Configuration", ondelete="set null"
    )
    personalized_json = fields.Text(string="Design Data")
    is_customized = fields.Boolean(
        string="Customized", help="The customer added something on this area."
    )
    price_extra = fields.Float(
        string="Extra Price",
        digits="Product Price",
        help="Extra price of the area when the design was made.",
    )
    product_image = fields.Image(string="Preview", max_width=1024, max_height=1024)
    print_image = fields.Binary(string="Print File (PNG)", attachment=True)
    print_image_filename = fields.Char(compute="_compute_filenames")
    print_svg = fields.Binary(string="Print File (SVG)", attachment=True)
    print_svg_filename = fields.Char(compute="_compute_filenames")
    artwork_attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Original Artwork",
        help="Images uploaded by the customer, at their original resolution.",
    )
    approval_state = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("pending", "To Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Artwork Status",
        default="not_required",
        required=True,
        index=True,
    )
    approval_note = fields.Text(
        string="Note to Customer", help="Explain what must change when rejecting a design."
    )
    approved_by_id = fields.Many2one("res.users", string="Reviewed By", readonly=True)

    @api.depends("design_type", "order_id.name")
    def _compute_filenames(self):
        for rec in self:
            base = re.sub(r"[^\w-]+", "-", f"{rec.order_id.name or 'design'}-{rec.design_type or rec.id}")
            rec.print_image_filename = f"{base}.png"
            rec.print_svg_filename = f"{base}.svg"

    # ------------------------------------------------------------------
    # Storing designs
    # ------------------------------------------------------------------

    def _lf_extract_artwork(self):
        """Move images embedded in the design (data URLs) to attachments.

        It keeps the original files for production and makes the stored JSON
        small. The JSON then references the attachments with an access token,
        so the customer can reopen the design.
        """
        for rec in self:
            data = rec._lf_canvas_data()
            attachments = extract_artwork(rec.env, data, rec._name, rec.id, rec.design_type)
            check_json_size(rec.env, data)
            if attachments:
                rec.write({
                    "personalized_json": json.dumps(data),
                    "artwork_attachment_ids": [fields.Command.link(a.id) for a in attachments],
                })

    def _lf_adopt_artwork(self, previous):
        """Images reused from an earlier design point to existing attachments.

        Attachments of ``previous`` (the designs being replaced) are moved to
        these records so they are not deleted with them. Images coming from
        elsewhere (saved design, ready-made template) are copied, so the order
        keeps its own files.
        """
        Attachment = self.env["ir.attachment"].sudo()
        adopted = {}
        for rec in self:
            data = rec._lf_canvas_data()
            changed = False
            linked = Attachment
            for obj in data["objects"]:
                match = CONTENT_SRC_RE.match(obj.get("src") or "") if obj.get("type") == "image" else None
                if not match:
                    continue
                attachment_id = int(match.group(1))
                attachment = adopted.get(attachment_id)
                if not attachment:
                    source = Attachment.browse(attachment_id).exists()
                    if not (
                        source and source.access_token
                        and consteq(source.access_token, match.group(2))
                    ):
                        raise UserError(rec.env._(
                            "An image of this design is no longer available. Please upload it again."
                        ))
                    if source.res_model == rec._name and source.res_id == rec.id:
                        attachment = source  # just extracted from a data URL
                    elif source.res_model == rec._name and source.res_id in previous.ids:
                        source.res_id = rec.id
                        attachment = source
                    else:
                        attachment = source.copy({"res_model": rec._name, "res_id": rec.id})
                        attachment.generate_access_token()
                    adopted[attachment_id] = attachment
                src = f"/web/content/{attachment.id}?access_token={attachment.access_token}"
                if obj["src"] != src:
                    obj["src"] = src
                    changed = True
                linked |= attachment
            values = {}
            if linked:
                values["artwork_attachment_ids"] = [fields.Command.link(a.id) for a in linked]
            if changed:
                values["personalized_json"] = json.dumps(data)
            if values:
                rec.write(values)

    def _lf_canvas_data(self):
        self.ensure_one()
        try:
            data = json.loads(self.personalized_json or "{}")
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        data.setdefault("objects", [])
        return data

    # ------------------------------------------------------------------
    # Approval workflow
    # ------------------------------------------------------------------

    def action_approve(self):
        if self.filtered(lambda rec: rec.approval_state != "pending"):
            raise UserError(
                self.env._("Only designs waiting for review can be approved. "
                  "Use 'Back to Review' first.")
            )
        self.write({
            "approval_state": "approved",
            "approved_by_id": self.env.user.id,
        })
        for order in self.order_id:
            order._lf_close_artwork_activity()

    def action_reject(self):
        if self.filtered(lambda rec: rec.approval_state != "pending"):
            raise UserError(self.env._("Only designs waiting for review can be rejected."))
        missing = self.filtered(lambda rec: not rec.approval_note)
        if missing:
            raise UserError(
                self.env._("Write a note to the customer explaining why the design is rejected.")
            )
        self.write({
            "approval_state": "rejected",
            "approved_by_id": self.env.user.id,
        })
        for order in self.order_id:
            records = self.filtered(lambda rec, order=order: rec.order_id == order)
            text = self.env._(
                "We could not approve your design for %(areas)s: %(notes)s",
                areas=", ".join(records.mapped("design_type")),
                notes=" / ".join(records.mapped("approval_note")),
            )
            url = order.get_base_url() + order.get_portal_url()
            body = Markup("<p>%s</p><p><a href='%s'>%s</a></p>") % (
                text, url, self.env._("Fix my design"),
            )
            order.message_post(
                body=body,
                partner_ids=order.partner_id.ids,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )

    def action_reset_to_review(self):
        self.write({"approval_state": "pending", "approved_by_id": False})

    def action_open_order(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": self.order_id.id,
            "view_mode": "form",
        }

    def _lf_revision_url(self):
        """Editor link letting the customer fix a rejected design."""
        self.ensure_one()
        token = self.order_id._portal_ensure_token()
        return f"/shop/personalize/revise/{self.sale_order_line_id.id}?access_token={token}"

    def _lf_image_url(self, field="product_image"):
        """Website URL of an image, readable by whoever can see the order."""
        self.ensure_one()
        token = self.order_id._portal_ensure_token()
        return f"/shop/personalization/{self.id}/{field}?access_token={token}"

    def _lf_preview_b64(self):
        self.ensure_one()
        return self.product_image or (
            self.design_config_id.design_image if self.design_config_id else False
        )

    @api.model
    def _lf_b64(self, raw):
        return base64.b64encode(raw) if raw else False
