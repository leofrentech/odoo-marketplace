from typing import NamedTuple

from odoo import api, fields, models, tools
from odoo.fields import Domain

# Models the Model Access lines can't target: restricting them breaks the
# login and the web client, granting them lets users escalate privileges.
PROTECTED_MODEL_PREFIXES = ("ir.", "res.users", "res.groups", "access.rule")
PROTECTED_MODELS = {
    "res.company",
    "field.access",
    "view.node",
    "access.hide.view.node",
}


def is_protected_model(model_name):
    return model_name in PROTECTED_MODELS or model_name.startswith(
        PROTECTED_MODEL_PREFIXES
    )


class ModelAccessLine(NamedTuple):
    """Immutable copy of a Model Access line, safe to keep in the ORM cache."""

    id: int
    rule_name: str
    domain: str
    ignore_standard_rules: bool
    perm_read: bool
    perm_write: bool
    perm_create: bool
    perm_unlink: bool

    def allows(self, mode):
        return getattr(self, f"perm_{mode}")


class AccessRule(models.Model):
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
    active = fields.Boolean("Active", default=True)
    company_ids = fields.Many2many(
        "res.company",
        "access_rule_company_rel",
        "rule_id",
        "company_id",
        string="Companies",
        default=lambda self: self.env.company,
        help="Apply the rule while the users work in one of these companies. "
        "Leave empty to apply it in all companies.",
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

    hide_report_btn = fields.Boolean(
        "Hide All Reports",
        help="Hide the Print menu, with all its reports, on every model.",
    )
    hidden_report_ids = fields.One2many(
        "access.rule.hidden.report", "rule_id", "Hidden Reports"
    )

    field_access_ids = fields.One2many("field.access", "rule_id", "Field Access")

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

    restricted_view_ids = fields.One2many(
        "access.rule.restricted.view", "rule_id", "Restricted Views"
    )

    chatter_setting_ids = fields.One2many(
        "access.rule.chatter.setting", "rule_id", "Chatter Settings"
    )

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

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

    # Menus, bindings and record rules are cached per user: drop the caches
    # whenever a rule changes so it applies immediately.

    @api.model_create_multi
    def create(self, vals_list):
        rules = super().create(vals_list)
        self.env.registry.clear_cache()
        return rules

    def write(self, vals):
        res = super().write(vals)
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    def action_toggle_active(self):
        self.ensure_one()
        self.write({"active": not self.active})

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    @api.model
    @tools.ormcache("self.env.uid", "model_name", "tuple(self.env.companies.ids)")
    def _get_model_access_lines(self, model_name):
        """Return the Model Access lines of the current user for ``model_name``.

        Cached, as the ACL check and the record rules call it constantly; the
        cache is cleared whenever an access rule or a record rule changes.
        """
        if not model_name or is_protected_model(model_name):
            return ()
        lines = self.get_model_rules(model_name).record_rule_ids.filtered(
            lambda line: line.model_id.model == model_name
        )
        return tuple(
            ModelAccessLine(
                id=line.id,
                rule_name=line.rule_id.name,
                domain=line.domain_force or "",
                ignore_standard_rules=line.ignore_standard_rules,
                perm_read=line.perm_read,
                perm_write=line.perm_write,
                perm_create=line.perm_create,
                perm_unlink=line.perm_unlink,
            )
            for line in lines
        )

    @api.model
    def _get_user_rules_domain(self):
        """Active rules of the current user, in the companies they work in."""
        return Domain.AND([
            [("user_ids", "in", self.env.uid), ("active", "=", True)],
            [
                "|",
                ("company_ids", "=", False),
                ("company_ids", "in", self.env.companies.ids),
            ],
        ])

    @api.model
    def get_model_rules(self, model):
        """Return the active rules of the current user that apply to ``model``.

        The rules are searched and returned as superuser: they restrict the
        current user whatever their rights on the configuration models.
        """
        domain = self._get_user_rules_domain()

        conditions = []
        if model_id := self.env["ir.model"]._get_id(model):
            conditions = [
                [(f"{field}.model_id", "=", model_id)]
                for field in (
                    "record_rule_ids",
                    "field_access_ids",
                    "hide_link_ids",
                    "hide_button_ids",
                    "hide_page_ids",
                    "restricted_view_ids",
                    "hidden_report_ids",
                    "chatter_setting_ids",
                )
            ]

        # Global conditions — these booleans apply to all models
        conditions += [
            [(field, "=", True)]
            for field in (
                "readonly",
                "restrict_debug_mode",
                "restrict_export",
                "restrict_import_records",
                "hide_report_btn",
                "hide_chatter",
                "hide_send_message",
                "hide_search_message",
                "hide_lognote",
                "hide_activity",
                "hide_attachments",
                "hide_followers",
            )
        ]

        # sudo: the rules restrict users who cannot read them; the domain
        # limits the search to the rules of the current user.
        return self.sudo().search(domain & Domain.OR(conditions))
