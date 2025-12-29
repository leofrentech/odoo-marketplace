from odoo import api, models, tools


class IrUiMenu(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "ir.ui.menu"

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
    @tools.ormcache(
        "self.env.uid",
        "debug",
        "self.env.lang",
        "self.env.user.access_rule_update_at",
    )
    def load_menus(self, debug):
        return super(IrUiMenu, self).load_menus(debug=debug)

    def _load_menus_blacklist(self):
        """
        Override to extend the blacklist menus list with hidden menus of user's access rule.
        """
        blacklist_menus = super(IrUiMenu, self)._load_menus_blacklist()

        hidden_menus = self.env.user._get_hidden_menus()
        if hidden_menus:
            blacklist_menus.extend(hidden_menus.ids)

        return blacklist_menus
