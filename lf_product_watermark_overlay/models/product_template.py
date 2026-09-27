import threading

from odoo import _, api, fields, models

from .watermark_utils import DEFAULT_LOGO_SIZE, render_watermark, resolve_watermark_type


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
    has_watermark = fields.Boolean(
        compute="_compute_has_watermark",
        help="Technical field: whether any of this product's images (see "
             "`_has_any_watermark()`) currently carries a watermark.",
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

    @api.depends("original_image_1920", "product_variant_ids.original_image_variant_1920")
    def _compute_has_watermark(self):
        for product in self:
            product.has_watermark = product._has_any_watermark()

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
        # `has_watermark` of the saved record covers every image that
        # unticking restores (variants, extra media, ...), not just the
        # main one.
        was_eligible = bool(self._origin) and self._origin.is_watermark_eligible
        if was_eligible and not self.is_watermark_eligible and self._origin.has_watermark:
            return {
                "warning": {
                    "title": _("This will remove the watermark"),
                    "message": _(
                        "Marking this product as not eligible for watermarking "
                        "will restore its original, unwatermarked images once saved."
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
            self._remove_all_watermarks()

        return res

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    def action_remove_watermark(self):
        """Restore the original, unwatermarked photo of every image of
        this product."""
        self.ensure_one()
        self._remove_all_watermarks()

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
        overridden by this pass.

        Returns whether the backfill ran — False when watermarking is
        disabled — so extensions backfilling further images only
        continue when True.
        """
        # sudo: reading the global config parameter must work regardless
        # of the calling user's own access rights.
        watermark_enabled = self.env["ir.config_parameter"].sudo().get_param(
            "lf_product_watermark_overlay.watermark_enabled", "False"
        ) == "True"
        if not watermark_enabled:
            return False

        self._watermark_in_batches(
            self,
            [
                ("image_1920", "!=", False),
                ("is_watermark_eligible", "=", True),
                ("original_image_1920", "=", False),
            ],
            lambda batch: batch._apply_watermark(),
        )
        return self._watermark_in_batches(
            self.env["product.product"],
            [
                ("image_variant_1920", "!=", False),
                ("product_tmpl_id.is_watermark_eligible", "=", True),
                ("original_image_variant_1920", "=", False),
            ],
            lambda batch: batch._apply_variant_watermark(),
        )

    @api.model
    def _watermark_in_batches(self, records_model, domain, apply):
        """Run `apply` on every `records_model` record matching `domain`,
        in committed batches, for the backfill cron.

        Walks the records by increasing id rather than by offset: the
        backfill domain excludes already-watermarked records, so each
        processed batch drops out of it and an offset would skip as many
        unprocessed ones. Records that can't be watermarked (unsupported
        format, ...) still match afterwards, which the id cursor also
        steps past instead of retrying forever.

        Each batch is committed, except while running tests (committing
        is forbidden inside a test), so should the cron be killed by the
        server's time limit, the committed batches stay done and the
        next run picks up the rest.

        Always returns True once every matching record was processed.
        """
        auto_commit = not getattr(threading.current_thread(), "testing", False)
        last_id = 0
        while True:
            batch = records_model.search(
                domain + [("id", ">", last_id)],
                order="id",
                limit=self._WATERMARK_REGEN_BATCH_SIZE,
            )
            if not batch:
                return True
            apply(batch)
            last_id = batch[-1].id
            if auto_commit:
                # Commit each batch so a cron killed by the server's time
                # limit keeps the work already done (see docstring).
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

    def _apply_watermark_to_all_images(self, settings):
        """Apply `settings` to every image of these products: the main
        image and each variant's own `image_variant_1920`. Modules
        watermarking further images of a product (e.g. eCommerce extra
        media) extend this, as they do `_remove_all_watermarks()`."""
        self._apply_watermark(settings)
        self.env["product.product"].search([
            ("product_tmpl_id", "in", self.ids),
            ("image_variant_1920", "!=", False),
        ])._apply_variant_watermark(settings)

    def _remove_all_watermarks(self):
        """Restore the original photo of every image of these products
        that currently carries a watermark: the main image and each
        variant's own `image_variant_1920`. Modules watermarking further
        images of a product (e.g. eCommerce extra media) extend this."""
        self.filtered("original_image_1920")._apply_watermark({"type": "none"})
        self.product_variant_ids.filtered(
            "original_image_variant_1920"
        )._apply_variant_watermark({"type": "none"})

    def _has_any_watermark(self):
        """Whether any image `_remove_all_watermarks()` would restore
        currently carries a watermark. Extended alongside it."""
        self.ensure_one()
        return bool(self.original_image_1920) or bool(self.env["product.product"].search_count([
            ("product_tmpl_id", "=", self.id),
            ("original_image_variant_1920", "!=", False),
        ], limit=1))

    def _get_watermark_settings(self):
        """Resolve the company-wide watermark settings for this product."""
        self.ensure_one()
        # sudo: reading global config parameters must work regardless of
        # the calling user's own access rights.
        params = self.env["ir.config_parameter"].sudo()

        # sudo: the product's company may not be one the current user
        # (or the cron's user) is allowed to read.
        company = (self.company_id or self.env.company).sudo()

        enabled = params.get_param("lf_product_watermark_overlay.watermark_enabled", "False") == "True"
        watermark_type = params.get_param("lf_product_watermark_overlay.watermark_type", "image")

        return {
            "type": resolve_watermark_type(enabled, watermark_type),
            "logo": company.watermark_logo,
            "text": params.get_param("lf_product_watermark_overlay.watermark_text", company.name),
            "font": params.get_param("lf_product_watermark_overlay.watermark_font", "Arial"),
            "size": int(params.get_param("lf_product_watermark_overlay.watermark_size", 6)),
            "logo_size": int(params.get_param(
                "lf_product_watermark_overlay.watermark_logo_size", DEFAULT_LOGO_SIZE
            )),
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

            watermarked = render_watermark(self.env, original, product_settings)
            if not watermarked:
                continue  # unsupported format or failed rendering, leave as is
            vals = {"image_1920": watermarked}
            if not product.original_image_1920:
                vals["original_image_1920"] = original
            super(ProductTemplate, product).write(vals)
