from odoo.tools import SQL
from odoo.tools.sql import table_exists

# Odoo 20 replaces ir.model.access and ir.rule with ir.access, declared in
# security/ir.access.csv. The Odoo 19 records of the module, whether the
# upgrade kept them or converted them to accesses, are removed so that only
# the new accesses apply. The record rules were noupdate: they would stay.
LEGACY_SECURITY_XMLIDS = (
    "access_email_tracker_recipient_user",
    "access_email_tracker_recipient_system",
    "email_tracker_recipient_rule_user",
    "email_tracker_recipient_rule_system",
)
MODEL_TABLES = {
    "ir.model.access": "ir_model_access",
    "ir.rule": "ir_rule",
    "ir.access": "ir_access",
}


def migrate(cr, version):
    # Rename the legacy, non-namespaced settings key to the module namespace
    cr.execute(SQL(
        """
        UPDATE ir_config_parameter
           SET key = 'email_tracker.open_notification'
         WHERE key = 'mail.open.notification'
           AND NOT EXISTS (
               SELECT 1 FROM ir_config_parameter
                WHERE key = 'email_tracker.open_notification'
           )
        """
    ))

    cr.execute(SQL(
        """
        SELECT id, model, res_id
          FROM ir_model_data
         WHERE module = 'email_tracker'
           AND name IN %s
        """,
        LEGACY_SECURITY_XMLIDS,
    ))
    for imd_id, model, res_id in cr.fetchall():
        table = MODEL_TABLES.get(model)
        if table and table_exists(cr, table):
            cr.execute(SQL("DELETE FROM %s WHERE id = %s", SQL.identifier(table), res_id))
        cr.execute(SQL("DELETE FROM ir_model_data WHERE id = %s", imd_id))
