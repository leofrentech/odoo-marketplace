from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestAccessRule(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = "base.group_user,base.group_partner_manager"
        cls.user = new_test_user(cls.env, "am_restricted", groups=groups)
        cls.other_user = new_test_user(cls.env, "am_other", groups=groups)
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.phone_field = cls.env["ir.model.fields"]._get("res.partner", "phone")
        cls.rule = cls.env["access.rule"].create({
            "name": "Test rule",
            "user_ids": [Command.set(cls.user.ids)],
        })

    def _get_arch(self, user, view_type="form"):
        views = self.env["res.partner"].with_user(user).get_views([(False, view_type)])
        return etree.fromstring(views["views"][view_type]["arch"])

    def _get_field_attrs(self, user, field_name, attr, view_type="form"):
        arch = self._get_arch(user, view_type)
        xpath = "//field[@name=$name][not(ancestor::field)]"
        return {node.get(attr) for node in arch.xpath(xpath, name=field_name)}

    def _visible_is_company(self, user):
        partners = self.env["res.partner"].with_user(user).search([])
        return set(partners.mapped("is_company"))

    def test_field_access_is_per_user(self):
        self.rule.field_access_ids = [Command.create({
            "model_id": self.partner_model.id,
            "field_id": self.phone_field.id,
            "access": "readonly",
        })]

        def readonly_attrs(user):
            return self._get_field_attrs(user, "phone", "readonly")

        # Load the other user's view first: the view cache must not leak
        self.assertNotIn("1", readonly_attrs(self.other_user))
        self.assertEqual(readonly_attrs(self.user), {"1"})
        self.assertNotIn("1", readonly_attrs(self.other_user))

        # A rule change applies without clearing the caches by hand
        self.rule.field_access_ids.access = "invisible"
        self.assertEqual(self._get_field_attrs(self.user, "phone", "invisible"), {"1"})
        self.assertLessEqual(
            self._get_field_attrs(self.user, "phone", "column_invisible", "list"), {"1"}
        )

    def test_record_rules_follow_rule_activity(self):
        self.rule.model_access_ids = [Command.create({
            "name": "Companies only",
            "model_id": self.partner_model.id,
            "domain_force": "[('is_company', '=', True)]",
        })]
        self.assertEqual(self._visible_is_company(self.user), {True})
        self.assertIn(False, self._visible_is_company(self.other_user))

        # An archived rule restricts nobody, rather than everybody
        self.rule.action_archive()
        self.assertIn(False, self._visible_is_company(self.user))
        self.assertIn(False, self._visible_is_company(self.other_user))

        self.rule.action_unarchive()
        self.assertEqual(self._visible_is_company(self.user), {True})

    def test_hide_view_nodes(self):
        hide_node = self.env["access.rule.hidden.node"].new({
            "model_id": self.partner_model.id,
        })
        hide_node._onchange_model_id_collect_view_nodes()
        ViewNode = self.env["access.view.node"]
        nodes = ViewNode.search([("model_id", "=", self.partner_model.id)])
        form = self._get_arch(self.other_user)
        page = nodes.filtered(
            lambda node: node.node_type == "page"
            and form.xpath("//page[@name=$name]", name=node.name or "")
        )[:1]
        self.assertTrue(page, "The form's pages are collected")

        hide_node._onchange_model_id_collect_view_nodes()
        self.assertEqual(
            ViewNode.search_count([("model_id", "=", self.partner_model.id)]),
            len(nodes),
            "Collecting the nodes again should not duplicate them",
        )

        link = ViewNode.create({
            "model_id": self.partner_model.id,
            "node_type": "link",
            "name": "action_test",
            "label": "Test",
            "button_type": "object",
        })
        self.rule.write({
            "hide_page_ids": [Command.create({
                "model_id": self.partner_model.id, "view_node_id": page.id,
            })],
            "hide_link_ids": [Command.create({
                "model_id": self.partner_model.id, "view_node_id": link.id,
            })],
        })
        xpath = "//page[@name=$name]"
        pages = self._get_arch(self.user).xpath(xpath, name=page.name)
        self.assertEqual({node.get("invisible") for node in pages}, {"1"})
        pages = self._get_arch(self.other_user).xpath(xpath, name=page.name)
        self.assertNotIn("1", {node.get("invisible") for node in pages})

    def test_hide_view_node_model_change(self):
        ViewNode = self.env["access.view.node"]
        link = ViewNode.create({
            "model_id": self.partner_model.id,
            "node_type": "link",
            "name": "action_test",
            "label": "Test",
            "button_type": "object",
        })
        # A model without anything to hide in its views
        empty_model = self.env["ir.model"]._get("res.partner.industry")
        HideNode = self.env["access.rule.hidden.node"].with_context(
            access_management_node_type="link"
        )

        line = HideNode.new({
            "model_id": self.partner_model.id,
            "view_node_id": link.id,
        })
        line.model_id = empty_model
        result = line._onchange_model_id_collect_view_nodes()
        self.assertFalse(line.view_node_id, "The other model's link is cleared")
        self.assertEqual(result["warning"]["title"], "Nothing to hide")

        with self.assertRaises(ValidationError):
            self.rule.hide_link_ids = [Command.create({
                "model_id": empty_model.id,
                "view_node_id": link.id,
            })]
        with self.assertRaises(ValidationError):
            self.rule.hide_button_ids = [Command.create({
                "model_id": self.partner_model.id,
                "view_node_id": link.id,
            })]

    def test_view_node_display_name(self):
        node = self.env["access.view.node"].create({
            "model_id": self.partner_model.id,
            "node_type": "button",
            "name": "action_test",
            "label": "Test",
            "is_smart_button": True,
        })
        self.assertEqual(node.display_name, "Test (action_test) (Smart Button)")

    def test_readonly_export_import(self):
        self.rule.write({
            "readonly": True,
            "restrict_export": True,
            "restrict_import_records": True,
        })
        arch = self._get_arch(self.user, "list")
        for attr in ("create", "edit", "delete"):
            self.assertEqual(arch.get(attr), "False")
        self.assertEqual(arch.get("export_xlsx"), "0")
        self.assertEqual(arch.get("import"), "0")
        self.assertFalse(
            self.env["res.users"]
            .with_user(self.user)
            .check_export_enable("res.partner")
        )
        arch = self._get_arch(self.other_user, "list")
        self.assertNotEqual(arch.get("create"), "False")
        self.assertNotEqual(arch.get("import"), "0")

    def test_export_import_refused_on_server(self):
        export_group = self.env.ref("base.group_allow_export")
        (self.user | self.other_user).group_ids = [Command.link(export_group.id)]
        self.rule.write({"restrict_export": True, "restrict_import_records": True})

        Partner = self.env["res.partner"].with_user(self.user)
        with self.assertRaisesRegex(AccessError, "Test rule"):
            Partner.search([], limit=1).export_data(["name"])
        with self.assertRaisesRegex(AccessError, "Test rule"):
            Partner.load(["name"], [["Imported"]])

        OtherPartner = self.env["res.partner"].with_user(self.other_user)
        self.assertTrue(OtherPartner.search([], limit=1).export_data(["name"])["datas"])
        self.assertTrue(OtherPartner.load(["name"], [["Imported"]])["ids"])

    def test_restrict_debug_without_request(self):
        self.rule.restrict_debug_mode = True
        self._get_arch(self.user)

    def test_hidden_reports_are_per_user(self):
        report = self.env["ir.actions.report"].search(
            [("binding_model_id", "!=", False)], limit=1
        )
        model = report.binding_model_id.model
        self.rule.hidden_report_ids = [Command.create({
            "model_id": report.binding_model_id.id,
            "report_id": report.id,
        })]
        Actions = self.env["ir.actions.actions"]

        def report_ids(user):
            bindings = Actions.with_user(user)._get_bindings(model)
            return [action["id"] for action in bindings.get("report", [])]

        self.assertNotIn(report.id, report_ids(self.user))
        self.assertIn(report.id, report_ids(self.other_user))

        self.rule.hidden_report_ids.hide_all_reports = True
        self.assertFalse(report_ids(self.user))
        self.assertIn(report.id, report_ids(self.other_user))

    def test_hidden_report_line(self):
        report = self.env["ir.actions.report"].search(
            [("binding_model_id", "!=", False)], limit=1
        )
        other_report = self.env["ir.actions.report"].search(
            [("model", "!=", report.model)], limit=1
        )
        report_model = self.env["ir.model"]._get(report.model)
        HiddenReport = self.env["access.rule.hidden.report"]
        values = {"rule_id": self.rule.id, "model_id": report_model.id}

        # Either a report of the model, or all of them
        with self.assertRaises(ValidationError):
            HiddenReport.create(values)
        with self.assertRaises(ValidationError):
            HiddenReport.create({**values, "report_id": other_report.id})
        hide_all = HiddenReport.create({
            **values, "hide_all_reports": True, "report_id": report.id,
        })
        self.assertFalse(hide_all.report_id)

        # Switching an existing line to hide all clears its report
        line = HiddenReport.create({**values, "report_id": report.id})
        line.hide_all_reports = True
        self.assertFalse(line.report_id)
        line.report_id = report
        self.assertFalse(line.report_id)

        line = HiddenReport.new({**values, "report_id": report.id})
        line.hide_all_reports = True
        line._onchange_hide_all_reports()
        self.assertFalse(line.report_id)

    def test_chatter_and_menus(self):
        self.rule.hide_lognote = True
        Partner = self.env["res.partner"]
        self.assertTrue(Partner.with_user(self.user).get_chatter_data()["hideLogNote"])
        self.assertFalse(
            Partner.with_user(self.other_user).get_chatter_data()["hideLogNote"]
        )

        menu = self.env["ir.ui.menu"].search([("parent_id", "=", False)], limit=1)
        self.rule.hide_menu_ids = [Command.set(menu.ids)]
        Menu = self.env["ir.ui.menu"]
        self.assertNotIn(menu.id, Menu.with_user(self.user).load_menus(False))
        self.assertIn(menu.id, Menu.with_user(self.other_user).load_menus(False))
        self.rule.hide_menu_ids = [Command.clear()]
        self.assertIn(menu.id, Menu.with_user(self.user).load_menus(False))

    def test_multi_company(self):
        company_a = self.env.company
        company_b = self.env["res.company"].create({"name": "Company B"})
        company_c = self.env["res.company"].create({"name": "Company C"})
        self.user.company_ids = [Command.link(company_b.id), Command.link(company_c.id)]
        menu = self.env["ir.ui.menu"].search([("parent_id", "=", False)], limit=1)
        child_menus = self.env["ir.ui.menu"].search([("parent_id", "=", menu.id)])
        self.rule.write({
            "company_ids": [Command.set([company_b.id, company_c.id])],
            "readonly": True,
            "hide_menu_ids": [Command.set(menu.ids)],
        })

        def state(*companies):
            company_ids = [company.id for company in companies]
            env = self.env(user=self.user, context={"allowed_company_ids": company_ids})
            menus = env["ir.ui.menu"].load_menus(False)
            arch = env["res.partner"].get_views([(False, "list")])["views"]["list"]
            return {
                "menu_hidden": menu.id not in menus,
                "children_hidden": not set(child_menus.ids) & set(menus),
                "in_root": menu.id in menus["root"]["children"],
                "readonly": etree.fromstring(arch["arch"]).get("create") == "False",
            }

        # Switching back and forth: the cached menus must not leak
        for _i in range(2):
            self.assertEqual(state(company_a), {
                "menu_hidden": False,
                "children_hidden": not child_menus,
                "in_root": True,
                "readonly": False,
            })
            for companies in ((company_b,), (company_c,), (company_a, company_b)):
                self.assertEqual(state(*companies), {
                    "menu_hidden": True,
                    "children_hidden": True,
                    "in_root": False,
                    "readonly": True,
                })

        # No company: the rule applies everywhere
        self.rule.company_ids = [Command.clear()]
        self.assertTrue(state(company_a)["readonly"])

    def test_restricted_views(self):
        kanban = self.env["ir.ui.view"].search([
            ("model", "=", "res.partner"),
            ("type", "=", "kanban"),
            ("mode", "=", "primary"),
        ], limit=1)
        self.rule.restricted_view_ids = [Command.create({
            "model_id": self.partner_model.id,
            "view_id": kanban.id,
        })]
        action = self.env["ir.actions.act_window"].create({
            "name": "Partners",
            "res_model": "res.partner",
            "view_mode": "list,kanban,form",
        })

        def view_types(user):
            action.invalidate_recordset(["views"])
            return [view_type for _view_id, view_type in action.with_user(user).views]

        self.assertNotIn("kanban", view_types(self.user))
        self.assertIn("kanban", view_types(self.other_user))

        # The restricted view type is not part of this action
        action.view_mode = "list,form"
        self.assertEqual(view_types(self.user), ["list", "form"])

    def _add_model_access(self, model, rule=None, **values):
        rule = rule or self.rule
        rule.model_access_ids = [Command.create({
            "name": model,
            "model_id": self.env["ir.model"]._get(model).id,
            **values,
        })]
        return rule.model_access_ids[-1]

    def test_model_access_refuses_unticked_operations(self):
        self._add_model_access(
            "res.partner",
            perm_read=True, perm_write=False, perm_create=False, perm_unlink=False,
        )
        Partner = self.env["res.partner"].with_user(self.user)
        partner = Partner.search([], limit=1)
        self.assertTrue(partner, "Read is ticked")

        with self.assertRaisesRegex(AccessError, "Test rule"):
            partner.name = "Changed"
        with self.assertRaisesRegex(AccessError, "Test rule"):
            partner.unlink()
        with self.assertRaisesRegex(AccessError, "Test rule"):
            Partner.create({"name": "New"})

        # The buttons follow the refused operations
        arch = self._get_arch(self.user, "list")
        for attr in ("create", "edit", "delete"):
            self.assertEqual(arch.get(attr), "False")

        # The user's groups still decide for the other users
        self.env["res.partner"].with_user(self.other_user).create({"name": "New"})

    def test_model_access_refuses_unticked_read(self):
        self._add_model_access(
            "res.partner",
            perm_read=False, perm_write=False, perm_create=False, perm_unlink=False,
        )
        with self.assertRaises(AccessError):
            self.env["res.partner"].with_user(self.user).search([])

    def test_model_access_grants_beyond_groups(self):
        basic_user = new_test_user(self.env, "am_basic", groups="base.group_user")
        Category = self.env["res.partner.category"].with_user(basic_user)
        with self.assertRaises(AccessError):
            Category.create({"name": "Not allowed"})

        rule = self.env["access.rule"].create({
            "name": "Grant rule",
            "user_ids": [Command.set(basic_user.ids)],
        })
        self._add_model_access("res.partner.category", rule=rule)
        category = Category.create({"name": "Allowed"})
        category.unlink()

    def test_model_access_domain_per_operation(self):
        # Read every partner, but edit only the companies
        self._add_model_access(
            "res.partner",
            perm_read=True, perm_write=False, perm_create=False, perm_unlink=False,
        )
        self._add_model_access(
            "res.partner",
            domain_force="[('is_company', '=', True)]",
            perm_read=True, perm_write=True, perm_create=False, perm_unlink=False,
        )
        Partner = self.env["res.partner"].with_user(self.user)
        self.assertIn(False, self._visible_is_company(self.user))
        Partner.search([("is_company", "=", True)], limit=1).name = "Changed"
        with self.assertRaisesRegex(AccessError, "Test rule"):
            Partner.search([("is_company", "=", False)], limit=1).name = "Changed"

    def test_model_access_standard_rules(self):
        other_company = self.env["res.company"].create({"name": "Other Company"})
        partner = self.env["res.partner"].create({
            "name": "Other Company Partner",
            "company_id": other_company.id,
        })
        line = self._add_model_access("res.partner")
        Partner = self.env["res.partner"].with_user(self.user)

        # Odoo's multi-company rule still applies
        self.assertNotIn(partner, Partner.search([]))

        line.ignore_standard_rules = True
        self.assertIn(partner, Partner.search([]))

    def test_model_access_checkbox_coupling(self):
        line = self.env["ir.rule"].with_context(
            access_management_model_access=True
        ).new({
            "model_id": self.partner_model.id,
            "perm_read": True,
            "perm_write": True,
            "perm_create": True,
            "perm_unlink": True,
        })
        line.perm_read = False
        line._onchange_perm_read()
        self.assertFalse(line.perm_write or line.perm_create or line.perm_unlink)

        line.perm_unlink = True
        line._onchange_perm_write_create_unlink()
        self.assertTrue(line.perm_read)

    def test_model_access_protected_models(self):
        with self.assertRaises(ValidationError):
            self._add_model_access("res.users")

    def test_administrator_only(self):
        admin = new_test_user(
            self.env,
            "am_admin",
            groups="base.group_user,access_management.access_management_group_admin",
        )
        AccessRule = self.env["access.rule"]
        for operation in ("read", "write", "create", "unlink"):
            self.assertFalse(AccessRule.with_user(self.user).has_access(operation))
        self.assertTrue(
            self.env.ref("base.user_admin").has_group(
                "access_management.access_management_group_admin"
            )
        )

        # The administrators manage the rules, Model Access included
        rule = AccessRule.with_user(admin).create({
            "name": "Admin rule",
            "user_ids": [Command.set(self.other_user.ids)],
            "model_access_ids": [Command.create({
                "name": "All partners",
                "model_id": self.partner_model.id,
            })],
        })
        rule.model_access_ids.name = "Renamed"
        rule.unlink()

        # but not Odoo's own record rules
        core_rule = self.env["ir.rule"].search(
            [("access_rule_id", "=", False)], limit=1
        )
        with self.assertRaises(AccessError):
            core_rule.with_user(admin).domain_force = "[(1, '=', 1)]"
