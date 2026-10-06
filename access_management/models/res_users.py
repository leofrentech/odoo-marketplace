from odoo import api, fields, models


class ResUsers(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "res.users"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    access_rule_ids = fields.Many2many(
        "access.rule",
        "ear_user_rel",
        "user_id",
        "ear_id",
        string="Easy Access Rules",
    )

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

    def _get_hidden_menus(self):
        """Menus hidden from the current user in the companies they work in."""
        AccessRule = self.env["access.rule"].with_user(self or self.env.user)
        # sudo: users are hidden menus by rules they cannot read; the domain
        # limits the search to their own rules.
        rules = AccessRule.sudo().search(AccessRule._get_user_rules_domain())
        return rules.hide_menu_ids

    @api.model
    def check_export_enable(self, model):
        if not self.env.user.has_group("base.group_allow_export"):
            return False
        model_rules = self.env["access.rule"].get_model_rules(model)
        return not any(model_rules.mapped("restrict_export"))
