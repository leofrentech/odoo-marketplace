from markupsafe import Markup

from odoo import api, fields, models, tools
from odoo.tools import SQL

from odoo.addons.mail.tools.discuss import Store

PARAM_OPEN_NOTIFICATION = "email_tracker.open_notification"
TOKEN_SCOPE = "email_tracker-recipient-open"


class EmailTrackerRecipient(models.Model):
    """One tracked email, as received by one recipient.

    Created at send time, it holds everything needed to log an open, so
    tracking keeps working after Odoo deletes the mail.mail and its
    mail.message (``auto_delete`` emails sent from code / templates).
    """

    _name = "email.tracker.recipient"
    _description = "Email Open Tracking"
    _order = "sent_date desc, id desc"
    _rec_name = "subject"

    # ------------------------------------------------------------------
    # FIELD DECLARATIONS
    # ------------------------------------------------------------------

    mail_message_id = fields.Many2one(
        "mail.message", "Message", index="btree_not_null", ondelete="set null", readonly=True,
        help="Sent message. Emptied when Odoo deletes it after sending.",
    )
    model = fields.Char("Document Model", required=True, index=True, readonly=True)
    res_id = fields.Many2oneReference("Document ID", model_field="model", required=True, index=True, readonly=True)
    record_name = fields.Char("Document", readonly=True)
    subject = fields.Char(readonly=True)
    partner_id = fields.Many2one("res.partner", "Recipient", index="btree_not_null", ondelete="set null", readonly=True)
    email = fields.Char("Recipient Email", readonly=True)
    author_id = fields.Many2one("res.partner", "Sent By", ondelete="set null", readonly=True)
    user_id = fields.Many2one(
        "res.users", "Responsible", index="btree_not_null", ondelete="set null", readonly=True,
        help="Responsible of the document when the email was sent.",
    )
    sent_date = fields.Datetime("Sent On", required=True, default=fields.Datetime.now, readonly=True)
    open_count = fields.Integer("Opens", readonly=True)
    first_open_date = fields.Datetime("First Opened On", readonly=True)
    last_open_date = fields.Datetime("Last Opened On", readonly=True)
    # display helpers for the list: "Brandon Freeman (Azure Interior)" and
    # "Mitchell Admin" rather than Odoo's "Company, Person" display names
    recipient_label = fields.Char("Recipient Name", compute="_compute_recipient_label")
    author_name = fields.Char("Sent By Name", related="author_id.name")

    # ------------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------------

    @api.depends("partner_id.name", "partner_id.parent_id.name", "partner_id.is_company", "email")
    def _compute_recipient_label(self):
        for tracker in self:
            tracker.recipient_label = tracker._get_recipient_label()

    @api.depends("subject", "record_name")
    def _compute_display_name(self):
        for tracker in self:
            tracker.display_name = tracker.subject or tracker.record_name or self.env._("Email")

    # ------------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------------

    def action_open_document(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.model,
            "res_id": self.res_id,
            "view_mode": "form",
            "target": "current",
        }

    # ------------------------------------------------------------------
    # BUSINESS METHODS
    # ------------------------------------------------------------------

    @api.model
    def _get_or_create_for_mail(self, mail, partner=False):
        """Tracker for ``mail`` as sent to ``partner`` (or to its raw
        email_to / email_cc addresses). Reused when the same mail is sent
        again, e.g. retried after a failure."""
        email = (
            partner.email_normalized or partner.email if partner
            else ", ".join(filter(None, [mail.email_to, mail.email_cc]))
        )
        message = mail.mail_message_id
        domain = [
            ("mail_message_id", "=", message.id),
            ("partner_id", "=", partner.id if partner else False),
            ("email", "=", email or False),
        ]
        tracker = self.sudo().search(domain, limit=1)
        if tracker:
            return tracker
        record = self.env[mail.model].sudo().browse(mail.res_id)
        user_field = record._fields.get("user_id")
        responsible = (
            record.user_id
            if user_field and user_field.type == "many2one" and user_field.comodel_name == "res.users"
            else self.env["res.users"]
        )
        return self.sudo().create({
            "mail_message_id": message.id,
            "model": mail.model,
            "res_id": mail.res_id,
            "record_name": message.record_name or record.display_name,
            "subject": mail.subject or message.subject or message.record_name or record.display_name,
            "partner_id": partner.id if partner else False,
            "email": email or False,
            "author_id": message.author_id.id,
            "user_id": responsible[:1].id,
        })

    def _get_token(self):
        self.ensure_one()
        return tools.hmac(self.env(su=True), TOKEN_SCOPE, self.id)

    def _get_tracking_url(self):
        self.ensure_one()
        record = self.env[self.model].browse(self.res_id)
        return tools.urls.urljoin(
            record.get_base_url(),
            f"/email_tracker/open/{self.id}/{self._get_token()}/blank.gif",
        )

    def _register_open(self):
        """Count an open. Only the first open of each recipient is logged in
        the chatter and notified: email clients and privacy proxies often
        load images several times.

        :return: True if this was the first open
        """
        self.ensure_one()
        # serialize concurrent opens (e.g. image proxy prefetch)
        self.env.cr.execute(SQL("SELECT id FROM email_tracker_recipient WHERE id = %s FOR UPDATE", self.id))
        self.invalidate_recordset(["open_count", "first_open_date"])
        now = fields.Datetime.now()
        first_open = not self.open_count
        values = {"open_count": self.open_count + 1, "last_open_date": now}
        if first_open:
            values["first_open_date"] = now
        self.write(values)
        if first_open:
            self._log_open()
        self._bus_send_update()
        return first_open

    def _bus_send_update(self):
        """Refresh the "opened" badge live in the chatter of the sender and of
        the document responsible (Odoo pushes chatter updates per user)."""
        self.ensure_one()
        users = self.author_id.user_ids | self.user_id
        if self.model in self.env:
            record = self.env[self.model].browse(self.res_id).exists()
            user_field = record._fields.get("user_id")
            if record and user_field and user_field.type == "many2one" and user_field.comodel_name == "res.users":
                users |= record.user_id
        for user in users.filtered(lambda user: not user.share):
            Store(bus_channel=user).add(self, "_store_email_tracker_fields")

    def _get_recipient_label(self):
        """"Brandon Freeman (Azure Interior)" rather than Odoo's display name
        "Azure Interior, Brandon Freeman", which reads like two people."""
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            return self.email or ""
        name = partner.name or partner.email or ""
        company = partner.parent_id
        if company and company.name and not partner.is_company:
            return f"{name} ({company.name})"
        return name

    def _get_notified_partners(self, record):
        """Internal partners to notify of an open: the sender and the current
        document responsible (``user_id``), never the opener nor OdooBot,
        and only if their own preference (or the company default) says so."""
        self.ensure_one()
        users = self.env["res.users"]
        if self.author_id:
            users |= self.author_id.user_ids
        user_field = record._fields.get("user_id")
        if user_field and user_field.type == "many2one" and user_field.comodel_name == "res.users":
            users |= record.user_id
        company_default = self.env["ir.config_parameter"].sudo().get_bool(PARAM_OPEN_NOTIFICATION)
        users = users.filtered(
            lambda user: not user.share and user._email_tracker_wants_open_notification(company_default),
        )
        return users.partner_id - self.partner_id - self.env.ref("base.partner_root")

    def _store_email_tracker_fields(self, res: Store.FieldList):
        """Data sent to the chatter ("opened" badge on sent emails)."""
        res.extend(["email", "first_open_date", "last_open_date", "mail_message_id", "open_count"])
        res.attr("recipient_label", lambda tracker: tracker._get_recipient_label())

    def _log_open(self):
        self.ensure_one()
        if self.model not in self.env:
            return
        record = self.env[self.model].browse(self.res_id).exists()
        if not record:
            return
        # write in the sender's language, not the one of the email client
        lang = self.author_id.lang or self.env.lang
        env = self.with_context(lang=lang).env
        body = Markup("<p>%s</p>") % env._(
            "%(recipient)s opened the email \"%(subject)s\".",
            recipient=self._get_recipient_label() or env._("The recipient"),
            subject=self.subject or record.display_name,
        )
        odoobot = self.env.ref("base.partner_root")
        origin = self.mail_message_id.exists()
        record.with_context(lang=lang, mail_create_nosubscribe=True).message_post(
            body=body,
            author_id=odoobot.id,
            message_type="notification",
            subtype_xmlid="mail.mt_note",
            email_open_origin_message_id=origin.id,
        )

        notified = self.with_context(lang=lang)._get_notified_partners(record)
        if notified:
            record.with_context(lang=lang).message_notify(
                partner_ids=notified.ids,
                body=body,
                subject=env._("Email opened: %(subject)s", subject=self.subject or record.display_name),
                author_id=odoobot.id,
                email_layout_xmlid="mail.mail_notification_light",
                email_open_origin_message_id=origin.id,
            )
