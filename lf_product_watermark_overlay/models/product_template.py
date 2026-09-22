import logging

from odoo import fields, models, api
from .watermark_utils import decode_image, encode_image, apply_watermark, resolve_watermark_type


_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "product.template"

    _WATERMARK_REGEN_BATCH_SIZE = 200

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    is_watermark_eligible = fields.Boolean(
        string="Eligible for Watermark",
        help="Check to include this product in watermarking: automatic "
             "watermarking on new photo uploads, the \"Add/Update "
             "Watermark\" button, and \"Regenerate All Images\" all "
             "require this. Defaults to unchecked, so enabling watermarking "
             "company-wide never silently watermarks — and duplicates the "
             "storage of — every product's image; each one has to be "
             "opted in explicitly.",
    )
    watermark_globally_enabled = fields.Boolean(
        compute="_compute_watermark_globally_enabled",
        help="Technical field mirroring the company-wide \"Enable "
             "Watermark\" setting; used only to hide the eligibility "
             "checkbox above when watermarking isn't enabled at all.",
    )
    original_image_1920 = fields.Image(
        string="Original Image",
        store=True,
        readonly=True,
        help="The untouched original photo. Set automatically the first "
             "time a watermark is applied to this product's image, and "
             "used to re-derive the watermark whenever settings change "
             "so the watermark is never applied on top of itself. Empty "
             "means image_1920 is still the plain, unwatermarked photo.",
    )

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    @api.depends()
    def _compute_watermark_globally_enabled(self):
        # No field dependency: this mirrors external (config parameter)
        # state, not anything on the record itself, so it's recomputed
        # fresh per read rather than tracked via `@api.depends`.
        # sudo: reading the global config parameter must work regardless
        # of the calling user's own access rights.
        enabled = self.env["ir.config_parameter"].sudo().get_param(
            "lf_product_watermark_overlay.watermark_enabled", "False"
        ) == "True"
        self.watermark_globally_enabled = enabled

    # ------------------------------------------------------------------
    # 5. SELECTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 6. CONSTRAINTS METHODS AND ONCHANGE METHODS
    # ------------------------------------------------------------------

    @api.onchange('is_watermark_eligible')
    def _onchange_is_watermark_eligible(self):
        # `self._origin` is the actually-saved record (falsy/empty for a
        # product that hasn't been saved yet); comparing against it,
        # rather than just the in-memory value, avoids firing this
        # warning just from opening the form of a product that's already
        # ineligible (the same false-positive the settings toggle had).
        was_eligible = bool(self._origin) and self._origin.is_watermark_eligible
        if was_eligible and not self.is_watermark_eligible and self.original_image_1920:
            return {
                "warning": {
                    "title": self.env._("This will remove the watermark"),
                    "message": self.env._(
                        "Marking this product as not eligible for watermarking "
                        "will restore its original, unwatermarked image once saved."
                    ),
                }
            }

    # ------------------------------------------------------------------
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-apply the company-wide watermark to any eligible product
        created with a photo already set."""
        records = super().create(vals_list)
        records.filtered(
            lambda p: p.image_1920 and p.is_watermark_eligible
        )._apply_watermark()
        return records

    def write(self, vals):
        """Auto re-apply the watermark whenever a new photo is uploaded,
        and immediately remove any existing watermark from a product
        that just got marked not eligible."""
        res = super().write(vals)
        if "image_1920" in vals:
            # A freshly uploaded photo is never "sticky" to a previous
            # watermark (company default or wizard-applied) — clear any
            # stale original first so `_apply_watermark()` treats the
            # new upload itself as the original to (maybe) watermark,
            # instead of mistaking this for a "remove watermark" request
            # and restoring the *old* photo over the new one. Applies to
            # every product in `self` regardless of eligibility, so an
            # ineligible product never keeps a stale original around.
            super(ProductTemplate, self).write({"original_image_1920": False})
            self.filtered("is_watermark_eligible")._apply_watermark()

        if "is_watermark_eligible" in vals and not vals["is_watermark_eligible"]:
            # Restrict to products that actually have a watermark right
            # now; `_apply_watermark({"type": "none"})` already no-ops
            # cleanly when there's nothing to restore, but filtering here
            # avoids the extra call for the common case of nothing to do.
            self.filtered("original_image_1920")._apply_watermark({"type": "none"})
            # Eligibility lives on the template, but a variant's own
            # `image_variant_1920` (see product_product.py) is a
            # separate watermark target that must be reverted too, not
            # just the template's own main image.
            self.mapped("product_variant_ids").filtered(
                "original_image_variant_1920"
            )._apply_variant_watermark({"type": "none"})

        return res

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    def action_apply_watermark(self, settings):
        """Apply a one-off custom watermark to this product's current
        photo (called by the watermark wizard)."""
        self.ensure_one()
        self._apply_watermark(settings)

    def action_remove_watermark(self):
        """Restore this product's original, unwatermarked photo."""
        self.ensure_one()
        self._apply_watermark({"type": "none"})

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    @api.model
    def _cron_regenerate_watermarked_images(self):
        """Backfill a watermark on every eligible product (and variant)
        that has a photo but no watermark yet.

        Does nothing at all — not even a query — if watermarking is
        currently disabled company-wide. This cron only ever *adds*
        watermarks; it never removes/reverts one. Removing an existing
        watermark is always an explicit action instead: the per-product
        "Remove Watermark" button, marking a product ineligible (see
        `write()`), or mass-unchecking eligibility (see
        `ResConfigSettings.action_uncheck_all_products_watermark_eligibility`).

        Runs as a scheduled action (triggered on-demand from the settings
        button, see `ResConfigSettings.regenerate_all_images`) instead of
        inline on the request, so a large catalog never blocks the UI or
        risks an HTTP timeout. Products with `is_watermark_eligible =
        False` are skipped entirely, left untouched regardless of their
        current state. A product that already has a watermark — whether
        from the automatic on-upload mechanism or customized by hand via
        the wizard — is also excluded, never silently re-derived/
        overridden by this pass. Processed in batches, committing after
        each one: this method only ever runs inside its own cron
        cursor/transaction (never inline on a user request), so a manual
        commit here is safe and keeps one huge catalog from being a
        single all-or-nothing transaction.
        """
        # sudo: reading the global config parameter must work regardless
        # of the calling user's own access rights.
        watermark_enabled = self.env["ir.config_parameter"].sudo().get_param(
            "lf_product_watermark_overlay.watermark_enabled", "False"
        ) == "True"
        if not watermark_enabled:
            return

        domain = [
            ("image_1920", "!=", False),
            ("is_watermark_eligible", "=", True),
            ("original_image_1920", "=", False),
        ]
        total = self.search_count(domain)
        processed = 0
        while processed < total:
            batch = self.search(domain, limit=self._WATERMARK_REGEN_BATCH_SIZE, offset=processed)
            if not batch:
                break
            batch._apply_watermark()
            processed += len(batch)
            self.env.cr.commit()

        variants = self.env["product.product"]
        variant_domain = [
            ("image_variant_1920", "!=", False),
            ("product_tmpl_id.is_watermark_eligible", "=", True),
            ("original_image_variant_1920", "=", False),
        ]
        variant_total = variants.search_count(variant_domain)
        processed = 0
        while processed < variant_total:
            batch = variants.search(variant_domain, limit=self._WATERMARK_REGEN_BATCH_SIZE, offset=processed)
            if not batch:
                break
            batch._apply_variant_watermark()
            processed += len(batch)
            self.env.cr.commit()

    def _uncheck_watermark_eligibility_for_all_products(self):
        """Mass-uncheck `is_watermark_eligible` on every product.

        A deliberate, explicit admin action (triggered from a Settings
        button, see `ResConfigSettings.action_uncheck_all_products_
        watermark_eligibility`) rather than an automatic side effect of
        disabling watermarking, so a product's eligibility only ever
        changes because someone actually chose to change it."""
        self.search([("is_watermark_eligible", "=", True)]).write(
            {"is_watermark_eligible": False}
        )

    def _get_watermark_settings(self):
        """Resolve the company-wide watermark settings for this product."""
        self.ensure_one()
        # sudo: reading global config parameters must work regardless of
        # the calling user's own access rights.
        params = self.env["ir.config_parameter"].sudo()

        company = self.company_id or self.env.company
        # sudo: a user computing this product's watermark may not have
        # direct read access to another record's (res.company) attachment.
        logo_attachment = self.env["ir.attachment"].sudo().search(
            [
                ("res_model", "=", "res.company"),
                ("res_field", "=", "watermark_logo"),
                ("res_id", "=", company.id),
            ],
            limit=1,
        )

        enabled = params.get_param("lf_product_watermark_overlay.watermark_enabled", "False") == "True"
        watermark_type = params.get_param("lf_product_watermark_overlay.watermark_type", "image")

        return {
            "type": resolve_watermark_type(enabled, watermark_type),
            "logo": logo_attachment.datas if logo_attachment else False,
            "text": params.get_param("lf_product_watermark_overlay.watermark_text", company.name),
            "font": params.get_param("lf_product_watermark_overlay.watermark_font", "Arial"),
            "size": int(params.get_param("lf_product_watermark_overlay.watermark_size", 6)),
            "color": params.get_param("lf_product_watermark_overlay.watermark_color", "#FFFFFF"),
            "position": params.get_param(
                "lf_product_watermark_overlay.watermark_position", "bottom_right"
            ),
            "opacity": float(
                params.get_param("lf_product_watermark_overlay.watermark_opacity", 0.5)
            ),
        }

    def _apply_watermark(self, settings=None):
        """Apply (or remove) a watermark on `image_1920`.

        `settings` overrides the resolved company defaults for every
        record in `self` (used by the wizard's Apply/Remove actions);
        when omitted, each product resolves its own settings via
        `_get_watermark_settings()` (the automatic, on-upload mechanism).

        Always sources pixels from `original_image_1920` once it exists
        (the single source of truth), so re-applying with new settings
        never watermarks an already-watermarked image. `original_image_1920`
        is captured from the current `image_1920` the first time a
        watermark is actually applied.
        """
        for product in self:
            product_settings = settings if settings is not None else product._get_watermark_settings()

            if product_settings["type"] == "none":
                if not product.original_image_1920:
                    continue  # already plain, nothing to restore
                super(ProductTemplate, product).write({
                    "image_1920": product.original_image_1920,
                    "original_image_1920": False,
                })
                continue

            original = product.original_image_1920 or product.image_1920
            if not original:
                continue  # no photo at all yet, nothing to watermark

            try:
                base_image = decode_image(original)
                result = apply_watermark(base_image, product_settings)
                vals = {"image_1920": encode_image(result)}
                if not product.original_image_1920:
                    vals["original_image_1920"] = original
                # Top-level guard: a bad image/font/setting must never
                # block saving the product itself, only skip its watermark.
                super(ProductTemplate, product).write(vals)

            except Exception as e:
                _logger.warning(
                    "Watermark failed for product %s: %s",
                    product.id,
                    str(e),
                )
