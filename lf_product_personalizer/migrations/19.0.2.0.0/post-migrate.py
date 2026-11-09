import json

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Designs saved by 1.0 have no 'customized' flag: compute it from their data."""
    cr.execute("SELECT id, personalized_json FROM sale_order_line_personalization")
    customized_ids = []
    for rec_id, data in cr.fetchall():
        try:
            objects = json.loads(data or "{}").get("objects") or []
        except (ValueError, AttributeError):
            objects = []
        if objects:
            customized_ids.append(rec_id)
    if customized_ids:
        cr.execute(
            "UPDATE sale_order_line_personalization SET is_customized = TRUE WHERE id = ANY(%s)",
            [customized_ids],
        )
    cr.execute(
        "UPDATE sale_order_line SET has_personalization = TRUE WHERE id IN "
        "(SELECT sale_order_line_id FROM sale_order_line_personalization)",
    )
    # Stored fields computed before this script ran must see the new flags.
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.invalidate_all()
    orders = env["sale.order.line.personalization"].search([]).order_id
    orders._compute_artwork_state()
    orders.flush_recordset(["artwork_state"])
