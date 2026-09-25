import base64
import io

from unittest.mock import patch

from PIL import Image, ImageChops

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from ..models.watermark_utils import _find_font_path, apply_watermark


def _make_image_b64(size=(64, 64), color=(255, 0, 0), image_format="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=image_format)
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
class TestProductWatermark(TransactionCase):

    def test_opacity_constraint_rejects_out_of_range(self):
        with self.assertRaises(ValidationError):
            self.env["res.config.settings"].create(
                {"watermark_enabled": True, "watermark_type": "text", "watermark_opacity": 1.5}
            ).execute()

    def test_logo_scaled_to_logo_size(self):
        """A logo far larger than the product photo is scaled down to fit
        `logo_size`% of it, instead of covering the whole photo."""
        base = Image.new("RGBA", (200, 100), (255, 255, 255, 255))
        settings = {
            "type": "image",
            "logo": _make_image_b64(size=(1000, 500), color=(0, 0, 0)),
            "logo_size": 20,
            "position": "center",
            "opacity": 1.0,
        }
        result = apply_watermark(base, settings)
        bbox = ImageChops.difference(result.convert("RGB"), base.convert("RGB")).getbbox()
        # Fits a 40x20 box (20% of 200x100), keeping the logo's 2:1 ratio.
        self.assertEqual((bbox[2] - bbox[0], bbox[3] - bbox[1]), (40, 20))

    def test_logo_size_constraint_rejects_out_of_range(self):
        with self.assertRaises(ValidationError):
            self.env["res.config.settings"].create(
                {"watermark_enabled": True, "watermark_type": "image", "watermark_logo_size": 0}
            ).execute()

    def test_automatic_watermark_on_upload_when_enabled(self):
        """A new photo uploaded while company watermarking is on gets
        watermarked in place; the original is preserved separately."""
        _configure_company_watermark(self.env, enabled=True)
        original_b64 = _make_image_b64()
        product = self.env["product.template"].create(
            {
                "name": "Auto Watermark Product",
                "is_watermark_eligible": True,
                "image_1920": original_b64,
            }
        )
        self.assertTrue(product.original_image_1920)
        self.assertNotEqual(bytes(product.image_1920), bytes(original_b64))
        self.assertEqual(bytes(product.original_image_1920), bytes(original_b64))

    def test_no_watermark_when_disabled(self):
        """With company watermarking off, a new photo upload is left
        untouched and no original is captured (nothing to restore)."""
        _configure_company_watermark(self.env, enabled=False)
        original_b64 = _make_image_b64()
        product = self.env["product.template"].create(
            {"name": "Plain Product", "image_1920": original_b64}
        )
        self.assertFalse(product.original_image_1920)
        self.assertEqual(bytes(product.image_1920), bytes(original_b64))

    def test_wizard_apply_independent_of_company_toggle(self):
        """The wizard's manual one-off watermark works even when the
        company-wide toggle is off."""
        _configure_company_watermark(self.env, enabled=False)
        product = self.env["product.template"].create(
            {"name": "Manual Watermark Product", "image_1920": _make_image_b64()}
        )
        self.assertFalse(product.original_image_1920)

        wizard = self.env["product.template.watermark"].create({
            "product_tmpl_id": product.id,
            "watermark_type": "text",
            "watermark_text": "CUSTOM",
            "watermark_position": "center",
            "watermark_opacity": 0.6,
        })
        wizard.action_apply()

        self.assertTrue(product.original_image_1920)

    def test_new_upload_is_not_sticky_to_wizard_customization(self):
        """A wizard-applied custom watermark does not survive a new
        photo upload — the new photo follows the company-wide rule
        instead (explicitly accepted trade-off of the simplified design,
        since no per-product settings are persisted)."""
        _configure_company_watermark(self.env, enabled=False)
        product = self.env["product.template"].create(
            {"name": "Not Sticky Product", "image_1920": _make_image_b64()}
        )
        wizard = self.env["product.template.watermark"].create({
            "product_tmpl_id": product.id,
            "watermark_type": "text",
            "watermark_text": "CUSTOM",
        })
        wizard.action_apply()
        self.assertTrue(product.original_image_1920)

        # Company watermarking is still off; a brand-new upload should
        # just land as plain, not re-apply the old custom watermark.
        new_photo = _make_image_b64(color=(0, 255, 0))
        product.write({"image_1920": new_photo})
        self.assertFalse(product.original_image_1920)
        self.assertEqual(bytes(product.image_1920), bytes(new_photo))

    def test_remove_watermark_restores_original(self):
        _configure_company_watermark(self.env, enabled=True)
        original_b64 = _make_image_b64()
        product = self.env["product.template"].create(
            {
                "name": "Remove Watermark Product",
                "is_watermark_eligible": True,
                "image_1920": original_b64,
            }
        )
        self.assertTrue(product.original_image_1920)

        product.action_remove_watermark()

        self.assertFalse(product.original_image_1920)
        self.assertEqual(bytes(product.image_1920), bytes(original_b64))

    def test_wizard_apply_covers_variant_images(self):
        """The wizard's Apply watermarks every image of the product,
        each variant's own image included, not just the main one."""
        _configure_company_watermark(self.env, enabled=False)
        product = self.env["product.template"].create({
            "name": "Wizard Variant Product", "image_1920": _make_image_b64(),
        })
        variant = product.product_variant_id
        variant.write({"image_variant_1920": _make_image_b64(color=(0, 0, 255))})
        self.assertFalse(variant.original_image_variant_1920)

        self.env["product.template.watermark"].create({
            "product_tmpl_id": product.id,
            "watermark_type": "text",
            "watermark_text": "CUSTOM",
        }).action_apply()

        self.assertTrue(product.original_image_1920)
        self.assertTrue(variant.original_image_variant_1920)

    def test_remove_watermark_reverts_variant_images(self):
        """Remove Watermark restores every image of the product, variant
        images included, not just the template's main image."""
        _configure_company_watermark(self.env, enabled=True)
        product = self.env["product.template"].create({
            "name": "Remove Variant Product", "is_watermark_eligible": True,
        })
        variant = product.product_variant_id
        original_b64 = _make_image_b64(color=(0, 0, 255))
        variant.write({"image_variant_1920": original_b64})
        self.assertTrue(product.has_watermark)

        product.action_remove_watermark()

        self.assertFalse(variant.original_image_variant_1920)
        self.assertEqual(bytes(variant.image_variant_1920), bytes(original_b64))

    def test_wizard_remove_restores_original(self):
        """The wizard's Remove button restores the original photo; it is
        only offered while the product actually carries a watermark."""
        _configure_company_watermark(self.env, enabled=True)
        original_b64 = _make_image_b64()
        product = self.env["product.template"].create({
            "name": "Wizard Remove Product",
            "is_watermark_eligible": True,
            "image_1920": original_b64,
        })
        wizard = self.env["product.template.watermark"].create({
            "product_tmpl_id": product.id,
            "watermark_type": "text",
            "watermark_text": "CUSTOM",
        })
        self.assertTrue(wizard.has_watermark)
        self.assertTrue(wizard.can_apply)

        wizard.action_remove()

        self.assertFalse(product.original_image_1920)
        self.assertEqual(bytes(product.image_1920), bytes(original_b64))
        wizard.invalidate_recordset(["has_watermark"])
        self.assertFalse(wizard.has_watermark)

    def test_watermarked_image_keeps_original_format(self):
        """The watermarked image is saved in the same format as the
        uploaded one, not always re-encoded as (much larger) PNG."""
        _configure_company_watermark(self.env, enabled=True)
        for image_format in ("PNG", "JPEG", "WEBP"):
            with self.subTest(image_format=image_format):
                product = self.env["product.template"].create({
                    "name": f"{image_format} Product",
                    "is_watermark_eligible": True,
                    "image_1920": _make_image_b64(image_format=image_format),
                })
                self.assertTrue(product.original_image_1920)
                watermarked = Image.open(io.BytesIO(base64.b64decode(product.image_1920)))
                self.assertEqual(watermarked.format, image_format)

    def test_watermarked_webp_gets_resized_alternates(self):
        """Odoo never resizes WebP server side; the smaller image fields
        must still get genuinely resized versions of the watermarked
        image, and PDF reports a JPEG fallback of it."""
        _configure_company_watermark(self.env, enabled=True)
        product = self.env["product.template"].create({
            "name": "Large WebP Product",
            "is_watermark_eligible": True,
            "image_1920": _make_image_b64(size=(600, 400), image_format="WEBP"),
        })
        self.assertTrue(product.original_image_1920)
        self.assertEqual(bytes(product.image_1920), bytes(product.image_1024))
        image_128 = Image.open(io.BytesIO(base64.b64decode(product.image_128)))
        self.assertEqual(image_128.format, "WEBP")
        self.assertEqual(max(image_128.size), 128)

        uri = self.env["ir.qweb"].with_context(webp_as_jpg=True)._get_converted_image_data_uri(
            product.image_1920
        )
        self.assertTrue(uri.startswith("data:image/jpg;"))

    def test_unsupported_image_format_left_untouched(self):
        """A GIF (possibly animated) is never watermarked: re-encoding
        it would flatten it to a single frame."""
        _configure_company_watermark(self.env, enabled=True)
        buffer = io.BytesIO()
        Image.new("RGB", (64, 64), (255, 0, 0)).save(buffer, format="GIF")
        gif_b64 = base64.b64encode(buffer.getvalue())
        product = self.env["product.template"].create({
            "name": "GIF Product",
            "is_watermark_eligible": True,
            "image_1920": gif_b64,
        })
        self.assertFalse(product.original_image_1920)
        self.assertEqual(bytes(product.image_1920), bytes(gif_b64))

    def test_marking_ineligible_removes_existing_watermark(self):
        """Unchecking is_watermark_eligible on a product that currently
        has a watermark immediately restores the original image."""
        _configure_company_watermark(self.env, enabled=True)
        original_b64 = _make_image_b64()
        product = self.env["product.template"].create(
            {
                "name": "Remove On Ineligible Product",
                "is_watermark_eligible": True,
                "image_1920": original_b64,
            }
        )
        self.assertTrue(product.original_image_1920)

        product.write({"is_watermark_eligible": False})

        self.assertFalse(product.original_image_1920)
        self.assertEqual(bytes(product.image_1920), bytes(original_b64))

    def test_marking_ineligible_reverts_variant_watermark(self):
        """Unchecking is_watermark_eligible on a template must also
        revert any of its variants' own watermarked image_variant_1920
        — eligibility lives on the template, but a variant's own image
        is a separate watermark target (see product_product.py) that
        must be reverted too, not just the template's main image."""
        _configure_company_watermark(self.env, enabled=True)
        product = self.env["product.template"].create({
            "name": "Variant Cascade Product", "is_watermark_eligible": True,
        })
        variant = product.product_variant_id
        original_b64 = _make_image_b64(color=(0, 0, 255))
        variant.write({"image_variant_1920": original_b64})
        self.assertTrue(variant.original_image_variant_1920)

        product.write({"is_watermark_eligible": False})

        variant = self.env["product.product"].browse(variant.id)
        self.assertFalse(variant.original_image_variant_1920)
        self.assertEqual(bytes(variant.image_variant_1920), bytes(original_b64))

    def test_marking_ineligible_with_no_watermark_is_a_noop(self):
        product = self.env["product.template"].create(
            {"name": "Already Plain Product", "image_1920": _make_image_b64()}
        )
        self.assertFalse(product.original_image_1920)
        # Must not raise or do anything odd when there's nothing to restore.
        product.write({"is_watermark_eligible": False})
        self.assertFalse(product.original_image_1920)

    def test_onchange_eligible_warns_only_on_genuine_uncheck(self):
        """Mirrors the settings-toggle fix: the warning must compare
        against the actually-saved value (via `_origin`), not just the
        in-memory field, so it doesn't fire from merely opening the form
        of a product that's already watermarked."""
        _configure_company_watermark(self.env, enabled=True)
        product = self.env["product.template"].create(
            {
                "name": "Onchange Eligible Product",
                "is_watermark_eligible": True,
                "image_1920": _make_image_b64(),
            }
        )
        self.assertTrue(product.original_image_1920)

        # Simulate reopening the form with no edit yet.
        reopened = self.env["product.template"].new(
            {"is_watermark_eligible": product.is_watermark_eligible}, origin=product
        )
        self.assertIsNone(reopened._onchange_is_watermark_eligible())

        # Simulate a genuine uncheck.
        reopened.is_watermark_eligible = False
        warning = reopened._onchange_is_watermark_eligible()
        self.assertTrue(warning and warning.get("warning"))

    def test_onchange_eligible_warns_for_variant_only_watermark(self):
        """The warning also fires when only a variant image (not the
        main one) carries a watermark, since unticking restores it too."""
        _configure_company_watermark(self.env, enabled=True)
        product = self.env["product.template"].create({
            "name": "Variant Only Product", "is_watermark_eligible": True,
        })
        product.product_variant_id.write({"image_variant_1920": _make_image_b64()})
        self.assertFalse(product.original_image_1920)

        reopened = self.env["product.template"].new(
            {"is_watermark_eligible": False}, origin=product
        )
        warning = reopened._onchange_is_watermark_eligible()
        self.assertTrue(warning and warning.get("warning"))

    def test_cron_backfills_every_batch(self):
        """The backfill walks records by id, not by offset: each processed
        batch drops out of the "not watermarked yet" domain, so an offset
        would skip as many unprocessed products as it just handled."""
        _configure_company_watermark(self.env, enabled=False)
        products = self.env["product.template"].create([
            {
                "name": f"Batch Product {index}",
                "is_watermark_eligible": True,
                "image_1920": _make_image_b64(color=(index * 40, 0, 0)),
            }
            for index in range(5)
        ])
        self.assertFalse(any(products.mapped("original_image_1920")))

        _configure_company_watermark(self.env, enabled=True)
        ProductTemplate = type(self.env["product.template"])
        IrCron = type(self.env["ir.cron"])
        # Batches of 2, and no real commit (forbidden inside a test).
        with patch.object(ProductTemplate, "_WATERMARK_REGEN_BATCH_SIZE", 2), \
                patch.object(IrCron, "_commit_progress", return_value=1.0):
            self.assertTrue(self.env["product.template"]._cron_regenerate_watermarked_images())

        products.invalidate_recordset(["original_image_1920"])
        self.assertTrue(all(products.mapped("original_image_1920")))

    def test_font_lookup_only_accepts_known_fonts(self):
        """An arbitrary font name (e.g. from an RPC call) never reaches the
        recursive font glob; it falls back to the default font."""
        self.assertEqual(_find_font_path("../../**/*"), _find_font_path("Arial"))

    def test_logo_saved_on_company(self):
        """The settings logo is stored on the current company and used to
        resolve product watermark settings."""
        logo_b64 = _make_image_b64(color=(0, 0, 0))
        _configure_company_watermark(
            self.env, enabled=True, watermark_type="image", watermark_logo=logo_b64
        )
        self.assertTrue(self.env.company.watermark_logo)
        product = self.env["product.template"].create({"name": "Logo Product"})
        self.assertTrue(product._get_watermark_settings()["logo"])

    def test_size_constraint_rejects_out_of_range(self):
        with self.assertRaises(ValidationError):
            self.env["res.config.settings"].create(
                {"watermark_enabled": True, "watermark_type": "text", "watermark_size": 500}
            ).execute()

    def test_variant_specific_image_watermarked_independently(self):
        _configure_company_watermark(self.env, enabled=True)
        product = self.env["product.template"].create(
            {
                "name": "Variant Watermark Product",
                "is_watermark_eligible": True,
                "image_1920": _make_image_b64(),
            }
        )
        variant = product.product_variant_id
        variant_photo = _make_image_b64(color=(0, 0, 255))
        variant.write({"image_variant_1920": variant_photo})

        self.assertTrue(variant.original_image_variant_1920)
        self.assertEqual(bytes(variant.original_image_variant_1920), bytes(variant_photo))
        self.assertNotEqual(bytes(variant.image_variant_1920), bytes(variant_photo))

    def test_variant_without_own_image_falls_back_to_template(self):
        _configure_company_watermark(self.env, enabled=True)
        product = self.env["product.template"].create(
            {
                "name": "Fallback Variant Product",
                "is_watermark_eligible": True,
                "image_1920": _make_image_b64(),
            }
        )
        variant = product.product_variant_id
        # Core Odoo's own fallback (image_variant_1920 or template's
        # image_1920) — confirms the already-watermarked template image
        # is what the variant ends up showing when it has no photo of
        # its own.
        self.assertFalse(variant.image_variant_1920)
        self.assertEqual(bytes(variant.image_1920), bytes(product.image_1920))

    def test_ineligible_product_not_auto_watermarked(self):
        """A product marked not eligible for watermarking is skipped by
        the automatic on-upload mechanism entirely, even with company
        watermarking on."""
        _configure_company_watermark(self.env, enabled=True)
        original_b64 = _make_image_b64()
        product = self.env["product.template"].create(
            {
                "name": "Ineligible Product",
                "is_watermark_eligible": False,
                "image_1920": original_b64,
            }
        )
        self.assertFalse(product.original_image_1920)
        self.assertEqual(bytes(product.image_1920), bytes(original_b64))

    def test_ineligible_variant_not_auto_watermarked(self):
        _configure_company_watermark(self.env, enabled=True)
        product = self.env["product.template"].create(
            {
                "name": "Ineligible Variant Product",
                "is_watermark_eligible": False,
                "image_1920": _make_image_b64(),
            }
        )
        variant = product.product_variant_id
        variant_photo = _make_image_b64(color=(0, 0, 255))
        variant.write({"image_variant_1920": variant_photo})

        self.assertFalse(variant.original_image_variant_1920)
        self.assertEqual(bytes(variant.image_variant_1920), bytes(variant_photo))

    def test_regenerate_domain_skips_ineligible_products(self):
        """Same domain `_cron_regenerate_watermarked_images` uses while
        watermarking is enabled — an ineligible product must be
        completely excluded (left exactly as it was) regardless of its
        watermark state, while an eligible product with no watermark yet
        is included. Verified against the domain directly rather than
        the cron method itself, for the same cr.commit()-in-test reason
        as `test_regenerate_reverts_watermarked_product_when_disabled`."""
        # Created while watermarking is off, so it starts with no
        # watermark — the case this domain is meant to backfill.
        _configure_company_watermark(self.env, enabled=False)
        eligible = self.env["product.template"].create(
            {
                "name": "Eligible Product",
                "is_watermark_eligible": True,
                "image_1920": _make_image_b64(),
            }
        )
        self.assertFalse(eligible.original_image_1920)

        _configure_company_watermark(self.env, enabled=True)
        ineligible = self.env["product.template"].create(
            {"name": "Ineligible Product 2", "image_1920": _make_image_b64(color=(0, 255, 0))}
        )
        ineligible.is_watermark_eligible = False
        # Simulate a product that was watermarked before being marked
        # ineligible (bypassing the UI button, which the wizard action
        # itself does not block).
        ineligible._apply_watermark_to_all_images(
            {"type": "text", "text": "X", "position": "bottom_right", "opacity": 0.5}
        )
        self.assertTrue(ineligible.original_image_1920)
        watermarked_bytes = bytes(ineligible.image_1920)

        domain = [
            ("image_1920", "!=", False),
            ("is_watermark_eligible", "=", True),
            ("original_image_1920", "=", False),
        ]
        matched = self.env["product.template"].search(domain)
        self.assertIn(eligible.id, matched.ids)
        self.assertNotIn(ineligible.id, matched.ids)

        matched._apply_watermark()
        # Eligible product backfilled with a watermark.
        self.assertTrue(eligible.original_image_1920)
        # Ineligible product untouched: still has its own watermark from
        # before, unaffected by the regenerate pass that skipped it.
        self.assertEqual(bytes(ineligible.image_1920), watermarked_bytes)

    def test_regenerate_does_not_override_already_watermarked_product(self):
        """While watermarking is enabled, the cron's backfill domain
        excludes any product that already has a watermark — whether it
        got there via the automatic on-upload mechanism or was
        hand-customized through the wizard — so a regenerate-all pass
        never silently re-derives/overrides it with the current company
        defaults. Only products with no watermark yet get backfilled."""
        # Created while watermarking is off, so it starts with no
        # watermark at all — the "never watermarked yet" case the
        # regenerate pass should still backfill.
        _configure_company_watermark(self.env, enabled=False)
        fresh = self.env["product.template"].create(
            {
                "name": "Fresh Product",
                "is_watermark_eligible": True,
                "image_1920": _make_image_b64(color=(0, 255, 0)),
            }
        )
        self.assertFalse(fresh.original_image_1920)

        _configure_company_watermark(
            self.env, enabled=True, watermark_text="COMPANY DEFAULT"
        )
        customized = self.env["product.template"].create(
            {
                "name": "Customized Product",
                "is_watermark_eligible": True,
                "image_1920": _make_image_b64(),
            }
        )
        # Hand-customize this product's watermark to something different
        # from the company default, simulating a wizard Apply.
        customized._apply_watermark_to_all_images(
            {"type": "text", "text": "CUSTOM", "position": "top_left", "opacity": 0.8}
        )
        customized_bytes = bytes(customized.image_1920)

        domain = [
            ("image_1920", "!=", False),
            ("is_watermark_eligible", "=", True),
            ("original_image_1920", "=", False),
        ]
        matched = self.env["product.template"].search(domain)
        self.assertNotIn(customized.id, matched.ids)
        self.assertIn(fresh.id, matched.ids)

        matched._apply_watermark()

        # Customized product untouched by the regenerate pass.
        self.assertEqual(bytes(customized.image_1920), customized_bytes)
        # Fresh product backfilled with the company default watermark.
        self.assertTrue(fresh.original_image_1920)

    def test_regenerate_reverts_watermarked_product_when_disabled(self):
        """`_apply_watermark()` still reverts an already-watermarked
        product when called directly while watermarking is disabled —
        this is the per-record capability "Remove Watermark" and marking
        a product ineligible (see `write()`) both rely on. The cron
        itself no longer calls this automatically when disabled (see
        `test_cron_does_nothing_when_disabled`); this test covers the
        lower-level method those explicit actions still depend on."""
        _configure_company_watermark(self.env, enabled=True)
        original_b64 = _make_image_b64()
        product = self.env["product.template"].create(
            {
                "name": "Revert Product",
                "is_watermark_eligible": True,
                "image_1920": original_b64,
            }
        )
        self.assertTrue(product.original_image_1920)

        _configure_company_watermark(self.env, enabled=False)
        product._apply_watermark()

        self.assertFalse(product.original_image_1920)
        self.assertEqual(bytes(product.image_1920), bytes(original_b64))

    def test_cron_does_nothing_when_disabled(self):
        """The cron must not touch anything at all while watermarking is
        disabled company-wide — not an already-watermarked product's
        image, not a fresh product's lack of one, not eligibility. It
        only ever adds watermarks; removing one is always an explicit
        action (Remove Watermark button, marking a product ineligible,
        or the mass uncheck-eligibility button). Calling the real cron
        method directly is safe here: with watermarking disabled it
        returns before any batch loop / cr.commit() (forbidden inside a
        TransactionCase) even runs."""
        _configure_company_watermark(self.env, enabled=True)
        watermarked = self.env["product.template"].create(
            {
                "name": "Already Watermarked",
                "is_watermark_eligible": True,
                "image_1920": _make_image_b64(),
            }
        )
        self.assertTrue(watermarked.original_image_1920)
        watermarked_bytes = bytes(watermarked.image_1920)

        _configure_company_watermark(self.env, enabled=False)
        never_watermarked = self.env["product.template"].create(
            {
                "name": "Never Watermarked",
                "is_watermark_eligible": True,
                "image_1920": _make_image_b64(color=(0, 255, 0)),
            }
        )
        self.assertFalse(never_watermarked.original_image_1920)

        self.env["product.template"]._cron_regenerate_watermarked_images()

        watermarked = self.env["product.template"].browse(watermarked.id)
        never_watermarked = self.env["product.template"].browse(never_watermarked.id)
        self.assertEqual(bytes(watermarked.image_1920), watermarked_bytes)
        self.assertTrue(watermarked.is_watermark_eligible)
        self.assertFalse(never_watermarked.original_image_1920)
        self.assertTrue(never_watermarked.is_watermark_eligible)

    def test_uncheck_all_products_watermark_eligibility_action(self):
        """The Settings button mass-unchecks is_watermark_eligible on
        every product, regardless of the company-wide watermark_enabled
        toggle — a deliberate, explicit admin action distinct from (and
        no longer triggered by) disabling watermarking itself."""
        _configure_company_watermark(self.env, enabled=True)
        product_a = self.env["product.template"].create(
            {
                "name": "Eligible A",
                "is_watermark_eligible": True,
                "image_1920": _make_image_b64(),
            }
        )
        product_b = self.env["product.template"].create(
            {"name": "Eligible B (no photo)", "is_watermark_eligible": True}
        )
        self.assertTrue(product_a.is_watermark_eligible)
        self.assertTrue(product_b.is_watermark_eligible)

        self.env["res.config.settings"].action_uncheck_all_products_watermark_eligibility()

        self.assertFalse(product_a.is_watermark_eligible)
        self.assertFalse(product_b.is_watermark_eligible)

        # Re-enabling watermarking should watermark product_a again
        # without anyone needing to re-check its eligibility.
        _configure_company_watermark(self.env, enabled=True)
        product_a._apply_watermark()
        self.assertTrue(product_a.original_image_1920)
