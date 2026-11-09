from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools.safe_eval import safe_eval

from .access_rule import is_protected_model


class AccessRuleModelAccess(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _name = "access.rule.model.access"
    _description = "Easy Access Rule Model Access"
    _order = "access_rule_id, id"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    # A Model Access line decides the operations of its rule's users on its
    # model: its checkboxes are permissions (unticked operations are refused)
    # and its domain limits the ticked operations.
    access_rule_id = fields.Many2one(
        "access.rule",
        "Access Rule",
        required=True,
        index=True,
        ondelete="cascade",
    )
    name = fields.Char("Name", required=True)
    model_id = fields.Many2one(
        "ir.model",
        "Model",
        required=True,
        index=True,
        ondelete="cascade",
    )
    domain_force = fields.Char(
        "Domain",
        help="Records the ticked operations are allowed on. Leave empty to "
        "allow all records.",
    )
    perm_read = fields.Boolean("Read", default=True)
    perm_write = fields.Boolean("Write", default=True)
    perm_create = fields.Boolean("Create", default=True)
    perm_unlink = fields.Boolean("Delete", default=True)
    ignore_standard_rules = fields.Boolean(
        "Ignore Standard Rules",
        help="Apply only this line's domain, without Odoo's own record rules "
        "(e.g. multi-company or own documents only). Use with care: the users "
        "may then reach records of other companies.",
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

    @api.constrains("model_id")
    def _check_model_id(self):
        for line in self:
            if is_protected_model(line.model_id.model):
                raise ValidationError(
                    self.env._(
                        "The access of the model %(model)s can't be managed "
                        "by an access rule.",
                        model=line.model_id.name,
                    ),
                )

    @api.constrains("model_id", "domain_force")
    def _check_domain_force(self):
        eval_context = self.env["ir.access"]._eval_context()
        for line in self.filtered("domain_force"):
            if line.model_id.model not in self.env:
                continue
            try:
                domain = safe_eval_domain(line.domain_force, eval_context)
                domain.validate(self.env[line.model_id.model].sudo())
            except Exception as error:  # noqa: BLE001
                raise ValidationError(
                    self.env._(
                        "Invalid domain %(domain)s: %(error)s",
                        domain=line.domain_force,
                        error=error,
                    ),
                ) from error

    # The checkboxes are permissions: an operation needs read.

    @api.onchange("perm_read")
    def _onchange_perm_read(self):
        for line in self:
            if not line.perm_read:
                line.update({
                    "perm_write": False,
                    "perm_create": False,
                    "perm_unlink": False,
                })

    @api.onchange("perm_write", "perm_create", "perm_unlink")
    def _onchange_perm_write_create_unlink(self):
        for line in self:
            if line.perm_write or line.perm_create or line.perm_unlink:
                line.perm_read = True

    # ------------------------------------------------------------------
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    # The access domains are cached per user: drop the caches whenever a line
    # changes so it applies immediately.

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        self.env["access.rule"]._invalidate_access_caches()
        return lines

    def write(self, vals):
        res = super().write(vals)
        self.env["access.rule"]._invalidate_access_caches()
        return res

    def unlink(self):
        res = super().unlink()
        self.env["access.rule"]._invalidate_access_caches()
        return res

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------


def safe_eval_domain(domain, eval_context):
    """Evaluate the text of a Model Access domain."""
    return Domain(safe_eval(domain, eval_context)) if domain else Domain.TRUE
