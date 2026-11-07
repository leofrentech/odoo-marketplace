from markupsafe import Markup

from odoo import models, tools

from .mail_message import strip_tracking_pixels

PARAM_TRACK_OPENS = "email_tracker.track_opens"


class MailMail(models.Model):
    _inherit = "mail.mail"

    # ------------------------------------------------------------------
    # BUSINESS METHODS
    # ------------------------------------------------------------------

    def _personalize_outgoing_body(self, body, partner=False, doc_to_followers=None):
        """Inject a per-recipient tracking pixel at send time.

        Doing it here (instead of in ``create``) means the pixel is never
        stored in the message body, and each recipient gets their own
        tracker (``email.tracker.recipient``) with its own signed URL.
        """
        body = super()._personalize_outgoing_body(
            body, partner=partner, doc_to_followers=doc_to_followers
        )
        # drop pixels copied from another email (quoted reply, forward...)
        body = strip_tracking_pixels(body)
        if body and self._email_tracker_is_trackable(partner):
            tracker = self.env["email.tracker.recipient"]._get_or_create_for_mail(self, partner)
            url = tracker._get_tracking_url()
            pixel = Markup(
                '<img src="%s" alt="" width="1" height="1" border="0" '
                'style="height:1px !important;width:1px !important;'
                'border-width:0 !important;margin:0 !important;padding:0 !important;"/>'
            ) % url
            body = tools.mail.append_content_to_html(body, pixel, plaintext=False)
        return body

    def _email_tracker_is_trackable(self, partner=False):
        """Whether an open of this email by ``partner`` should be tracked.

        Only emails linked to a chatter-enabled document are tracked (open
        events are logged on that document). Internal users and the
        "email opened" notifications themselves are never tracked.
        """
        self.ensure_one()
        if not self.env["ir.config_parameter"].sudo().get_param(PARAM_TRACK_OPENS):
            return False
        # Email Marketing (mass_mailing, marketing_automation) has its own
        # open/click statistics: never add our pixel nor log on contacts.
        if "mailing_id" in self._fields and self.mailing_id:
            return False
        message = self.mail_message_id
        if not (message and self.model and self.res_id):
            return False
        if self.model not in self.env or not isinstance(
            self.env[self.model], self.env.registry["mail.thread"]
        ):
            return False
        if message.message_type == "user_notification" or message.email_open_origin_message_id:
            return False
        if partner and partner.sudo().user_ids.filtered(lambda user: not user.share):
            return False
        return True
