from typing import NamedTuple

from odoo import api, fields, models, tools
from odoo.fields import Domain

# Models the Model Access lines can't target: restricting them breaks the
# login and the web client, granting them lets users escalate privileges.
PROTECTED_MODEL_PREFIXES = (
    "ir.",
    "res.users",
    "res.groups",
    "access.rule",
    "access.view.node",
)
PROTECTED_MODELS = {"res.company"}


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
    _description = "Easy Access Rule"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    name = fields.Char("Name", required=True)
    active = fields.Boolean(
        "Active",
        default=True,
        help="Archive the rule to stop applying it without deleting it.",
    )
    user_ids = fields.Many2many(
        "res.users",
        "ear_user_rel",
        "ear_id",
        "user_id",
        string="Users",
        help="Users the rule applies to. Other users are not affected.",
    )
    company_ids = fields.Many2many(
        "res.company",
        "access_rule_company_rel",
        "rule_id",
        "company_id",
        string="Companies",
        default=lambda self: self.env.company,
        help="Apply the rule while the users work in one of these companies, "
        "also when it is one of several companies selected in the company "
        "switcher. Leave empty to apply it in all companies.",
    )

    readonly = fields.Boolean(
        "Read-only",
        help="Remove the New, Edit and Delete buttons from all the screens. "
        "Use Model Access to also refuse these operations on the server.",
    )
    restrict_debug_mode = fields.Boolean(
        "Restrict Debug Mode",
        help="Switch the developer mode off for the users of the rule.",
    )

    # Model Access
    model_access_ids = fields.One2many(
        "ir.rule",
        "access_rule_id",
        "Model Access",
        help="Operations allowed per model, enforced on the server.",
    )

    # Menus
    hide_menu_ids = fields.Many2many(
        "ir.ui.menu",
        "ear_ui_menu_rel",
        "ear_id",
        "menu_id",
        string="Hidden Menus",
        help="Menus removed from the users' navigation, with their sub-menus.",
    )
    hide_menu_domain = fields.Binary(
        string="Hidden Menus Domain", compute="_compute_hide_menu_domain"
    )

    # Views and fields
    restricted_view_ids = fields.One2many(
        "access.rule.restricted.view",
        "rule_id",
        "Restricted Views",
        help="Views the users can't switch to, e.g. the kanban view of a model.",
    )
    field_access_ids = fields.One2many(
        "access.rule.field",
        "rule_id",
        "Field Access",
        help="Fields made read-only, required or hidden in the views.",
    )
    hide_button_ids = fields.One2many(
        "access.rule.hidden.node",
        "button_rule_id",
        "Hidden Buttons",
        help="Buttons removed from the views of a model.",
    )
    hide_page_ids = fields.One2many(
        "access.rule.hidden.node",
        "page_rule_id",
        "Hidden Pages",
        help="Tabs removed from the forms of a model.",
    )
    hide_link_ids = fields.One2many(
        "access.rule.hidden.node",
        "link_rule_id",
        "Hidden Links",
        help="Clickable links (e.g. on dashboard cards) removed from a model's "
        "views.",
    )

    # Reports
    hidden_report_ids = fields.One2many(
        "access.rule.hidden.report",
        "rule_id",
        "Hidden Reports",
        help="Reports removed from the Print menu of a model.",
    )
    hide_all_reports = fields.Boolean(
        "Hide All Reports",
        help="Hide the Print menu, with all its reports, on every model.",
    )

    # Import and export
    restrict_import_records = fields.Boolean(
        "Restrict Import",
        help="Refuse importing records, on every model. The Import menu is "
        "removed too.",
    )
    restrict_export = fields.Boolean(
        "Restrict Export",
        help="Refuse exporting records, on every model. The Export menu is "
        "removed too.",
    )

    # Chatter
    chatter_setting_ids = fields.One2many(
        "access.rule.chatter.setting",
        "rule_id",
        "Chatter Settings",
        help="Chatter parts hidden on the forms of a model.",
    )
    hide_chatter = fields.Boolean(
        "Hide Chatter", help="Hide the whole chatter, on every model."
    )
    hide_send_message = fields.Boolean(
        "Hide Send Message",
        help="Hide the Send message button of the chatter, on every model.",
    )
    hide_lognote = fields.Boolean(
        "Hide Log Note",
        help="Hide the Log note button of the chatter, on every model.",
    )
    hide_activity = fields.Boolean(
        "Hide Activities",
        help="Hide the Activities button of the chatter, on every model.",
    )
    hide_attachments = fields.Boolean(
        "Hide Attachments",
        help="Hide the attachment button of the chatter, on every model.",
    )
    hide_followers = fields.Boolean(
        "Hide Followers",
        help="Hide the followers of the chatter, on every model.",
    )
    hide_search_message = fields.Boolean(
        "Hide Message Search",
        help="Hide the message search of the chatter, on every model.",
    )

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    @api.depends("hide_menu_ids")
    def _compute_hide_menu_domain(self):
        for rule in self:
            # Don't offer the menus already hidden, nor their sub-menus
            hidden_menus = rule.hide_menu_ids | rule.hide_menu_ids.child_id
            rule.hide_menu_domain = (
                [("id", "not in", hidden_menus.ids)] if hidden_menus else []
            )

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
        lines = self._get_model_rules(model_name).model_access_ids.filtered(
            lambda line: line.model_id.model == model_name
        )
        return tuple(
            ModelAccessLine(
                id=line.id,
                rule_name=line.access_rule_id.name,
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
    def _get_model_rules(self, model):
        """Return the active rules of the current user that apply to ``model``.

        The rules are searched and returned as superuser: they restrict the
        current user whatever their rights on the configuration models.
        """
        conditions = []
        if model_id := self.env["ir.model"]._get_id(model):
            conditions = [
                [(f"{field}.model_id", "=", model_id)]
                for field in (
                    "model_access_ids",
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
                "hide_all_reports",
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
        return self.sudo().search(
            self._get_user_rules_domain() & Domain.OR(conditions)
        )
