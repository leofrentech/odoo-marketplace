from odoo import api, fields, models


class ViewNode(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _name = "view.node"
    _description = "View Nodes"
    _rec_name = "node_string"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    name = fields.Char("Node Name")
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        index=True,
        ondelete="cascade",
        required=True,
    )
    node_option = fields.Selection(
        [("button", "Button"), ("page", "Page"), ("link", "Link")],
        string="Node Option",
        required=True,
    )
    node_string = fields.Char("Node String", required=True, translate=True)
    lang_code = fields.Char("Language Code")
    button_type = fields.Selection(
        [("object", "Object"), ("action", "Action")], string="Button Type"
    )
    is_smart_button = fields.Boolean("Smart Button")

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    @api.depends("node_string", "name", "node_option", "is_smart_button")
    def _compute_display_name(self):
        for node in self:
            name = node.node_string or ""
            if node.name:
                name = f"{name} ({node.name})"
                if node.is_smart_button and node.node_option == "button":
                    name = f"{name} (Smart Button)"
            node.display_name = name

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
