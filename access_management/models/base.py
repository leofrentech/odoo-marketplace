from lxml import etree

from odoo import api, models
from odoo.http import request


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
        result = super(Base, self).get_views(views, options)

        # Check if any rule is defined for readonly
        model_rules = self.env["access.rule"].get_model_rules(self._name)
        if any(model_rules.mapped("readonly")):
            for view_type, view in result["views"].items():
                arch = etree.fromstring(view.get("arch"))
                arch.attrib.update(
                    {"edit": "False", "create": "False", "delete": "False"}
                )
                view["arch"] = etree.tostring(arch)

        # Restrict debug mode
        if any(model_rules.mapped("restrict_debug_mode")):
            request.session.debug = ""

        # Remove restricted views
        if model_rules.sudo().restrict_view_ids:
            view_dict = {key: value for value, key in views}
            for restricted_view in model_rules.sudo().restrict_view_ids:
                result["views"].pop(restricted_view.type, False)
                view_dict.pop(restricted_view.type, False)

            views = [(v, k) for k, v in view_dict.items()]

        return result

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super(Base, self)._get_view(view_id, view_type, **options)

        # Fetch rules for the model
        model_rules = (
            self.env["access.rule"].get_model_rules(self._name).sudo()
        )
        if model_rules and model_rules.field_access_ids:
            field_access_map = dict(
                [
                    (fa.field_id.name, fa.access)
                    for fa in model_rules.field_access_ids
                ]
            )
            # Make fields readonly/hidden
            for field, access in field_access_map.items():
                for f in arch.xpath(f"//field[@name='{field}']"):
                    if view_type == "list" and access == "invisible":
                        access = "column_invisible"

                    f.attrib[access] = "1"

        # Check if any button is hidden
        nodes_to_hide = (
            model_rules.hide_link_ids
            | model_rules.hide_page_ids
            | model_rules.hide_button_ids
        ).view_node_id
        for node in nodes_to_hide:
            if node.node_option == "button":
                xpath = f"//button[@name='{node.name}']"
                
                for button in arch.xpath(xpath):
                    button.attrib["invisible"] = "1"
            elif node.node_option == "page":
                for page in arch.xpath(f"//page[@name='{node.name}']"):
                    page.attrib["invisible"] = "1"
            elif node.node_option == "link":
                for link in arch.xpath(f"//"):
                    link.attrib["invisible"] = "1"

        if view_type in [
            "kanban",
            "list",
        ] and not self.env.user.check_export_enable(self._name):
            for list in arch.xpath("//list"):
                list.attrib["export_xlsx"] = "0"

        # Hide Import records
        if self.env.user.check_import_enabled(self._name):
            arch.attrib["import"] = "0"

        return arch, view
