from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestQrTrackController(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "Test QR Scan Product", "website_published": True}
        )
        cls.unpublished_product = cls.env["product.product"].create(
            {
                "name": "Test QR Scan Unpublished Product",
                "website_published": False,
            }
        )

    def test_scan_published_product_creates_visit_and_redirects(self):
        visit_count_before = self.env["product.qr.visit"].search_count(
            [("product_id", "=", self.product.id)]
        )

        response = self.url_open(
            f"/qr/{self.product.id}", allow_redirects=False
        )

        self.assertEqual(response.status_code, 303)
        self.assertIn(self.product.website_url, response.headers["Location"])
        visit_count_after = self.env["product.qr.visit"].search_count(
            [("product_id", "=", self.product.id)]
        )
        self.assertEqual(visit_count_after, visit_count_before + 1)

    def test_scan_unpublished_product_is_not_found(self):
        visit_count_before = self.env["product.qr.visit"].search_count([])

        response = self.url_open(
            f"/qr/{self.unpublished_product.id}", allow_redirects=False
        )

        self.assertEqual(response.status_code, 404)
        visit_count_after = self.env["product.qr.visit"].search_count([])
        self.assertEqual(visit_count_after, visit_count_before)

    def test_scan_nonexistent_product_is_not_found(self):
        missing_id = (
            self.env["product.product"]
            .search([], order="id desc", limit=1)
            .id
            + 1000
        )

        response = self.url_open(
            f"/qr/{missing_id}", allow_redirects=False
        )

        self.assertEqual(response.status_code, 404)
