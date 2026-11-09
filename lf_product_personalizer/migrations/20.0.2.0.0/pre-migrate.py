from odoo.tools import SQL
from odoo.tools.sql import table_exists

# Odoo 20 replaces ir.model.access and ir.rule with ir.access, declared in
# security/ir.access.csv. The Odoo 19 records of the module, whether the
# upgrade kept them or converted them to accesses, are removed so that only
# the new accesses apply.
LEGACY_SECURITY_XMLIDS = (
    "access_product_design_config_user",
    "access_product_design_config_manager",
    "access_product_design_config_designer",
    "access_product_design_set_user",
    "access_product_design_set_manager",
    "access_product_design_set_designer",
    "access_product_design_font_public",
    "access_product_design_font_portal",
    "access_product_design_font_user",
    "access_product_design_font_manager",
    "access_product_design_font_designer",
    "access_product_design_clipart_public",
    "access_product_design_clipart_portal",
    "access_product_design_clipart_user",
    "access_product_design_clipart_manager",
    "access_product_design_clipart_designer",
    "access_product_design_clipart_category_public",
    "access_product_design_clipart_category_portal",
    "access_product_design_clipart_category_user",
    "access_product_design_clipart_category_manager",
    "access_product_design_clipart_category_designer",
    "access_product_design_preset_public",
    "access_product_design_preset_portal",
    "access_product_design_preset_user",
    "access_product_design_preset_manager",
    "access_product_design_preset_designer",
    "access_product_design_saved_salesman",
    "access_product_design_saved_manager",
    "access_sale_order_line_personalization_salesman",
    "personalization_rule_personal",
    "personalization_rule_all",
    "personalization_rule_company",
    "design_set_rule_company",
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
        "lf_product_personalizer",
        LEGACY_SECURITY_XMLIDS,
    ))
    for imd_id, model, res_id in cr.fetchall():
        table = MODEL_TABLES.get(model)
        if table and table_exists(cr, table):
            cr.execute(SQL("DELETE FROM %s WHERE id = %s", SQL.identifier(table), res_id))
        cr.execute(SQL("DELETE FROM ir_model_data WHERE id = %s", imd_id))
