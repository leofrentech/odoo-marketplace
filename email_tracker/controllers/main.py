import base64
import werkzeug

from datetime import datetime, timezone
from markupsafe import Markup
from werkzeug.exceptions import BadRequest


from odoo import tools
from odoo.http import request, route, Controller


class EmailTrackerController(Controller):
    @route(
        "/mail/track/<string:model>/<int:record_id>/<int:message_id>/<int:mail_id>/<string:token>/blank.gif",
        type="http",
        auth="public",
        cors="*",
    )
    def track_quotation_mail_open(
        self, model, record_id, message_id, mail_id, token
    ):
        """Email tracking."""
        if not tools.consteq(
            token,
            tools.hmac(
                request.env(su=True), "email_tracker-mail_mail-open", mail_id
            ),
        ):
            raise BadRequest()

        self.set_mail_opened(model, record_id, message_id, mail_id)

        response = werkzeug.wrappers.Response()
        response.mimetype = "image/gif"
        response.data = base64.b64decode(
            b"R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
        )
        response.cache_control.no_store = True

        return response

    def set_mail_opened(self, model, record_id, message_id, mail_id):
        odoobot = request.env.ref("base.partner_root")
        record = request.env[model].sudo().browse(record_id)
        mail = request.env["mail.mail"].sudo().browse(mail_id)
        message_id = request.env["mail.message"].sudo().browse(message_id)
        if message_id.exists():
            # Logs email opened message
            body = """
                {} opened: {}<br/>
                Opened on {}.
                """.format(
                record.name,
                message_id.subject or mail.subject,
                datetime.now().strftime("%m/%d/%Y %I:%M %p").upper(),
            )

            record.message_post(
                body=Markup(body),
                author_id=odoobot.id,
                email_open_origin_message_id=message_id.id,
            )

            # Send recipient email open notification
            notify_email_open = (
                request.env["ir.config_parameter"]
                .sudo()
                .get_param("mail.open.notification")
            )
            if (
                notify_email_open
                and hasattr(record, "user_id")
                and record.user_id.partner_id
            ):
                record.message_notify(
                    partner_ids=[record.user_id.partner_id.id],
                    model=model,
                    res_id=record_id,
                    body=body,
                    subject="Mail Opened",
                    author_id=odoobot.id,
                    email_open_origin_message_id=message_id.id,
                )
