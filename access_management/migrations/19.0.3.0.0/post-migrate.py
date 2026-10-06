from odoo.tools import SQL
from odoo.tools.sql import column_exists


def migrate(cr, version):
    # Access rules moved from one company to several: keep the company of the
    # existing rules (the old column is dropped once the update is done)
    if not column_exists(cr, "access_rule", "company_id"):
        return
    cr.execute(SQL("""
        INSERT INTO access_rule_company_rel (rule_id, company_id)
             SELECT id, company_id
               FROM access_rule
              WHERE company_id IS NOT NULL
        ON CONFLICT DO NOTHING
    """))
