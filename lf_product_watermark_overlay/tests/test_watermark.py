import base64
import io

from PIL import Image

from odoo.exceptions import ValidationError
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
class TestProductWatermark(TransactionCase):

    def test_opacity_constraint_rejects_out_of_range(self):
        with self.assertRaises(ValidationError):
            self.env["res.config.settings"].create(
                {"watermark_enabled": True, "watermark_type": "text", "watermark_opacity": 1.5}
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

        wizard = self.env["product.watermark.wizard"].create({
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
        wizard = self.env["product.watermark.wizard"].create({
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
        ineligible.action_apply_watermark(
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
        customized.action_apply_watermark(
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
