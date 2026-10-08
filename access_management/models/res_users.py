from odoo import api, fields, models
from odoo.http import request


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
        user = self or self.env.user
        AccessRule = self.env["access.rule"].with_user(user).with_context(
            allowed_company_ids=user._get_active_company_ids()
        )
        # sudo: users are hidden menus by rules they cannot read; the domain
        # limits the search to their own rules.
        rules = AccessRule.sudo().search(AccessRule._get_user_rules_domain())
        return rules.hide_menu_ids

    def _get_active_company_ids(self):
        """Companies the user works in, also for requests without context.

        The webclient loads its menus with a plain HTTP request, which only
        carries the selected companies in the ``cids`` cookie; without it,
        Odoo would apply the rules of all the user's companies.
        """
        self.ensure_one()
        if self.env.context.get("allowed_company_ids") or not request:
            return self.with_user(self).env.companies.ids
        user_company_ids = self._get_company_ids()
        cids = request.cookies.get("cids", "").replace(",", "-").split("-")
        company_ids = [
            int(cid) for cid in cids
            if cid.isdigit() and int(cid) in user_company_ids
        ]
        # Same fallback as the webclient: the user's default company
        return company_ids or [self.company_id.id]

    @api.model
    def check_export_enable(self, model):
        if not self.env.user.has_group("base.group_allow_export"):
            return False
        model_rules = self.env["access.rule"]._get_model_rules(model)
        return not any(model_rules.mapped("restrict_export"))
