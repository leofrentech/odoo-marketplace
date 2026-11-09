from odoo.tools import SQL
from odoo.tools.sql import table_exists

STASH_TABLE = "access_management_model_access_v19"


def migrate(cr, version):
    if not table_exists(cr, STASH_TABLE):
        return
    cr.execute(SQL(
        """
        INSERT INTO access_rule_model_access (
            access_rule_id, name, model_id, domain_force, perm_read, perm_write,
            perm_create, perm_unlink, ignore_standard_rules, create_uid,
            create_date, write_uid, write_date
        )
             SELECT stash.access_rule_id, COALESCE(stash.name, model.model),
                    stash.model_id, stash.domain_force,
                    COALESCE(stash.perm_read, false), COALESCE(stash.perm_write, false),
                    COALESCE(stash.perm_create, false), COALESCE(stash.perm_unlink, false),
                    COALESCE(stash.ignore_standard_rules, false), 1, now() AT TIME ZONE 'UTC',
                    1, now() AT TIME ZONE 'UTC'
               FROM %s stash
               JOIN access_rule rule ON rule.id = stash.access_rule_id
               JOIN ir_model model ON model.id = stash.model_id
        """,
        SQL.identifier(STASH_TABLE),
    ))
    cr.execute(SQL("DROP TABLE %s", SQL.identifier(STASH_TABLE)))
