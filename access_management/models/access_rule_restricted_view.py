from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccessRuleRestrictedView(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _name = "access.rule.restricted.view"
    _description = "Easy Access Rule Restricted View"

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
        help="Model whose view is restricted.",
    )
    model = fields.Char("Model Name", related="model_id.model", store=True)
    view_id = fields.Many2one(
        "ir.ui.view",
        "View",
        required=True,
        ondelete="cascade",
        help="View the users can't open. Its view type (e.g. kanban) is "
        "removed from the actions showing it.",
    )

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 5. SELECTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 6. CONSTRAINS METHODS AND ONCHANGE METHODS
    # ------------------------------------------------------------------

    @api.constrains("model_id", "view_id")
    def _check_view_id(self):
        for line in self:
            if line.view_id.model != line.model:
                raise ValidationError(
                    self.env._(
                        "The view %(view)s doesn't belong to %(model)s.",
                        view=line.view_id.name,
                        model=line.model_id.name,
                    )
                )

    @api.onchange("model_id")
    def _onchange_model_id(self):
        if self.view_id.model != self.model_id.model:
            self.view_id = False

    # ------------------------------------------------------------------
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------
