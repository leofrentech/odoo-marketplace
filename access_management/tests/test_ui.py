from odoo import Command
from odoo.tests import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestUi(HttpCase):
    def test_webclient_with_rules(self):
        """The web client loads views, chatter and menus with active rules."""
        user = new_test_user(
            self.env,
            "am_ui",
            groups=(
                "base.group_user,base.group_partner_manager,"
                "base.group_allow_export"
            ),
        )
        self.env["access.rule"].create({
            "name": "UI rule",
            "user_ids": [Command.set(user.ids)],
            "restrict_export": True,
            "restrict_debug_mode": True,
            "hide_lognote": True,
        })
        partner = self.env["res.partner"].create({"name": "Access Rule Partner"})
        self.start_tour(
            f"/odoo/action-base.action_partner_form/{partner.id}",
            "access_management_tour",
            login=user.login,
        )
