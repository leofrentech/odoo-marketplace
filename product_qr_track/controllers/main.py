from odoo.http import request, route, Controller


class ProductQrScanTrack(Controller):

    @route("/qr/<int:product_id>", type="http", methods=["GET"], auth="public")
    def track_qr_scan(self, product_id=False):
        product = request.env["product.product"].sudo().browse(product_id)

        if not product.exists():
            return request.not_found()

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
                "os": os,
                "browser": browser,
                "country_id": country.id if country else False,
            }
        )

        return request.redirect(product.website_url)
