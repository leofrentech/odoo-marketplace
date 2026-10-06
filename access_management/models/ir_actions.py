from odoo import models
from odoo.tools import frozendict


class IrActions(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "ir.actions.actions"

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

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    def _get_bindings(self, model_name):
        """Remove the reports hidden by the current user's access rules.

        Filtered after the cached super call, as the result depends on the user.
        """
        result = super()._get_bindings(model_name)
        if not result.get("report"):
            return result

        access_rules = self.env["access.rule"].get_model_rules(model_name)
        hidden_report_lines = access_rules.hidden_report_ids.filtered(
            lambda line: line.model_id.model == model_name
        )
        result = dict(result)
        if any(access_rules.mapped("hide_report_btn")) or any(
            hidden_report_lines.mapped("hide_report_btn")
        ):
            del result["report"]
        elif hidden_report_ids := set(hidden_report_lines.report_id.ids):
            result["report"] = [
                report
                for report in result["report"]
                if report["id"] not in hidden_report_ids
            ]

        return frozendict(result)
