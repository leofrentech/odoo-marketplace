from odoo.tools import SQL
from odoo.tools.sql import table_exists

# Odoo 20 replaces ir.model.access with ir.access, declared in
# security/ir.access.csv under the same xml id. The Odoo 19 record of the
# module, whether the upgrade kept it or converted it to an access, is
# removed so that the new access loads cleanly in its place.
LEGACY_SECURITY_XMLIDS = ("access_product_qr_visit",)
MODEL_TABLES = {
    "ir.model.access": "ir_model_access",
    "ir.access": "ir_access",
}


def migrate(cr, version):
    cr.execute(SQL(
        """
        SELECT id, model, res_id
          FROM ir_model_data
         WHERE module = 'product_qr_track'
           AND name IN %s
        """,
        LEGACY_SECURITY_XMLIDS,
    ))
    for imd_id, model, res_id in cr.fetchall():
        table = MODEL_TABLES.get(model)
        if table and table_exists(cr, table):
            cr.execute(SQL("DELETE FROM %s WHERE id = %s", SQL.identifier(table), res_id))
        cr.execute(SQL("DELETE FROM ir_model_data WHERE id = %s", imd_id))
