import io

from PIL import Image

from odoo import Command
from odoo.tests import TransactionCase, tagged
from odoo.tools import BinaryBytes


def _make_product_with_colors(env, name):
    """A template with two color variants."""
    color = env["product.attribute"].create({
        "name": f"{name} Color",
        "value_ids": [Command.create({"name": "Red"}), Command.create({"name": "Blue"})],
    })
    return env["product.template"].create({
        "name": name,
        "attribute_line_ids": [Command.create({
            "attribute_id": color.id,
            "value_ids": [Command.set(color.value_ids.ids)],
        })],
    })


def _first_color_value(product):
    return product.attribute_line_ids.product_template_value_ids[:1]


def _make_image(size=(64, 64), color=(255, 0, 0)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return BinaryBytes(buffer.getvalue())


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
            "image_1920": _make_image(),
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
        original_image = _make_image()
        extra = self.env["product.image"].create({
            "name": "Extra 1",
            "product_tmpl_id": product.id,
            "image_1920": original_image,
        })
        self.assertFalse(extra.original_image_1920)
        self.assertEqual(bytes(extra.image_1920), bytes(original_image))

    def test_video_extra_media_not_watermarked(self):
        """Extra media carrying a video only uses image_1920 as the
        video's thumbnail, so it is never watermarked, neither on
        upload nor by the backfill cron."""
        _configure_company_watermark(self.env, enabled=True)
        # A main image first: Odoo 20 refuses a video as the main image,
        # which the first extra image of a product becomes.
        product = self.env["product.template"].create({
            "name": "Video Gallery Product", "is_watermark_eligible": True,
            "image_1920": _make_image(color=(0, 255, 0)),
        })
        thumbnail_image = _make_image()
        video = self.env["product.image"].create({
            "name": "Video 1",
            "product_tmpl_id": product.id,
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "image_1920": thumbnail_image,
        })
        self.assertFalse(video.original_image_1920)

        self.env["product.template"]._cron_regenerate_watermarked_images()

        video = self.env["product.image"].browse(video.id)
        self.assertFalse(video.original_image_1920)
        self.assertEqual(bytes(video.image_1920), bytes(thumbnail_image))

    def test_extra_image_not_watermarked_when_disabled(self):
        """No automatic watermark on a new extra image while company
        watermarking is disabled."""
        _configure_company_watermark(self.env, enabled=False)
        product = self.env["product.template"].create({
            "name": "Gallery Product", "is_watermark_eligible": True,
        })
        original_image = _make_image()
        extra = self.env["product.image"].create({
            "name": "Extra 1",
            "product_tmpl_id": product.id,
            "image_1920": original_image,
        })
        self.assertFalse(extra.original_image_1920)
        self.assertEqual(bytes(extra.image_1920), bytes(original_image))

    def test_variant_specific_extra_image_uses_variant_template_eligibility(self):
        """An extra image shown only for some variants (restricted to an
        attribute value) resolves its eligibility/settings from its
        template, via `_watermark_template()`."""
        _configure_company_watermark(self.env, enabled=True)
        product = _make_product_with_colors(self.env, "Variant Gallery Product")
        product.is_watermark_eligible = True
        extra = self.env["product.image"].create({
            "name": "Variant Extra",
            "product_tmpl_id": product.id,
            "attribute_value_ids": [Command.set(_first_color_value(product).ids)],
            "image_1920": _make_image(color=(0, 0, 255)),
        })
        self.assertTrue(extra.original_image_1920)

    def test_cron_backfills_extra_images_only_when_enabled(self):
        """The extended cron only backfills extra images with no
        watermark yet, and only while watermarking is enabled, same
        "only ever adds" rule as the base cron."""
        _configure_company_watermark(self.env, enabled=False)
        product = self.env["product.template"].create({
            "name": "Backfill Gallery Product", "is_watermark_eligible": True,
        })
        extra = self.env["product.image"].create({
            "name": "Extra 1",
            "product_tmpl_id": product.id,
            "image_1920": _make_image(),
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
            ("product_tmpl_id.is_watermark_eligible", "=", True),
        ]
        matched = self.env["product.image"].search(domain)
        self.assertIn(extra.id, matched.ids)
        matched._apply_watermark()
        extra = self.env["product.image"].browse(extra.id)
        self.assertTrue(extra.original_image_1920)

    def test_wizard_apply_covers_extra_images_but_not_videos(self):
        """The wizard's Apply watermarks the product's extra images too
        (template- and variant-level), but never video media."""
        _configure_company_watermark(self.env, enabled=False)
        product = _make_product_with_colors(self.env, "Wizard Gallery Product")
        extra = self.env["product.image"].create({
            "name": "Extra 1",
            "product_tmpl_id": product.id,
            "image_1920": _make_image(),
        })
        variant_extra = self.env["product.image"].create({
            "name": "Variant Extra",
            "product_tmpl_id": product.id,
            "attribute_value_ids": [Command.set(_first_color_value(product).ids)],
            "image_1920": _make_image(color=(0, 0, 255)),
        })
        video = self.env["product.image"].create({
            "name": "Video 1",
            "product_tmpl_id": product.id,
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "image_1920": _make_image(),
        })

        self.env["product.template.watermark"].create({
            "product_tmpl_id": product.id,
            "watermark_type": "text",
            "watermark_text": "CUSTOM",
        }).action_apply()

        self.assertTrue(extra.original_image_1920)
        self.assertTrue(variant_extra.original_image_1920)
        self.assertFalse(video.original_image_1920)

    def test_remove_watermark_reverts_extra_images(self):
        """The product's Remove Watermark action restores its extra
        images too, and is offered even when only an extra image (not
        the main one) carries a watermark."""
        # The main image is added while watermarking is off, so only the
        # extra image added next carries a watermark. (In Odoo 20 the
        # first extra image of a product is its main image.)
        _configure_company_watermark(self.env, enabled=False)
        product = self.env["product.template"].create({
            "name": "Remove Gallery Product", "is_watermark_eligible": True,
            "image_1920": _make_image(color=(0, 255, 0)),
        })
        _configure_company_watermark(self.env, enabled=True)
        original_image = _make_image()
        extra = self.env["product.image"].create({
            "name": "Extra 1",
            "product_tmpl_id": product.id,
            "image_1920": original_image,
        })
        self.assertFalse(product.original_image_1920)
        self.assertTrue(product.has_watermark)

        product.action_remove_watermark()

        extra = self.env["product.image"].browse(extra.id)
        self.assertFalse(extra.original_image_1920)
        self.assertEqual(bytes(extra.image_1920), bytes(original_image))
        product.invalidate_recordset(["has_watermark"])
        self.assertFalse(product.has_watermark)

    def test_marking_product_ineligible_reverts_extra_images(self):
        """Marking a product not eligible for watermarking also reverts
        any already-watermarked extra images attached to it, not just
        its main product image."""
        _configure_company_watermark(self.env, enabled=True)
        product = self.env["product.template"].create({
            "name": "Cascade Gallery Product", "is_watermark_eligible": True,
        })
        original_image = _make_image()
        extra = self.env["product.image"].create({
            "name": "Extra 1",
            "product_tmpl_id": product.id,
            "image_1920": original_image,
        })
        self.assertTrue(extra.original_image_1920)

        product.write({"is_watermark_eligible": False})

        extra = self.env["product.image"].browse(extra.id)
        self.assertFalse(extra.original_image_1920)
        self.assertEqual(bytes(extra.image_1920), bytes(original_image))

    # Odoo 20 eCommerce keeps the main images in sync with the gallery: the
    # first extra image of a product is its main image (and the first
    # variant image of a variant, that variant's main image).

    def test_main_image_and_gallery_copy_watermarked_once(self):
        """Uploading a main image watermarks it and its gallery copy, each
        exactly once, both keeping the untouched upload as original."""
        _configure_company_watermark(self.env, enabled=True)
        upload = _make_image()
        product = self.env["product.template"].create({
            "name": "Synced Gallery Product", "is_watermark_eligible": True,
            "image_1920": upload,
        })
        gallery_copy = product.product_template_image_ids.sorted("sequence")[:1]
        self.assertTrue(gallery_copy)
        self.assertEqual(bytes(product.original_image_1920), bytes(upload))
        self.assertEqual(bytes(gallery_copy.original_image_1920), bytes(upload))
        self.assertNotEqual(bytes(product.image_1920), bytes(upload))
        self.assertEqual(bytes(gallery_copy.image_1920), bytes(product.image_1920))

        product.action_remove_watermark()

        self.assertEqual(bytes(product.image_1920), bytes(upload))
        self.assertEqual(bytes(gallery_copy.image_1920), bytes(upload))
        self.assertFalse(product.original_image_1920)
        self.assertFalse(gallery_copy.original_image_1920)

    def test_watermarking_gallery_keeps_variant_images(self):
        """Watermarking extra images never resets the variants' own
        images (eCommerce resyncs them from the gallery on each extra
        image write)."""
        _configure_company_watermark(self.env, enabled=False)
        product = _make_product_with_colors(self.env, "Variant Keep Product")
        red, blue = product.product_variant_ids
        red.image_variant_1920 = _make_image(color=(255, 0, 0))
        blue.image_variant_1920 = _make_image(color=(0, 0, 255))
        self.env["product.image"].create({
            "name": "Extra", "product_tmpl_id": product.id, "image_1920": _make_image(),
        })

        self.env["product.template.watermark"].create({
            "product_tmpl_id": product.id,
            "watermark_type": "text",
            "watermark_text": "CUSTOM",
        }).action_apply()

        for variant in (red, blue):
            self.assertTrue(variant.image_variant_1920)
            self.assertTrue(variant.original_image_variant_1920)

    def test_reordered_gallery_image_not_watermarked_twice(self):
        """When a watermarked extra image becomes the first one, eCommerce
        makes it the main image: the main image shows it as is and keeps
        its original, instead of watermarking it again."""
        _configure_company_watermark(self.env, enabled=True)
        product = self.env["product.template"].create({
            "name": "Reorder Gallery Product", "is_watermark_eligible": True,
            "image_1920": _make_image(color=(0, 255, 0)),
        })
        upload = _make_image(color=(0, 0, 255))
        extra = self.env["product.image"].create({
            "name": "Extra", "product_tmpl_id": product.id, "image_1920": upload,
        })
        self.assertTrue(extra.original_image_1920)

        extra.sequence = product.product_template_image_ids.sorted("sequence")[0].sequence - 1

        self.assertEqual(bytes(product.image_1920), bytes(extra.image_1920))
        self.assertEqual(bytes(product.original_image_1920), bytes(upload))
