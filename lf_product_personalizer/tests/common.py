import base64

from odoo.tests import HttpCase

PNG_1PX = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
PNG_DATA_URL = f"data:image/png;base64,{PNG_1PX}"


class PersonalizerCase(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env["website"].get_current_website()
        cls.product = cls.env["product.template"].create({
            "name": "Test Mug",
            "list_price": 10.0,
            "type": "consu",
            "is_published": True,
            "is_product_personalization": True,
            "personalization_fee": 2.0,
            "taxes_id": [(5, 0, 0)],
            "website_id": cls.website.id,
        })
        cls.variant = cls.product.product_variant_id
        cls.area_front = cls.env["product.design.config"].create({
            "product_tmpl_id": cls.product.id,
            "design_type": "Front",
            "design_image": PNG_1PX,
            "is_restricted_area": True,
            "bound_x": 100, "bound_y": 100, "bound_width": 400, "bound_height": 300,
            "price_extra": 3.0,
        })
        cls.area_back = cls.env["product.design.config"].create({
            "product_tmpl_id": cls.product.id,
            "design_type": "Back",
            "price_extra": 4.0,
        })

    def text_design(self, text="Hello"):
        return {"objects": [{"type": "i-text", "text": text, "left": 300, "top": 250}]}

    def designs(self, front=None, back=None):
        result = {
            str(self.area_front.id): {
                "json": front if front is not None else self.text_design(),
                "preview": PNG_DATA_URL,
                "print": PNG_DATA_URL,
                "svg": '<svg xmlns="http://www.w3.org/2000/svg"><text>Hello</text></svg>',
            },
        }
        if back is not None:
            result[str(self.area_back.id)] = {"json": back}
        return result

    def add(self, designs=None, quantity=1):
        return self.make_jsonrpc_request("/shop/personalize/add", {
            "product_id": self.product.id,
            "variant_id": self.variant.id,
            "quantity": quantity,
            "designs": designs or self.designs(),
        })

    @staticmethod
    def b64(raw):
        return base64.b64encode(raw).decode()
