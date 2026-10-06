from odoo import api, models


class IrActionsActWindow(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "ir.actions.act_window"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    @api.depends("view_ids.view_mode", "view_mode", "view_id.type")
    def _compute_views(self):
        super()._compute_views()
        restricted_views_by_model = {}
        for action in self:
            res_model = action.res_model
            if not res_model:
                continue
            if res_model not in restricted_views_by_model:
                model_rules = self.env["access.rule"].get_model_rules(res_model)
                restricted_views_by_model[res_model] = (
                    model_rules.restricted_view_ids.filtered(
                        lambda line: line.model == res_model
                    ).view_id
                )
            restricted_views = restricted_views_by_model[res_model]
            if not restricted_views:
                continue

            # A restricted view hides its type when the action uses the
            # default view of that type or that view specifically
            views = [
                (view_id, view_type)
                for view_id, view_type in action.views
                if not any(
                    view.type == view_type and view_id in (False, view.id)
                    for view in restricted_views
                )
            ]
            if len(views) != len(action.views):
                action.views = views

    # ------------------------------------------------------------------
    # 5. SELECTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 6. CONSTRAINS METHODS AND ONCHANGE METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------
