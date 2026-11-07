import re

from odoo import api, fields, models

from odoo.addons.mail.tools.discuss import Store

PIXEL_TAG_RE = re.compile(r"<img\b[^>]*/email_tracker/open/[^>]*>", re.IGNORECASE)


def strip_tracking_pixels(body):
    """Remove our tracking pixels from an HTML body, keeping its type (str /
    Markup). Pixels are only added at send time, so one found in a stored
    body is a quoted copy (customer reply, forward...) and must not be kept:
    whoever later displays it would register a fake open."""
    if not body or "/email_tracker/open/" not in body:
        return body
    return body.__class__(PIXEL_TAG_RE.sub("", str(body)))


class MailMessage(models.Model):
    _inherit = "mail.message"

    # ------------------------------------------------------------------
    # FIELD DECLARATIONS
    # ------------------------------------------------------------------

    email_open_origin_message_id = fields.Many2one(
        "mail.message",
        "Email Open Message Origin",
        help="Set on the 'email opened' log / notification: the sent email it refers to.",
        ondelete="set null",
        index="btree_not_null",
        copy=False,
    )
    email_tracker_recipient_ids = fields.One2many(
        "email.tracker.recipient", "mail_message_id", "Email Opens", readonly=True,
    )

    # ------------------------------------------------------------------
    # CRUD METHODS
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("body"):
                vals["body"] = strip_tracking_pixels(vals["body"])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("body"):
            vals["body"] = strip_tracking_pixels(vals["body"])
        return super().write(vals)

    # ------------------------------------------------------------------
    # BUSINESS METHODS
    # ------------------------------------------------------------------

    def _to_store_defaults(self, target):
        """Send open tracking of sent emails to the chatter, internal users only
        (same visibility as Odoo's own delivery status of notifications)."""
        field_names = super()._to_store_defaults(target)
        if target.is_internal(self.env):
            field_names.append(
                # sudo: email.tracker.recipient - internal users can see the open
                # status of emails on documents they can read, like notifications
                Store.Many(
                    "email_tracker_recipient_ids",
                    value=lambda message: message.sudo().email_tracker_recipient_ids,
                ),
            )
        return field_names
