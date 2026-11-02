from odoo.http import Controller, request, route


class AccessManagementController(Controller):
    @route("/restrict_debug/check", type="json", auth="user")
    def check_debug_restriction(self, model_name):
        if model_name not in request.env:
            return False
        rules = request.env["access.rule"]._get_model_rules(model_name)
        return any(rules.mapped("restrict_debug_mode"))

    @route("/check_restricted_views", type="json", auth="user")
    def check_restricted_views(self, model):
        """Return the ``[view_id, view_type]`` of the views the current user
        can't open on ``model``."""
        if model not in request.env:
            return []
        rules = request.env["access.rule"]._get_model_rules(model)
        views = rules.restricted_view_ids.filtered(
            lambda line: line.model == model
        ).view_id
        # The web client calls the "tree" views "list" views
        return [
            [view.id, "list" if view.type == "tree" else view.type] for view in views
        ]
