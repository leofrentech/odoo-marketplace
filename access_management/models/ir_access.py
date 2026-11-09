from odoo import models
from odoo.exceptions import AccessError


class IrAccess(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "ir.access"

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

    def _make_model_access_error(self, model_name, operation):
        """Name the access rules refusing the operation, rather than the
        groups allowing it: the groups don't decide for these users."""
        lines = self.env["access.rule"]._get_model_access_lines(model_name)
        if not lines or any(line.allows(operation) for line in lines):
            return super()._make_model_access_error(model_name, operation)

        operations = {
            "read": self.env._("read"),
            "write": self.env._("edit"),
            "create": self.env._("create"),
            "unlink": self.env._("delete"),
        }
        return AccessError(
            self.env._(
                "You are not allowed to %(operation)s %(document_kind)s "
                "(%(document_model)s) records.\n\n"
                "The access rule %(rules)s does not allow it. Contact your "
                "administrator if you need this access.",
                operation=operations[operation],
                document_kind=self.env["ir.model"]._get(model_name).name or model_name,
                document_model=model_name,
                rules=sorted({line.rule_name for line in lines}),
            ),
        )

    def _make_record_access_error(self, records, operation):
        error = super()._make_record_access_error(records, operation)
        lines = self.env["access.rule"]._get_model_access_lines(records._name)
        if not lines:
            return error

        access_error = AccessError(
            self.env._(
                "%(error)s\n\nThese records are limited by the access rule: %(rules)s",
                error=error.args[0],
                rules=sorted({line.rule_name for line in lines}),
            ),
        )
        if context := getattr(error, "context", None):
            access_error.context = context
        return access_error
