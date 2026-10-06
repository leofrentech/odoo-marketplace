from odoo import api, fields, models, tools
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL, config
from odoo.tools.safe_eval import safe_eval

from .access_rule import is_protected_model


class IrRule(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "ir.rule"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    # A record rule with an access rule is a "Model Access" line: its perm_*
    # checkboxes are permissions (unticked operations are refused) and its
    # domain limits the ticked operations, instead of the standard meaning.
    # Allow Model Access lines without any operation: they refuse them all
    _no_access_rights = models.Constraint(
        "CHECK (rule_id IS NOT NULL OR perm_read OR perm_write OR perm_create "
        "OR perm_unlink)",
        "Rule must have at least one checked access right!",
    )

    rule_id = fields.Many2one("access.rule", "Rule", ondelete="cascade")
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

    @api.constrains("model_id", "rule_id")
    def _check_access_rule_model(self):
        for rule in self.filtered("rule_id"):
            if is_protected_model(rule.model_id.model):
                raise ValidationError(
                    self.env._(
                        "The access of the model %(model)s can't be managed "
                        "by an access rule.",
                        model=rule.model_id.name,
                    )
                )

    # The Model Access checkboxes are permissions: an operation needs read.

    @api.onchange("perm_read")
    def _onchange_perm_read(self):
        for rule in self._model_access_lines():
            if not rule.perm_read:
                rule.update({
                    "perm_write": False,
                    "perm_create": False,
                    "perm_unlink": False,
                })

    @api.onchange("perm_write", "perm_create", "perm_unlink")
    def _onchange_perm_write_create_unlink(self):
        for rule in self._model_access_lines():
            if rule.perm_write or rule.perm_create or rule.perm_unlink:
                rule.perm_read = True

    # ------------------------------------------------------------------
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        rules = super().create(vals_list)
        rules._check_access_rule_scope()
        return rules

    def write(self, vals):
        self._check_access_rule_scope()
        res = super().write(vals)
        self._check_access_rule_scope()
        return res

    def unlink(self):
        self._check_access_rule_scope()
        return super().unlink()

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    def _model_access_lines(self):
        if self.env.context.get("access_management_model_access"):
            return self
        return self.filtered("rule_id")

    def _check_access_rule_scope(self):
        """Users granted ir.rule access by this module may only manage the
        Model Access lines, not the other record rules."""
        if self.env.su or self.env.user.has_group("base.group_erp_manager"):
            return
        if any(not rule.rule_id for rule in self):
            raise AccessError(
                self.env._("You can only manage the record rules of an access rule.")
            )

    def _get_rules(self, model_name, mode="read"):
        """Leave out the Model Access lines: `_compute_domain` applies them
        with their own meaning."""
        rules = super()._get_rules(model_name, mode)
        if not rules:
            return rules

        self.flush_model(["rule_id"])
        model_access_line_ids = self.env.execute_query(SQL(
            "SELECT id FROM ir_rule WHERE id IN %s AND rule_id IS NOT NULL",
            tuple(rules.ids),
        ))
        return rules - self.browse(line_id for line_id, in model_access_line_ids)

    @api.model
    @tools.conditional(
        "xml" not in config["dev_mode"],
        tools.ormcache(
            "self.env.uid",
            "self.env.su",
            "model_name",
            "mode",
            "tuple(self._compute_domain_context_values())",
        ),
    )
    def _compute_domain(self, model_name, mode="read"):
        """Limit the operation to the domains of the Model Access lines that
        allow it, each combined with the standard record rules unless the
        line ignores them."""
        domain = super()._compute_domain(model_name, mode)
        lines = self.env["access.rule"]._get_model_access_lines(model_name)
        if not lines:
            return domain

        eval_context = self._eval_context()

        def line_domain(line):
            if not line.domain:
                return Domain.TRUE
            return Domain(safe_eval(line.domain, eval_context))

        line_domains = [
            line_domain(line) & (Domain.TRUE if line.ignore_standard_rules else domain)
            for line in lines
            if line.allows(mode)
        ]
        # No line allows the operation: the ACL check refuses it already
        return Domain.OR(line_domains).optimize(self.env[model_name])

    def _make_access_error(self, operation, records):
        error = super()._make_access_error(operation, records)
        lines = self.env["access.rule"]._get_model_access_lines(records._name)
        if not lines:
            return error

        rule_names = ", ".join(sorted({line.rule_name for line in lines}))
        message = self.env._(
            "%(error)s\n\nThese records are limited by the access rule: %(rules)s",
            error=error.args[0],
            rules=rule_names,
        )
        access_error = AccessError(message)
        if context := getattr(error, "context", None):
            access_error.context = context
        return access_error
