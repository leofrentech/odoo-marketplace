from odoo.tools import SQL


def uninstall_hook(env):
    # Without the module, the Model Access lines would remain as global
    # record rules restricting every user
    env["ir.rule"].search([("rule_id", "!=", False)]).unlink()

    # Restore the constraint of base, relaxed for the Model Access lines
    env.cr.execute(SQL("""
        ALTER TABLE ir_rule DROP CONSTRAINT IF EXISTS ir_rule_no_access_rights;
        ALTER TABLE ir_rule ADD CONSTRAINT ir_rule_no_access_rights
            CHECK (perm_read OR perm_write OR perm_create OR perm_unlink);
    """))
