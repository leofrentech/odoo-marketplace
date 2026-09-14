from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductQrTrack(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.size_attribute = cls.env["product.attribute"].create(
            {
                "name": "Test QR Size",
                "value_ids": [
                    Command.create({"name": "Small"}),
                    Command.create({"name": "Large"}),
                ],
            }
        )
        cls.template = cls.env["product.template"].create(
            {
                "name": "Test QR Product",
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": cls.size_attribute.id,
                            "value_ids": [
                                Command.set(cls.size_attribute.value_ids.ids)
                            ],
                        }
                    )
                ],
            }
        )
        cls.variant_small, cls.variant_large = cls.template.product_variant_ids
        cls.single_variant_template = cls.env["product.template"].create(
            {"name": "Test QR Single Variant Product"}
        )

    def test_product_qr_url_is_per_variant(self):
        base_url = self.variant_small.get_base_url()
        self.assertEqual(
            self.variant_small.qr_url,
            f"{base_url}/qr/{self.variant_small.id}",
        )
        self.assertNotEqual(
            self.variant_small.qr_url, self.variant_large.qr_url
        )

    def test_template_qr_url_mirrors_default_variant(self):
        self.assertEqual(
            self.template.qr_url, self.template.product_variant_id.qr_url
        )

    def test_qr_visit_count_aggregates_across_variants(self):
        self.env["product.qr.visit"].create(
            [
                {"product_id": self.variant_small.id},
                {"product_id": self.variant_small.id},
                {"product_id": self.variant_large.id},
            ]
        )
        self.assertEqual(self.variant_small.qr_visit_count, 2)
        self.assertEqual(self.variant_large.qr_visit_count, 1)
        self.assertEqual(self.template.qr_visit_count, 3)

    def test_wizard_blocks_multi_variant_template(self):
        """A QR code identifies one variant, so printing from a
        multi-variant product is ambiguous and must be refused rather
        than silently printing every variant or just the default one."""
        wizard = self.env["product.label.layout"].create(
            {
                "product_tmpl_ids": [Command.set([self.template.id])],
                "print_format": "qr",
                "custom_quantity": 1,
            }
        )
        with self.assertRaises(UserError):
            wizard._prepare_report_data()

    def test_wizard_prints_single_variant_template(self):
        wizard = self.env["product.label.layout"].create(
            {
                "product_tmpl_ids": [
                    Command.set([self.single_variant_template.id])
                ],
                "print_format": "qr",
                "custom_quantity": 1,
            }
        )
        __, data = wizard._prepare_report_data()
        self.assertEqual(len(data["products"]), 1)
        self.assertEqual(
            data["products"][0]["qr_url"],
            self.single_variant_template.product_variant_id.qr_url,
        )

    def test_wizard_uses_selected_variant_only(self):
        wizard = self.env["product.label.layout"].create(
            {
                "product_ids": [Command.set([self.variant_small.id])],
                "print_format": "qr",
                "custom_quantity": 1,
            }
        )
        __, data = wizard._prepare_report_data()
        self.assertEqual(len(data["products"]), 1)
        self.assertEqual(
            data["products"][0]["qr_url"], self.variant_small.qr_url
        )

    def test_wizard_falls_back_for_other_formats(self):
        wizard = self.env["product.label.layout"].create(
            {
                "product_ids": [Command.set([self.variant_small.id])],
                "print_format": "dymo",
                "custom_quantity": 1,
            }
        )
        __, data = wizard._prepare_report_data()
        self.assertNotIn("products", data)
        self.assertIn("quantity_by_product", data)
