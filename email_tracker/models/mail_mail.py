import werkzeug

from markupsafe import Markup

from odoo import api, models, tools


class MailMail(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "mail.mail"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 5. SELECTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 6. CONSTRAINS METHODS AND ONCHANGE METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        mails = super(MailMail, self).create(vals_list)
        # Add tracker link
        for mail in mails:
            body_html = tools.append_content_to_html(
                mail.body_html,
                '<img src="%s"/>' % mail._get_email_tracking_url(),
                plaintext=False,
            )
            mail.body_html = Markup(body_html)
        return mails

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    def _get_email_tracking_url(self):
        """
        Generate and return tracker link with token to verify
        """
        self.ensure_one()
        token = tools.hmac(
            self.env(su=True), "email_tracker-mail_mail-open", self.id
        )
        return werkzeug.urls.url_join(
            self.get_base_url(),
            "/mail/track/%s/%s/%s/%s/%s/blank.gif"
            % (
                self.model,
                self.res_id,
                self.mail_message_id.id,
                self.id,
                token,
            ),
        )
