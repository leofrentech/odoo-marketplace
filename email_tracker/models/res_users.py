from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    # ------------------------------------------------------------------
    # FIELD DECLARATIONS
    # ------------------------------------------------------------------

    email_tracker_open_notification = fields.Selection(
        [
            ("default", "Company default"),
            ("always", "Notify me"),
            ("never", "Don't notify me"),
        ],
        string="Email Opened Notifications",
        default="default",
        required=True,
        help="Get notified when a customer opens an email you sent or one sent "
             "from a document you are responsible for.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["email_tracker_open_notification"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["email_tracker_open_notification"]

    # ------------------------------------------------------------------
    # BUSINESS METHODS
    # ------------------------------------------------------------------

    def _email_tracker_wants_open_notification(self, company_default):
        self.ensure_one()
        if self.email_tracker_open_notification == "default":
            return company_default
        return self.email_tracker_open_notification == "always"
