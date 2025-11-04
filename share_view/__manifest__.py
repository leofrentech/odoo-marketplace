{
    "name": "Share View",
    "version": "0.0.1",
    "summary": "Share the link of the current view.",
    "category": "",
    "description": """
    - Share view with simple copy link
    """,
    "author": "Leofren Technologies",
    "website": "https://leofren.com",
    "depends": ["web"],
    "data": [
        "security/ir.model.access.csv",
        "views/templates.xml",
        "views/shared_view_state_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "share_view/static/src/js/share_view.js",
            "share_view/static/src/js/share_view.xml",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
