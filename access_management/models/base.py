from lxml import etree

from odoo import api, models
from odoo.addons.base.models.ir_access import IN_SELECTION
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.http import request
from odoo.tools.safe_eval import safe_eval

RESTRICTED_VIEW_TYPES = ("form", "list", "kanban")

# Nodes of the view itself, not of the inline sub-views of its x2many fields
NODE_XPATHS = {
    "field": "//field[@name=$name][not(ancestor::field)]",
    "button": "//button[@name=$name][not(ancestor::field)]",
    "link": "//a[@name=$name][not(ancestor::field)]",
    "page": "//page[@name=$name][not(ancestor::field)] | //app[@name=$name]",
    "page_string": (
        "//page[@string=$name][not(ancestor::field)] | //app[@string=$name]"
    ),
}


class Base(models.AbstractModel):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "base"

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
    @api.ormcache("operation", "self.env._access_context")
    def _access_domain(self, operation):
        """Let the Model Access lines of the user's access rules decide the
        operation: it is allowed on the domains of the lines ticking it, even
        if the user's groups don't allow it, and refused otherwise.

        Each line's domain is combined with Odoo's own access domain, unless
        the line ignores the standard rules.
        """
        domain = super()._access_domain(operation)
        lines = self.env["access.rule"]._get_model_access_lines(self._name)
        if not lines:
            return domain

        allowing_lines = [line for line in lines if line.allows(operation)]
        if not allowing_lines:
            return Domain.FALSE

        IrAccess = self.env["ir.access"]
        eval_context = IrAccess._eval_context()
        standard_domain = self._access_management_standard_domain(operation)
        return Domain.OR(
            (Domain(safe_eval(line.domain, eval_context)) if line.domain else Domain.TRUE)
            & (Domain.TRUE if line.ignore_standard_rules else standard_domain)
            for line in allowing_lines
        )

    def _access_management_standard_domain(self, operation):
        """Odoo's own access domain of ``operation``, for a Model Access line
        granting it.

        Like ``_access_domain``, without requiring a permission of the user's
        groups: the line grants the operation. When the groups do grant it,
        their domains (e.g. own documents only) still limit it, as do the
        restrictions applying to everyone (e.g. multi-company).
        """
        operations = IN_SELECTION[operation]
        IrAccess = self.env["ir.access"]
        group_ids = set(self.env.user._get_group_ids())
        permissions, restrictions = [], []
        eval_context = None

        if self._check_inherits_access:
            for parent_model_name, parent_field_name in self._inherits.items():
                parent_domain = self.env[parent_model_name]._access_domain(operation)
                restrictions.append(Domain(parent_field_name, "any", parent_domain))

        for access in IrAccess._get_all_access().get(self._name, ()):
            if access.operation not in operations:
                continue
            if access.group_id and access.group_id not in group_ids:
                continue
            access_domain = access.domain
            if not isinstance(access_domain, Domain):
                if eval_context is None:
                    eval_context = IrAccess._eval_context()
                access_domain = Domain(safe_eval(access_domain, eval_context))
            if access.group_id:
                permissions.append(access_domain)
            else:
                restrictions.append(access_domain)

        permission_domain = Domain.OR(permissions) if permissions else Domain.TRUE
        return permission_domain & Domain.AND(restrictions)

    def export_data(self, fields_to_export):
        if rules := self._get_access_rules_setting("restrict_export"):
            raise AccessError(
                self.env._(
                    "You are not allowed to export %(model)s records: the access "
                    "rule %(rules)s restricts the export.",
                    model=self._description,
                    rules=", ".join(rules.mapped("name")),
                )
            )
        return super().export_data(fields_to_export)

    @api.model
    def load(self, fields, data):
        if rules := self._get_access_rules_setting("restrict_import_records"):
            raise AccessError(
                self.env._(
                    "You are not allowed to import %(model)s records: the access "
                    "rule %(rules)s restricts the import.",
                    model=self._description,
                    rules=", ".join(rules.mapped("name")),
                )
            )
        return super().load(fields, data)

    def _get_access_rules_setting(self, flag):
        """Access rules of the current user setting ``flag`` on this model."""
        if self.env.su:
            return self.env["access.rule"]
        return self.env["access.rule"]._get_model_rules(self._name).filtered(flag)

    @api.model
    @api.readonly
    def get_views(self, views, options=None):
        result = super().get_views(views, options)

        # Restrict debug mode
        model_rules = self.env["access.rule"]._get_model_rules(self._name)
        if request and any(model_rules.mapped("restrict_debug_mode")):
            request.session.debug = ""

        return result

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        # Applied here rather than in `_get_view`: its result is cached for
        # all users, while the access rules depend on the current user.
        result = super().get_view(view_id, view_type, **options)
        if view_type not in RESTRICTED_VIEW_TYPES:
            return result

        model_rules = self.env["access.rule"]._get_model_rules(self._name)
        if model_rules:
            arch = etree.fromstring(result["arch"])
            self._apply_access_rules(arch, view_type, model_rules)
            result["arch"] = etree.tostring(arch, encoding="unicode")

        return result

    def _apply_access_rules(self, arch, view_type, model_rules):
        """Hide or lock the nodes of ``arch`` according to ``model_rules``."""

        def on_model(lines):
            return lines.filtered(lambda line: line.model_id.model == self._name)

        # Make fields readonly/required/hidden
        for field_access in on_model(model_rules.field_access_ids):
            access = field_access.access
            if view_type == "list" and access == "invisible":
                access = "column_invisible"
            field_name = field_access.field_id.name
            for node in arch.xpath(NODE_XPATHS["field"], name=field_name):
                node.set(access, "1")

        # Hide buttons, pages and links
        view_nodes = on_model(
            model_rules.hide_link_ids
            | model_rules.hide_page_ids
            | model_rules.hide_button_ids
        ).view_node_id
        for view_node in view_nodes:
            if view_node.node_type == "page" and not view_node.name:
                xpath, name = NODE_XPATHS["page_string"], view_node.label
            else:
                xpath, name = NODE_XPATHS[view_node.node_type], view_node.name
            for node in arch.xpath(xpath, name=name):
                node.set("invisible", "1")

        if any(model_rules.mapped("restrict_export")):
            arch.set("export_xlsx", "0")
        if any(model_rules.mapped("restrict_import_records")):
            arch.set("import", "0")

        # Readonly rules lock the whole model. The Model Access lines need no
        # handling here: the access check hides the buttons of refused operations.
        if any(model_rules.mapped("readonly")):
            for attr in ("create", "edit", "delete"):
                arch.set(attr, "False")
