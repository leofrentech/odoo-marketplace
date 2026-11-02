from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccessRuleHiddenReport(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _name = "access.rule.hidden.report"
    _description = "Easy Access Rule Hidden Report"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    rule_id = fields.Many2one("access.rule", "Rule", ondelete="cascade", required=True)
    model_id = fields.Many2one(
        "ir.model",
        "Model",
        required=True,
        ondelete="cascade",
        help="Model whose Print menu shows the report.",
    )
    hide_all_reports = fields.Boolean(
        "Hide All Reports",
        help="Hide the Print menu of the model, with all its reports.",
    )
    report_id = fields.Many2one(
        "ir.actions.report",
        "Report to Hide",
        ondelete="cascade",
        help="Hide only this report from the Print menu of the model.",
    )

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 5. SELECTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 6. CONSTRAINTS METHODS AND ONCHANGE METHODS
    # ------------------------------------------------------------------

    @api.constrains("model_id", "hide_all_reports", "report_id")
    def _check_report_id(self):
        for line in self:
            if line.hide_all_reports:
                continue
            if not line.report_id:
                raise ValidationError(
                    self.env._(
                        "Select the report to hide for %(model)s, or hide all "
                        "its reports.",
                        model=line.model_id.name,
                    )
                )
            if line.report_id.model != line.model_id.model:
                raise ValidationError(
                    self.env._(
                        "The report %(report)s doesn't belong to %(model)s.",
                        report=line.report_id.name,
                        model=line.model_id.name,
                    )
                )

    @api.onchange("hide_all_reports", "model_id")
    def _onchange_hide_all_reports(self):
        for line in self:
            if line.hide_all_reports or line.report_id.model != line.model_id.model:
                line.report_id = False

    # ------------------------------------------------------------------
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    # Hiding all the reports leaves no report to pick

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("hide_all_reports"):
                vals["report_id"] = False
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("hide_all_reports"):
            vals = {**vals, "report_id": False}
        res = super().write(vals)
        if vals.get("report_id"):
            self.filtered("hide_all_reports").report_id = False
        return res

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------
