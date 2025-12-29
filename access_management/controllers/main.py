from odoo.http import request, route, Controller


class RestrictDebugController(Controller):
    @route("/restrict_debug/check", type="json", auth="user")
    def check_debug_restriction(self, model_name):
        rule = (
            request.env["access.rule"]
            .sudo()
            .search(
                [
                    ("model_id.model", "=", model_name),
                    ("user_ids", "in", request.env.user.ids),
                    ("restrict_debug_mode", "=", True),
                ],
                limit=1,
            )
        )
        return bool(rule)

    @route("/check_restricted_views", type="json", auth="user")
    def _check_restricted_views(self, model):
        model_rules = request.env["access.rule"].sudo().get_model_rules(model)
        restricted_views = model_rules.restrict_view_ids.sudo().mapped("type")

        return restricted_views
