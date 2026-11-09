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
        user_writeable=True,
        help="Get notified when a customer opens an email you sent or one sent "
             "from a document you are responsible for.",
    )

    # ------------------------------------------------------------------
    # BUSINESS METHODS
    # ------------------------------------------------------------------

    def _email_tracker_wants_open_notification(self, company_default):
        self.ensure_one()
        if self.email_tracker_open_notification == "default":
            return company_default
        return self.email_tracker_open_notification == "always"
