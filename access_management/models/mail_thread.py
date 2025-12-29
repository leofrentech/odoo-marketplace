from odoo import api, models


class MailThread(models.AbstractModel):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "mail.thread"

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
    def get_chatter_data(self):
        model_rules = self.env["access.rule"].get_model_rules(self._name)
        defaults = {
            "hideSendMessage": False,
            "hideLogNote": False,
            "hideActivity": False,
            "hideAttachments": False,
            "hideFollowers": False,
            "hideSearchMessage": False,
            "hideChatter": False,
        }

        if not model_rules:
            return defaults

        # Map Odoo field names to chatter data keys
        field_map = {
            "hide_send_message": "hideSendMessage",
            "hide_lognote": "hideLogNote",
            "hide_activity": "hideActivity",
            "hide_attachments": "hideAttachments",
            "hide_followers": "hideFollowers",
            "hide_search_message": "hideSearchMessage",
            "hide_chatter": "hideChatter",
        }
        # Collect all rule values once
        rule_data = model_rules.read(list(field_map.keys()))
        # If any rule has True for a given field, mark it hidden
        for field, key in field_map.items():
            if any(rule[field] for rule in rule_data):
                defaults[key] = True

        return defaults
