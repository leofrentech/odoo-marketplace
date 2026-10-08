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

    def test_menus_follow_selected_companies(self):
        """The web client loads its menus without context: the rules apply
        in the companies selected in the ``cids`` cookie."""
        company_a = self.env.company
        company_b = self.env["res.company"].create({"name": "Company B"})
        user = new_test_user(
            self.env,
            "am_ui_mc",
            groups="base.group_user",
            company_ids=[Command.set([company_a.id, company_b.id])],
            company_id=company_a.id,
        )
        menu = self.env.ref("mail.menu_root_discuss")
        self.env["access.rule"].create({
            "name": "Company B rule",
            "user_ids": [Command.set(user.ids)],
            "company_ids": [Command.set(company_b.ids)],
            "hide_menu_ids": [Command.set(menu.ids)],
        })
        self.authenticate(user.login, user.login)
        for cids, hidden in (
            (f"{company_a.id}", False),
            (f"{company_b.id}", True),
            (f"{company_a.id}-{company_b.id}", True),
            ("", False),  # No selection: the user's default company
        ):
            self.opener.cookies.set("cids", cids)
            menus = self.url_open("/web/webclient/load_menus").json()
            self.assertEqual(str(menu.id) not in menus, hidden, f"cids={cids!r}")
