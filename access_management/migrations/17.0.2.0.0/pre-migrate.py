from odoo.tools import SQL
from odoo.tools.sql import column_exists, table_exists


def migrate(cr, version):
    # The rules of 17.0.1 targeted a single model (access_rule.model_id): the
    # lines now carry their own model, filled from their rule.
    if not column_exists(cr, "access_rule", "model_id"):
        return

    if table_exists(cr, "field_access"):
        if not column_exists(cr, "field_access", "model_id"):
            cr.execute(SQL("ALTER TABLE field_access ADD COLUMN model_id int4"))
        cr.execute(SQL("""
            UPDATE field_access line
               SET model_id = rule.model_id
              FROM access_rule rule
             WHERE rule.id = line.rule_id
               AND line.model_id IS NULL
        """))
        # Lines without a model or field never applied
        cr.execute(SQL("""
            DELETE FROM field_access
             WHERE model_id IS NULL OR field_id IS NULL OR rule_id IS NULL
        """))

    if table_exists(cr, "access_hide_view_node"):
        cr.execute(SQL("""
            UPDATE access_hide_view_node line
               SET model_id = rule.model_id
              FROM access_rule rule
             WHERE rule.id = COALESCE(
                       line.access_rule_id,
                       line.access_rule_btn_id,
                       line.access_rule_page_id
                   )
               AND line.model_id IS NULL
        """))
        cr.execute(SQL("DELETE FROM access_hide_view_node WHERE model_id IS NULL"))
