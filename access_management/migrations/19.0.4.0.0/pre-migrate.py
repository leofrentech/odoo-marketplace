from odoo.tools import SQL
from odoo.tools.sql import column_exists, table_exists

# Models and fields renamed to follow the naming guidelines. Renaming their
# tables, columns and metadata before the update keeps the existing data:
# otherwise the update would drop the old ones as removed.
RENAMED_MODELS = [
    ("field.access", "access.rule.field"),
    ("access.hide.view.node", "access.rule.hidden.node"),
    ("view.node", "access.view.node"),
]
RENAMED_FIELDS = [
    ("ir.rule", "rule_id", "access_rule_id"),
    ("access.rule", "record_rule_ids", "model_access_ids"),
    ("access.rule", "hide_report_btn", "hide_all_reports"),
    ("access.rule.hidden.report", "hide_report_btn", "hide_all_reports"),
    ("access.rule.hidden.node", "access_rule_id", "link_rule_id"),
    ("access.rule.hidden.node", "access_rule_btn_id", "button_rule_id"),
    ("access.rule.hidden.node", "access_rule_page_id", "page_rule_id"),
    ("access.view.node", "node_option", "node_type"),
    ("access.view.node", "node_string", "label"),
]


def _rename_xmlids(cr, old_prefix, new_prefix):
    cr.execute(SQL(
        """
        UPDATE ir_model_data
           SET name = %s || substr(name, %s)
         WHERE module = 'access_management'
           AND starts_with(name, %s)
        """,
        new_prefix,
        len(old_prefix) + 1,
        old_prefix,
    ))


def _rename_model(cr, old, new):
    old_table, new_table = old.replace(".", "_"), new.replace(".", "_")
    if table_exists(cr, old_table) and not table_exists(cr, new_table):
        cr.execute(SQL(
            "ALTER TABLE %s RENAME TO %s",
            SQL.identifier(old_table),
            SQL.identifier(new_table),
        ))
        cr.execute(SQL(
            "ALTER SEQUENCE IF EXISTS %s RENAME TO %s",
            SQL.identifier(f"{old_table}_id_seq"),
            SQL.identifier(f"{new_table}_id_seq"),
        ))
    cr.execute(SQL("UPDATE ir_model SET model = %s WHERE model = %s", new, old))
    cr.execute(SQL("UPDATE ir_model_fields SET model = %s WHERE model = %s", new, old))
    cr.execute(SQL(
        "UPDATE ir_model_fields SET relation = %s WHERE relation = %s", new, old
    ))
    cr.execute(SQL("UPDATE ir_model_data SET model = %s WHERE model = %s", new, old))
    _rename_xmlids(cr, f"model_{old_table}", f"model_{new_table}")
    _rename_xmlids(cr, f"field_{old_table}__", f"field_{new_table}__")
    _rename_xmlids(cr, f"selection__{old_table}__", f"selection__{new_table}__")


def _rename_field(cr, model, old, new):
    table = model.replace(".", "_")
    if column_exists(cr, table, old) and not column_exists(cr, table, new):
        cr.execute(SQL(
            "ALTER TABLE %s RENAME COLUMN %s TO %s",
            SQL.identifier(table),
            SQL.identifier(old),
            SQL.identifier(new),
        ))
    cr.execute(SQL(
        "UPDATE ir_model_fields SET name = %s WHERE model = %s AND name = %s",
        new,
        model,
        old,
    ))
    # The one2many fields of the access rules using it as inverse
    cr.execute(SQL(
        """
        UPDATE ir_model_fields
           SET relation_field = %s
         WHERE relation = %s
           AND relation_field = %s
           AND model = 'access.rule'
        """,
        new,
        model,
        old,
    ))
    _rename_xmlids(cr, f"field_{table}__{old}", f"field_{table}__{new}")
    _rename_xmlids(cr, f"selection__{table}__{old}__", f"selection__{table}__{new}__")


def migrate(cr, version):
    for old, new in RENAMED_MODELS:
        _rename_model(cr, old, new)
    for model, old, new in RENAMED_FIELDS:
        _rename_field(cr, model, old, new)
