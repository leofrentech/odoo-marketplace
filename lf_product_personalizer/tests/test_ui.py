from odoo.tests import tagged

from .common import PersonalizerCase


@tagged("post_install", "-at_install")
class TestPersonalizerUi(PersonalizerCase):

    def test_editor_tour(self):
        self.start_tour(f"/shop/personalize/{self.product.id}", "lf_personalizer_editor_tour")
        order = self.env["sale.order"].search(
            [("website_id", "=", self.website.id)], order="id desc", limit=1
        )
        design = order.order_line.personalization_ids.filtered("is_customized")
        self.assertEqual(design.design_type, "Front")
        self.assertTrue(design.print_image and design.print_svg and design.product_image)
        base = order.pricelist_id._get_product_price(self.variant, 1.0)
        self.assertAlmostEqual(order.order_line.price_unit, base + 5.0)
