from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    personalization_ids = fields.One2many(
        "sale.order.line.personalization", "order_id", string="Designs"
    )
    personalization_count = fields.Integer(compute="_compute_personalization_count")
    artwork_state = fields.Selection(
        [
            ("none", "No Artwork"),
            ("pending", "To Review"),
            ("rejected", "Rejected"),
            ("approved", "Approved"),
            ("ready", "Ready"),
        ],
        string="Artwork",
        compute="_compute_artwork_state",
        store=True,
        index=True,
    )

    @api.depends("personalization_ids")
    def _compute_personalization_count(self):
        for order in self:
            order.personalization_count = len(order.personalization_ids)

    @api.depends("personalization_ids.approval_state", "personalization_ids.is_customized")
    def _compute_artwork_state(self):
        for order in self:
            states = set(
                order.personalization_ids.filtered("is_customized").mapped("approval_state")
            )
            if not states:
                order.artwork_state = "none"
            elif "rejected" in states:
                order.artwork_state = "rejected"
            elif "pending" in states:
                order.artwork_state = "pending"
            elif "approved" in states:
                order.artwork_state = "approved"
            else:
                # No design of this order needs a review.
                order.artwork_state = "ready"

    # ------------------------------------------------------------------
    # Cart
    # ------------------------------------------------------------------

    def _cart_find_product_line(self, product_id, line_id=None, **kwargs):
        """A personalized item always gets its own line, and a regular
        "Add to cart" never merges into a personalized line.

        A given ``line_id`` (quantity changes from the cart page) is left alone.
        """
        if line_id:
            return super()._cart_find_product_line(product_id, line_id=line_id, **kwargs)
        if self.env.context.get("lf_personalized"):
            return self.env["sale.order.line"]
        lines = super()._cart_find_product_line(product_id, line_id=line_id, **kwargs)
        return lines.filtered(lambda line: not line.personalization_ids)

    def _cart_update(self, product_id, line_id=None, add_qty=0, set_qty=0, **kwargs):
        if not line_id and (add_qty or set_qty) and not self.env.context.get("lf_personalized"):
            template = self.env["product.product"].browse(product_id).product_tmpl_id
            if template.personalization_required and template._lf_is_personalizable():
                raise UserError(
                    self.env._("%s must be personalized: use the 'Personalize' button.",
                      template.display_name)
                )
        return super()._cart_update(
            product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, **kwargs
        )

    # ------------------------------------------------------------------
    # Artwork review
    # ------------------------------------------------------------------

    def action_confirm(self):
        result = super().action_confirm()
        self.filtered(lambda order: order.artwork_state == "pending")._lf_schedule_artwork_review()
        return result

    def _lf_artwork_activity_summary(self):
        return self.env._("Review customer artwork")

    def _lf_schedule_artwork_review(self):
        summary = self._lf_artwork_activity_summary()
        for order in self:
            if order.activity_ids.filtered(lambda act: act.summary == summary):
                continue
            order.activity_schedule(
                "mail.mail_activity_data_todo",
                summary=self._lf_artwork_activity_summary(),
                note=self.env._("Approve or reject the designs before production."),
                user_id=order.user_id.id or self.env.uid,
            )

    def _lf_close_artwork_activity(self):
        summary = self._lf_artwork_activity_summary()
        for order in self.filtered(lambda order: order.artwork_state == "approved"):
            order.activity_ids.filtered(
                lambda act: act.summary == summary
            ).action_feedback(feedback=self.env._("Artwork approved"))

    def _lf_notify_design_revised(self, line):
        """The customer sent a new version of a rejected design."""
        self.ensure_one()
        self.message_post(
            body=self.env._(
                "The customer updated the design of %s. Please review it.",
                line.product_id.display_name,
            ),
            author_id=self.partner_id.id,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        if self.artwork_state == "pending":
            self._lf_schedule_artwork_review()

    def action_view_personalizations(self):
        self.ensure_one()
        return {
            "name": self.env._("Designs"),
            "type": "ir.actions.act_window",
            "res_model": "sale.order.line.personalization",
            "view_mode": "kanban,list,form",
            "domain": [("order_id", "=", self.id)],
            "context": {"create": False},
        }

    def action_download_artwork(self):
        self.ensure_one()
        if not self.personalization_ids.filtered("is_customized"):
            raise UserError(self.env._("This order has no personalized design."))
        return {
            "type": "ir.actions.act_url",
            "url": f"/lf_personalizer/order/{self.id}/artwork.zip",
            "target": "download",
        }
