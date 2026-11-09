from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from .common import PNG_DATA_URL
from odoo.addons.lf_product_personalizer.models.design_tools import (
    decode_data_url,
    sanitize_canvas_json,
    sanitize_svg,
)


@tagged("post_install", "-at_install")
class TestDesignTools(TransactionCase):

    def test_sanitize_keeps_supported_objects(self):
        clean = sanitize_canvas_json(self.env, {"objects": [
            {"type": "i-text", "text": "Hi"},
            {"type": "rect"},
            {"type": "image", "src": PNG_DATA_URL},
            {"type": "image", "src": "https://shop.example.com/web/image/product.design.clipart/3/image"},
        ]})
        self.assertEqual(len(clean["objects"]), 4)
        # absolute URLs of the shop are stored as relative paths
        self.assertEqual(clean["objects"][3]["src"], "/web/image/product.design.clipart/3/image")

    def test_sanitize_rejects_unknown_types_and_sources(self):
        for bad in (
            {"objects": [{"type": "group", "objects": []}]},
            {"objects": [{"type": "image", "src": "https://evil.example.com/x.png"}]},
            {"objects": [{"type": "image", "src": "data:image/svg+xml;base64,PHN2Zz4="}]},
            {"objects": [{"type": "image", "src": "/web/content/12"}]},
            {"objects": "nope"},
            "not json",
        ):
            with self.assertRaises(UserError):
                sanitize_canvas_json(self.env, bad)

    def test_sanitize_text_limits(self):
        with self.assertRaises(UserError):
            sanitize_canvas_json(self.env, {"objects": [{"type": "text", "text": "x" * 11}]}, max_text_length=10)
        with self.assertRaises(UserError):
            sanitize_canvas_json(self.env, {"objects": [{"type": "rect"}] * 101})

    def test_decode_data_url(self):
        raw, mimetype = decode_data_url(self.env, PNG_DATA_URL, 1024)
        self.assertEqual(mimetype, "image/png")
        self.assertTrue(raw.startswith(b"\x89PNG"))
        with self.assertRaises(UserError):  # wrong magic bytes
            decode_data_url(self.env, "data:image/png;base64,aGVsbG8=", 1024)
        with self.assertRaises(UserError):  # too large
            decode_data_url(self.env, PNG_DATA_URL, 10)

    def test_sanitize_svg(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" onload="alert(1)">'
            '<script>alert(1)</script>'
            '<a href="javascript:alert(1)"><text onclick="x()">Hi</text></a>'
            '<image xlink:href="https://evil.example.com/a.png"/>'
            f'<image xlink:href="{PNG_DATA_URL}"/>'
            '<foreignObject><div>x</div></foreignObject>'
            '</svg>'
        )
        clean = sanitize_svg(self.env, svg, 1024 * 1024).decode()
        self.assertNotIn("script", clean)
        self.assertNotIn("onload", clean)
        self.assertNotIn("onclick", clean)
        self.assertNotIn("javascript", clean)
        self.assertNotIn("evil.example.com", clean)
        self.assertNotIn("foreignObject", clean)
        self.assertIn(PNG_DATA_URL, clean)
        with self.assertRaises(UserError):
            sanitize_svg(self.env, "<html/>", 1024)
