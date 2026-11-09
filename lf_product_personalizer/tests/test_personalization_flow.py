import io
import json
import zipfile

from odoo.exceptions import UserError
from odoo.tests import JsonRpcException, new_test_user, tagged

from .common import PNG_1PX, PNG_DATA_URL, PersonalizerCase


@tagged("post_install", "-at_install")
class TestPersonalizationFlow(PersonalizerCase):

    def last_cart(self):
        return self.env["sale.order"].search(
            [("website_id", "=", self.website.id)], order="id desc", limit=1,
        )

    def base_price(self, order):
        """Product price on the order pricelist (the test DB may discount it)."""
        return order.pricelist_id._get_product_price(self.variant, 1.0)

    def other_customer_line(self):
        """A personalized line in someone else's order."""
        partner = self.env["res.partner"].create({"name": "Someone Else"})
        order = self.env["sale.order"].create({
            "partner_id": partner.id,
            "website_id": self.website.id,
            "order_line": [(0, 0, {"product_id": self.variant.id, "product_uom_qty": 1})],
        })
        line = order.order_line
        line.with_context(lf_personalized=True)._lf_set_personalization(self.designs())
        return line

    # ------------------------------------------------------------------
    # Cart
    # ------------------------------------------------------------------

    def test_each_design_gets_its_own_line_with_surcharge(self):
        self.authenticate(None, None)
        self.assertTrue(self.add(quantity=2)["success"])
        self.assertTrue(self.add(self.designs(front=self.text_design("Other")))["success"])
        order = self.last_cart()
        lines = order.order_line.filtered(lambda line: line.product_id == self.variant)
        self.assertEqual(len(lines), 2, "two different designs must not be merged")
        self.assertEqual(sorted(lines.mapped("product_uom_qty")), [1, 2])
        for line in lines:
            # list price + 2 personalization fee + 3 front area
            self.assertAlmostEqual(line.price_unit, self.base_price(order) + 5.0)
            self.assertIn("Personalized: Front", line.name)
            front = line.personalization_ids.filtered("is_customized")
            self.assertEqual(front.design_type, "Front")
            self.assertTrue(front.print_image)
            self.assertTrue(front.print_svg)

    def test_regular_add_does_not_merge_into_personalized_line(self):
        self.authenticate(None, None)
        self.add()
        order = self.last_cart()
        order._cart_add(self.variant.id, 1)
        self.assertEqual(len(order.order_line), 2)
        plain = order.order_line.filtered(lambda line: not line.personalization_ids)
        self.assertAlmostEqual(plain.price_unit, self.base_price(order))

    def test_update_line(self):
        self.authenticate(None, None)
        line_id = self.add()["line_id"]
        result = self.make_jsonrpc_request("/shop/personalize/update", {
            "line_id": line_id,
            "quantity": 3,
            "designs": self.designs(front=self.text_design("Changed"), back=self.text_design("B")),
        })
        self.assertTrue(result["success"])
        line = self.env["sale.order.line"].browse(line_id)
        self.assertEqual(line.product_uom_qty, 3)
        self.assertEqual(len(line.personalization_ids), 2)
        # list price + 2 fee + 3 front + 4 back
        self.assertAlmostEqual(line.price_unit, self.base_price(line.order_id) + 9.0)
        front = line.personalization_ids.filtered(lambda p: p.design_config_id == self.area_front)
        self.assertEqual(json.loads(front.personalized_json)["objects"][0]["text"], "Changed")

    def test_required_personalization(self):
        self.product.personalization_required = True
        order = self.env["sale.order"].create({
            "partner_id": self.env.ref("base.partner_admin").id,
            "website_id": self.website.id,
        })
        with self.assertRaises(UserError):
            order._cart_add(self.variant.id, 1)

    def test_required_area_and_empty_design(self):
        self.authenticate(None, None)
        self.area_back.is_required = True
        self.assertIn("Back", self.add()["error"])
        self.area_back.is_required = False
        self.assertIn("error", self.add(self.designs(front={"objects": []})))

    def test_invalid_payloads(self):
        self.authenticate(None, None)
        bad_area = self.designs()
        bad_area["999999"] = {"json": self.text_design()}
        self.assertIn("error", self.add(bad_area))
        svg_image = self.designs(front={"objects": [
            {"type": "image", "src": "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4="},
        ]})
        self.assertIn("error", self.add(svg_image))
        self.assertFalse(
            self.env["sale.order.line"].search([("product_id", "=", self.variant.id)]),
            "a failed add must not leave a line",
        )

    def test_artwork_extracted_to_attachments(self):
        self.authenticate(None, None)
        image = {"objects": [{"type": "image", "src": PNG_DATA_URL, "left": 200, "top": 200}]}
        line = self.env["sale.order.line"].browse(self.add(self.designs(front=image))["line_id"])
        front = line.personalization_ids.filtered("is_customized")
        self.assertEqual(len(front.artwork_attachment_ids), 1)
        self.assertNotIn("base64", front.personalized_json)
        src = json.loads(front.personalized_json)["objects"][0]["src"]
        self.assertRegex(src, r"^/web/content/\d+\?access_token=")
        self.assertEqual(self.url_open(src).status_code, 200)

    def test_cart_page_quantity_change(self):
        """The cart page +/- buttons update the personalized line itself."""
        self.authenticate(None, None)
        line_id = self.add()["line_id"]
        self.make_jsonrpc_request("/shop/cart/update", {
            "product_id": self.variant.id, "line_id": line_id, "quantity": 5,
        })
        line = self.env["sale.order.line"].browse(line_id)
        self.assertEqual(line.product_uom_qty, 5)
        self.assertEqual(len(line.order_id.order_line), 1)
        self.assertTrue(line.personalization_ids)

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def test_pages_show_personalization(self):
        # Rendered once: product pages are cached per write_date, which does
        # not change inside a test transaction.
        self.product.personalization_required = True
        self.authenticate(None, None)
        page = self.url_open(self.product.website_url).text
        self.assertIn("o_lf_personalize_btn", page)
        self.assertRegex(page, r'name="add_to_cart"[^>]*class="[^"]*d-none')

        line = self.other_customer_line()
        order = line.order_id
        portal = self.url_open(order.get_portal_url()).text
        self.assertIn("o_lf_portal_designs", portal)
        html = self.env["ir.actions.report"]._render_qweb_html(
            "sale.action_report_saleorder", order.ids,
        )[0].decode()
        self.assertIn("data:image", html)

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------

    def test_cannot_access_other_customer_lines(self):
        line = self.other_customer_line()
        design = line.personalization_ids.filtered("is_customized")
        self.authenticate(None, None)
        for route, params in (
            ("/shop/personalize/update", {"line_id": line.id, "quantity": 50, "designs": self.designs()}),
            ("/shop/personalize/data", {"product_id": self.product.id, "line_id": line.id}),
        ):
            with self.assertRaises(JsonRpcException):
                self.make_jsonrpc_request(route, params)
        self.assertEqual(line.product_uom_qty, 1)
        self.assertTrue(design.exists())
        self.assertEqual(self.url_open(f"/shop/personalize/edit/{line.id}").status_code, 404)
        image_url = f"/shop/personalization/{design.id}/product_image"
        self.assertEqual(self.url_open(image_url).status_code, 404)
        self.assertEqual(self.url_open(f"{image_url}?access_token=wrong").status_code, 404)
        token = line.order_id._portal_ensure_token()
        self.assertEqual(self.url_open(f"{image_url}?access_token={token}").status_code, 200)
        svg = self.url_open(f"/shop/personalization/{design.id}/print_svg?access_token={token}")
        self.assertIn("attachment", svg.headers.get("Content-Disposition", ""))

    def test_access_rights(self):
        portal = new_test_user(self.env, "lf_portal", groups="base.group_portal")
        model = self.env["sale.order.line.personalization"].with_user(portal)
        self.assertFalse(model.has_access("read"))
        config = self.env["product.design.config"].with_user(portal)
        self.assertFalse(config.has_access("write"))

    def test_unpublished_product_is_hidden(self):
        area_image = f"/shop/personalize/area/{self.area_front.id}/image"
        self.product.is_published = False
        self.authenticate(None, None)
        self.assertEqual(self.url_open(f"/shop/personalize/{self.product.id}").status_code, 404)
        self.assertEqual(self.url_open(area_image).status_code, 404)
        self.product.is_published = True
        self.assertEqual(self.url_open(f"/shop/personalize/{self.product.id}").status_code, 200)
        self.assertEqual(self.url_open(area_image).status_code, 200)
        self.assertEqual(self.url_open("/shop/personalize/999999").status_code, 404)

    # ------------------------------------------------------------------
    # Production
    # ------------------------------------------------------------------

    def test_artwork_without_review(self):
        line = self.other_customer_line()
        self.assertEqual(line.personalization_ids.filtered("is_customized").approval_state, "not_required")
        self.assertEqual(line.order_id.artwork_state, "ready")

    def test_approval_workflow(self):
        self.product.personalization_requires_approval = True
        line = self.other_customer_line()
        order = line.order_id
        self.assertEqual(order.artwork_state, "pending")
        order.action_confirm()
        self.assertTrue(order.activity_ids)
        design = line.personalization_ids.filtered("is_customized")
        with self.assertRaises(UserError):
            design.action_reject()
        design.approval_note = "Logo too blurry"
        design.action_reject()
        self.assertEqual(order.artwork_state, "rejected")
        self.assertIn("Logo too blurry", order.message_ids[0].body)
        with self.assertRaises(UserError):  # must go back to review first
            design.action_approve()
        design.action_reset_to_review()
        self.assertEqual(order.artwork_state, "pending")
        design.action_approve()
        self.assertEqual(order.artwork_state, "approved")
        self.assertFalse(order.activity_ids)

    def test_update_keeps_uploaded_images(self):
        """Editing a cart line resubmits images by URL: the files must survive."""
        self.authenticate(None, None)
        image = {"objects": [{"type": "image", "src": PNG_DATA_URL}]}
        line_id = self.add(self.designs(front=image))["line_id"]
        line = self.env["sale.order.line"].browse(line_id)
        src = json.loads(line.personalization_ids.filtered("is_customized").personalized_json)["objects"][0]["src"]
        reused = {"objects": [{"type": "image", "src": src}, {"type": "i-text", "text": "New"}]}
        result = self.make_jsonrpc_request("/shop/personalize/update", {
            "line_id": line_id, "quantity": 1, "designs": self.designs(front=reused),
        })
        self.assertTrue(result["success"])
        front = line.personalization_ids.filtered("is_customized")
        new_src = json.loads(front.personalized_json)["objects"][0]["src"]
        self.assertEqual(len(front.artwork_attachment_ids), 1)
        self.assertEqual(self.url_open(new_src).status_code, 200)
        # An attachment URL with a wrong token is refused.
        forged = {"objects": [{"type": "image", "src": new_src.split("=")[0] + "=forged"}]}
        result = self.make_jsonrpc_request("/shop/personalize/update", {
            "line_id": line_id, "quantity": 1, "designs": self.designs(front=forged),
        })
        self.assertIn("error", result)

    def test_customer_fixes_rejected_design(self):
        self.product.personalization_requires_approval = True
        line = self.other_customer_line()
        line.with_context(lf_personalized=True)._lf_set_personalization(
            self.designs(back=self.text_design("Back v1")),
        )
        order = line.order_id
        order.action_confirm()
        price = line.price_unit
        front = line.personalization_ids.filtered(lambda p: p.design_config_id == self.area_front)
        back = line.personalization_ids.filtered(lambda p: p.design_config_id == self.area_back)
        front.action_approve()
        back.approval_note = "Text too long"
        back.action_reject()
        token = order._portal_ensure_token()
        url = f"/shop/personalize/revise/{line.id}"

        self.authenticate(None, None)
        self.assertEqual(self.url_open(url).status_code, 404)
        self.assertEqual(self.url_open(f"{url}?access_token=bad").status_code, 404)
        page = self.url_open(f"{url}?access_token={token}")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Text too long", page.text)

        def revise(designs, access_token=token):
            return self.make_jsonrpc_request("/shop/personalize/revise", {
                "line_id": line.id, "access_token": access_token, "designs": designs,
            })

        with self.assertRaises(JsonRpcException):
            revise(self.designs(back=self.text_design("Hack")), access_token="bad")

        front_json = front._lf_canvas_data()
        result = revise({
            str(self.area_front.id): {"json": front_json, "preview": PNG_DATA_URL},
            str(self.area_back.id): {"json": self.text_design("Back v2"), "preview": PNG_DATA_URL},
        })
        self.assertTrue(result["success"])
        states = {p.design_config_id: p.approval_state for p in line.personalization_ids}
        self.assertEqual(states[self.area_front], "approved", "unchanged area stays approved")
        self.assertEqual(states[self.area_back], "pending")
        self.assertEqual(order.artwork_state, "pending")
        self.assertEqual(line.price_unit, price, "a placed order keeps its price")
        self.assertIn("updated the design", order.message_ids[0].body)
        # Nothing rejected anymore: the revision link is closed.
        self.assertEqual(self.url_open(f"{url}?access_token={token}").status_code, 404)

    def test_revision_cannot_add_paid_area(self):
        self.product.personalization_requires_approval = True
        line = self.other_customer_line()  # front only
        line.order_id.action_confirm()
        design = line.personalization_ids.filtered("is_customized")
        design.approval_note = "No"
        design.action_reject()
        self.authenticate(None, None)
        result = self.make_jsonrpc_request("/shop/personalize/revise", {
            "line_id": line.id,
            "access_token": line.order_id._portal_ensure_token(),
            "designs": self.designs(back=self.text_design("Extra")),
        })
        self.assertIn("contact us", result["error"])

    def test_artwork_zip(self):
        line = self.other_customer_line()
        new_test_user(self.env, "lf_sales", groups="sales_team.group_sale_salesman_all_leads")
        self.authenticate("lf_sales", "lf_sales")
        response = self.url_open(f"/lf_personalizer/order/{line.order_id.id}/artwork.zip")
        self.assertEqual(response.status_code, 200)
        names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
        self.assertTrue(any(name.endswith("Front-print.png") for name in names), names)
        self.assertTrue(any(name.endswith("Front-print.svg") for name in names), names)

    # ------------------------------------------------------------------
    # Saved designs & templates
    # ------------------------------------------------------------------

    def save_design(self):
        return self.make_jsonrpc_request("/shop/personalize/save_design", {
            "product_id": self.product.id,
            "variant_id": self.variant.id,
            "name": "My mug",
            "designs": {str(self.area_front.id): {"json": self.text_design()}},
            "preview": PNG_DATA_URL,
        })

    def test_saved_design_and_share_link(self):
        self.authenticate(None, None)
        self.assertTrue(self.save_design().get("login_required"))

        new_test_user(self.env, "lf_customer", groups="base.group_portal")
        self.authenticate("lf_customer", "lf_customer")
        result = self.save_design()
        design = self.env["product.design.saved"].browse(result["design_id"])
        self.assertEqual(design.name, "My mug")
        self.assertIn(design.access_token, result["share_url"])
        self.assertEqual(self.url_open("/my/designs").status_code, 200)

        new_test_user(self.env, "lf_other", groups="base.group_portal")
        self.authenticate("lf_other", "lf_other")
        url = f"/shop/personalize/design/{design.id}"
        self.assertEqual(self.url_open(url).status_code, 404)
        self.assertEqual(self.url_open(f"{url}?access_token={design.access_token}").status_code, 200)
        data = self.make_jsonrpc_request("/shop/personalize/data", {
            "product_id": self.product.id,
            "design_id": design.id,
            "access_token": design.access_token,
        })
        self.assertIn(str(self.area_front.id), data["designs"])

    def test_presets_reserved_to_managers(self):
        params = {
            "product_id": self.product.id,
            "variant_id": self.variant.id,
            "name": "Birthday",
            "designs": {str(self.area_front.id): {"json": self.text_design()}},
            "preview": PNG_DATA_URL,
        }
        new_test_user(self.env, "lf_customer2", groups="base.group_portal")
        self.authenticate("lf_customer2", "lf_customer2")
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request("/shop/personalize/save_preset", params)

        new_test_user(self.env, "lf_manager", groups="sales_team.group_sale_manager")
        self.authenticate("lf_manager", "lf_manager")
        result = self.make_jsonrpc_request("/shop/personalize/save_preset", params)
        preset = self.env["product.design.preset"].browse(result["preset_id"])
        self.assertEqual(preset.product_tmpl_id, self.product)
        self.authenticate(None, None)
        data = self.make_jsonrpc_request("/shop/personalize/data", {"product_id": self.product.id})
        self.assertEqual([p["name"] for p in data["presets"]], ["Birthday"])

    def test_print_quality_setting(self):
        settings = self.product._lf_get_editor_settings()
        self.assertEqual(settings["print_scale"], 4, "high quality by default")
        self.assertEqual(self.product.personalization_min_image_px, 600)
        self.env["res.config.settings"].create({"lf_personalizer_print_quality": "standard"}).execute()
        self.assertEqual(self.product._lf_get_editor_settings()["print_scale"], 2)

    def test_design_set_shared_by_products(self):
        design_set = self.env["product.design.set"].create({
            "name": "Mug",
            "area_ids": [(0, 0, {"design_type": "Wrap", "design_image": PNG_1PX})],
        })
        other = self.env["product.template"].create({
            "name": "Other Mug",
            "is_published": True,
            "is_product_personalization": True,
            "design_set_id": design_set.id,
        })
        self.assertTrue(other._lf_is_personalizable())
        self.assertEqual(other._lf_get_areas(other.product_variant_id).design_type, "Wrap")
        self.assertEqual(design_set.product_count, 1)
