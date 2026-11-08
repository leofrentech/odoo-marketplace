from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


class PersonalizerPortal(CustomerPortal):

    def _lf_designs_domain(self):
        return [("partner_id", "=", request.env.user.partner_id.id)]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "design_count" in counters:
            values["design_count"] = request.env["product.design.saved"].sudo().search_count(
                self._lf_designs_domain()
            )
        return values

    @http.route("/my/designs", type="http", auth="user", website=True)
    def portal_my_designs(self, **kw):
        designs = request.env["product.design.saved"].sudo().search(self._lf_designs_domain())
        values = self._prepare_portal_layout_values()
        values.update({"designs": designs, "page_name": "designs"})
        return request.render("lf_product_personalizer.portal_my_designs", values)

    @http.route(
        "/my/designs/<int:design_id>/delete",
        type="http", auth="user", website=True, methods=["POST"],
    )
    def portal_delete_design(self, design_id, **kw):
        design = request.env["product.design.saved"].sudo().search(
            self._lf_designs_domain() + [("id", "=", design_id)]
        )
        if not design:
            raise NotFound()
        design.unlink()
        return request.redirect("/my/designs")
