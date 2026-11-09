from odoo.tools import SQL
from odoo.tools.sql import column_exists, table_exists

# Odoo 20 replaces the record rules (ir.rule) with the accesses (ir.access).
# The Model Access lines were record rules linked to an access rule: they now
# have their own model. Keep them aside until its table is created, see the
# post-migration.
STASH_TABLE = "access_management_model_access_v19"


def migrate(cr, version):
    cr.execute(SQL(
        """
        CREATE TABLE IF NOT EXISTS %s (
            access_rule_id integer NOT NULL,
            name varchar,
            model_id integer NOT NULL,
            domain_force text,
            perm_read boolean,
            perm_write boolean,
            perm_create boolean,
            perm_unlink boolean,
            ignore_standard_rules boolean
        )
        """,
        SQL.identifier(STASH_TABLE),
    ))

    # The record rules are still there
    if table_exists(cr, "ir_rule") and column_exists(cr, "ir_rule", "access_rule_id"):
        ignore = (
            SQL("ignore_standard_rules")
            if column_exists(cr, "ir_rule", "ignore_standard_rules")
            else SQL("false")
        )
        cr.execute(SQL(
            """
            INSERT INTO %s
                 SELECT access_rule_id, name, model_id, domain_force, perm_read,
                        perm_write, perm_create, perm_unlink, %s
                   FROM ir_rule
                  WHERE access_rule_id IS NOT NULL
                    AND active
            """,
            SQL.identifier(STASH_TABLE),
            ignore,
        ))
        # Without the module's meaning, they would restrict every user
        cr.execute(SQL("DELETE FROM ir_rule WHERE access_rule_id IS NOT NULL"))

    # The record rules were converted to accesses with their columns: as
    # accesses without a group, they would restrict every user
    if column_exists(cr, "ir_access", "access_rule_id"):
        ignore = (
            SQL("ignore_standard_rules")
            if column_exists(cr, "ir_access", "ignore_standard_rules")
            else SQL("false")
        )
        cr.execute(SQL(
            """
            INSERT INTO %s
                 SELECT access_rule_id, name, model_id, domain,
                        position('r' in operation) > 0,
                        position('u' in operation) > 0,
                        position('c' in operation) > 0,
                        position('d' in operation) > 0,
                        %s
                   FROM ir_access
                  WHERE access_rule_id IS NOT NULL
                    AND active
            """,
            SQL.identifier(STASH_TABLE),
            ignore,
        ))
        cr.execute(SQL("DELETE FROM ir_access WHERE access_rule_id IS NOT NULL"))
