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

    @api.depends(
        "view_ids.view_mode", "view_mode", "view_id.type", "view_id.rule_ids"
    )
    def _compute_views(self):
        result = super(IrActionsActWindow, self)._compute_views()
        Rule = self.env["access.rule"]
        for act in self:
            # Views in the window action (set through default compute method)
            views = {key: value for value, key in act.views}

            # If the specific view_id is provided in the views,
            # then check that specific view for restriction
            # otherwise restrict by view type
            model_rules = Rule.get_model_rules(model=act.res_model)
            for restricted_view in model_rules.restrict_view_ids:
                if (not views[restricted_view.type]) or (
                    views[restricted_view.type]
                    and views[restricted_view.type] == restricted_view.id
                ):
                    views.pop(restricted_view.type, False)

            # Only update views, if any are restricted
            if len(views) != len(act.views):
                act.views = [(v, k) for k, v in views.items()]

        return result

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
