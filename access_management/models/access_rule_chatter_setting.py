from odoo import fields, models


class AccessRuleChatterSetting(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _name = "access.rule.chatter.setting"
    _description = "Easy Access Rule Chatter Setting"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    rule_id = fields.Many2one("access.rule", "Rule", ondelete="cascade", required=True)
    model_id = fields.Many2one(
        "ir.model",
        "Model",
        required=True,
        ondelete="cascade",
        help="Model whose forms show the chatter.",
    )
    hide_chatter = fields.Boolean("Hide Chatter", help="Hide the whole chatter.")
    hide_send_message = fields.Boolean(
        "Hide Send Message", help="Hide the Send message button."
    )
    hide_lognote = fields.Boolean("Hide Log Note", help="Hide the Log note button.")
    hide_activity = fields.Boolean(
        "Hide Activities", help="Hide the Activities button."
    )
    hide_attachments = fields.Boolean(
        "Hide Attachments", help="Hide the attachment button."
    )
    hide_followers = fields.Boolean("Hide Followers", help="Hide the followers.")
    hide_search_message = fields.Boolean(
        "Hide Message Search", help="Hide the message search."
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
