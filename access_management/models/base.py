from lxml import etree

from odoo import api, models
from odoo.http import request

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
    @api.readonly
    def get_views(self, views, options=None):
        result = super().get_views(views, options)

        # Restrict debug mode
        model_rules = self.env["access.rule"].get_model_rules(self._name)
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

        model_rules = self.env["access.rule"].get_model_rules(self._name)
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
            if view_node.node_option == "page" and not view_node.name:
                xpath, name = NODE_XPATHS["page_string"], view_node.node_string
            else:
                xpath, name = NODE_XPATHS[view_node.node_option], view_node.name
            for node in arch.xpath(xpath, name=name):
                node.set("invisible", "1")

        if any(model_rules.mapped("restrict_export")):
            arch.set("export_xlsx", "0")
        if any(model_rules.mapped("restrict_import_records")):
            arch.set("import", "0")

        # Readonly rules lock the whole model. The Model Access lines need no
        # handling here: the ACL check hides the buttons of refused operations.
        if any(model_rules.mapped("readonly")):
            for attr in ("create", "edit", "delete"):
                arch.set(attr, "False")
