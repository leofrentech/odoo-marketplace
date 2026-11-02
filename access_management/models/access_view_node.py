from odoo import api, fields, models


class AccessViewNode(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _name = "access.view.node"
    _description = "Easy Access View Node"
    _rec_name = "label"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    # Catalog of the buttons, pages and links found in the views of the
    # models, filled when a model is picked on a rule.
    name = fields.Char(
        "Technical Name",
        help="Name of the button, page or link in the view: the method or "
        "action it runs, or the page name.",
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        index=True,
        ondelete="cascade",
        required=True,
    )
    node_type = fields.Selection(
        [("button", "Button"), ("page", "Page"), ("link", "Link")],
        string="Type",
        required=True,
    )
    label = fields.Char("Label", required=True, translate=True)
    button_type = fields.Selection(
        [("object", "Method"), ("action", "Action")],
        string="Button Type",
        help="Whether the button or link runs a method or opens an action.",
    )
    is_smart_button = fields.Boolean(
        "Smart Button", help="Button of the button box at the top of the form."
    )

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    @api.depends("label", "name", "node_type", "is_smart_button")
    def _compute_display_name(self):
        for node in self:
            name = node.label or ""
            if node.name:
                name = f"{name} ({node.name})"
                if node.is_smart_button and node.node_type == "button":
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
