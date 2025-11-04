from odoo import models, fields


class SharedViewState(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _name = "shared.view.state"
    _description = "Shared View State"
    _rec_name = "model"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    action_id = fields.Many2one("ir.actions.act_window", string="Action")
    model = fields.Char()
    view_mode = fields.Char()
    domain = fields.Text()
    context = fields.Text()
    sort = fields.Char()
    owner_id = fields.Many2one("res.users", default=lambda self: self.env.user)

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

    def action_copy_url(self):
        self.ensure_one()
        url = f"{self.get_base_url()}/share/view/{self.id}"
        # return an action with info for the client
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Share Link",
                "message": url,
                "sticky": False,
            },
        }

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------
