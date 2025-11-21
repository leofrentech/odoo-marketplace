# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ProductPersonalizerController(http.Controller):
    
    @http.route(
        "/shop/personalize/<int:product_id>",
        type="http",
        auth="public",
        website=True,
    )
    def personalize_page(self, product_id, **kw):
        product = (
            request.env["product.template"].sudo().browse(product_id)
        )
        return request.render(
            "leo_product_personalizer.product_personalization_page",
            {"product": product},
        )

    # ---------------------------------------------------------------------------
    # Product metadata endpoint
    # ---------------------------------------------------------------------------
    @http.route(
        ["/shop/product_personalization_data"],
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def product_personalization_data(self, product_id=None, variant_id=None, **kwargs):
        if not product_id:
            return {"error": "Missing product_id"}

        product_template = (
            request.env["product.template"].sudo().browse(int(product_id))
        )
        if not product_template:
            return {"error": "Product not found"}

        variants_data = self._get_variants_data(product_template)
        active_variant_id = (
            int(variant_id)
            if variant_id
            else variants_data[0]["id"] if variants_data else None
        )

        if not active_variant_id:
            return {"error": "No variants found"}

        designs, design_types = self._get_variant_designs(active_variant_id)
        fallback_image = self._get_best_design_image(None, active_variant_id)

        return {
            "product_id": product_template.id,
            "variants": variants_data,
            "active_variant_id": active_variant_id,
            "design_types": design_types,
            "default_design_type": design_types[0] if design_types else None,
            "designs": designs,
            "fallback_image_url": fallback_image,
        }

    def _get_variants_data(self, product_template):
        variants_data = []
        for variant in product_template.product_variant_ids:
            image_url = (
                f"/web/image/product.product/{variant.id}/image_1920"
                if variant.image_1920
                else None
            )
            variants_data.append(
                {
                    "id": variant.id,
                    "name": variant.display_name,
                    "image_url": image_url,
                }
            )
        return variants_data

    def _get_variant_designs(self, variant_id):
        variant = request.env["product.product"].sudo().browse(variant_id)
        if not variant.exists():
            return {}, []

        designs = {}
        design_types = []

        for config in variant.design_config_ids:
            design_type = config.design_type or config.label or str(config.id)
            designs[design_type] = {
                "id": config.id,
                "design_type": design_type,
                "label": config.label or config.design_type,
                "image_url": self._get_best_design_image(config, variant_id),
                "is_restricted_area": config.is_restricted_area,
                "bound_x": float(config.bound_x or 0.0),
                "bound_y": float(config.bound_y or 0.0),
                "bound_width": float(config.bound_width or 0.0),
                "bound_height": float(config.bound_height or 0.0),
            }
            design_types.append(design_type)
        return designs, design_types

    def _get_best_design_image(self, config, variant_id):
        if config and config.design_image:
            return f"/web/image/product.design.config/{config.id}/design_image"

        variant = request.env["product.product"].sudo().browse(variant_id)
        if variant.exists() and variant.image_1920:
            return f"/web/image/product.product/{variant_id}/image_1920"
        
        return None
    
    # ---------------------------------------------------------------------------
    # Add/update personalization in cart
    # ---------------------------------------------------------------------------
    @http.route(
        ["/shop/cart/update_personalization"],
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        csrf=False,
        website=True,
    )
    def update_personalization(self, variant_id=None, designs=None, add_qty=1, **kwargs):
        if not variant_id:
            return {"error": "Missing variant_id"}

        try:
            if isinstance(designs, str):
                designs = json.loads(designs)
        except Exception:
            designs = designs or {}

        if not isinstance(designs, dict):
            return {"error": "Invalid designs payload"}

        try:
            website = request.env["website"].sudo().get_current_website()
            order_sudo = website._create_cart()

            values = order_sudo.with_context(skip_cart_verification=True)._cart_add(
                product_id=int(variant_id),
                quantity=float(add_qty),
            )

            line_id = values.get("line_id")
            if not line_id:
                return {"error": "Could not create cart line"}

            line = request.env["sale.order.line"].sudo().browse(int(line_id))
            variant = request.env["product.product"].sudo().browse(int(variant_id))

        except Exception as e:
            _logger.exception("Cart update error: %s", e)
            return {"error": str(e)}

        created = []
        
        # Get ALL design configs for this variant
        all_configs = variant.design_config_ids
        
        for config in all_configs:
            d_type = config.design_type
            d_data = designs.get(d_type, {})
            
            try:
                personalized_json = d_data.get("json") if isinstance(d_data, dict) else None
                preview_dataurl = d_data.get("preview") if isinstance(d_data, dict) else None
                
                preview_bin = False
                
                if preview_dataurl:
                    if "data:" in str(preview_dataurl):
                        try:
                            preview_bin = preview_dataurl.split(",", 1)[1]
                        except Exception:
                            pass
                    
                vals = {
                    "sale_order_line_id": line.id,
                    "design_type": d_type,
                    "design_config_id": config.id,
                    "personalized_json": personalized_json or json.dumps({"objects": []}),
                    "product_image": preview_bin if preview_bin else config.design_image,
                }

                rec = request.env["sale.order.line.personalization"].sudo().create(vals)
                created.append(rec.id)

            except Exception as e:
                _logger.exception("Save personalization error for %s: %s", d_type, e)

        return {
            "success": True,
            "line_id": line.id,
            "created_personalization_ids": created,
            "cart_quantity": order_sudo.cart_quantity,
        }