from odoo import SUPERUSER_ID, Command, api
from odoo.tools import SQL
from odoo.tools.sql import column_exists, table_exists

from odoo.addons.access_management.models.access_rule import is_protected_model

CHATTER_FIELDS = (
    "hide_chatter",
    "hide_send_message",
    "hide_lognote",
    "hide_activity",
    "hide_attachments",
    "hide_followers",
    "hide_search_message",
)


def _fetch_pairs(cr, table, rule_column, value_column):
    if not table_exists(cr, table):
        return {}
    cr.execute(SQL(
        "SELECT %s, %s FROM %s",
        SQL.identifier(rule_column),
        SQL.identifier(value_column),
        SQL.identifier(table),
    ))
    pairs = {}
    for rule_id, value_id in cr.fetchall():
        pairs.setdefault(rule_id, []).append(value_id)
    return pairs


def migrate(cr, version):
    """The settings of a 17.0.1 rule applied to its single model only: move
    them to the per-model lines, as the settings on the rule now apply to all
    the models."""
    if not column_exists(cr, "access_rule", "model_id"):
        return
    env = api.Environment(cr, SUPERUSER_ID, {"active_test": False})

    cr.execute(SQL("SELECT id, model_id FROM access_rule"))
    model_by_rule = dict(cr.fetchall())
    reports_by_rule = _fetch_pairs(
        cr, "ear_hidden_report_rel", "ear_id", "hidden_report_id"
    )
    views_by_rule = _fetch_pairs(
        cr, "access_rule_restricted_views_rel", "access_rule_id", "view_id"
    )

    IrModel = env["ir.model"]
    for rule in env["access.rule"].browse(model_by_rule):
        model = IrModel.browse(model_by_rule[rule.id]).exists()
        vals = {}

        # Reports and views were picked directly, each has its own model
        # The models of the modules loaded after this one are not in the
        # registry yet: look them up in ir.model.
        reports = env["ir.actions.report"].browse(reports_by_rule.get(rule.id, []))
        commands = [
            Command.create({"model_id": model_id, "report_id": report.id})
            for report in reports.exists()
            if (model_id := IrModel._get_id(report.model))
        ]
        if model and rule.hide_all_reports:
            commands.append(Command.create({
                "model_id": model.id,
                "hide_all_reports": True,
            }))
        if commands:
            vals["hidden_report_ids"] = commands

        views = env["ir.ui.view"].browse(views_by_rule.get(rule.id, []))
        commands = [
            Command.create({"model_id": model_id, "view_id": view.id})
            for view in views.exists()
            if (model_id := IrModel._get_id(view.model))
        ]
        if commands:
            vals["restricted_view_ids"] = commands

        if model:
            chatter = {field: True for field in CHATTER_FIELDS if rule[field]}
            if chatter:
                vals["chatter_setting_ids"] = [
                    Command.create({"model_id": model.id, **chatter})
                ]

            # Read-only on the model: refuse writing it, now on the server too.
            # The protected models can't have Model Access lines.
            if rule.readonly and not is_protected_model(model.model):
                lines = rule.model_access_ids.filtered(
                    lambda line: line.model_id == model
                )
                if lines:
                    lines.write({
                        "perm_write": False,
                        "perm_create": False,
                        "perm_unlink": False,
                    })
                else:
                    vals["model_access_ids"] = [Command.create({
                        "name": model.name,
                        "model_id": model.id,
                        "perm_read": True,
                        "perm_write": False,
                        "perm_create": False,
                        "perm_unlink": False,
                    })]

        # These settings now apply to every model. Import, export and debug
        # mode stay restricted: they have no per-model setting, and keeping
        # them is safer than lifting them. Without a model, the rule never
        # applied them.
        vals.update(dict.fromkeys(("readonly", "hide_all_reports", *CHATTER_FIELDS), False))
        if not model:
            vals.update(dict.fromkeys(
                ("restrict_import_records", "restrict_export", "restrict_debug_mode"),
                False,
            ))
        rule.write(vals)
