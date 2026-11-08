import base64
import io
import json
import re
import zipfile

from werkzeug.exceptions import Forbidden, NotFound

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.lf_product_personalizer.models.design_tools import (
    check_json_size,
    decode_data_url,
    extract_artwork,
    max_upload_bytes,
    parse_json,
    sanitize_canvas_json,
)

IMAGE_FIELDS = ("product_image", "print_image", "print_svg")


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise NotFound() from None


class ProductPersonalizerController(http.Controller):

    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------

    def _lf_get_product(self, product_id):
        """Return the product template (sudo) if the visitor may personalize it."""
        product = request.env["product.template"].browse(_to_int(product_id)).exists()
        if (
            not product
            or not product.has_access("read")
            or not product.can_access_from_current_website()
            or not product.sudo()._lf_is_personalizable()
        ):
            raise NotFound()
        return product.sudo()

    def _lf_get_variant(self, product, variant_id=None):
        variants = product.product_variant_ids.filtered("sale_ok")
        if variant_id:
            variant = variants.filtered(lambda v: v.id == _to_int(variant_id))
            if not variant:
                raise NotFound()
            return variant
        return variants[:1]

    def _lf_get_cart_line(self, line_id):
        """Only lines of the visitor's own, still editable cart."""
        order = request.cart
        line = order.order_line.filtered(lambda l: l.id == _to_int(line_id)) if order else None
        if not line or not line.personalization_ids:
            raise NotFound()
        return line

    def _lf_get_revision_line(self, line_id, access_token=None):
        """Line of a placed order with a rejected design, for its customer only."""
        line = request.env["sale.order.line"].sudo().browse(_to_int(line_id)).exists()
        if (
            not line
            or line.order_id.state == "cancel"
            or "rejected" not in line.personalization_ids.mapped("approval_state")
        ):
            raise NotFound()
        order = line.order_id
        has_token = bool(
            access_token and order.access_token and consteq(order.access_token, access_token)
        )
        is_customer = not request.env.user._is_public() and order.with_user(
            request.env.user
        ).has_access("read")
        if not (has_token or is_customer):
            raise NotFound()
        return line

    def _lf_get_saved_design(self, design_id, access_token=None):
        design = request.env["product.design.saved"].sudo().browse(_to_int(design_id)).exists()
        if not design:
            raise NotFound()
        is_owner = (
            not request.env.user._is_public()
            and design.partner_id == request.env.user.partner_id
        )
        if not is_owner and not (
            access_token and design.access_token and consteq(design.access_token, access_token)
        ):
            raise NotFound()
        return design

    def _lf_can_manage_presets(self):
        user = request.env.user
        return user.has_group("sales_team.group_sale_manager") or user.has_group(
            "website.group_website_designer"
        )

    def _lf_currency_info(self):
        currency = request.website.currency_id
        return {
            "symbol": currency.symbol,
            "position": currency.position,
            "digits": currency.decimal_places,
        }

    def _lf_convert_price(self, product, amount):
        if not amount:
            return 0.0
        return product.currency_id._convert(
            amount, request.website.currency_id, request.website.company_id,
        )

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def _lf_render_editor(self, product, **values):
        return request.render(
            "lf_product_personalizer.product_personalization_page",
            {"product": product, "main_object": product, **values},
        )

    @http.route(
        "/shop/personalize/<int:product_id>",
        type="http", auth="public", website=True, sitemap=False,
    )
    def personalize_page(self, product_id, variant_id=None, **kwargs):
        product = self._lf_get_product(product_id)
        variant = self._lf_get_variant(product, variant_id)
        return self._lf_render_editor(product, variant_id=variant.id)

    @http.route(
        "/shop/personalize/edit/<int:line_id>",
        type="http", auth="public", website=True, sitemap=False,
    )
    def personalize_edit(self, line_id, **kwargs):
        line = self._lf_get_cart_line(line_id)
        return self._lf_render_editor(
            line.product_id.product_tmpl_id.sudo(),
            variant_id=line.product_id.id,
            line=line,
            quantity=int(line.product_uom_qty),
        )

    @http.route(
        "/shop/personalize/revise/<int:line_id>",
        type="http", auth="public", website=True, sitemap=False,
    )
    def personalize_revise(self, line_id, access_token=None, **kwargs):
        line = self._lf_get_revision_line(line_id, access_token)
        return self._lf_render_editor(
            line.product_id.product_tmpl_id.sudo(),
            variant_id=line.product_id.id,
            line=line,
            revision=True,
            rejected=line.personalization_ids.filtered(
                lambda p: p.approval_state == "rejected"
            ),
            access_token=access_token or "",
            back_url=line.order_id.get_portal_url(),
        )

    @http.route(
        "/shop/personalize/design/<int:design_id>",
        type="http", auth="public", website=True, sitemap=False,
    )
    def personalize_saved_design(self, design_id, access_token=None, **kwargs):
        design = self._lf_get_saved_design(design_id, access_token)
        product = self._lf_get_product(design.product_tmpl_id.id)
        variant = design.product_id if design.product_id in product.product_variant_ids else None
        return self._lf_render_editor(
            product,
            variant_id=(variant or self._lf_get_variant(product)).id,
            saved_design=design,
            access_token=access_token or "",
        )

    # ------------------------------------------------------------------
    # Editor data
    # ------------------------------------------------------------------

    @http.route("/shop/personalize/data", type="jsonrpc", auth="public", website=True)
    def personalization_data(
        self, product_id, variant_id=None, line_id=None, design_id=None, access_token=None,
        revision=False, **kw
    ):
        if revision:
            # The order is placed: the product may not be published anymore.
            line = self._lf_get_revision_line(line_id, access_token)
            product = line.product_id.product_tmpl_id.sudo()
            variant = line.product_id
        else:
            product = self._lf_get_product(product_id)
            variant = self._lf_get_variant(product, variant_id)
        areas = product._lf_get_areas(variant)

        designs = {}
        if line_id:
            line = line if revision else self._lf_get_cart_line(line_id)
            designs = {
                str(p.design_config_id.id): {"json": p._lf_canvas_data()}
                for p in line.personalization_ids if p.design_config_id
            }
        elif design_id:
            saved = self._lf_get_saved_design(design_id, access_token)
            designs = parse_json(request.env, saved.design_json)

        settings = product._lf_get_editor_settings()
        presets = product._lf_get_presets()
        cliparts = request.env["product.design.clipart"].sudo().search([])
        return {
            "product_id": product.id,
            "product_name": product.display_name,
            "active_variant_id": variant.id,
            "variants": [
                {
                    "id": v.id,
                    "name": v.display_name,
                    "image_url": f"/web/image/product.product/{v.id}/image_256",
                }
                for v in product.product_variant_ids.filtered("sale_ok")
                if product._lf_get_areas(v)
            ],
            "areas": [area._lf_to_frontend(variant) for area in areas],
            "designs": designs,
            "settings": settings,
            "pricing": {
                "currency": self._lf_currency_info(),
                "fee": self._lf_convert_price(product, product.personalization_fee),
                "areas": {
                    str(area.id): self._lf_convert_price(product, area.price_extra)
                    for area in areas
                },
            },
            "cliparts": cliparts._lf_to_frontend() if settings["allow_clipart"] else [],
            "presets": [
                {
                    "id": preset.id,
                    "name": preset.name,
                    "preview_url": f"/web/image/product.design.preset/{preset.id}/preview_image",
                    "designs": parse_json(request.env, preset.design_json),
                }
                for preset in presets
            ],
            "can_manage_presets": self._lf_can_manage_presets(),
            "is_public_user": request.env.user._is_public(),
            "max_upload_mb": max_upload_bytes(request.env) // (1024 * 1024),
            "login_url": f"/web/login?redirect=/shop/personalize/{product.id}",
        }

    # ------------------------------------------------------------------
    # Cart
    # ------------------------------------------------------------------

    def _lf_quantity(self, quantity):
        try:
            quantity = float(quantity or 1)
        except (TypeError, ValueError):
            quantity = 1.0
        return max(1.0, quantity)

    @http.route("/shop/personalize/add", type="jsonrpc", auth="public", website=True)
    def personalization_add(self, product_id, variant_id, designs, quantity=1, **kw):
        product = self._lf_get_product(product_id)
        variant = self._lf_get_variant(product, variant_id)
        try:
            with request.env.cr.savepoint():
                order_sudo = request.cart or request.website._create_cart()
                values = order_sudo.with_context(lf_personalized=True)._cart_add(
                    product_id=variant.id, quantity=self._lf_quantity(quantity),
                )
                line = order_sudo.order_line.filtered(lambda l: l.id == values.get("line_id"))
                if not line:
                    raise UserError(values.get("warning") or _("This product is not available."))
                line._lf_set_personalization(parse_json(request.env, designs))
        except UserError as error:
            return {"error": error.args[0]}
        return {
            "success": True,
            "line_id": line.id,
            "cart_quantity": order_sudo.cart_quantity,
            "warning": values.get("warning"),
        }

    @http.route("/shop/personalize/update", type="jsonrpc", auth="public", website=True)
    def personalization_update(self, line_id, designs, quantity=1, **kw):
        line = self._lf_get_cart_line(line_id)
        order_sudo = line.order_id
        try:
            with request.env.cr.savepoint():
                values = order_sudo._cart_update_line_quantity(
                    line.id, self._lf_quantity(quantity)
                )
                line._lf_set_personalization(parse_json(request.env, designs))
        except UserError as error:
            return {"error": error.args[0]}
        return {
            "success": True,
            "line_id": line.id,
            "cart_quantity": order_sudo.cart_quantity,
            "warning": values.get("warning"),
        }

    @http.route("/shop/personalize/revise", type="jsonrpc", auth="public", website=True)
    def personalization_revise(self, line_id, designs, access_token=None, **kw):
        line = self._lf_get_revision_line(line_id, access_token)
        try:
            with request.env.cr.savepoint():
                line._lf_set_personalization(parse_json(request.env, designs), revision=True)
        except UserError as error:
            return {"error": error.args[0]}
        line.order_id._lf_notify_design_revised(line)
        return {"success": True, "redirect_url": line.order_id.get_portal_url()}

    # ------------------------------------------------------------------
    # Saved designs & ready-made templates
    # ------------------------------------------------------------------

    def _lf_clean_designs(self, product, variant, designs):
        designs = parse_json(request.env, designs)
        if not isinstance(designs, dict):
            raise UserError(_("The design data is invalid."))
        area_keys = {str(area.id) for area in product._lf_get_areas(variant)}
        clean = {}
        for key, design in designs.items():
            if key not in area_keys or not isinstance(design, dict):
                continue
            canvas = sanitize_canvas_json(
                request.env, design.get("json"), product.personalization_max_text_length
            )
            if canvas["objects"]:
                clean[key] = {"json": canvas}
        if not clean:
            raise UserError(_("Add some text or an image to your design first."))
        return clean

    def _lf_store_designs(self, record, designs, preview):
        for key, design in designs.items():
            extract_artwork(record.env, design["json"], record._name, record.id, f"area-{key}")
        check_json_size(record.env, designs)
        values = {"design_json": json.dumps(designs)}
        if preview:
            raw, _mimetype = decode_data_url(record.env, preview, max_upload_bytes(record.env))
            values["preview_image"] = base64.b64encode(raw)
        record.write(values)

    @http.route("/shop/personalize/save_design", type="jsonrpc", auth="public", website=True)
    def personalization_save_design(
        self, product_id, variant_id, designs, name=None, preview=None, design_id=None, **kw
    ):
        product = self._lf_get_product(product_id)
        if request.env.user._is_public():
            return {"login_required": True}
        variant = self._lf_get_variant(product, variant_id)
        try:
            with request.env.cr.savepoint():
                clean = self._lf_clean_designs(product, variant, designs)
                Saved = request.env["product.design.saved"].sudo()
                design = Saved.browse()
                if design_id:
                    design = Saved.search([
                        ("id", "=", _to_int(design_id)),
                        ("partner_id", "=", request.env.user.partner_id.id),
                    ])
                if not design:
                    design = Saved.create({
                        "name": (name or "").strip()[:100] or product.name,
                        "partner_id": request.env.user.partner_id.id,
                        "product_tmpl_id": product.id,
                        "product_id": variant.id,
                        "website_id": request.website.id,
                        "design_json": "{}",
                    })
                elif name:
                    design.name = name.strip()[:100]
                self._lf_store_designs(design, clean, preview)
        except UserError as error:
            return {"error": error.args[0]}
        return {
            "success": True,
            "design_id": design.id,
            "share_url": design.get_base_url() + design.get_portal_url(),
        }

    @http.route("/shop/personalize/save_preset", type="jsonrpc", auth="user", website=True)
    def personalization_save_preset(self, product_id, variant_id, designs, name, preview=None, **kw):
        if not self._lf_can_manage_presets():
            raise Forbidden()
        product = self._lf_get_product(product_id)
        variant = self._lf_get_variant(product, variant_id)
        try:
            with request.env.cr.savepoint():
                clean = self._lf_clean_designs(product, variant, designs)
                uses_set = product.design_set_id and not product.design_config_ids
                preset = request.env["product.design.preset"].sudo().create({
                    "name": (name or "").strip()[:100] or product.name,
                    "product_tmpl_id": False if uses_set else product.id,
                    "design_set_id": product.design_set_id.id if uses_set else False,
                    "design_json": "{}",
                })
                self._lf_store_designs(preset, clean, preview)
        except UserError as error:
            return {"error": error.args[0]}
        return {"success": True, "preset_id": preset.id}

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------

    @http.route(
        "/shop/personalization/<int:personalization_id>/<string:field>",
        type="http", auth="public", website=True, sitemap=False,
    )
    def personalization_image(self, personalization_id, field, access_token=None, download=False):
        if field not in IMAGE_FIELDS:
            raise NotFound()
        record = request.env["sale.order.line.personalization"].browse(personalization_id)
        record_sudo = record.sudo().exists()
        if not record_sudo:
            raise NotFound()
        allowed = (
            (request.env.user._is_internal() and record.has_access("read"))
            or (request.cart and record_sudo.order_id == request.cart)
            or (
                access_token
                and record_sudo.order_id.access_token
                and consteq(record_sudo.order_id.access_token, access_token)
            )
        )
        if not allowed:
            raise NotFound()
        filename = {
            "print_image": record_sudo.print_image_filename,
            "print_svg": record_sudo.print_svg_filename,
        }.get(field)
        stream = request.env["ir.binary"]._get_stream_from(
            record_sudo, field, filename=filename,
            default_mimetype="image/png",
        )
        # SVG files come from visitors: never render them inline on our domain.
        as_attachment = bool(download) or field == "print_svg"
        return stream.get_response(as_attachment=as_attachment)

    @http.route(
        "/shop/personalize/area/<int:area_id>/image",
        type="http", auth="public", website=True, sitemap=False,
    )
    def personalization_area_image(self, area_id, **kw):
        """Mockup of an area, visible to whoever can see one of its products."""
        area = request.env["product.design.config"].sudo().browse(area_id).exists()
        if not area or not area.design_image:
            raise NotFound()
        products = area.product_tmpl_id or area.design_set_id.product_tmpl_ids
        visible = any(
            product.with_user(request.env.user).has_access("read")
            and product.can_access_from_current_website()
            for product in products
        )
        if not visible and not request.env.user._is_internal():
            raise NotFound()
        stream = request.env["ir.binary"]._get_stream_from(area, "design_image")
        return stream.get_response(max_age=86400 if kw.get("unique") else 0)

    @http.route(
        "/lf_personalizer/order/<int:order_id>/artwork.zip",
        type="http", auth="user", sitemap=False,
    )
    def order_artwork_zip(self, order_id, **kw):
        order = request.env["sale.order"].browse(order_id).exists()
        if not order:
            raise NotFound()
        try:
            order.check_access("read")
            order.personalization_ids.check_access("read")
        except AccessError:
            raise Forbidden() from None

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for index, line in enumerate(order.order_line.filtered("personalization_ids"), 1):
                folder = self._lf_safe_name(f"{index:02d}-{line.product_id.display_name}")
                for design in line.personalization_ids.filtered("is_customized"):
                    area = self._lf_safe_name(design.design_type)
                    files = {
                        f"{area}-print.png": design.print_image,
                        f"{area}-print.svg": design.print_svg,
                        f"{area}-preview.png": design.product_image,
                    }
                    for name, b64 in files.items():
                        if b64:
                            archive.writestr(
                                f"{folder}/{name}", base64.b64decode(b64)
                            )
                    for attachment in design.sudo().artwork_attachment_ids:
                        archive.writestr(
                            f"{folder}/{area}-original-{self._lf_safe_name(attachment.name)}",
                            attachment.raw,
                        )
                    archive.writestr(f"{folder}/{area}-design.json", design.personalized_json or "{}")
        filename = f"{self._lf_safe_name(order.name)}-artwork.zip"
        return request.make_response(
            buffer.getvalue(),
            headers=[
                ("Content-Type", "application/zip"),
                ("Content-Disposition", http.content_disposition(filename)),
            ],
        )

    @staticmethod
    def _lf_safe_name(name):
        return re.sub(r"[^\w.-]+", "-", name or "file").strip("-")[:80] or "file"
