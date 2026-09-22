import base64
import io

from PIL import Image

from odoo.tests import TransactionCase, tagged


def _make_image_b64(size=(64, 64), color=(255, 0, 0)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue())


def _configure_company_watermark(env, enabled, **extra):
    """Helper: set the company-wide watermark settings via the same
    path a real admin would use (res.config.settings)."""
    vals = {
        "watermark_enabled": enabled,
        "watermark_type": "text",
        "watermark_text": "COMPANY DEFAULT",
        "watermark_position": "bottom_right",
        "watermark_opacity": 0.5,
    }
    vals.update(extra)
    env["res.config.settings"].create(vals).execute()


@tagged("post_install", "-at_install")
class TestProductWatermarkWebsiteSale(TransactionCase):

    def test_extra_image_auto_watermarked_on_upload(self):
        """A new product.image created with a photo on an eligible
        product gets watermarked automatically, same as the main
        product image."""
        _configure_company_watermark(self.env, enabled=True)
        product = self.env["product.template"].create({
            "name": "Gallery Product", "is_watermark_eligible": True,
        })
        extra = self.env["product.image"].create({
            "name": "Extra 1",
            "product_tmpl_id": product.id,
            "image_1920": _make_image_b64(),
        })
        self.assertTrue(extra.original_image_1920)

    def test_extra_image_not_watermarked_when_product_ineligible(self):
        """No automatic watermark on an extra image whose product is not
        eligible for watermarking."""
        _configure_company_watermark(self.env, enabled=True)
        product = self.env["product.template"].create({
            "name": "Ineligible Gallery Product",
            "is_watermark_eligible": False,
        })
        original_b64 = _make_image_b64()
        extra = self.env["product.image"].create({
            "name": "Extra 1",
            "product_tmpl_id": product.id,
            "image_1920": original_b64,
        })
        self.assertFalse(extra.original_image_1920)
        self.assertEqual(bytes(extra.image_1920), bytes(original_b64))

    def test_extra_image_not_watermarked_when_disabled(self):
        """No automatic watermark on a new extra image while company
        watermarking is disabled."""
        _configure_company_watermark(self.env, enabled=False)
        product = self.env["product.template"].create({
            "name": "Gallery Product", "is_watermark_eligible": True,
        })
        original_b64 = _make_image_b64()
        extra = self.env["product.image"].create({
            "name": "Extra 1",
            "product_tmpl_id": product.id,
            "image_1920": original_b64,
        })
        self.assertFalse(extra.original_image_1920)
        self.assertEqual(bytes(extra.image_1920), bytes(original_b64))

    def test_variant_specific_extra_image_uses_variant_template_eligibility(self):
        """An extra image attached to a specific variant (not the
        template) resolves its eligibility/settings from that variant's
        own template, via `_watermark_template()`."""
        _configure_company_watermark(self.env, enabled=True)
        product = self.env["product.template"].create({
            "name": "Variant Gallery Product", "is_watermark_eligible": True,
        })
        variant = product.product_variant_id
        extra = self.env["product.image"].create({
            "name": "Variant Extra",
            "product_variant_id": variant.id,
            "image_1920": _make_image_b64(color=(0, 0, 255)),
        })
        self.assertTrue(extra.original_image_1920)

    def test_cron_backfills_extra_images_only_when_enabled(self):
        """The extended cron only backfills extra images with no
        watermark yet, and only while watermarking is enabled — same
        "only ever adds" rule as the base cron."""
        _configure_company_watermark(self.env, enabled=False)
        product = self.env["product.template"].create({
            "name": "Backfill Gallery Product", "is_watermark_eligible": True,
        })
        extra = self.env["product.image"].create({
            "name": "Extra 1",
            "product_tmpl_id": product.id,
            "image_1920": _make_image_b64(),
        })
        self.assertFalse(extra.original_image_1920)

        # Cron must do nothing while disabled.
        self.env["product.template"]._cron_regenerate_watermarked_images()
        extra = self.env["product.image"].browse(extra.id)
        self.assertFalse(extra.original_image_1920)

        # Enable and backfill: the extra image now gets watermarked.
        _configure_company_watermark(self.env, enabled=True)
        domain = [
            ("image_1920", "!=", False),
            ("original_image_1920", "=", False),
            "|",
            ("product_tmpl_id.is_watermark_eligible", "=", True),
            ("product_variant_id.product_tmpl_id.is_watermark_eligible", "=", True),
        ]
        matched = self.env["product.image"].search(domain)
        self.assertIn(extra.id, matched.ids)
        matched._apply_watermark()
        extra = self.env["product.image"].browse(extra.id)
        self.assertTrue(extra.original_image_1920)

    def test_marking_product_ineligible_reverts_extra_images(self):
        """Marking a product not eligible for watermarking also reverts
        any already-watermarked extra images attached to it, not just
        its main product image."""
        _configure_company_watermark(self.env, enabled=True)
        product = self.env["product.template"].create({
            "name": "Cascade Gallery Product", "is_watermark_eligible": True,
        })
        original_b64 = _make_image_b64()
        extra = self.env["product.image"].create({
            "name": "Extra 1",
            "product_tmpl_id": product.id,
            "image_1920": original_b64,
        })
        self.assertTrue(extra.original_image_1920)

        product.write({"is_watermark_eligible": False})

        extra = self.env["product.image"].browse(extra.id)
        self.assertFalse(extra.original_image_1920)
        self.assertEqual(bytes(extra.image_1920), bytes(original_b64))
