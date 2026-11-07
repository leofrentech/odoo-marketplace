from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # ------------------------------------------------------------------
    # FIELD DECLARATIONS
    # ------------------------------------------------------------------

    email_tracker_track_opens = fields.Boolean(
        "Track Email Opens",
        config_parameter="email_tracker.track_opens",
    )
    email_tracker_open_notification = fields.Boolean(
        "Email Open Notification",
        config_parameter="email_tracker.open_notification",
    )
