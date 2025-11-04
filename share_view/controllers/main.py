import json


from odoo import http
from odoo.http import request
import urllib.parse


class ShareViewController(http.Controller):

    @http.route("/share/view/<int:share_id>", type="http", auth="user")
    def open_shared_view(self, share_id, **kw):
        shared = request.env["shared.view.state"].sudo().browse(share_id)
        if not shared.exists():
            return request.not_found()

        action = shared.action_id.read()[0]
        action.update(
            {
                "domain": eval(shared.domain or "[]"),
                "context": eval(shared.context or "{}"),
            }
        )
        params = {
            "action": shared.action_id.id,
            "model": shared.model,
            "view_type": (shared.view_mode or "list").split(",")[0],
            "domain": shared.domain or "[]",
            "context": shared.context or "{}",
        }
        # return request.env["ir.actions.act_window"]._for_xml_id(
        #     action["xml_id"]
        # )
        return request.render(
            "share_view.shared_view_state_load",
            {"action_json": json.dumps(action, default=str)},
        )
        # query = "&".join(
        #     f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()
        # )
        # url = f"/web#{query}"
        # return request.redirect(url)
