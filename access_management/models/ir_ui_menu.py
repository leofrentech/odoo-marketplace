from odoo import api, models


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

    # The menus are cached per user, while the access rules also depend on
    # the user's companies: the hidden menus are removed after the cache.

    @api.model
    def get_user_roots(self):
        roots = super().get_user_roots()
        if self.env.context.get("access_management_all_menus"):
            return roots
        return roots - self.env.user._get_hidden_menus()

    @api.model
    def load_menus_root(self):
        menu_root = super(
            IrUiMenu, self.with_context(access_management_all_menus=True)
        ).load_menus_root()
        hidden_menu_ids = set(self.env.user._get_hidden_menus().ids)
        if not hidden_menu_ids:
            return menu_root
        return {
            **menu_root,
            "children": [
                menu for menu in menu_root["children"]
                if menu["id"] not in hidden_menu_ids
            ],
            "all_menu_ids": [
                menu_id for menu_id in menu_root["all_menu_ids"]
                if menu_id not in hidden_menu_ids
            ],
        }

    @api.model
    def load_menus(self, debug):
        menus = super().load_menus(debug)
        hidden_menu_ids = self._get_hidden_menu_tree_ids(menus)
        if not hidden_menu_ids:
            return menus
        # Copy rather than alter the cached menus
        return {
            key: {
                **menu,
                "children": [
                    child for child in menu["children"]
                    if child not in hidden_menu_ids
                ],
            }
            for key, menu in menus.items()
            if key not in hidden_menu_ids
        }

    def _get_hidden_menu_tree_ids(self, menus):
        """Ids of the user's hidden menus and of their sub-menus in ``menus``."""
        hidden_menu_ids = set()
        to_hide = [
            menu_id
            for menu_id in self.env.user._get_hidden_menus().ids
            if menu_id in menus
        ]
        while to_hide:
            menu_id = to_hide.pop()
            if menu_id not in hidden_menu_ids:
                hidden_menu_ids.add(menu_id)
                to_hide.extend(menus[menu_id]["children"])
        return hidden_menu_ids
