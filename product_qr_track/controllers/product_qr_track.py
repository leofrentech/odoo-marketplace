from odoo.http import Controller, request, route


class ProductQrScanTrack(Controller):

    @route(
        "/qr/<int:product_id>",
        type="http",
        methods=["GET"],
        auth="public",
        website=True,
    )
    def track_qr_scan(self, product_id=False):
        # sudo: public visitors have no read access on product.product,
        # but any published product must be resolvable from its QR code.
        product = request.env["product.product"].sudo().browse(product_id)

        if not product.exists() or not product.website_published:
            raise request.not_found()

        user_agent = request.httprequest.user_agent
        browser = user_agent.browser
        os = user_agent.platform

        country_code = request.geoip.country_code or False

        country = (
            request.env["res.country"]
            .sudo()
            .search([("code", "=", country_code)])
        )

        request.env["product.qr.visit"].sudo().create(
            {
                "product_id": product.id,
                "geoip": request.geoip.ip,
                "city": request.geoip.city.name,
                "os": os,
                "browser": browser,
                "country_id": country.id if country else False,
            }
        )

        return request.redirect(product.website_url)
