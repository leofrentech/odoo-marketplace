from odoo import _, api, models
from odoo.exceptions import AccessError


class IrModelAccess(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "ir.model.access"

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

    @api.model
    def check(self, model, mode="read", raise_exception=True):
        """The Model Access lines of the user's access rules decide the
        operation on their model: granted when a line ticks it, even if the
        user's groups don't, and refused otherwise."""
        if self.env.su:
            return True

        lines = self.env["access.rule"]._get_model_access_lines(model)
        if not lines:
            return super().check(model, mode, raise_exception)

        if any(line.allows(mode) for line in lines):
            return True
        if raise_exception:
            raise self._make_access_rule_error(model, mode, lines) from None
        return False

    def _make_access_rule_error(self, model, mode, lines):
        """Error of an operation refused by the Model Access lines."""
        operations = {
            "read": _("read"),
            "write": _("edit"),
            "create": _("create"),
            "unlink": _("delete"),
        }
        return AccessError(
            _(
                "You are not allowed to %(operation)s %(document_kind)s "
                "(%(document_model)s) records.\n\n"
                "The access rule %(rules)s does not allow it. Contact your "
                "administrator if you need this access.",
                operation=operations[mode],
                document_kind=self.env["ir.model"]._get(model).name or model,
                document_model=model,
                rules=", ".join(sorted({line.rule_name for line in lines})),
            )
        )
