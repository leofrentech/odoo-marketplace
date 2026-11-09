from odoo.tools import SQL
from odoo.tools.sql import table_exists

# Odoo 20 replaces ir.model.access and ir.rule with ir.access, declared in
# security/ir.access.csv. The Odoo 19 records of the module, whether the
# upgrade kept them or converted them to accesses, are removed so that only
# the new accesses apply.
LEGACY_SECURITY_XMLIDS = (
    "access_product_template_watermark",
)
MODEL_TABLES = {
    "ir.model.access": "ir_model_access",
    "ir.rule": "ir_rule",
    "ir.access": "ir_access",
}


def migrate(cr, version):
    cr.execute(SQL(
        """
        SELECT id, model, res_id
          FROM ir_model_data
         WHERE module = %s
           AND name IN %s
        """,
        "lf_product_watermark_overlay",
        LEGACY_SECURITY_XMLIDS,
    ))
    for imd_id, model, res_id in cr.fetchall():
        table = MODEL_TABLES.get(model)
        if table and table_exists(cr, table):
            cr.execute(SQL("DELETE FROM %s WHERE id = %s", SQL.identifier(table), res_id))
        cr.execute(SQL("DELETE FROM ir_model_data WHERE id = %s", imd_id))
