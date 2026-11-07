import base64
import logging

from werkzeug.exceptions import BadRequest

from odoo.http import Controller, request, route
from odoo.tools import consteq

_logger = logging.getLogger(__name__)

PIXEL_GIF = base64.b64decode(b"R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==")


class EmailTrackerController(Controller):

    def _pixel_response(self):
        return request.make_response(PIXEL_GIF, headers=[
            ("Content-Type", "image/gif"),
            ("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"),
            ("Pragma", "no-cache"),
        ])

    @route(
        "/email_tracker/open/<int:tracker_id>/<string:token>/blank.gif",
        type="http",
        auth="public",
        methods=["GET", "HEAD"],
        save_session=False,
    )
    def email_tracker_open(self, tracker_id, token, **kwargs):
        tracker = request.env["email.tracker.recipient"].sudo().browse(tracker_id)
        if not consteq(token, tracker._get_token()):
            raise BadRequest()

        # an internal user viewing a copy of the email (chatter, preview)
        # is not the recipient opening it
        user = request.env.user
        viewed_internally = not user._is_public() and not user.share

        if request.httprequest.method == "GET" and not viewed_internally and tracker.exists():
            try:
                with request.env.cr.savepoint():
                    tracker._register_open()
            except Exception:
                # never break the image for the recipient
                _logger.exception("Email tracker: could not register open of tracker %s", tracker_id)
        return self._pixel_response()

    @route(
        "/mail/track/<string:model>/<int:record_id>/<int:message_id>/<int:mail_id>/<string:token>/blank.gif",
        type="http",
        auth="public",
        methods=["GET", "HEAD"],
        save_session=False,
    )
    def email_tracker_open_legacy(self, **kwargs):
        """Pixels of emails sent with version 1.0 of the module. Their token
        does not sign the document, so opens cannot be trusted and are not
        logged; the image is still served to avoid broken images / 404s."""
        return self._pixel_response()
