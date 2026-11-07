from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    # ------------------------------------------------------------------
    # BUSINESS METHODS
    # ------------------------------------------------------------------

    def _get_message_create_valid_field_names(self):
        """Allow message_post / message_notify to link the open log to its email."""
        return super()._get_message_create_valid_field_names() | {"email_open_origin_message_id"}
