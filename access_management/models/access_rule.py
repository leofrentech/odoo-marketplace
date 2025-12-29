from odoo import api, fields, models


class EasyAccessRole(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _name = "access.rule"
    _description = "Easy Access Rules"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    name = fields.Char("Name", required=True)
    model_id = fields.Many2one("ir.model", "Model")
    model = fields.Char(
        "Model", compute="_compute_model", search="_search_model"
    )
    active = fields.Boolean("Active", default=True)
    company_id = fields.Many2one(
        "res.company", "Company", default=lambda self: self.env.company.id
    )

    readonly = fields.Boolean("Read-only")

    hide_menu_domain = fields.Binary(
        string="Hide Menu Domain", compute="_compute_hide_menu_domain"
    )
    hide_menu_ids = fields.Many2many(
        "ir.ui.menu",
        "ear_ui_menu_rel",
        "ear_id",
        "menu_id",
        string="Hide Menus",
    )
    user_ids = fields.Many2many(
        "res.users", "ear_user_rel", "ear_id", "user_id", string="Users"
    )

    hide_report_btn = fields.Boolean("Hide Reports Button?")
    hide_report_ids = fields.Many2many(
        "ir.actions.report",
        "ear_hidden_report_rel",
        "ear_id",
        "hidden_report_id",
        string="Hidden Reports",
    )

    field_access_ids = fields.One2many(
        "field.access", "rule_id", "Field Access"
    )

    # Chatter
    hide_chatter = fields.Boolean("Hide Chatter?")
    hide_send_message = fields.Boolean("Hide Send Message?")
    hide_search_message = fields.Boolean("Hide Search Message?")
    hide_lognote = fields.Boolean("Hide Log Note?")
    hide_activity = fields.Boolean("Hide Activity")
    hide_attachments = fields.Boolean("Hide Attachments")
    hide_followers = fields.Boolean("Hide Followers?")

    restrict_import_records = fields.Boolean("Restrict Import Records?")

    restrict_debug_mode = fields.Boolean("Restrict Debug Mode?")
    hide_link_ids = fields.One2many(
        "access.hide.view.node", "access_rule_id", "Hide Links"
    )
    hide_button_ids = fields.One2many(
        "access.hide.view.node", "access_rule_btn_id", "Hide Buttons"
    )
    hide_page_ids = fields.One2many(
        "access.hide.view.node", "access_rule_page_id", "Hide Pages"
    )

    restrict_export = fields.Boolean("Restrict Export?")

    record_rule_ids = fields.One2many("ir.rule", "rule_id", "Model Rules")

    restrict_view_ids = fields.Many2many(
        comodel_name="ir.ui.view",
        relation="access_rule_restricted_views_rel",
        column1="access_rule_id",
        column2="view_id",
        string="Restricted Views",
        copy=False,
    )

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    @api.depends("model_id", "model_id.model")
    def _compute_model(self):
        for rule in self:
            rule.model = rule.model_id.sudo().model

    def _search_model(self, operator, value):
        return [("model_id.model", operator, value)]

    @api.depends("hide_menu_ids")
    def _compute_hide_menu_domain(self):
        for access in self:
            domain = []

            # Remove the hidden menus and it's childs
            if access.hide_menu_ids:
                menu_ids = access.hide_menu_ids.ids
                if access.hide_menu_ids.child_id:
                    menu_ids.extend(access.hide_menu_ids.child_id.ids)

                domain = [("id", "not in", menu_ids)]

            access.hide_menu_domain = domain

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

    def action_toggle_active(self):
        self.ensure_one()
        self.write({"active": not self.active})

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    def get_model_rules(self, model):
        return self.search(
            [("user_ids", "in", self.env.user.ids), ("model", "=", model)]
        )
