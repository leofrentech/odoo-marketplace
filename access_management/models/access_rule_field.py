from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccessRuleField(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _name = "access.rule.field"
    _description = "Easy Access Rule Field Access"

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
        help="Model whose views show the field.",
    )
    field_id = fields.Many2one(
        "ir.model.fields",
        "Field",
        required=True,
        ondelete="cascade",
        help="Field to change in the views of the model.",
    )
    access = fields.Selection(
        [
            ("readonly", "Read-only"),
            ("required", "Required"),
            ("invisible", "Hidden"),
        ],
        string="Access",
        required=True,
        help="How the views show the field. The views only change: use Model "
        "Access to refuse writing the records. Hiding a required field "
        "prevents creating records from its form.",
    )
    used_field_ids = fields.Many2many(
        "ir.model.fields", compute="_compute_used_field_ids"
    )

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    @api.depends("rule_id.field_access_ids.field_id")
    def _compute_used_field_ids(self):
        for line in self:
            line.used_field_ids = line.rule_id.field_access_ids.field_id

    # ------------------------------------------------------------------
    # 5. SELECTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 6. CONSTRAINS METHODS AND ONCHANGE METHODS
    # ------------------------------------------------------------------

    @api.constrains("model_id", "field_id")
    def _check_field_id(self):
        for line in self:
            if line.field_id.model_id != line.model_id:
                raise ValidationError(
                    self.env._(
                        "The field %(field)s doesn't belong to %(model)s.",
                        field=line.field_id.field_description,
                        model=line.model_id.name,
                    )
                )

    @api.onchange("model_id")
    def _onchange_model_id(self):
        if self.field_id.model_id != self.model_id:
            self.field_id = False

    # ------------------------------------------------------------------
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------
