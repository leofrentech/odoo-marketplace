{
    "name": "Access Management",
    "version": "19.0.4.0.1",
    "summary": "Per-user rules for model access, menus, views, fields, buttons, "
    "reports, chatter, import, export and debug mode",
    "category": "Tools",
    "author": "Leofren Technologies",
    "maintainer": "Fenil Moradiya",
    "website": "https://leofren.com",
    "description": """
Easy Access Rules: choose, per user and company, which operations users may do
on each model (enforced on the server) and which menus, views, fields, buttons,
pages, links, reports and chatter parts they see.
""",
    "depends": ["base", "mail"],
    "data": [
        "security/access_management_groups.xml",
        "security/ir.model.access.csv",
        "security/access_rule_security.xml",
        "views/access_rule_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "access_management/static/src/chatter/*",
            "access_management/static/src/view_service.js",
            "access_management/static/src/views/*",
        ],
        "web.assets_tests": [
            "access_management/static/tests/tours/*",
        ],
    },
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": True,
    "auto_install": False,
    "images": ["static/description/icon.png"],
    "license": "LGPL-3",
}
