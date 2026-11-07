import re

from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

PIXEL_RE = re.compile(r'/email_tracker/open/(\d+)/(\w+)/blank\.gif')


@tagged("post_install", "-at_install", "email_tracker")
class TestEmailTracker(MailCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("email_tracker.track_opens", True)
        cls.env["ir.config_parameter"].sudo().set_param("email_tracker.open_notification", True)
        cls.Tracker = cls.env["email.tracker.recipient"]
        cls.user_responsible = cls.user_employee
        cls.customer = cls.env["res.partner"].create({
            "name": "Customer <script>alert(1)</script>",
            "email": "customer@example.com",
            "user_id": cls.user_responsible.id,
        })
        cls.customer_2 = cls.env["res.partner"].create({
            "name": "Second Customer",
            "email": "customer2@example.com",
        })
        # record on which emails are posted (res.partner is a mail.thread with user_id)
        cls.record = cls.env["res.partner"].create({
            "name": "Deal Partner",
            "user_id": cls.user_responsible.id,
        })

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _post_email(self, partners, record=None, user=None):
        record = (record or self.record).with_user(user or self.user_admin)
        with self.mock_mail_gateway():
            message = record.message_post(
                body="<p>Please find our offer.</p>",
                subject="Our Offer",
                partner_ids=partners.ids,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
        return message

    def _pixel_url(self, email_to):
        mail = next((m for m in self._mails if email_to in "".join(m["email_to"])), None)
        self.assertTrue(mail, f"no email sent to {email_to}")
        match = PIXEL_RE.search(mail["body"])
        return match and match.group(0)

    def _tracker(self, url):
        return self.Tracker.browse(int(PIXEL_RE.search(url).group(1)))

    def _open_logs(self, record=None):
        record = record or self.record
        return self.env["mail.message"].search([
            ("model", "=", record._name),
            ("res_id", "=", record.id),
            ("message_type", "=", "notification"),
            ("author_id", "=", self.env.ref("base.partner_root").id),
            ("body", "ilike", "opened the email"),
        ])

    def _open_notifications(self):
        return self.env["mail.message"].search([
            ("message_type", "=", "user_notification"),
            ("body", "ilike", "opened the email"),
        ])

    # ------------------------------------------------------------------
    # pixel injection
    # ------------------------------------------------------------------

    def test_pixel_per_recipient(self):
        message = self._post_email(self.customer | self.customer_2)
        url_1 = self._pixel_url("customer@example.com")
        url_2 = self._pixel_url("customer2@example.com")
        self.assertTrue(url_1 and url_2)
        self.assertNotEqual(url_1, url_2, "each recipient must get its own pixel")
        tracker = self._tracker(url_1)
        self.assertEqual(tracker.mail_message_id, message)
        self.assertEqual(tracker.partner_id, self.customer)
        self.assertEqual(tracker.email, "customer@example.com")
        self.assertEqual((tracker.model, tracker.res_id), (self.record._name, self.record.id))
        self.assertEqual(tracker.subject, "Our Offer")
        self.assertEqual(tracker.author_id, self.user_admin.partner_id)
        self.assertEqual(tracker.user_id, self.user_responsible)
        self.assertEqual(tracker.open_count, 0)
        self.assertEqual(self._tracker(url_2).partner_id, self.customer_2)
        # pixel is added at send time only, never stored in the message body
        self.assertNotIn("email_tracker", str(message.body))

    def test_no_pixel_for_internal_users(self):
        self.user_admin.notification_type = "email"
        message = self._post_email(self.user_admin.partner_id | self.customer, user=self.user_responsible)
        self.assertFalse(self._pixel_url(self.user_admin.partner_id.email))
        self.assertTrue(self._pixel_url("customer@example.com"))
        self.assertEqual(message.email_tracker_recipient_ids.partner_id, self.customer)

    def test_no_pixel_without_document(self):
        with self.mock_mail_gateway():
            self.env["mail.mail"].sudo().create({
                "subject": "Password reset",
                "body_html": "<p>Reset</p>",
                "email_to": "someone@example.com",
            }).send()
        self.assertNotIn("email_tracker", self._mails[0]["body"])

    def test_no_pixel_when_disabled(self):
        self.env["ir.config_parameter"].sudo().set_param("email_tracker.track_opens", False)
        self._post_email(self.customer)
        self.assertFalse(self._pixel_url("customer@example.com"))

    def test_no_pixel_for_mass_mailing(self):
        """Email Marketing tracks its own opens: do not interfere."""
        if "mailing.mailing" not in self.env:
            self.skipTest("mass_mailing not installed")
        mailing = self.env["mailing.mailing"].create({
            "subject": "Promo",
            "body_html": "<p>Promo</p>",
            "mailing_model_id": self.env["ir.model"]._get_id("res.partner"),
        })
        message = self.record.message_post(body="<p>Promo</p>", subject="Promo")
        with self.mock_mail_gateway():
            self.env["mail.mail"].sudo().create({
                "mail_message_id": message.id,
                "mailing_id": mailing.id,
                "model": self.customer._name,
                "res_id": self.customer.id,
                "body_html": "<p>Promo</p>",
                "email_to": "customer@example.com",
            }).send()
        self.assertFalse(self._pixel_url("customer@example.com"))

    def test_retry_reuses_tracker(self):
        """A mail sent again (retry after failure) keeps a single tracker."""
        message = self.record.message_post(body="<p>hi</p>", subject="Retry")
        mail = self.env["mail.mail"].sudo().create({
            "mail_message_id": message.id,
            "model": self.record._name,
            "res_id": self.record.id,
            "body_html": "<p>hi</p>",
            "recipient_ids": [(6, 0, self.customer.ids)],
        })
        bodies = [mail._prepare_outgoing_list()[0]["body"] for _i in range(2)]
        self.assertEqual(PIXEL_RE.search(bodies[0]).group(0), PIXEL_RE.search(bodies[1]).group(0))
        self.assertEqual(len(message.email_tracker_recipient_ids), 1)

    # ------------------------------------------------------------------
    # emails sent from code (templates)
    # ------------------------------------------------------------------

    def test_template_send_mail_auto_delete(self):
        """template.send_mail() with auto_delete: Odoo deletes the mail and its
        message after sending, opens must still be logged on the document."""
        template = self.env["mail.template"].create({
            "name": "Offer",
            "model_id": self.env["ir.model"]._get_id("res.partner"),
            "subject": "Template Offer",
            "body_html": "<p>Offer</p>",
            "use_default_to": False,
            "partner_to": f"{self.customer.id},{self.user_responsible.partner_id.id}",
            "email_to": "raw1@example.com, raw2@example.com",
            "email_cc": "cc@example.com",
            "auto_delete": True,
        })
        with self.mock_mail_gateway(mail_unlink_sent=True):
            template.send_mail(self.record.id, force_send=True)

        url_customer = self._pixel_url("customer@example.com")
        url_raw = self._pixel_url("raw1@example.com")
        self.assertFalse(self._pixel_url(self.user_responsible.email), "internal recipient not tracked")
        tracker_raw = self._tracker(url_raw)
        self.assertFalse(tracker_raw.partner_id)
        self.assertEqual(tracker_raw.email, "raw1@example.com, raw2@example.com, cc@example.com")
        # the mail and its message are gone
        self.assertFalse(self._tracker(url_customer).mail_message_id)

        with self.mock_mail_gateway():
            self.url_open(url_customer)
            self.url_open(url_raw)
        logs = self._open_logs()
        self.assertEqual(len(logs), 2)
        bodies = " ".join(str(body) for body in logs.mapped("body"))
        self.assertIn("Template Offer", bodies)
        self.assertIn("raw1@example.com, raw2@example.com, cc@example.com opened the email", bodies)
        self.assertEqual(self._tracker(url_customer).open_count, 1)

    # ------------------------------------------------------------------
    # open tracking (controller)
    # ------------------------------------------------------------------

    def test_open_logs_once_and_counts(self):
        self._post_email(self.customer | self.customer_2)
        url = self._pixel_url("customer@example.com")
        url_2 = self._pixel_url("customer2@example.com")
        tracker = self._tracker(url)

        with self.mock_mail_gateway():
            response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "image/gif")
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertTrue(response.content.startswith(b"GIF89a"))

        logs = self._open_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs.subtype_id, self.env.ref("mail.mt_note"))
        self.assertEqual(logs.email_open_origin_message_id, tracker.mail_message_id)
        # opener name is escaped: no HTML injection in chatter
        self.assertNotIn("<script>", str(logs.body))
        self.assertIn("&lt;script&gt;", str(logs.body))
        self.assertIn("Our Offer", str(logs.body))
        self.assertEqual(tracker.open_count, 1)
        self.assertTrue(tracker.first_open_date)
        self.assertEqual(tracker.first_open_date, tracker.last_open_date)

        # second open: counter moves, no new chatter log nor notification
        with self.mock_mail_gateway():
            self.url_open(url)
        self.assertFalse(self._mails, "re-opening must not re-notify")
        self.env.invalidate_all()
        self.assertEqual(len(self._open_logs()), 1)
        self.assertEqual(tracker.open_count, 2)

        # the other recipient opening is a separate first open
        self.url_open(url_2)
        self.env.invalidate_all()
        self.assertEqual(len(self._open_logs()), 2)
        self.assertEqual(self._tracker(url_2).open_count, 1)

    def test_open_log_recipient_with_company(self):
        company = self.env["res.partner"].create({"name": "Azure Interior", "is_company": True})
        contact = self.env["res.partner"].create({
            "name": "Brandon Freeman",
            "email": "brandon@example.com",
            "parent_id": company.id,
        })
        self._post_email(contact)
        self.url_open(self._pixel_url("brandon@example.com"))
        body = str(self._open_logs().body)
        self.assertIn("Brandon Freeman (Azure Interior) opened the email", body)
        self.assertNotIn("Azure Interior, Brandon Freeman", body)

    def test_open_notifies_responsible_and_sender(self):
        self._post_email(self.customer, user=self.user_admin)
        url = self._pixel_url("customer@example.com")
        with self.mock_mail_gateway():
            self.url_open(url)
        notification = self._open_notifications()
        self.assertEqual(len(notification), 1)
        self.assertEqual(
            notification.partner_ids,
            self.user_admin.partner_id | self.user_responsible.partner_id,
        )
        # notification emails must not themselves be tracked (no loop)
        for mail in self._mails:
            self.assertNotIn("email_tracker", mail["body"])

    def test_open_no_notification_when_disabled(self):
        self.env["ir.config_parameter"].sudo().set_param("email_tracker.open_notification", False)
        self._post_email(self.customer)
        self.url_open(self._pixel_url("customer@example.com"))
        self.assertEqual(len(self._open_logs()), 1)
        self.assertFalse(self._open_notifications())

    def test_open_after_message_deleted(self):
        """The tracker keeps working once the message itself is gone."""
        message = self._post_email(self.customer)
        url = self._pixel_url("customer@example.com")
        message.unlink()
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self._open_logs()), 1)

    def test_open_raw_email_address(self):
        message = self.record.message_post(body="<p>hi</p>", subject="Raw")
        with self.mock_mail_gateway():
            self.env["mail.mail"].sudo().create({
                "mail_message_id": message.id,
                "model": self.record._name,
                "res_id": self.record.id,
                "body_html": "<p>hi</p>",
                "email_to": "raw@example.com",
            }).send()
        url = self._pixel_url("raw@example.com")
        self.url_open(url)
        self.assertEqual(self._tracker(url).open_count, 1)
        self.assertIn("raw@example.com opened the email", str(self._open_logs().body))

    def test_open_document_deleted(self):
        partner = self.env["res.partner"].create({"name": "Temp Deal"})
        self._post_email(self.customer, record=partner)
        url = self._pixel_url("customer@example.com")
        tracker = self._tracker(url)
        partner.unlink()
        self.assertEqual(self.url_open(url).status_code, 200, "pixel is still served")
        self.assertEqual(tracker.open_count, 1)

    def test_reply_quoting_pixel_is_stripped(self):
        """Customer replies quoting the tracked email: the quoted pixel must
        not be stored, nor sent to the salesperson (fake opens)."""
        self.user_responsible.notification_type = "email"
        self.record.message_subscribe(partner_ids=self.user_responsible.partner_id.ids)
        message = self._post_email(self.customer)
        pixel = re.search(
            r'<img[^>]*email_tracker/open[^>]*>',
            next(m for m in self._mails if "customer@example.com" in "".join(m["email_to"]))["body"],
        ).group(0)
        raw = (
            "From: Customer <customer@example.com>\n"
            "To: catchall@test.mycompany.com\n"
            "Subject: Re: Our Offer\n"
            "Message-ID: <reply-quoting-pixel@example.com>\n"
            f"In-Reply-To: {message.message_id}\n"
            "MIME-Version: 1.0\n"
            "Content-Type: text/html; charset=utf-8\n\n"
            f'<div>Looks good!</div><blockquote type="cite"><p>Offer</p>{pixel}</blockquote>\n'
        )
        with self.mock_mail_gateway():
            self.env["mail.thread"].message_process("res.partner", raw, thread_id=self.record.id)
        reply = self.env["mail.message"].search([("message_id", "=", "<reply-quoting-pixel@example.com>")])
        self.assertEqual(reply.res_id, self.record.id)
        self.assertIn("Looks good!", str(reply.body))
        self.assertNotIn("email_tracker", str(reply.body))
        mails_to_sales = [m for m in self._mails if self.user_responsible.email in "".join(m["email_to"])]
        self.assertTrue(mails_to_sales)
        for mail in mails_to_sales:
            self.assertNotIn("email_tracker", mail["body"])

    def test_open_by_logged_internal_user_ignored(self):
        self._post_email(self.customer)
        url = self._pixel_url("customer@example.com")
        self.authenticate(self.user_responsible.login, self.user_responsible.login)
        self.assertEqual(self.url_open(url).status_code, 200)
        self.assertEqual(self._tracker(url).open_count, 0)
        self.assertFalse(self._open_logs())

    @mute_logger("odoo.http")
    def test_invalid_or_tampered_token(self):
        self._post_email(self.customer | self.customer_2)
        url = self._pixel_url("customer@example.com")
        url_2 = self._pixel_url("customer2@example.com")
        tracker_id, token = PIXEL_RE.search(url).groups()
        tracker_2_id = PIXEL_RE.search(url_2).group(1)
        for bad_url in (
            f"/email_tracker/open/{tracker_id}/{'0' * len(token)}/blank.gif",
            # a valid token reused on another tracker
            f"/email_tracker/open/{tracker_2_id}/{token}/blank.gif",
            f"/email_tracker/open/999999999/{token}/blank.gif",
        ):
            self.assertEqual(self.url_open(bad_url).status_code, 400, bad_url)
        self.assertFalse(self._open_logs())
        self.assertEqual(self._tracker(url).open_count + self._tracker(url_2).open_count, 0)

    def test_head_request_does_not_count(self):
        self._post_email(self.customer)
        url = self._pixel_url("customer@example.com")
        self.assertEqual(self.opener.head(self.base_url() + url).status_code, 200)
        self.assertEqual(self._tracker(url).open_count, 0)

    def test_legacy_pixel_url(self):
        """Pixels of emails sent with v1.0 still return an image, but log nothing."""
        response = self.url_open(f"/mail/track/res.partner/{self.record.id}/1/1/abc/blank.gif")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "image/gif")
        self.assertFalse(self._open_logs())

    # ------------------------------------------------------------------
    # access rights
    # ------------------------------------------------------------------

    def test_access_rules(self):
        self._post_email(self.customer, user=self.user_admin)
        tracker = self._tracker(self._pixel_url("customer@example.com"))
        other_user = mail_new_test_user(self.env, login="other_sales", groups="base.group_user")
        Tracker = self.env["email.tracker.recipient"]
        # responsible of the document and sender see it; another user does not
        self.assertEqual(Tracker.with_user(self.user_responsible).search([("id", "=", tracker.id)]), tracker)
        self.assertEqual(Tracker.with_user(self.user_admin).search([("id", "=", tracker.id)]), tracker)
        self.assertFalse(Tracker.with_user(other_user).search([("id", "=", tracker.id)]))
        # read only for users
        self.assertFalse(Tracker.with_user(self.user_responsible).check_access_rights("write", raise_exception=False))

    # ------------------------------------------------------------------
    # per-user notification preference
    # ------------------------------------------------------------------

    def test_user_preference_overrides_company_default(self):
        ICP = self.env["ir.config_parameter"].sudo()
        cases = [
            # (company default, responsible's preference, responsible notified)
            (True, "default", True),
            (True, "never", False),
            (False, "default", False),
            (False, "always", True),
        ]
        for company_default, preference, notified in cases:
            with self.subTest(company_default=company_default, preference=preference):
                ICP.set_param("email_tracker.open_notification", company_default)
                self.user_responsible.email_tracker_open_notification = preference
                # the sender (admin) opts out: only the responsible's preference matters
                self.user_admin.email_tracker_open_notification = "never"
                notifications_before = self._open_notifications()
                self._post_email(self.customer, user=self.user_admin)
                url = self._pixel_url("customer@example.com")
                with self.mock_mail_gateway():
                    self.url_open(url)
                new_notification = self._open_notifications() - notifications_before
                self.assertEqual(bool(new_notification), notified)
                if notified:
                    self.assertEqual(new_notification.partner_ids, self.user_responsible.partner_id)

    def test_user_can_set_own_preference(self):
        self.user_responsible.with_user(self.user_responsible).write(
            {"email_tracker_open_notification": "never"}
        )
        self.assertEqual(self.user_responsible.email_tracker_open_notification, "never")

    # ------------------------------------------------------------------
    # chatter
    # ------------------------------------------------------------------

    def test_chatter_store_data(self):
        """Internal users get the open status of sent emails with the chatter messages."""
        self._post_email(self.customer)
        tracker = self._tracker(self._pixel_url("customer@example.com"))
        self.url_open(self._pixel_url("customer@example.com"))
        self.authenticate(self.user_responsible.login, self.user_responsible.login)
        result = self.make_jsonrpc_request(
            "/mail/thread/messages", {"thread_model": "res.partner", "thread_id": self.record.id}
        )
        message = next(m for m in result["messages"] if m["id"] == tracker.mail_message_id.id)
        trackers = message["email_tracker_recipient_ids"]
        self.assertEqual([t["id"] for t in trackers], [tracker.id])
        self.assertEqual(trackers[0]["open_count"], 1)
        self.assertTrue(trackers[0]["first_open_date"])
        self.assertTrue(trackers[0]["recipient_label"].startswith("Customer"))

    def test_chatter_badge_tour(self):
        company = self.env["res.partner"].create({"name": "Azure Interior", "is_company": True})
        contact = self.env["res.partner"].create({
            "name": "Brandon Freeman",
            "email": "brandon@example.com",
            "parent_id": company.id,
        })
        self._post_email(contact | self.customer_2)
        self.url_open(self._pixel_url("brandon@example.com"))
        self.record.message_post(body="<p>Internal remark</p>", subtype_xmlid="mail.mt_note")
        self.start_tour(
            f"/web#model=res.partner&id={self.record.id}&view_type=form", "email_tracker_chatter_badge", login="admin"
        )
